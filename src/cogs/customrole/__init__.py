from __future__ import annotations

from sqlite3 import OperationalError
import typing

from cogs.esports.events.slots import SlotManagerEvents
from cogs.esports.views.scrims.main import ScrimsMain
from cogs.esports.views.tourney.main import TourneyManager

if typing.TYPE_CHECKING:
    from core import Quotient

from tortoise.exceptions import ConfigurationError, IntegrityError
import discord
from discord.ext import commands

from core import Cog, Context, QuotientView
from models.esports.custom_role import CustomRole, Moderator
from utils import QuoRole, QuoTextChannel, checks
from .view import *
from .events import *

class Customrole(Cog, name="Custom role"):
    def __init__(self, bot: Quotient):
        self.bot = bot
    
    @commands.group(name="moderator", aliases=["mod"], invoke_without_command=True)
    async def mod(self, ctx: Context):
        """Custom role moderator management commands."""
        await ctx.send(embed=error_embed("Please Use a Subcommand: add, remove, list"))    
        
    @commands.has_permissions(manage_guild=True)    
    @mod.command(name="add", aliases=["a"])
    async def add_mod(self, ctx: Context, user: discord.User):
        """Add a user as a moderator for the custom role system."""
        if not ctx.guild:
            return await ctx.send("This command can only be used in a server.")
        
        mod = await Moderator.get_or_none(guild_id=ctx.guild.id, user_id=user.id)
        if mod:
            return await ctx.send(embed=error_embed(f"{user.mention} is already a moderator."))
        
        try:
            await Moderator.create(guild_id=ctx.guild.id, user_id=user.id)
            await ctx.send(embed=success_embed(f"{user.mention} has been added as a moderator."))
        except IntegrityError:
            await ctx.send(embed=error_embed(f"{user.mention} is already a moderator (database error)."))
    
    @commands.has_permissions(manage_guild=True)
    @mod.command(name="remove", aliases=["r"])
    async def remove_mod(self, ctx: Context, user: discord.User):
        """Remove a user as a moderator for the custom role system."""
        if not ctx.guild:
            return await ctx.send("This command can only be used in a server.")
        
        mod = await Moderator.get_or_none(guild_id=ctx.guild.id, user_id=user.id)
        if not mod:
            return await ctx.send(embed=error_embed(f"{user.mention} is not a moderator."))
        
        await mod.delete()
        await ctx.send(embed=success_embed(f"{user.mention} has been removed as a moderator."))
    
    @commands.has_permissions(manage_guild=True)
    @mod.command(name="list", aliases=["l"])
    async def list_mods(self, ctx: Context):
        """List all moderators for the custom role system."""
        if not ctx.guild:
            return await ctx.send("This command can only be used in a server.")
        
        mods = await Moderator.filter(guild_id=ctx.guild.id)
        if not mods:
            return await ctx.send(embed=error_embed("No moderators found."))
        
        mod_list = "\n".join([f"{self.bot.get_user(mod.user_id).mention or f'User ID: {mod.user_id}'}" for mod in mods])
        await ctx.send(embed=success_embed(f"Moderators:\n{mod_list}"))    
        
    @commands.group(name="cr", invoke_without_command=True)
    async def custom_role(self, ctx: Context):
        """Custom role management commands."""
        await ctx.send(embed=error_embed("Please Use a Subcommand: create, delete, config"))
        
    @custom_role.command(name="create", aliases=["c"])
    async def create_role_custom(self, ctx: Context, role: discord.Role, name: str):
        """Create a custom role."""
        if not ctx.guild:
            return await ctx.send("This command can only be used in a server.")
        
        mod = await Moderator.filter(guild_id=ctx.guild.id, user_id=ctx.author.id).first()
        if not mod:
            return await ctx.send(embed=error_embed("You must be a moderator to use this command."))
        
        custom_role_count = await CustomRole.filter(guild_id=ctx.guild.id).count()
    
        # Check if the server has more than 3 custom roles and doesn't meet premium or member count conditions
        if custom_role_count >= 3:
            if not await ctx.is_premium_guild():
                return await ctx.send(embed=error_embed(
                    "Your server has reached the maximum of 3 custom roles. "
                    "Premium servers can set up unlimited custom roles."
                ))
        
        existing = await CustomRole.get_or_none(guild_id=ctx.guild.id, name=name)
        if existing:
            return await ctx.send(embed=error_embed(f"A custom role with the name {name} already exists."))
        
        existing_role = await CustomRole.get_or_none(guild_id=ctx.guild.id, role_id=role.id)
        if existing_role:
            return await ctx.send(embed=error_embed(f"The role {role.name} is already a custom role."))
        
        await CustomRole.create(guild_id=ctx.guild.id, role_id=role.id, name=name)
        await ctx.send(embed=success_embed(f"Custom role `{name}` has been created with the role `{role.name}`."))
        
    @custom_role.command(name="delete", aliases=["d"])
    async def delete_role_custom(self, ctx: Context, role: discord.Role):
        """Delete a custom role."""
        if not ctx.guild:
            return await ctx.send("This command can only be used in a server.")
        
        mod = await Moderator.filter(guild_id=ctx.guild.id, user_id=ctx.author.id).first()
        if not mod:
            return await ctx.send(embed=error_embed("You must be a moderator to use this command."))
        
        existing = await CustomRole.get_or_none(guild_id=ctx.guild.id, role_id=role.id)
        if not existing:
            return await ctx.send(embed=error_embed(f"The role {role.name} is not a custom role."))
        
        await existing.delete()
        await ctx.send(embed=success_embed(f"Custom role {role.name} has been deleted."))
        
    @custom_role.command(name="config")
    async def config_role_custom(self, ctx: Context):
        """List all custom roles."""
        if not ctx.guild:
            return await ctx.send("This command can only be used in a server.")
        
        roles = await CustomRole.filter(guild_id=ctx.guild.id)
        await ctx.send(embed=config_embed(roles, ctx.guild))
        
async def setup(bot: Quotient):
    await bot.add_cog(Customrole(bot))
    await bot.add_cog(Customroleevents(bot))
