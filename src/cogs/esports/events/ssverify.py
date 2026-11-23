from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, List

import discord
from PIL import Image
import pytesseract
from io import BytesIO
import imagehash

from constants import SSType

if TYPE_CHECKING:
    from core import Quotient

from collections import defaultdict
from contextlib import suppress

import humanize

from core import Cog, Context, QuotientRatelimiter
from models import ImageResponse, SSVerify
from utils import emote, plural


class MemberLimits(defaultdict):
    def __missing__(self, key):
        r = self[key] = QuotientRatelimiter(1, 7)
        return r


class GuildLimits(defaultdict):
    def __missing__(self, key):
        r = self[key] = QuotientRatelimiter(10, 60)
        return r


class Ssverification(Cog):
    def __init__(self, bot: Quotient):
        self.bot = bot
        self.__mratelimiter = MemberLimits(QuotientRatelimiter)   # 1 batch per 7s per member
        self.__gratelimiter = GuildLimits(QuotientRatelimiter)    # 10 batches per min per guild

        # ── One lock per channel so guilds don't block each other ──────────
        self.__channel_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    # ── Rate-limit helper ─────────────────────────────────────────────────────

    async def __check_ratelimit(self, message: discord.Message) -> bool:
        if retry := self.__mratelimiter[message.author].is_ratelimited(message.author):
            await message.reply(
                embed=discord.Embed(
                    color=discord.Color.red(),
                    description=f"**You are too fast. Kindly resend after `{retry:.2f}` seconds.**",
                )
            )
            return False

        if retry := self.__gratelimiter[message.guild].is_ratelimited(message.guild):
            await message.reply(
                embed=discord.Embed(
                    color=discord.Color.red(),
                    description=(
                        "**Many users are submitting screenshots right now. "
                        f"Kindly retry after `{retry:.2f}` seconds.**"
                    ),
                )
            )
            return False

        return True

    # ── Image processing ──────────────────────────────────────────────────────

    def _process_image(self, image_data: bytes, attachment_url: str) -> ImageResponse | None:
        """CPU-bound work — runs in a thread executor."""
        try:
            image = Image.open(BytesIO(image_data))

            # ── Smart resize for OCR quality ───────────────────────────────
            # Tesseract needs >= ~1200px wide to reliably read UI text.
            # If the image is a Discord embed thumbnail it may be much smaller,
            # so we upscale. Very large originals are capped to avoid OOM.
            MIN_WIDTH = 1200
            MAX_WIDTH = 2400
            MAX_HEIGHT = 3200
            MAX_PIXELS = MAX_WIDTH * MAX_HEIGHT
            MAX_SOURCE_PIXELS = 20_000_000

            if image.width * image.height > MAX_SOURCE_PIXELS:
                print(
                    f"[SSVerify] Skipping oversized image "
                    f"({image.width}x{image.height}): {attachment_url}"
                )
                return None

            target_width = image.width
            if image.width < MIN_WIDTH:
                target_width = MIN_WIDTH
            elif image.width > MAX_WIDTH:
                target_width = MAX_WIDTH

            ratio = target_width / image.width
            target_height = max(1, int(image.height * ratio))

            if target_width * target_height > MAX_PIXELS or target_height > MAX_HEIGHT:
                ratio *= min(
                    MAX_HEIGHT / target_height,
                    (MAX_PIXELS / (target_width * target_height)) ** 0.5,
                )
                target_width = max(1, int(image.width * ratio))
                target_height = max(1, int(image.height * ratio))

            if (target_width, target_height) != image.size:
                image = image.resize(
                    (target_width, target_height),
                    Image.Resampling.LANCZOS,
                )

            if image.mode != "RGB":
                image = image.convert("RGB")

            # PSM 3 = fully automatic page segmentation (best for UI screenshots)
            # OEM 3 = default engine (LSTM)
            text = pytesseract.image_to_string(
                image, lang="eng", config="--psm 3 --oem 3"
            ).strip()

            return ImageResponse(
                text=text,
                dhash=str(imagehash.dhash(image)),
                phash=str(imagehash.phash(image)),
                url=attachment_url,
            )
        except Exception as exc:
            print(f"[SSVerify] _process_image error ({attachment_url}): {exc}")
            return None

    async def _process_image_async(self, attachment: discord.Attachment) -> ImageResponse | None:
        """Download then offload CPU work to executor."""
        try:
            async with self.bot.session.get(attachment.proxy_url) as resp:
                if resp.status != 200:
                    print(f"[SSVerify] HTTP {resp.status} for {attachment.proxy_url}")
                    return None
                image_data = await resp.read()

            return await self.bot.loop.run_in_executor(
                None, self._process_image, image_data, attachment.proxy_url
            )
        except Exception as exc:
            print(f"[SSVerify] _process_image_async error ({attachment.proxy_url}): {exc}")
            return None

    # ── Main listener ─────────────────────────────────────────────────────────

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if not all((
            message.guild,
            not message.author.bot,
            message.channel.id in self.bot.cache.ssverify_channels,
        )):
            return

        record = await SSVerify.get_or_none(channel_id=message.channel.id)
        if not record:
            self.bot.cache.ssverify_channels.discard(message.channel.id)
            return

        if "tourney-mod" in (role.name.lower() for role in message.author.roles):
            return

        ctx: Context = await self.bot.get_context(message)
        _e = discord.Embed(color=discord.Color.red())

        with suppress(discord.HTTPException):
            if await record.is_user_verified(message.author.id):
                _e.description = "**Your screenshots are already verified, kindly move on to the next step.**"
                return await ctx.reply(embed=_e)

            attachments = self.__valid_attachments(message)
            if not attachments:
                _e.description = "**Kindly send screenshots in `png/jpg/jpeg` format only.**"
                return await ctx.reply(embed=_e)

            if not await self.__check_ratelimit(message):
                return

            if len(attachments) > record.required_ss:
                _e.description = (
                    f"**You only need to send `{record.required_ss}` "
                    f"screenshot(s), but you sent `{len(attachments)}`.**"
                )
                return await ctx.reply(embed=_e)

            _e.color = self.bot.color
            _e.description = (
                f"Processing your {plural(attachments):screenshot|screenshots}… {emote.loading}"
            )
            m: discord.Message = await message.reply(embed=_e)

            start_at = self.bot.current_time

            # ── OCR phase (no lock needed — pure CPU/network) ──────────────
            ocr_results: list[ImageResponse] = []
            for attachment in attachments:
                try:
                    result = await asyncio.wait_for(
                        self._process_image_async(attachment), timeout=25
                    )
                    if result is not None:
                        ocr_results.append(result)
                except asyncio.TimeoutError:
                    print(f"[SSVerify] OCR timeout: {attachment.url}")
                except Exception as exc:
                    print(f"[SSVerify] Error processing {attachment.url}: {exc}")

            complete_at = self.bot.current_time

            if not ocr_results:
                _e.color = discord.Color.red()
                _e.description = (
                    "**Failed to process your screenshots. "
                    "Please send clearer or smaller images and try again.**"
                )
                return await m.edit(embed=_e)

            # ── Verify + write phase (locked per channel) ──────────────────
            # The lock here covers BOTH duplicate-check and DB insert so that
            # two concurrent submissions from the same channel cannot both
            # pass duplicate detection before either is written.
            async with self.__channel_locks[message.channel.id]:
                embed = await self.__verify_screenshots(ctx, record, ocr_results)

            embed.set_footer(text=f"Time taken: {humanize.precisedelta(complete_at - start_at)}")
            embed.set_author(
                name=f"Submitted {await record.data.filter(author_id=ctx.author.id).count()}/{record.required_ss}",
                icon_url=getattr(ctx.author.display_avatar, "url", None),
            )

            with suppress(discord.HTTPException):
                await m.delete()

            await message.reply(embed=embed)

            if await record.is_user_verified(ctx.author.id):
                await message.author.add_roles(discord.Object(id=record.role_id))

                _e.color = self.bot.color
                if record.success_message:
                    _e.title = "Screenshot Verification Complete"
                    _e.url = message.jump_url
                    _e.description = record.success_message
                else:
                    _e.description = (
                        f"{ctx.author.mention} Your screenshots are verified. Move to the next step."
                    )
                await message.reply(embed=_e)

    # ── Verification dispatcher ───────────────────────────────────────────────

    async def __verify_screenshots(
        self, ctx: Context, record: SSVerify, _ocr: list[ImageResponse]
    ) -> discord.Embed:
        _e = discord.Embed(color=self.bot.color, description="")

        for img in _ocr:
            # Duplicate check first (unless allow_same is set)
            if not record.allow_same:
                is_dup, dup_msg = await record._match_for_duplicate(
                    img.dhash, img.phash, ctx.author.id
                )
                if is_dup:
                    _e.description += dup_msg
                    continue

            if record.ss_type == SSType.anyss:
                # Even for "any ss", require the image to have readable text
                if not img.has_enough_text:
                    _e.description += (
                        f"{record.emoji(False)} | Could not read the screenshot clearly. "
                        "Please send a higher-quality image.\n"
                    )
                else:
                    await record._add_to_data(ctx, img)
                    _e.description += f"{record.emoji(True)} | Verified successfully.\n"

            elif record.ss_type == SSType.yt:
                _e.description += await record.verify_yt(ctx, img)

            elif record.ss_type == SSType.insta:
                _e.description += await record.verify_insta(ctx, img)

            elif record.ss_type == SSType.loco:
                _e.description += await record.verify_loco(ctx, img)

            elif record.ss_type == SSType.rooter:
                _e.description += await record.verify_rooter(ctx, img)

            elif record.ss_type == SSType.custom:
                _e.description += await record.verify_custom(ctx, img)

        return _e

    # ── Utilities ─────────────────────────────────────────────────────────────

    def __valid_attachments(self, message: discord.Message) -> list[discord.Attachment]:
        return [
            a for a in message.attachments
            if a.content_type in ("image/png", "image/jpeg", "image/jpg")
            and a.size < 5 * 1024 * 1024
        ]

    # ── Cleanup listeners ─────────────────────────────────────────────────────

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.TextChannel):
        if channel.id in self.bot.cache.ssverify_channels:
            record = await SSVerify.get_or_none(channel_id=channel.id)
            if record:
                await record.full_delete()
            self.__channel_locks.pop(channel.id, None)

    @Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        records = await SSVerify.filter(role_id=role.id)
        for record in records:
            await record.full_delete()
