import asyncio
import io
from ast import literal_eval as leval
from contextlib import suppress
import uuid

from datetime import timedelta
from pathlib import Path
from typing import List, Optional


import discord
import config
import humanize
import datetime
from aiocache import cached
from PIL import Image, ImageDraw, ImageFont
from tortoise import fields, models

import utils
from constants import AutocleanType, Day, EsportsLog, EsportsRole
from core import Context
from models import BaseDbModel
from models.helpers import *
from utils import discord_timestamp, plural, truncate_string


class Scrim(BaseDbModel):
    class Meta:
        table = "sm.scrims"

    id = fields.BigIntField(pk=True, index=True)
    guild_id = fields.BigIntField()
    name = fields.TextField(default="VersatileX-Scrims")
    registration_channel_id = fields.BigIntField(index=True)
    slotlist_channel_id = fields.BigIntField()
    reg_close_auto_clean = fields.BooleanField(default=False)
    
    
    slotlist_message_id = fields.BigIntField(null=True)
    role_id = fields.BigIntField(null=True)
    required_mentions = fields.IntField(default=4)
    start_from = fields.IntField(default=1)
    available_slots = ArrayField(fields.IntField(), default=list)
    total_slots = fields.IntField()
    host_id = fields.BigIntField()
    open_time = fields.DatetimeField()
    opened_at = fields.DatetimeField(null=True)
    closed_at = fields.DatetimeField(null=True)
    drop_location_days = fields.TextField(null=True)  # e.g., "Monday,Tuesday,Wednesday"
    drop = fields.TextField(null=True)  # e.g., "Monday:Erangel,Tuesday:Miramar"
    drop_menu_enabled = fields.BooleanField(default=False)  # New field
    drop_message_id = fields.BigIntField(null=True)  # New field
    # drop_location_days2 = fields.TextField(null=True)  # e.g., "Monday,Tuesday,Wednesday"
    # drop2 = fields.TextField(null=True)  # e.g., "Monday:Erangel,Tuesday:Miramar"
    # drop_menu_enabled2 = fields.BooleanField(default=False)  # New field
    # drop_message_id2 = fields.BigIntField(null=True)  # New field

    autoclean = ArrayField(fields.CharEnumField(AutocleanType), default=lambda: list(AutocleanType))
    autoclean_done = fields.BooleanField(default=False)
    autoclean_time = fields.DatetimeField(null=True)

    autoslotlist = fields.BooleanField(default=True)
    ping_role_id = fields.BigIntField(null=True)
    multiregister = fields.BooleanField(default=False)
    stoggle = fields.BooleanField(default=True)
    open_role_id = fields.BigIntField(null=True)
    autodelete_rejects = fields.BooleanField(default=False)
    reg_close_auto_clean = fields.BooleanField(default=False)
    
    autodelete_extras = fields.BooleanField(default=True)
    teamname_compulsion = fields.BooleanField(default=False)

    time_elapsed = fields.CharField(null=True, max_length=100)
    show_time_elapsed = fields.BooleanField(default=True)

    open_days = ArrayField(fields.CharEnumField(Day), default=lambda: list(Day))
    slotlist_format = fields.JSONField(default=dict)  #!str > jsonb

    no_duplicate_name = fields.BooleanField(default=False)

    open_message = fields.JSONField(default=dict)
    close_message = fields.JSONField(default=dict)
    banlog_channel_id = fields.BigIntField(null=True)

    match_time = fields.DatetimeField(null=True)

    emojis = fields.JSONField(default=dict)  #!new
    cdn = fields.JSONField(default={"status": False, "countdown": 3, "msg": {}})  #!new
    idp_channel = fields.BigIntField(null=True)  #!new

    required_lines = fields.SmallIntField(default=0)
    allow_duplicate_tags = fields.BooleanField(default=True)
    # require_drop_location = fields.BooleanField(default=False)

    assigned_slots: fields.ManyToManyRelation["AssignedSlot"] = fields.ManyToManyField("models.AssignedSlot")
    reserved_slots: fields.ManyToManyRelation["ReservedSlot"] = fields.ManyToManyField("models.ReservedSlot")
    banned_teams: fields.ManyToManyRelation["BannedTeam"] = fields.ManyToManyField("models.BannedTeam")
    slot_reminders: fields.ManyToManyRelation["ScrimsSlotReminder"] = fields.ManyToManyField("models.ScrimsSlotReminder")
    

    def __str__(self):
        return f"{getattr(self.registration_channel,'mention','deleted-channel')} (ID: {self.id})"

    @staticmethod
    def is_ignorable(member: discord.Member) -> bool:
        return "scrims-mod" in (role.name.lower() for role in member.roles)

    @property
    def guild(self) -> Optional[discord.Guild]:
        return self.bot.get_guild(self.guild_id)

    @property
    def role(self):
        if self.guild is not None:
            return self.guild.get_role(self.role_id)

    @property
    def logschan(self):
        if self.guild is not None:
            return discord.utils.get(self.guild.text_channels, name="versatilex-scrims-logs")

    @property
    def modrole(self):
        if self.guild is not None:
            return discord.utils.get(self.guild.roles, name="scrims-mod")

    @property
    def registration_channel(self):
        return self.bot.get_channel(self.registration_channel_id)

    @property
    def banlog_channel(self):
        return self.bot.get_channel(self.banlog_channel_id)

    @property
    def slotlist_channel(self):
        return self.bot.get_channel(self.slotlist_channel_id)

    @property
    def host(self):
        if self.guild is not None:
            return self.guild.get_member(self.host_id)

        return self.bot.get_user(self.host_id)

    @property
    def check_emoji(self):
        return self.emojis.get("tick", "✅")

    @property
    def cross_emoji(self):
        return self.emojis.get("cross", "❌")

    @property
    def available_to_reserve(self):
        """
        gives a range obj of available slots to reserve.
        this isn't true because some slots might be already reserved , we will sort them later
        """
        return range(self.start_from, self.total_slots + self.start_from)

    @property
    def opened(self):
        if self.opened_at is None:
            return False

        if self.closed_at is not None:
            return self.closed_at < self.opened_at

        return True
   

    @property
    def closed(self):
        return not self.opened

    @property
    def ping_role(self):
        if self.guild is not None:
            return self.guild.get_role(self.ping_role_id)

    @property
    def open_role(self):
        if self.guild is not None:
            if self.open_role_id is not None:
                return self.guild.get_role(self.open_role_id)
            return self.guild.default_role

    @property  # what? you think its useless , i know :)
    def toggle(self):
        return self.stoggle

    @property
    def teams_registered(self):  # This should be awaited
        return self.assigned_slots.order_by("num")

    async def reserved_user_ids(self):
        return (i.user_id for i in await self.reserved_slots.all())

    async def banned_user_ids(self):
        return (i.user_id for i in await self.banned_teams.all()) 
    
    

    async def cleaned_slots(self) -> List["AssignedSlot"]:
        slots = await self.assigned_slots.order_by("num")

        _list = []
        for _ in {slot.num for slot in slots}:
            _list.append(next(i for i in slots if i.num == _))

        return _list
    
    

    async def add_tick(self, msg: discord.Message):
        with suppress(discord.HTTPException):
            await msg.add_reaction(self.check_emoji)
            await msg.author.add_roles(self.role)

    @staticmethod
    def default_slotlist_format():
        return discord.Embed(color=config.COLOR, title=f"<<name>> Slotlist", description="```\n<<slots>>\n```").set_footer(
            text=f"Registration took: <<time_taken>>"
        )

    async def create_slotlist(self):
        _slots = await self.cleaned_slots()

        desc = "\n".join(f"Slot {slot.num:02}  ->  {slot.team_name}" for slot in _slots)

        if len(self.slotlist_format) <= 1:
            text = str(self.default_slotlist_format().to_dict())
        else:
            text = str(self.slotlist_format)

        changes = [
            ("<<name>>", self.name),
            ("<<time_taken>>", self.time_elapsed or "N/A"),
            ("<<open_time>>", discord_timestamp(self.open_time)),
        ]

        for _ in changes:
            text = text.replace(*_)

        embed = discord.Embed.from_dict(leval(text))
        if embed.color == None:
            embed.color = self.bot.color

        embed.description = embed.description.replace("<<slots>>", desc)

        return embed, self.slotlist_channel
    
    async def refresh_slotlist_message(self, msg: discord.Message = None):
        embed, channel = await self.create_slotlist()

        with suppress(discord.HTTPException, AttributeError):
            if not msg:
                msg = await self.bot.get_or_fetch_message(channel, self.slotlist_message_id)
                # msg = await channel.fetch_message(self.slotlist_message_id)

            await msg.edit(embed=embed)
    
    async def send_slotlist(self, channel: discord.TextChannel = None) -> discord.Message:
        from cogs.esports.views.smslotlist.button import SlotlistEditButton

        channel = channel or self.slotlist_channel

        _v = SlotlistEditButton(self.bot, self)
        embed, schannel = await self.create_slotlist()
        _v.message = await channel.send(embed=embed, view=_v)

        if channel == schannel:
            await self.make_changes(slotlist_message_id=_v.message.id)

        scrim = await Scrim.filter(id=self.id).first()
        if scrim and scrim.reg_close_auto_clean:
            with suppress(discord.HTTPException):
                await _v.message.pin()

        return _v.message


            

    async def dispatch_reminders(self, channel: discord.TextChannel, link: str):
        reminders = await self.slot_reminders.all().order_by("created_at")

        if not reminders:
            return

        _e = discord.Embed(color=self.bot.color, title=f"Slot Available to Claim - {channel.guild.name}", url=link)
        _e.description = f"A slot of {self} is available to claim in {channel.mention}!\nClaim it before anyone else do."

        async for user in self.bot.resolve_member_ids(self.guild, [i.user_id for i in reminders]):
            with suppress(discord.HTTPException):
                await user.send(embed=_e)

        await ScrimsSlotReminder.filter(pk__in=(i.pk for i in reminders)).delete()

    async def ensure_match_timer(self):
        from models import Timer

        from .slotm import ScrimsSlotManager

        if not self.match_time:
            self.match_time = self.bot.current_time.replace(hour=0, minute=0, microsecond=0, second=0)

        _time = self.match_time
        while _time < self.bot.current_time:
            _time = _time + timedelta(hours=24)

        if self.match_time != _time:
            await Scrim.filter(pk=self.pk).update(match_time=_time)

        check = await Timer.filter(event="scrim_match", expires=_time, extra={"args": [], "kwargs": {"scrim_id": self.pk}}).exists()
        if not check:
            await self.bot.reminders.create_timer(_time, "scrim_match", scrim_id=self.pk)

        await ScrimsSlotManager.refresh_guild_message(self.guild_id, self.pk)

    async def make_changes(self, **kwargs):
        await Scrim.filter(pk=self.pk).update(**kwargs)
        return await self.refresh_from_db()

    async def get_text_slotlist(self):
        _text = f"{self} Slot details:\n\n"
        _slots = await self.cleaned_slots()

        for _ in _slots:
            _text += f"{_.num}. {_.team_name} <@{_.user_id}>\n"

        return _text

    async def ban_slot(self, slot: "AssignedSlot", *, reason, mod: discord.Member, ban_type: str):
        to_ban, scrims = [slot.user_id], [self]

        if ban_type == "2":
            to_ban = [_ for _ in slot.members]

        elif ban_type == "3":
            scrims = await Scrim.filter(guild_id=self.guild_id).order_by("open_time")

        elif ban_type == "4":
            to_ban = [_ for _ in slot.members]
            scrims = await Scrim.filter(guild_id=self.guild_id).order_by("open_time")

        for _ in to_ban:
            for scrim in scrims:
                if _ in await scrim.banned_user_ids():
                    continue

                b = await BannedTeam.create(user_id=_, expires=reason.dt, reason=reason.arg)
                await scrim.banned_teams.add(b)

            if banlog := await BanLog.get_or_none(guild_id=self.guild_id):
                await banlog.log_ban(_, mod, scrims, reason.arg, reason.dt)

            if reason.dt:
                await self.bot.reminders.create_timer(
                    reason.dt,
                    "scrim_ban",
                    scrims=[scrim.id for scrim in scrims],
                    user_id=_,
                    mod=mod.id,
                    reason=reason.arg,
                )

        return f"Banned {utils.plural(to_ban):player|players} from {utils.plural(scrims):scrim|scrims}."

    async def create_slotlist_img(self):
        """
        This is done! Now do whatever you can : )
        """
        slots = await self.teams_registered

        def wrapper():
            font = ImageFont.truetype(str(Path.cwd() / "src" / "data" / "font" / "Ubuntu-Regular.ttf"), 16)
            rects = []

            for slot in slots:
                image = Image.new("RGBA", (290, 30), "#2e2e2e")
                draw = ImageDraw.Draw(image)
                draw.text((10, 5), f"Slot {slot.num:02}  |  {slot.team_name}", font=font, fill="white")
                rects.append(image)

            # We will add 10 slots in a image.
            images = []
            for group in utils.split_list(rects, 10):
                size = (
                    290,
                    len(group) * 40,
                )
                image = Image.new("RGBA", size)
                x = 0
                y = 0

                for rect in group:
                    image.paste(rect, (x, y))
                    y += rect.size[1] + 10

                img_bytes = io.BytesIO()
                image.save(img_bytes, "PNG")
                img_bytes.seek(0)
                images.append(discord.File(img_bytes, "slotlist.png"))

            return images

        return await asyncio.get_event_loop().run_in_executor(
            None, wrapper
        )  # As pillow is blocking, we will process image in executor

    async def reg_open_msg(self):
        reserved_count = await self.reserved_slots.all().count()

        if len(self.open_message) <= 1:
            return discord.Embed(
                color=self.bot.color,
                title="Registration is now open!",
                description=f"📣 **`{self.required_mentions}`** mentions required.\n"
                f"📣 Total slots: **`{self.total_slots}`** [`{reserved_count}` slots reserved]",
            )

        changes = [
            ("<<mentions>>", str(self.required_mentions)),
            ("<<slots>>", str(self.total_slots)),
            ("<<reserved>>", str(reserved_count)),
            ("<<slotlist>>", getattr(self.slotlist_channel, "mention", "Not Found")),
            ("<<multireg>>", "Enabled" if self.multiregister else "Not Enabled"),
            ("<<teamname>>", "Yes" if self.teamname_compulsion else "No"),
            (
                "<<mention_banned>>",
                ", ".join(map(lambda x: getattr(x, "mention", "Left"), map(self.guild.get_member, await self.banned_user_ids()))),
            ),
            (
                "<<mention_reserved>>",
                ", ".join(
                    map(
                        lambda x: getattr(x, "mention", "Left"),
                        map(self.guild.get_member, await self.reserved_user_ids()),
                    )
                ),
            ),
        ]

        text = str(self.open_message)
        for _ in changes:
            text = text.replace(*_)

        return discord.Embed.from_dict(leval(text))

    def reg_close_msg(self):
        if len(self.close_message) <= 1:
            return discord.Embed(color=self.bot.config.COLOR, description="**Registration is now Closed!**")

        changes = [
            ("<<slots>>", str(self.total_slots)),
            ("<<filled>>", str(self.total_slots  - len(self.available_slots))),
            ("<<time_taken>>", self.time_elapsed or "N/A"),
            ("<<open_time>>", discord_timestamp(self.open_time)),
        ]

        text = str(self.close_message)
        for _ in changes:
            text = text.replace(*_)

        return discord.Embed.from_dict(leval(text))

    async def setup_logs(self):
        _reason = "Created for scrims management."

        guild = self.guild

        if not (scrims_mod := self.modrole):
            scrims_mod = await guild.create_role(name="scrims-mod", color=self.bot.color, reason=_reason)

        overwrite = self.registration_channel.overwrites_for(guild.default_role)
        overwrite.update(read_messages=True, send_messages=True, read_message_history=True)
        await self.registration_channel.set_permissions(scrims_mod, overwrite=overwrite)

        if (scrims_log_channel := self.logschan) is None:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True),
                scrims_mod: discord.PermissionOverwrite(read_messages=True),
            }
            scrims_log_channel = await guild.create_text_channel(
                name="VersatileX-scrims-logs",
                overwrites=overwrites,
                reason=_reason,
                topic="**DO NOT RENAME THIS CHANNEL**",
            )

            note = await scrims_log_channel.send(
                embed=discord.Embed(
                    description=f"Scrim events (e.g., opening registrations, adding roles) will be logged in this channel. "
                    f"The {scrims_mod.mention} role has been created for scrim moderators—users with it can message in "
                    f"registration channels without affecting registrations.\n\n"
                    f"`Note`: **Do not rename this channel.**",
                    color=self.bot.color,
                )
            )
            await note.pin()
    
    
    async def full_delete(self):
        from .slotm import ScrimsSlotManager

        _id = self.pk
        self.bot.cache.scrim_channels.discard(self.registration_channel_id)

        slotm = await ScrimsSlotManager.filter(guild_id=self.guild_id, scrim_ids__contains=self.pk)
        
        slot_managers = await ScrimsSlotManager.filter(pk__in=[_.pk for _ in slotm])
        for slot_manager in slot_managers:
            if _id in slot_manager.scrim_ids:
                slot_manager.scrim_ids.remove(_id)
                await slot_manager.save(update_fields=["scrim_ids"])
                
        _d = await self.assigned_slots.all()
        await AssignedSlot.filter(pk__in=[_.pk for _ in _d]).delete()
        _r = await self.slot_reminders.all()
        await ScrimsSlotReminder.filter(pk__in=[_.pk for _ in _r]).delete()
        _re = await self.reserved_slots.all()
        await ReservedSlot.filter(pk__in=[_.pk for _ in _re]).delete()
        await self.delete()


    async def confirm_all_scrims(self, ctx: Context, **kwargs):
        if not await Scrim.scrim_count(ctx.guild.id) > 1:
            return

        prompt = await ctx.prompt("Do you want to apply these changes to all scrims in this server?")
        if not prompt:
            return await ctx.simple("Alright, this scrim only.", 4)

        await Scrim.filter(guild_id=ctx.guild.id).update(**kwargs)
        await ctx.simple("This change was applied to all your scrims.", 4)
    
   
    async def close_registration(self):
        from cogs.esports.helpers.utils import toggle_channel, wait_and_purge
        from cogs.esports.views.scrims._drop_send import get_current_day_drop, DropLocationView, generate_map_image
        from .slotm import ScrimsSlotManager
        import json

        closed_at = self.bot.current_time
        registration_channel = self.registration_channel
        open_role = self.open_role

        self.time_elapsed = humanize.precisedelta(closed_at - self.opened_at)
        await self.make_changes(opened_at=None, time_elapsed=self.time_elapsed, closed_at=closed_at)

        channel_update = await toggle_channel(registration_channel, open_role, False)
        _e = self.reg_close_msg()
        await registration_channel.send(embed=_e)

        self.bot.dispatch("scrim_log", EsportsLog.closed, self, permission_updated=channel_update)

        registered = await self.teams_registered

        if self.autoslotlist and registered:
            await self.send_slotlist()

        scrim = await Scrim.filter(id=self.id).first()
        if not scrim or not scrim.drop_menu_enabled:
            return

        drop_locations, error = await get_current_day_drop(self.id)
        if error:
            await registration_channel.send(f"Error: {error}")
            return

        message_ids = []
        for map_name in drop_locations:
            embed = discord.Embed(
                title="Select Your Drop Location",
                description=f"Map: **{map_name}**",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Scrim Name: {scrim.name}")

            file, error = await generate_map_image(map_name, scrim)
            if error:
                await registration_channel.send(f"Error generating map for {map_name}: {error}")
                continue

            if file:
                embed.set_image(url=f"attachment://{file.filename}")

            view = DropLocationView(map_name, self.id, self.registration_channel, 0)
            message = await registration_channel.send(embed=embed, file=file, view=view)
            view.message_id = message.id
            
            # Save state after message_id is set
            await view.save_state()
            await view.initialize_async(self.id)
            message_ids.append(message.id)

        if message_ids:
            scrim.drop_message_id = json.dumps(message_ids)
            await scrim.save()
            

        if not scrim.reg_close_auto_clean:
            def check(msg: discord.Message) -> bool:
                return not msg.pinned

            self.bot.loop.create_task(wait_and_purge(registration_channel, check=check, wait_for=60))

        slotm = await ScrimsSlotManager.get_or_none(guild_id=self.guild_id, scrim_ids__contains=self.id)
        if slotm:
            await slotm.refresh_public_message()
        
    async def __add_role_to_reserved_users(self, member_ids: set[int]):
        role = discord.Object(id=self.role_id)
        async for member in self.bot.resolve_member_ids(self.guild, member_ids):
            try:
                if not member._roles.has(role.id):
                    await member.add_roles(role, reason=f"Reserved Slot [{self.pk}]")
                    await asyncio.sleep(0.2)
            except discord.HTTPException:
                continue
    

    async def start_registration(self):
        from cogs.esports.helpers.utils import (
            available_to_reserve,
            scrim_work_role,
            toggle_channel,
        )

        oldslots = await self.assigned_slots
        await AssignedSlot.filter(id__in=(slot.id for slot in oldslots)).delete()
        await self.assigned_slots.clear()

        # here we insert a list of slots we can give for the registration.
        await self.bot.db.execute(
            """
            UPDATE public."sm.scrims" SET available_slots = $1 WHERE id = $2
            """,
            await available_to_reserve(self),
            self.id,
        )

        reserved_slots = await self.reserved_slots.all().order_by("num")
        reserved_user_ids = {slot.user_id for slot in reserved_slots if slot.user_id is not None}

        for slot in reserved_slots:
            assinged_slot = await AssignedSlot.create(
                num=slot.num,
                user_id=slot.user_id,
                team_name=slot.team_name,
                jump_url=None,
            )

            await self.assigned_slots.add(assinged_slot)

        self.bot.loop.create_task(self.__add_role_to_reserved_users(reserved_user_ids))

        await Scrim.filter(pk=self.id).update(
            opened_at=self.bot.current_time,
            closed_at=None,
            slotlist_message_id=None,
        )
        self.bot.loop.create_task(self.ensure_match_timer())
        await asyncio.sleep(0.2)

        # Opening Channel for Normal Janta
        registration_channel = self.registration_channel
        open_role = self.open_role

        # check if countdown is on

        # if self.cdn.get("status", False):
        #     ...

        _e = await self.reg_open_msg()

        await registration_channel.send(
            content=scrim_work_role(self, EsportsRole.ping),
            embed=_e,
            allowed_mentions=discord.AllowedMentions(roles=True, everyone=True),
        )

        self.bot.cache.scrim_channels.add(registration_channel.id)

        await toggle_channel(registration_channel, open_role, True)
        self.bot.dispatch("scrim_log", EsportsLog.open, self)

    @staticmethod
    async def show_selector(*args, **kwargs):
        """
        :param: ctx: Context
        :param: scrims: List[Scrim]
        :param: placeholder:str
        :param: multi:bool=True
        """
        from cogs.esports.views.scrims.selector import prompt_selector

        return await prompt_selector(*args, **kwargs)

    async def scrim_posi(self):
        from cogs.esports.views.scrims.selector import scrim_position

        return await scrim_position(self.pk, self.guild_id)
    
    
    @staticmethod
    @cached(ttl=60 * 2)
    async def scrim_count(guild_id: int):
        return await Scrim.filter(guild_id=guild_id).count()

    async def check_fake_tags(self, message: discord.Message):
        query = """
        SELECT *
            FROM PUBLIC."sm.scrims_sm.assigned_slots" AS ASSIGNED_SLOT
            INNER JOIN PUBLIC."sm.assigned_slots" AS SLOTS ON SLOTS.ID = ASSIGNED_SLOT.ASSIGNEDSLOT_ID
        WHERE ASSIGNED_SLOT."sm.scrims_id" = $1
        AND $2 && SLOTS.MEMBERS;

        """
        return await self.bot.db.fetch(query, self.id, [i.id for i in message.mentions])
    
 
class IdpClaimData(models.Model):
    class Meta:
        table = "sm.idp_claim_data"

    id = fields.BigIntField(pk=True, index=True)
    scrim = fields.ForeignKeyField("models.Scrim", related_name="idp_claims", index=True)  # Links to Scrim via idp_channel
    team_name = fields.TextField()
    user_id = fields.BigIntField(index=True)
    slot_num = fields.IntField()

    created_at = fields.DatetimeField(auto_now_add=True)






from tortoise.models import Model
from tortoise import fields

class TicketSystem(Model):
    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField()
    panel_channel_id = fields.BigIntField(null=True)
    tickets_category_id = fields.BigIntField(null=True)
    transcript_channel_id = fields.BigIntField(null=True)
    support_role_id = fields.BigIntField(null=True)
    ping_support = fields.BooleanField(default=True)
    panel_title = fields.CharField(max_length=255, default="Ticket Panel")
    panel_description = fields.TextField(default="Click below to create a ticket")
    panel_color = fields.IntField(default=0x1E90FF)
    panel_thumbnail = fields.CharField(max_length=255, default="https://example.com/thumbnail.png", null=True)
    panel_image = fields.CharField(max_length=255, default="https://example.com/image.png", null=True)
    panel_footer = fields.CharField(max_length=255, default="Ticket System Bot")
    ticket_title = fields.CharField(max_length=255, default="Ticket System")
    ticket_description = fields.TextField(default="How can I help you?")
    ticket_color = fields.IntField(default=0x1E90FF)
    ticket_thumbnail = fields.CharField(max_length=255, default="https://example.com/thumbnail.png", null=True)
    ticket_image = fields.CharField(max_length=255, default="https://example.com/image.png", null=True)
    ticket_footer = fields.CharField(max_length=255, default="Ticket System Bot")
    panel_message_id = fields.BigIntField(null=True)
    ticket_message_ids = fields.JSONField(default=dict)
    max_tickets_per_user = fields.IntField(default=1)
    ticket_name_format = fields.CharField(max_length=50, default="ticket-{user}")
    auto_close_inactive_days = fields.IntField(default=0)
    allow_priority_tags = fields.BooleanField(default=False)
    # New fields
    ticket_categories = fields.JSONField(default=["Support" ])  # List of category options
    ticket_notes = fields.JSONField(default=dict)  # {channel_id: [notes]}
    archive_channel_id = fields.BigIntField(null=True)  # Archive channel for closed tickets

    class Meta:
        table = "ticket_systems"
class BaseSlot(models.Model):
    class Meta:
        abstract = True

    id = fields.IntField(pk=True)
    num = fields.IntField(null=True)
    user_id = fields.BigIntField(null=True)
    team_name = fields.TextField(null=True)
    members = ArrayField(fields.BigIntField(), default=list)
        
class WelcomeConfig(models.Model):
    guild_id = fields.BigIntField(pk=True)
    welcome_type = fields.CharField(max_length=50, null=True)
    welcome_message = fields.TextField(null=True)
    channel_id = fields.BigIntField(null=True)
    embed_data = fields.JSONField(null=True)
    auto_delete_duration = fields.IntField(null=True)
    enabled = fields.BooleanField(default=True)
    dm_message = fields.TextField(null=True)

    class Meta:
        table = "welcome"
        
class AssignedSlot(BaseSlot):
    class Meta:
        table = "sm.assigned_slots"

    id = fields.BigIntField(pk=True)
    team_name = fields.TextField()
    num = fields.IntField(null=True)
    user_id = fields.BigIntField(null=True)
    message_id = fields.BigIntField(null=True)
    jump_url = fields.TextField(null=True)
    drop_location = fields.TextField(null=True)
    drop_location2 = fields.TextField(null=True)

    @property
    def owner(self) -> discord.User:
        return self.bot.get_user(self.user_id)


class ReservedSlot(BaseSlot):
    class Meta:
        table = "sm.reserved_slots"

    expires = fields.DatetimeField(null=True)
    drop_locations = fields.TextField(null=True, blank=True)

    @property
    def leader(self):
        return self.bot.get_user(self.user_id)
   
class DropLocationViewState(models.Model):
        id = fields.IntField(pk=True)
        scrim_id = fields.IntField()
        map_name = fields.CharField(max_length=50)
        channel_id = fields.BigIntField()
        message_id = fields.BigIntField()

        class Meta:
            table = "drop_location_view_states"
            unique_together = (("scrim_id", "map_name"),)    

class BannedTeam(BaseSlot):
    class Meta:
        table = "sm.banned_teams"
   
    reason = fields.CharField(max_length=200, null=True)
    expires = fields.DatetimeField(null=True)
    
class StickyMessage(models.Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    channel_id = fields.BigIntField()
    message_content = fields.TextField()
    message_id = fields.BigIntField(null=True)
    count = fields.IntField(default=0)

    class Meta:
        table = "sticky_messages"

class BanLog(BaseDbModel):
    class Meta:
        table = "esports_bans"

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField()
    channel_id = fields.BigIntField()

    @property
    def channel(self):
        return self.bot.get_channel(self.channel_id)

    def __format_scrims(self, scrims: List[Scrim]):
        _scrims = []
        for idx, _ in enumerate(scrims, start=1):
            if idx < 4:
                _scrims.append(getattr(_.registration_channel, "mention", "`deleted-channel`"))

            elif idx == 4:
                _scrims.append(f"**...{len(scrims) -  3} more**")

        return ", ".join(_scrims)

    async def log_ban(self, user_id: int, mod: discord.Member, scrims: List[Scrim], reason: str = None, dt: str = None):
        user: discord.User = await self.bot.getch(self.bot.get_user, self.bot.fetch_user, user_id)

        _e = discord.Embed(
            color=discord.Color.red(), 
            title=f" Banned from {plural(scrims):scrim|scrims} "  # 🔨 for ban, 🚫 for restriction
        )
        _e.add_field(name="<:user:1359761105349640242> User", value=f"<:read:1359402059308335188> {getattr(user, 'mention', 'unknown-user')}")  # 👤 for user
        _e.add_field(name="<:fcm_mod:1359763121681600654> Moderator", value="<:read:1359402059308335188>" + str(mod))  # 🛡️ for authority
        _e.add_field(
            name="<a:emoji_1744262867905:1359761827386495046> Effected Scrims", 
            value="<:read:1359402059308335188>" + self.__format_scrims(scrims), 
            inline=False
        )  # 🏆 for scrims
        _e.add_field(
            name="<:emoji_1744262966588:1359762233462358148> Reason", 
            value=f"```{truncate_string(reason, 100) if reason else 'No Reason given..'}```"
        )  # 📝 for reason

        _e.set_footer(text=f"Expiring: {'Never' if not dt else ''}")
        if dt:
            _e.timestamp = dt

        if user:
            _e.set_thumbnail(url=getattr(user.display_avatar, "url", "https://cdn.discordapp.com/embed/avatars/0.png"))

        with suppress(discord.HTTPException, AttributeError):
            await self.channel.send(getattr(user, "mention", ""), embed=_e)

    async def log_unban(self, user_id: int, mod: discord.Member, scrims: List[Scrim], reason: str = None):
        user = await self.bot.getch(self.bot.get_user, self.bot.fetch_user, user_id)
        _e = discord.Embed(
            color=discord.Color.green(), 
            title=f"Unbanned from {plural(scrims):Scrim|Scrims}"  # Added 🎉 for celebration
        )
        _e.add_field(name="<:user:1359761105349640242> User", value=f"<:read:1359402059308335188> ({getattr(user, 'mention', 'unknown-user')})")  # 👤 for user
        _e.add_field(name="<:fcm_mod:1359763121681600654> Moderator", value="<:read:1359402059308335188>" + str(mod))  # 🛡️ for authority
        _e.add_field(
            name="<a:emoji_1744262867905:1359761827386495046> Effected Scrims", 
            value="<:read:1359402059308335188>" + self.__format_scrims(scrims), 
            inline=False
        )  # 🏆 for scrims
        _e.add_field(
            name="<:emoji_1744262966588:1359762233462358148> Reason", 
            value=reason or "```No Reason given..```", 
            inline=False
        )  # 📝 for reason
        _e.timestamp = self.bot.current_time

        if user:
            _e.set_thumbnail(url=getattr(user.display_avatar, "url", "https://cdn.discordapp.com/embed/avatars/0.png"))

        with suppress(discord.HTTPException, AttributeError):
            await self.channel.send(getattr(user, "mention", ""), embed=_e)


class ScrimsSlotReminder(BaseDbModel):
    class Meta:
        table = "scrims_slot_reminders"

    id = fields.IntField(pk=True)
    user_id = fields.BigIntField()
    created_at = fields.DatetimeField(auto_now=True)
