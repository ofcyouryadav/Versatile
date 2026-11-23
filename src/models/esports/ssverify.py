from typing import Tuple

import imagehash
from pydantic import BaseModel, HttpUrl
from tortoise import fields

import config
from constants import SSType
from core import Context
from models import BaseDbModel
from models.helpers import *
from utils import emote


# ── Tuning constants (adjust without touching logic) ──────────────────────────
DHASH_DUPLICATE_THRESHOLD = 5          # lower  → stricter duplicate detection (was 7)
MIN_OCR_TEXT_LENGTH       = 8          # screenshots with fewer chars are rejected
# ─────────────────────────────────────────────────────────────────────────────


class ImageResponse(BaseModel):
    url: HttpUrl
    dhash: str
    phash: str
    text: str

    @property
    def lower_text(self) -> str:
        return self.text.lower().replace(" ", "").replace("\n", "")

    @property
    def spaced_text(self) -> str:
        """Lowercased but keeps single spaces — useful for whole-word checks."""
        return " ".join(self.text.lower().split())

    def contains_word(self, word: str) -> bool:
        """
        True if *word* appears as a standalone token inside the OCR text.
        Avoids "subscribe" matching inside "unsubscribe".
        """
        import re
        return bool(re.search(rf"\b{re.escape(word.lower())}\b", self.spaced_text))

    def contains_any(self, words: list[str]) -> bool:
        return any(self.contains_word(w) for w in words)

    @property
    def has_enough_text(self) -> bool:
        """Guard against blank / unreadable images."""
        return len(self.text.strip()) >= MIN_OCR_TEXT_LENGTH


class SSData(BaseDbModel):
    class Meta:
        table = "ss_data"

    id = fields.IntField(pk=True)
    author_id = fields.BigIntField()
    channel_id = fields.BigIntField()
    message_id = fields.BigIntField()
    dhash = fields.CharField(max_length=1024, null=True)
    phash = fields.CharField(max_length=1024, null=True)
    submitted_at = fields.DatetimeField(auto_now=True)

    @property
    def author(self):
        return self.bot.get_user(self.author_id)

    @property
    def jump_url(self):
        return "https://discord.com/channels/{}/" + f"{self.channel_id}/{self.message_id}"


