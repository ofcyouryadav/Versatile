import random
from contextlib import suppress
from datetime import datetime, timedelta
from enum import Enum

import discord
import pytz

import config


class _Sentinel:
    def __repr__(self):
        return "<MISSING>"


class Day(Enum):
    monday = "monday"
    tuesday = "tuesday"
    wednesday = "wednesday"
    thursday = "thursday"
    friday = "friday"
    saturday = "saturday"
    sunday = "sunday"


class PremiumPurchase(Enum):
    GIFT = "gift"
    PARTNERSHIP = "partner"
    SHOP = "shop"
    REGULAR = "regular"


class PartnerRequest(Enum):
    pending = "1"
    approved = "2"
    denied = "3"


class EsportsType(Enum):
    tourney = "tourney"
    scrim = "scrim"


class AutocleanType(Enum):
    channel = "channel"
    role = "role"


class SSType(Enum):
    yt = "youtube"
    insta = "instagram"
    rooter = "rooter"
    loco = "loco"
    anyss = "Any SS"
    custom = "custom"


class EsportsLog(Enum):
    open = "open"
    closed = "closed"
    success = "reg_success"


class EsportsRole(Enum):
    ping = "ping_role"
    open = "open_role"


class RegDeny(Enum):
    botmention = "mentioned bots"
    nomention = "insufficient mentions"
    banned = "banned"
    multiregister = "multiregister"
    noteamname = "no_team_name"
    reqperms = "lack_permissions"
    duplicate = "duplicate_name"
    bannedteammate = "banned_teammate"
    nolines = "no_lines"
    faketag = "fake_tag"


class RegMsg(Enum):
    sopen = "Scrim Registration Open"
    sclose = "Scrim Registration Close"
    topen = "Tourney Registration Open"
    tclose = "Tourney Registration Close"


class LockType(Enum):
    channel = "channel"
    guild = "guild"
    category = "category"
    maintenance = "maintenance"


class ScrimBanType(Enum):
    ban = "banned"
    unban = "unbanned"


bot_colors = {
    746348747918934096: 0x00FFB3,
    744990850064580660: 0xF3B82B,
    846339012607082506: 0x87EA5C,
    902856923311919104: 0xFF4E4A,
    902857046574129172: 0x5F6FFA,
    902857418390765569: 0xFFFFFF,
}

perks = {
    "Premium Role": ["❌", "✅"],
    "Scrims": ["3", "Unlimited"],
    "Tourneys": ["2", "Unlimited"],
    "TagCheck": ["1", "Unlimited"],
    "EasyTags": ["1", "Unlimited"],
    "Autorole": ["1", "Unlimited"],
    "Custom Footer": ["❌", "✅"],
    "Custom Color": ["❌", "✅"],
    "Giveaway": ["5", "Unlimited"],
    "Edit Ptable Watermark": ["❌", "✅"],
    "Autopurge": ["1", "Unlimited"],
}


def random_greeting():
    greetings = [
        "Hello, sunshine!",
        "chomu !",
        "Howdy-doody!",
        "Ahoy, matey!",
        "Hiya!",
        "What’s crackin’?",
        "Howdy, howdy ,howdy!",
        "Yo!",
        "I like your face.",
        "Bonjour!",
        "Yo! You know who this is.",
    ]
    return random.choice(greetings)


def random_thanks():
    msges = (
        "https://cdn.discordapp.com/attachments/877888851241238548/877890130478784532/unknown.png",
        "https://cdn.discordapp.com/attachments/877888851241238548/877890377426821140/unknown.png",
        "https://cdn.discordapp.com/attachments/877888851241238548/877890550399918122/unknown.png",
        "https://cdn.discordapp.com/attachments/877888851241238548/877891011349725194/unknown.png",
        "https://cdn.discordapp.com/attachments/877888851241238548/877891209421549628/unknown.png",
        "https://cdn.discordapp.com/attachments/877888851241238548/877891348869550100/unknown.png",
        "https://cdn.discordapp.com/attachments/877888851241238548/877891767058444359/unknown.png",
        "https://cdn.discordapp.com/attachments/877888851241238548/877891874671706162/unknown.png",
        "https://cdn.discordapp.com/attachments/877888851241238548/877892011720572988/unknown.png",
        "https://cdn.discordapp.com/attachments/829953427336593429/878898567509573652/unknown.png",
        "https://cdn.discordapp.com/attachments/877888851241238548/881575840578695178/unknown.png",
        "https://cdn.discordapp.com/attachments/877888851241238548/881576005498732625/unknown.png",
        "https://cdn.discordapp.com/attachments/877888851241238548/881576299137761350/unknown.png",
        "https://cdn.discordapp.com/attachments/851846932593770496/886275684304044142/unknown.png",
    )
    return random.choice(msges)


tips = ("")

async def show_tip(ctx):
    try:
        # Ensure `config.DEVS` is iterable
        if isinstance(config.DEVS, int):
            config.DEVS = [config.DEVS]  # Convert to a list if it's an integer

        if ctx.author.id in config.DEVS:
            return

        if random.random() < 0.1: 
            with suppress(discord.HTTPException, discord.Forbidden):
                await ctx.send(f"**Tip of the Moment? :** {random.choice(tips)}")
    except Exception as e:
        print(f"Error in show_tip: {e}")

async def remind_premium(ctx):
    if random.randint(1, 3) != 1:
        return

    from cogs.premium.views import PremiumPurchaseBtn
    from models import Guild
    from utils import discord_timestamp

    guild = await Guild.get_or_none(
        pk=ctx.guild.id, is_premium=True, premium_end_time__lte=ctx.bot.current_time + timedelta(days=5)
    )
    if not guild:
        return

    if guild.premium_end_time < ctx.bot.current_time:
        return

    _e = discord.Embed(color=discord.Color.red(), title="Premium Ending Soon....")
    _e.description = (
        f"Your VersatileXPremium subscription is ending {discord_timestamp(guild.premium_end_time)}\n\n"
        "*Click the button to renew your subscription.*"
    )
    v = discord.ui.View(timeout=None)
    v.add_item(PremiumPurchaseBtn(label="Renew Premium"))

    try:
        await ctx.reply(embed=_e, view=v)
    except discord.HTTPException:
        return


class HelpGIF(Enum):
    pass


MISSING = _Sentinel()
IST = pytz.timezone("Asia/Kolkata")
