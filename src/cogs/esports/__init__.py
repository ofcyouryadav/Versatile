
from __future__ import annotations

from sqlite3 import OperationalError
import typing

from cogs.esports.events.slots import SlotManagerEvents
from cogs.esports.views.scrims.main import ScrimsMain
from cogs.esports.views.tourney.main import TourneyManager

if typing.TYPE_CHECKING:
    from core import Quotient

# from ..esports.views.scrims.music import MusicCog
from discord import app_commands    
import re


    

from tortoise.exceptions import ConfigurationError
import discord
from discord.ext import commands

from core import Cog, Context, QuotientView
from models import *
from utils import QuoRole, QuoTextChannel, checks
import wavelink

import logging
 
from .errors import SMError
from .events import ScrimEvents, Ssverification, TagEvents, TourneyEvents 
from .helpers import delete_denied_message
from .slash import *
from .views.scrims._ban_cmd import ScrimBanView
from .views import *
from .views.idp import IdpCog
from .views.scrims.slot_cancel import *
from .views.scrims.music import Music
from .views.scrims._drop_send import DropLocationView , get_current_day_drop, generate_map_image

async def fetch_all_idp_channels(bot, guild: discord.Guild) -> List[discord.TextChannel]:
    """
    Fetches all idp_channel IDs from Scrim objects for a given guild and converts them to discord.TextChannel objects.

    Args:
        bot: The bot instance to access current_time and other utilities.
        guild: The discord.Guild object to fetch channels from.

    Returns:
        A list of valid discord.TextChannel objects.
    """
    valid_channels = []

    # Fetch all Scrim objects for the guild
    scrims = await Scrim.filter(guild_id=guild.id).all()  # Query all Scrims for the guild

    for scrim in scrims:
        # Convert the idp_channel ID to a discord.TextChannel object
        configured_idp_channel = guild.get_channel(scrim.idp_channel)

        # Validate that the channel exists and is a text channel
        if not configured_idp_channel or not isinstance(configured_idp_channel, discord.TextChannel):
            continue  # Skip invalid channels silently (or log if needed)

        # Check bot permissions in the channel
        bot_permissions = configured_idp_channel.permissions_for(guild.me)
        if not (bot_permissions.view_channel and bot_permissions.send_messages and bot_permissions.embed_links):
            continue  # Skip channels where the bot lacks permissions

        valid_channels.append(configured_idp_channel)

    return valid_channels