class SSVerify(BaseDbModel):
    class Meta:
        table = "ss_info"

    id = fields.IntField(pk=True)
    channel_id = fields.BigIntField(index=True)
    guild_id = fields.BigIntField()
    role_id = fields.BigIntField()
    required_ss = fields.IntField(default=4)
    channel_name = fields.CharField(max_length=50)
    channel_link = fields.CharField(max_length=150, default=config.SERVER_LINK)

    keywords = ArrayField(fields.CharField(max_length=50), default=list)
    allow_same = fields.BooleanField(default=False)

    ss_type = fields.CharEnumField(SSType)

    success_message = fields.CharField(null=True, max_length=500)

    data: fields.ManyToManyRelation["SSData"] = fields.ManyToManyField("models.SSData", index=True)

    # ── Internal helpers ──────────────────────────────────────────────────────

    @property
    def _guild(self):
        return self.bot.get_guild(self.guild_id)

    @property
    def channel(self):
        return self.bot.get_channel(self.channel_id)

    @property
    def role(self):
        if g := self._guild:
            return g.get_role(self.role_id)

    def emoji(self, _bool: bool = False) -> str:
        return emote.check if _bool else "⚠️"

    def __str__(self) -> str:
        _f = self.ss_type.value.title()
        if self.ss_type == SSType.custom:
            _f += f"(`{self.keywords[0]}`)"
        return f"{getattr(self.channel, 'mention', 'deleted-channel')} - {_f}"

    @property
    def _name_token(self) -> str:
        """Channel name stripped of spaces/case for OCR matching."""
        return self.channel_name.lower().replace(" ", "")

    @property
    def filtered_keywords(self) -> list[str]:
        _l = [self._name_token]
        for kw in self.keywords:
            _l.append(kw.lower().replace(" ", ""))
        return _l

    # ── DB helpers ────────────────────────────────────────────────────────────

    async def is_user_verified(self, user_id: int) -> bool:
        return await self.data.filter(author_id=user_id).count() >= self.required_ss

    async def required_by_user(self, user_id: int) -> int:
        diff = self.required_ss - await self.data.filter(author_id=user_id).count()
        return max(0, diff)

    async def full_delete(self):
        self.bot.cache.ssverify_channels.discard(self.channel_id)
        data = await self.data.all()
        await SSData.filter(pk__in=[d.id for d in data]).delete()
        await self.delete()

    async def _add_to_data(self, ctx: Context, img: ImageResponse):
        data = await SSData.create(
            author_id=ctx.author.id,
            channel_id=ctx.channel.id,
            message_id=ctx.message.id,
            dhash=img.dhash,
            phash=img.phash,
        )
        await self.data.add(data)

    # ── Duplicate detection ───────────────────────────────────────────────────

    async def _match_for_duplicate(
        self, dhash: str, phash: str, author_id: int
    ) -> Tuple[bool, str]:
        """
        Two-stage check:
          1. Perceptual hash distance against this user's previous submissions
             (catches cropped / slightly edited re-sends).
          2. Exact hash pair match guild-wide
             (catches the same screenshot submitted by different users).
        Threshold lowered to 5 (was 7) for stricter matching.
        """
        incoming_dhash = imagehash.hex_to_hash(dhash)
        incoming_phash = imagehash.hex_to_hash(phash)

        # Stage 1 – per-user perceptual similarity
        async for record in self.data.filter(author_id=author_id).order_by("submitted_at"):
            d_dist = incoming_dhash - imagehash.hex_to_hash(record.dhash)
            p_dist = incoming_phash - imagehash.hex_to_hash(record.phash)

            # Require BOTH distances to be small — reduces false positives
            if d_dist <= DHASH_DUPLICATE_THRESHOLD and p_dist <= DHASH_DUPLICATE_THRESHOLD:
                return (
                    True,
                    f"{self.emoji(False)} | You've already submitted this screenshot "
                    f"[here]({record.jump_url.format(self.guild_id)}).\n",
                )

        # Stage 2 – exact pair match across all users
        if r := await self.data.filter(dhash=dhash, phash=phash).first():
            return (
                True,
                f"{self.emoji(False)} | <@{r.author_id}> already submitted the "
                f"[same screenshot]({r.jump_url.format(self.guild_id)}).\n",
            )

        return False, False

    # ── Platform verifiers ────────────────────────────────────────────────────

    def _ocr_guard(self, image: ImageResponse) -> str | None:
        """
        Return an error string if the image has too little text to be trustworthy,
        otherwise return None (all clear).
        """
        if not image.has_enough_text:
            return (
                f"{self.emoji()} | Could not read the screenshot clearly. "
                "Please send a higher-quality image.\n"
            )
        return None

    async def verify_yt(self, ctx: Context, image: ImageResponse) -> str:
        if err := self._ocr_guard(image):
            return err

        # Must contain at least one YouTube-specific marker
        if not image.contains_any(["subscribe", "subscribed", "subscribers", "videos"]):
            return f"{self.emoji()} | This is not a valid YouTube screenshot.\n"

        # Channel name must appear
        if self._name_token not in image.lower_text:
            return (
                f"{self.emoji()} | Screenshot must belong to "
                f"[`{self.channel_name}`]({self.channel_link}) channel.\n"
            )

        # Important:
        # Do NOT verify unless exact word "subscribed" is found.
        # "subscribers" only proves it is a channel page, not that user subscribed.
        has_subscribed = image.contains_word("subscribed")
        has_subscribe = image.contains_word("subscribe")
        has_unsubscribed = image.contains_word("unsubscribed")

        # If screenshot shows Subscribe / Unsubscribed, user is not subscribed
        if has_subscribe or has_unsubscribed:
            return (
                f"{self.emoji()} | You must subscribe to "
                f"[`{self.channel_name}`]({self.channel_link}) first.\n"
            )

        # Strict rule: must show Subscribed button
        if not has_subscribed:
            return (
                f"{self.emoji()} | I could not detect that you are subscribed to "
                f"[`{self.channel_name}`]({self.channel_link}). Please subscribe first and send a clear screenshot.\n"
            )

        await self._add_to_data(ctx, image)
        return f"{self.emoji(True)} | Verified successfully.\n"
        

    async def verify_insta(self, ctx: Context, image: ImageResponse) -> str:
        if err := self._ocr_guard(image):
            return err

        # Basic Instagram profile markers
        if not image.contains_any(["followers", "following", "posts", "follow"]):
            return f"{self.emoji()} | This is not a valid Instagram screenshot.\n"

        # Page / username must appear
        if self._name_token not in image.lower_text:
            return (
                f"{self.emoji()} | Screenshot must belong to "
                f"[`{self.channel_name}`]({self.channel_link}) page.\n"
            )

        import re

        def has_word(text: str, word: str) -> bool:
            return bool(
                re.search(
                    rf"(?<![a-z0-9]){re.escape(word.lower())}(?![a-z0-9])",
                    text.lower()
                )
            )

        # Keep OCR line structure.
        # This helps separate:
        # "183 posts 57.6K followers 284 following"
        # from:
        # "Following Message"
        lines = [
            " ".join(line.lower().split())
            for line in image.text.splitlines()
            if line.strip()
        ]

        has_follow_button = any(has_word(line, "follow") for line in lines)
        has_requested_button = any(has_word(line, "requested") for line in lines)

        # A real followed Instagram profile usually has a button row like:
        # "Following Message"
        has_following_button = any(
            has_word(line, "following")
            and not has_word(line, "followers")
            and not has_word(line, "posts")
            for line in lines
        )

        # If screenshot shows Follow / Requested, user has not followed
        if has_follow_button or has_requested_button:
            return (
                f"{self.emoji()} | You must follow "
                f"[`{self.channel_name}`]({self.channel_link}) first.\n"
            )

        # Strict rule: do not verify unless we detect the actual Following button
        if not has_following_button:
            return (
                f"{self.emoji()} | I could not detect that you are following "
                f"[`{self.channel_name}`]({self.channel_link}). Please follow first and send a clear screenshot.\n"
            )

        await self._add_to_data(ctx, image)
        return f"{self.emoji(True)} | Verified successfully.\n"

    async def verify_loco(self, ctx: Context, image: ImageResponse) -> str:
        if err := self._ocr_guard(image):
            return err

        if self._name_token not in image.lower_text:
            return (
                f"{self.emoji()} | Screenshot must belong to "
                f"[`{self.channel_name}`]({self.channel_link}) channel.\n"
            )

        if image.contains_word("follow") and not image.contains_word("following"):
            return (
                f"{self.emoji()} | You must follow "
                f"[`{self.channel_name}`]({self.channel_link}) first.\n"
            )

        await self._add_to_data(ctx, image)
        return f"{self.emoji(True)} | Verified successfully.\n"

    async def verify_rooter(self, ctx: Context, image: ImageResponse) -> str:
        if err := self._ocr_guard(image):
            return err

        if self._name_token not in image.lower_text:
            return (
                f"{self.emoji()} | Screenshot must belong to "
                f"[`{self.channel_name}`]({self.channel_link}) channel.\n"
            )

        if image.contains_word("follow") and not image.contains_word("following"):
            return (
                f"{self.emoji()} | You must follow "
                f"[`{self.channel_name}`]({self.channel_link}) first.\n"
            )

        await self._add_to_data(ctx, image)
        return f"{self.emoji(True)} | Verified successfully.\n"

    async def verify_custom(self, ctx: Context, image: ImageResponse) -> str:
        if err := self._ocr_guard(image):
            return err

        if not any(kw in image.lower_text for kw in self.filtered_keywords):
            return f"{self.emoji()} | This is not a valid {self.keywords[0]} screenshot.\n"

        await self._add_to_data(ctx, image)
        return f"{self.emoji(True)} | Verified successfully.\n"