async def get_scrim_record(guild_id: int) -> Scrim | None:
    """
    Fetch the active Scrim record for the given guild.
    You can customize the logic to filter for 'open' scrims only if needed.
    """
    scrim = await Scrim.filter(guild_id=guild_id).order_by("-id").first()
    return scrim

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScrimSelect(discord.ui.Select):
    def __init__(self, scrims: list[Scrim], message: discord.Message):
        self.message = message
        options = [
            discord.SelectOption(
                label=f"Scrim {scrim.id}: {scrim.name}",
                value=str(scrim.id),
                description=f"Day: {scrim.drop_location_days[:50] or 'None'}"
            ) for scrim in scrims[:25]
        ] or [discord.SelectOption(label="No scrims available", value="none")]

        super().__init__(
            placeholder="Select a scrim",
            options=options,
            min_values=1,
            max_values=1,
            disabled=len(options) == 1 and options[0].value == "none",
            custom_id="scrim_select_resenddrop"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.values[0] == "none":
            return await interaction.followup.send("No scrims available!", ephemeral=True)

        scrim_id = int(self.values[0])
        scrim = await Scrim.filter(id=scrim_id).first()
        if not scrim:
            return await interaction.followup.send(f"Scrim with ID {scrim_id} not found!", ephemeral=True)

        view = discord.ui.View(timeout=3600)
        view.add_item(ConfirmResendButton(scrim_id=scrim_id, message=self.message))
        view.add_item(CancelResendButton(self.message))
        embed = discord.Embed(
            title="Confirm Resend Drop Location",
            description=f"Are you sure you want to resend the drop location menu for Scrim {scrim.id}: {scrim.name}?",
            color=interaction.client.color
        )
        await self.message.edit(embed=embed, view=view)

class ConfirmResendButton(discord.ui.Button):
    def __init__(self, scrim_id: int, message: discord.Message):
        super().__init__(label="Yes", style=discord.ButtonStyle.green, custom_id=f"confirm_resend_{scrim_id}")
        self.scrim_id = scrim_id
        self.message = message

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(title="Processing...", description="🗑 Deleting old drop menus...", color=interaction.client.color)
        await self.message.edit(embed=embed, view=None)

        scrim = await Scrim.filter(id=self.scrim_id).first()
        if not scrim:
            return await self.message.edit(embed=discord.Embed(description=f"❌ Scrim ID {self.scrim_id} not found.", color=discord.Color.red()))

        view_states = await DropLocationViewState.filter(scrim_id=self.scrim_id).all()
        for state in view_states:
            try:
                channel = interaction.guild.get_channel(state.channel_id)
                if isinstance(channel, discord.TextChannel):
                    message = await channel.fetch_message(state.message_id)
                    await message.delete()
                await state.delete()
            except:
                await state.delete()

        embed.description += "\n✅ Old drop menus deleted.\n⏳ Fetching map data..."
        await self.message.edit(embed=embed)

        maps, error = await get_current_day_drop(self.scrim_id)
        if error or not maps:
            return await self.message.edit(embed=discord.Embed(description=f"❌ {error or 'No maps found.'}", color=discord.Color.red()))

        embed.description += f"\n✅ Fetched {len(maps)} map(s).\n⏳ Sending new drop menus..."
        await self.message.edit(embed=embed)

        channel = interaction.channel
        sent_maps = []
        failed_maps = []

        for map_name in maps:
            try:
                file, gen_error = await generate_map_image(map_name, scrim)
                if gen_error:
                    failed_maps.append(f"{map_name}: {gen_error}")
                    continue

                embed_map = discord.Embed(
                    title="Select Your Drop Location",
                    description=f"Map: **{map_name}**\n\n**Selected Locations:**\n(None)",
                    color=interaction.client.color
                )
                embed_map.set_footer(text=f"Scrim Name: {scrim.name}")
                if file:
                    embed_map.set_image(url=f"attachment://{file.filename}")

                view = DropLocationView(map_name=map_name, scrim_id=self.scrim_id, channel=channel, message_id=0)
                message = await channel.send(embed=embed_map, file=file, view=view)
                view.message_id = message.id
                await view.save_state()
                interaction.client.add_view(view, message_id=message.id)
                sent_maps.append(map_name)

            except Exception as e:
                failed_maps.append(f"{map_name}: {str(e)}")

        final_embed = discord.Embed(
            title="Drop Menu Resend Complete",
            description=f"✅ Sent: {', '.join(sent_maps) if sent_maps else 'None'}\n❌ Failed: {', '.join(failed_maps) if failed_maps else 'None'}",
            color=discord.Color.green() if sent_maps else discord.Color.red()
        )
        await self.message.edit(embed=final_embed)

class CancelResendButton(discord.ui.Button):
    def __init__(self, message: discord.Message):
        super().__init__(label="No", style=discord.ButtonStyle.red, custom_id="cancel_resend")
        self.message = message

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.message.edit(embed=discord.Embed(description="❌ Resend canceled.", color=discord.Color.red()), view=None)
            
class ScrimManager(Cog, name="Esports"):
    def __init__(self, bot: Quotient):
        self.bot = bot
         
        
    async def fetch_all_idp_channels(bot, guild: discord.Guild) -> List[discord.TextChannel]:
  
        valid_channels = []

        # Fetch all Scrim objects for the guild
        scrims = await Scrim.filter(guild_id=guild.id).all()  # Query all Scrims for the guild

        for scrim in scrims:
            # Convert the idp_channel ID to a discord.TextChannel object
            configured_idp_channel = guild.get_channel(scrim.idp_channel)

            # Validate that the channel exists and is a text channel
            if not configured_idp_channel or not isinstance(configured_idp_channel, discord.TextChannel):
                continue  # Skip invalid channels silently (or log if needed)

            # Check bot permissions in the channel
            bot_permissions = configured_idp_channel.permissions_for(guild.me)
            if not (bot_permissions.view_channel and bot_permissions.send_messages and bot_permissions.embed_links):
                continue  # Skip channels where the bot lacks permissions

            valid_channels.append(configured_idp_channel)

        return valid_channels    

    # ************************************************************************************************
    @Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        if message.channel.id in self.bot.cache.scrim_channels:
            scrim = await Scrim.get_or_none(registration_channel_id=message.channel.id)
            if not scrim or not scrim.opened_at:  # either scrim doesn't exist or it is closed.
                return 

            if not message.id in (record.message_id for record in await scrim.assigned_slots.all()):
                return

            slot = [
                slot
                for slot in await scrim.assigned_slots.all()
                if slot.user_id == message.author.id and slot.message_id == message.id
            ]
            if not slot:  # means their registration was denied
                return
            slot = slot[0]

            self.bot.dispatch("scrim_registration_delete", scrim, message, slot)

    # ************************************************************************************************
   
    

    @commands.command(name="resenddrop", help="Resend the drop location menu for a scrim")
    @commands.has_permissions(administrator=True)
    async def resend_drop(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Drop Location Menu Resend",
            description="⏳ Initializing...",
            color=ctx.bot.color
        )
        msg = await ctx.send(embed=embed)

        scrims = await Scrim.filter(drop_menu_enabled=True).all()
        if not scrims:
            return await msg.edit(embed=discord.Embed(description="❌ No scrims with drop menu enabled found!", color=discord.Color.red()))

        view = discord.ui.View(timeout=3600)
        view.add_item(ScrimSelect(scrims, msg))
        embed.title = "Select Scrim to Resend Drop Menu"
        embed.description = "Choose a scrim to resend the drop location menu. This will disable existing menus."
        embed.color = ctx.bot.color
        await msg.edit(embed=embed, view=view)

    @resend_drop.error
    async def resend_drop_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need administrator permissions to use this command!", delete_after=10)
        else:
            logger.error(f"Error in resenddrop command: {str(error)}")
            await ctx.send(f"Unexpected error: {str(error)}", delete_after=10)


    
            
    @commands.command(aliases=["claimclear" , "clearclaim"] , hidden=True)
    async def test_clear(self, ctx: commands.Context, channel: discord.TextChannel):
        if not Scrim.is_ignorable(ctx.author):
            return await ctx.error(f"You need `scrims-mod` role to use this command.")
      
        
        scrim = await Scrim.filter(idp_channel=channel.id).first()
        if not scrim:
            embed = discord.Embed(
                color=discord.Color.red(),
                description=f"No scrim found for {channel.mention}."
            )
            await ctx.send(embed=embed, delete_after=10)
            return

        try:
            deleted_count = await IdpClaimData.filter(scrim=scrim).delete()
           
            embed = discord.Embed(
                color=discord.Color.green(),
                description=f"Cleared {deleted_count} IdpClaimData records for {channel.mention}."
            )
        except Exception as e:
          
                embed = discord.Embed(
                color=discord.Color.red(),
                description = f"Failed to clear IdpClaimData for {channel.Ascertain(str(e))}"
            )
            
        await ctx.send(embed=embed, delete_after=10)
    




    @commands.command(name="claimcheck", aliases=("cc", "claimshow"), hidden=True)
    async def claimshow(self, ctx: commands.Context, channel: discord.TextChannel):
        logger.debug(f"claimshow: Command invoked by user {ctx.author.id} for channel {channel.id}")

        # Check if user has scrims-mod role
        try:
            if not any((ctx.author.guild_permissions.manage_guild, Scrim.is_ignorable(ctx.author))):
                    return await ctx.error(f"You need `scrims-mod` role or `Manage-Server` permissions to use this command.")
        except AttributeError as e:
            logger.error(f"claimshow: Error checking scrims-mod role for user {ctx.author.id}: {e}")
            embed = discord.Embed(
                color=discord.Color.red(),
                description="Error checking permissions. Please ensure you have the correct roles."
            )
            await ctx.send(embed=embed, delete_after=10)
            return

        try:
            # Fetch Scrim for the channel
            scrim = await Scrim.filter(idp_channel=channel.id).first()
            if not scrim:
                logger.debug(f"claimshow: No scrim found for channel {channel.id}")
                embed = discord.Embed(
                    color=discord.Color.red(),
                    description=f"No scrim found for {channel.mention}. Please ensure a scrim is configured for this channel."
                )
                await ctx.send(embed=embed, delete_after=10)
                return

            # Fetch all IdpClaimData for the scrim, sorted by slot_num
            claims = await IdpClaimData.filter(scrim_id=scrim.id).order_by("slot_num").all()
            if not claims:
                logger.debug(f"claimshow: No claims found for scrim {scrim.id}")
                embed = discord.Embed(
                    color=discord.Color.red(),
                    description=f"No click data recorded for {channel.mention}."
                )
                await ctx.send(embed=embed, delete_after=10)
                return

            # Create the embed
            embed = discord.Embed(
                title=f"Idp Claim Data for {channel.name}",
                color=ctx.bot.color,
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text="Data fetched at")

            # Format claims for description
            claim_lines = []
            for claim in claims:
                try:
                    user = await ctx.bot.fetch_user(claim.user_id)
                    username = user.name
                except discord.NotFound:
                    username = f"Unknown User (ID: {claim.user_id})"
                except discord.HTTPException as e:
                    logger.error(f"claimshow: Failed to fetch user {claim.user_id} for scrim {scrim.id}: {e}")
                    username = f"Error Fetching User (ID: {claim.user_id})"

                # Format claim info
                claim_line = f"`Slot: {claim.slot_num} | {claim.team_name}`"
                claim_lines.append(claim_line)

            # Join claims into description
            embed.description = "\n".join(claim_lines) if claim_lines else "No claims found."

            # Send the embed
            try:
                await ctx.send(embed=embed)
            except discord.HTTPException as e:
                logger.error(f"claimshow: Failed to send embed for user {ctx.author.id}, channel {channel.id}: {e}")
                embed = discord.Embed(
                    color=discord.Color.red(),
                    description="Failed to send claim data. Please try again later."
                )
                await ctx.send(embed=embed, delete_after=10)

        except OperationalError as e:
            logger.error(f"claimshow: Database error for user {ctx.author.id}, channel {channel.id}: {e}")
            embed = discord.Embed(
                color=discord.Color.red(),
                description="Database error while fetching claim data   . Please try again later."
            )
            await ctx.send(embed=embed, delete_after=10)
        except Exception as e:
            logger.error(f"claimshow: Unexpected error for user {ctx.author.id}, channel {channel.id}: {e}")
            embed = discord.Embed(
                color=discord.Color.red(),
                description="An unexpected error occurred while fetching claim data. Please try again later."
            )
            await ctx.send(embed=embed, delete_after=10)
    

  
    @commands.command(name="slotcheck")
    async def slotcheck(self, ctx: commands.Context, member: discord.Member):
        """Check if a user is registered in any scrims."""
        if not any((ctx.author.guild_permissions.manage_guild, Scrim.is_ignorable(ctx.author))):
            return await ctx.error(f"You need `scrims-mod` role or `Manage-Server` permissions to use this command.")
        try:
            # Fetch all scrims with their assigned slots
            scrims = await Scrim.filter(guild_id=ctx.guild.id).prefetch_related("assigned_slots")
        except ConfigurationError as e:
            embed = discord.Embed(color=discord.Color.red(), description="Error: Database is not properly configured.")
            await ctx.send(embed=embed)
            return

        registered_slots = []
        for scrim in scrims:
            for slot in scrim.assigned_slots:
                if slot.user_id == member.id:
                    registered_slots.append((scrim, slot))

        embed = discord.Embed(color=self.bot.color, timestamp=ctx.message.created_at)
        embed.set_author(
            name=f"Slot Check for {member}",
            icon_url=member.avatar.url if member.avatar else member.default_avatar.url
        )

        if not registered_slots:
            embed.description = f"{member.mention} is not registered in any scrims."
            await ctx.send(embed=embed)
            return

        text = ""
        for idx, (scrim, slot) in enumerate(registered_slots, 1):
            channel = self.bot.get_channel(scrim.registration_channel_id) or "Unknown Channel"
            team_name = slot.team_name or "No Team Name"
            slot_number = slot.num
            
            text += (
                f"`{idx:02}.` {channel.mention if isinstance(channel, discord.TextChannel) else channel}\n"
                f"{team_name} | Slot: {slot_number} \n\n"
            )

        embed.description = truncate_string(text, 3900)
        embed.set_footer(text=f"Checked by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

        await ctx.send(embed=embed)
            
    @commands.command(aliases=("banc", "bcheck") , hidden=True)
    async def bancheck(self, ctx: commands.Context, member: discord.Member):
        """Check if a user is banned from any scrims."""
        
        if not Scrim.is_ignorable(ctx.author):
            return await ctx.error(f"You need `scrims-mod` role to use this command.")
        # Fetch all scrims from the database using tortoise-orm
        scrims = await Scrim.filter(guild_id=ctx.guild.id).prefetch_related("banned_teams")

        banned_scrims = []
        for scrim in scrims:
            for ban in scrim.banned_teams:
                if ban.user_id == member.id:
                    banned_scrims.append((scrim, ban))

        embed = discord.Embed(color=self.bot.color, timestamp=ctx.message.created_at)
        embed.set_author(
            name=f"Ban Check for {member}",
            icon_url=member.avatar.url if member.avatar else member.default_avatar.url
        )

        if not banned_scrims:
            embed.description = f"{member.mention} is not banned from any scrims."
            await ctx.send(embed=embed)
            return

        embed.description = f"{member.mention} is banned from the following scrims:\n\n"
        text = ""
        for idx, (scrim, ban) in enumerate(banned_scrims, 1):
            channel = self.bot.get_channel(scrim.registration_channel_id) or "Unknown Channel"
            text += (
                f"`{idx:02}.` Scrim: {scrim.name} {channel.mention if isinstance(channel, discord.TextChannel) else channel}\n"
                f"            User: {member.mention} `[{member.id}]`\n"
                f"            Expires: {discord_timestamp(ban.expires)}\n"
                f"            Reason: {ban.reason}\n\n"
            )

        embed.description += truncate_string(text, 3900)
        embed.set_footer(text=f"Checked by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

        await ctx.send(embed=embed)

    
    
    @commands.command(aliases=("s", "sm"))
    @commands.bot_has_permissions(embed_links=True, add_reactions=True, manage_messages=True)
    @commands.bot_has_guild_permissions(manage_channels=True, manage_roles=True, manage_messages=True)
    @commands.cooldown(1, 15, type=commands.BucketType.guild)
    async def smanager(self, ctx: Context):
        """
        Contains commands related to Versatilx's powerful scrims manager.
        """
        if not any((ctx.author.guild_permissions.manage_guild, Scrim.is_ignorable(ctx.author))):
            return await ctx.error(f"You need `scrims-mod` role or `Manage-Server` permissions to use this command.")

        v = ScrimsMain(ctx)
        v.message = await ctx.send(embed=await v.initial_embed(), view=v)

    # ************************************************************************************************
    # ************************************************************************************************

    @commands.command(aliases=("tm", "t"))
    @commands.bot_has_permissions(embed_links=True, add_reactions=True, manage_messages=True)
    @commands.bot_has_guild_permissions(
        manage_channels=True, manage_permissions=True, manage_roles=True, manage_messages=True
    )
    @commands.cooldown(1, 15, type=commands.BucketType.guild)
    async def tourney(self, ctx: Context):
        """Create & Manage tournaments with versatilex"""
        if not Tourney.is_ignorable(ctx.author) and not ctx.author.guild_permissions.manage_guild:
            return await ctx.error(
                "You need either `Manage Server` permissions or `@tourney-mod` role to manage tournaments."
            )

        view = TourneyManager(ctx)
        view.add_item(QuotientView.tricky_invite_button())
        view.message = await ctx.send(embed=await view.initial_embed(), view=view)

    @commands.hybrid_command(
    aliases=("quickidp",),
    extras={"examples": ["idp 1234 pass Miramar #idp-channel", "idp 1234 pass Sanhok #idp-channel @role"]}
    )
    @commands.bot_has_permissions(embed_links=True, manage_messages=True)
    @checks.can_use_sm()
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def idp(self, ctx: Context, room_id: str, password: str, map: str, idp_channel: discord.TextChannel, role_to_ping: Optional[discord.Role] = None):
        """
        Share Id/pass with embed quickly in a specified channel.
        Message is automatically deleted after 30 minutes.
        """
        await ctx.message.delete(delay=0)

        # Fetch all valid idp channels for the guild
        valid_idp_channels = await fetch_all_idp_channels(ctx.bot, ctx.guild)
        
        if not valid_idp_channels:
            error_embed = discord.Embed(
                color=discord.Color.red(),
                description="Error: No valid ID/Pass channels configured for this server."
            )
            await ctx.send(embed=error_embed, delete_after=10)
            return

        # Validate that the provided channel is a text channel
        if not isinstance(idp_channel, discord.TextChannel):
            error_embed = discord.Embed(
                color=discord.Color.red(),
                description="Error: The specified channel is not a text channel."
            )
            await ctx.send(embed=error_embed, delete_after=10)
            return

        # Validate that the provided channel is one of the configured ID/Pass channels
        if idp_channel not in valid_idp_channels:
            valid_channels_mention = ", ".join([channel.mention for channel in valid_idp_channels])
            error_embed = discord.Embed(
                color=discord.Color.red(),
                description=f"Error: You can only share ID/Pass in one of these channels: {valid_channels_mention}."
            )
            await ctx.send(embed=error_embed, delete_after=10)
            return

        # Check bot permissions in the target channel
        bot_permissions = idp_channel.permissions_for(ctx.guild.me)
        if not (bot_permissions.view_channel and bot_permissions.send_messages and bot_permissions.embed_links):
            error_embed = discord.Embed(
                color=discord.Color.red(),
                description=f"Error: I don't have permission to view or send messages/embeds in {idp_channel.mention}."
            )
            await ctx.send(embed=error_embed, delete_after=10)
            return

        # Truncate inputs to prevent overly long fields
        room_id, password, map = truncate_string(room_id, 100), truncate_string(password, 100), truncate_string(map, 100)
        
        # Create the embed
        _e = discord.Embed(color=ctx.bot.color)
        _e.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)
           # Set description, including topic only if valid
        base_description = "**Just Click Below Button To claim ID/Pass**\n\n\n"
        if idp_channel.topic:
            try:
                if idp_channel.topic:
                    _e.description = f"{base_description}{idp_channel.topic}"
                else:
                    _e.description = base_description
            except ValueError:
                _e.description = base_description
        else:
            _e.description = base_description
            
            _e.set_footer(text="Auto-delete time")
            _e.timestamp = ctx.bot.current_time + timedelta(minutes=30)

        # Send the embed with optional role ping
        view = IdpView(room_id, password, map, idp_channel)
        msg = await idp_channel.send(
            content=role_to_ping.mention if role_to_ping else None,
            embed=_e,
            view=view,
            allowed_mentions=discord.AllowedMentions(roles=True),
        )
        # Schedule message deletion and click data cleanup
        await self.bot.wait_and_delete(msg, 60*30)  # Delete after 30 minutes (60 seconds)
       
        # Send confirmation
        confirm_embed = discord.Embed(
            color=ctx.bot.color,
            description=f"ID/Pass shared in {idp_channel.mention}."
        )
        await ctx.send(embed=confirm_embed, delete_after=10)

    @commands.group(aliases=("eztag",), invoke_without_command=True)
    async def easytag(self, ctx: Context):
        """Commands related to versatilex's eztag"""
        await ctx.send_help(ctx.command)

    @easytag.command(name="set", extras={"examples": ["eztag set #channel"]})
    # @checks.has_done_setup()
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def set_eztag(self, ctx: Context, *, channel: QuoTextChannel):
        """Set a channel as eztag channel."""
        count = await EasyTag.filter(guild_id=ctx.guild.id).count()
        guild = await Guild.get(guild_id=ctx.guild.id)

        if count == 1 and not guild.is_premium:
            return await ctx.error(
                f"Upgrade your server to versatilex Premium to setup more than 1 EasyTag channel.\n[Click Me to Purchase]({self.bot.prime_link})"
            )

        if channel.id in self.bot.cache.eztagchannels:
            return await ctx.error(f"This channel is already a easy tag channel.")

        if (
            not channel.permissions_for(ctx.me).send_messages
            or not channel.permissions_for(ctx.me).embed_links
            or not channel.permissions_for(ctx.me).manage_messages
        ):
            return await ctx.error(
                f"I need `send messages`, `embed links` and `manage messages` permission in {channel.mention}"
            )

        role = discord.utils.get(ctx.guild.roles, name="versatilex-tag-ignore")
        if not role:
            role = await ctx.guild.create_role(
                name="versatilex-tag-ignore", color=self.bot.color, reason=f"Created by {ctx.author}"
            )

        await EasyTag.create(guild_id=ctx.guild.id, channel_id=channel.id)
        self.bot.cache.eztagchannels.add(channel.id)

        embed = self.bot.embed(ctx, title="Easy Tagging")
        embed.description = """
        Unable to mention teammates while registering for scrims or tournaments? versatilex is here for the rescue.

        Use `teammate's ID`, `@teammate_name` or `@teammate's_discord_tag` in your registration format. versatilex will convert that into an actual discord tag.        
        """
        embed.set_image(url="")
        msg = await channel.send(embed=embed)
        await msg.pin()

        await ctx.success(
            f"Successfully added **{channel}** to easy tag channels.\n\nAdd {role.mention} to your roles to ignore your messages in **{channel}**"
        )

    @easytag.command(name="remove", extras={"examples": ["eztag remove #channel"]})
    # @checks.has_done_setup()
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def remove_eztag(self, ctx: Context, *, channel: QuoTextChannel):
        """Remove a eztag channel"""
        if not channel.id in self.bot.cache.eztagchannels:
            return await ctx.error(f"This is not a EasyTag channel.")

        await EasyTag.filter(channel_id=channel.id).delete()
        self.bot.cache.eztagchannels.discard(channel.id)
        await ctx.success(f"Removed {channel} from EasyTag channels.")

    @easytag.command(name="config")
    # @checks.has_done_setup()
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def config_eztag(self, ctx: Context):
        """Get a list of all your easytag channels."""
        records = await EasyTag.filter(guild_id=ctx.guild.id)
        if not records:
            return await ctx.error(
                f"You haven't set any easytag channel yet.\n\nUse `{ctx.prefix}eztag set #{ctx.channel}`"
            )

        eztags = []
        for idx, record in enumerate(records, start=1):
            channel = getattr(record.channel, "mention", record.channel_id)
            eztags.append(
                f"`{idx:02}.` {channel} (Delete After: {record.delete_after if record.delete_after else 'Not Set'})"
            )

        embed = self.bot.embed(ctx, title="EasyTag config", description="\n".join(eztags))
        await ctx.send(embed=embed)

    @easytag.command(name="autodelete", extras={"examples": ["eztag autodelete #channel"]})
    #    @checks.has_done_setup()
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def delete_eztag(self, ctx: Context, channel: QuoTextChannel):
        """Enable/Disable autodelete for eztag."""
        record = await EasyTag.get_or_none(channel_id=channel.id)
        if not record:
            return await ctx.error(f"This is not a EasyTag Channel.")

        await EasyTag.filter(channel_id=channel.id).update(delete_after=not record.delete_after)
        await ctx.success(
            f"Delete After for **{channel}** turned {'ON' if not record.delete_after else 'OFF'}!\n\nDelete After automatically deletes the format message after some time."
        )

    # ************************************************************************************************
    # ************************************************************************************************
    # ************************************************************************************************
    # ************************************************************************************************
    # ************************************************************************************************
    # ************************************************************************************************
    # ************************************************************************************************

    @commands.group(invoke_without_command=True, aliases=("tc",))
    async def tagcheck(self, ctx: Context):
        """
        Setup tagcheck channels for scrims/tournaments.
        """
        await ctx.send_help(ctx.command)

    @tagcheck.command(name="set", extras={"examples": ["tc set #channel 4", "tagcheck set #channel 2"]})
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    # @checks.has_done_setup()
    async def tagcheck_set(self, ctx: Context, channel: discord.TextChannel, mentions: int = 4):
        """
        Set a channel for tagcheck.
        mentions defines required mentions, It's 4 by default.
        """
        count = await TagCheck.filter(guild_id=ctx.guild.id).count()
        guild = await Guild.get(guild_id=ctx.guild.id)

        if count == 2 and not guild.is_premium:
            return await ctx.error(
                f"Upgrade your server to VersatileX Premium to setup more than 1 Tagcheck channel.\n[Click Me to Purchase]({self.bot.prime_link})"
            )

        if channel.id in self.bot.cache.tagcheck:
            return await ctx.error(f"This channel is already a tagcheck channel.")

        if (
            not channel.permissions_for(ctx.me).send_messages
            or not channel.permissions_for(ctx.me).embed_links
            or not channel.permissions_for(ctx.me).manage_messages
        ):
            return await ctx.error(
                f"I need `send_messages`, `embed_links` and `manage_messages` permission in {channel.mention}"
            )

        role = discord.utils.get(ctx.guild.roles, name="versatilex-tag-ignore")
        if not role:
            role = await ctx.guild.create_role(
                name="versatilex-tag-ignore", color=self.bot.color, reason=f"Created by {ctx.author}"
            )

        await TagCheck.create(guild_id=ctx.guild.id, channel_id=channel.id, required_mentions=mentions)
        self.bot.cache.tagcheck.add(channel.id)

        await ctx.success(
            f"Successfully added **{channel}** to tagcheck channels.\n\nAdd {role.mention} to your roles to ignore your messages in **{channel}**"
        )

    @tagcheck.command(name="config")
    # @checks.has_done_setup()
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def tagcheck_config(self, ctx: Context):
        """
        Get tagcheck config.
        """
        records = await TagCheck.filter(guild_id=ctx.guild.id)
        if not records:
            return await ctx.error(
                f"You haven't set any tagcheck channel yet.\n\nUse `{ctx.prefix}tagcheck set #{ctx.channel}`"
            )

        tags = []
        for idx, record in enumerate(records, start=1):
            channel = getattr(record.channel, "mention", record.channel_id)
            tags.append(
                f"`{idx:02}.` {channel} (Mentions: {record.required_mentions},Auto-delete: {record.delete_after if record.delete_after else 'Not Set'})"
            )

        embed = self.bot.embed(ctx, title="TagCheck config", description="\n".join(tags))
        await ctx.send(embed=embed)

    @tagcheck.command(name="remove", extras={"examples": ["tagcheck remove #channel"]})
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def tagcheck_remove(self, ctx: Context, *, channel: QuoTextChannel):
        """Remove a channel from tagcheck"""
        if not channel.id in self.bot.cache.tagcheck:
            return await ctx.error(f"This is not a TagCheck channel.")

        await TagCheck.filter(channel_id=channel.id).delete()
        self.bot.cache.tagcheck.discard(channel.id)
        await ctx.success(f"Removed {channel} from TagCheck channels.")

    @tagcheck.command(name="autodelete", extras={"examples": ["tagcheck autodelete #channel"]})
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def tagcheck_autodelete(self, ctx: Context, *, channel: QuoTextChannel):
        """Enable/Disable autodelete wrong tagchecks."""
        record = await TagCheck.get_or_none(channel_id=channel.id)
        if not record:
            return await ctx.error(f"This is not a TagCheck Channel.")

        await TagCheck.filter(channel_id=channel.id).update(delete_after=not record.delete_after)
        await ctx.success(
            f"Autodelete for **{channel}** turned {'ON' if not record.delete_after else 'OFF'}!\nThis automatically deletes the wrong format message after some time."
        )

    # ************************************************************************************************
    # ************************************************************************************************
    # ************************************************************************************************
    # ************************************************************************************************
    # ************************************************************************************************
    # ************************************************************************************************
    # ************************************************************************************************

    @commands.command(aliases=("slotm",))
    @checks.can_use_sm()
    @commands.bot_has_guild_permissions(embed_links=True, manage_messages=True, manage_channels=True)
    # # @checks.has_done_setup()
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def slotmanager(self, ctx: Context):
        """
        SlotManager helps people to setup scrims-slots cancel and claim manager.
        Users can easily claim and cancel their slots anytime without bothering mods.
        """
        _view = ScrimsSlotManagerSetup(ctx)
        _e = await _view.initial_message(ctx.guild)
        _view.add_item(QuotientView.tricky_invite_button())
        _view.message = await ctx.send(embed=_e, view=_view, embed_perms=True)

    @commands.command(name="banlog", extras={"examples": ["banlog #channel"]})
    @checks.can_use_sm()
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def _banlog(self, ctx: Context, *, channel: discord.TextChannel = None):
        """
        Set a channel for all scrims ban/unban logs
        """
        if not channel:
            record = await BanLog.get_or_none(guild_id=ctx.guild.id)
            if not record:
                return await ctx.simple(
                    f"You haven't setup any esports ban log channel yet.\n"
                    f"Use `{ctx.prefix}banlog #{ctx.channel}` to do it."
                )
            return await ctx.simple(
                f"Currently {getattr(record.channel, 'mention', 'deleted-channel')} is serving as ban/unban log channel."
            )
        if not channel.permissions_for(ctx.me).embed_links:
            return await ctx.error(f"I need `embed_links` permission in {channel.mention} to send logs.")

        await BanLog.update_or_create(guild_id=ctx.guild.id, defaults={"channel_id": channel.id})
        await ctx.success(f"Successfully set {channel.mention} as esports ban/unban log channel.")

    @commands.group(invoke_without_command=True, aliases=("ss",))
    @checks.can_use_tm()
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    @commands.bot_has_permissions(manage_channels=True, add_reactions=True, embed_links=True, manage_roles=True)
    async def ssverify(self, ctx: Context):
        """
        Setup/Edit ssverification in your server
        """
        if not await ctx.is_premium_guild():
            if not ctx.guild.member_count > 100 and not ctx.guild.id == 779229001986080779:
                return await ctx.error("Your server must have atleast 100 members to setup ssverification.")

        _view = SsmodMainView(ctx)
        _view.message = await ctx.send(embed=await _view.initial_message(), view=_view, embed_perms=True)
    
    @commands.command(name="sban")
    async def scrimban(self, ctx: Context, user: discord.Member):
        """Manage bans for scrims"""
        if not any((ctx.author.guild_permissions.manage_guild, Scrim.is_ignorable(ctx.author))):
            return await ctx.error(f"You need `scrims-mod` role or `Manage-Server` permissions to use this command.")
        
        view = ScrimBanView(ctx, user)
        await view._add_buttons()
        embed = await view.initial_message
        view.message = await ctx.send(embed=embed, view=view)

    
    
    

async def setup(bot: Quotient):
    await bot.add_cog(ScrimManager(bot))
    await bot.add_cog(SMError(bot))
    await bot.add_cog(ScrimEvents(bot)) 
    await bot.add_cog(TourneyEvents(bot))
    await bot.add_cog(ScrimsCog(bot))
    await bot.add_cog(TagEvents(bot))
    await bot.add_cog(Ssverification(bot))

    await bot.add_cog(SlotManagerEvents(bot))
    await bot.add_cog(SlashCog(bot)) 
    await bot.add_cog(IdpCog(bot))
