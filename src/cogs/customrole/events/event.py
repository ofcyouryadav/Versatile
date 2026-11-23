from core import Cog, Quotient
import discord
from discord.ext import commands
from models.esports.custom_role import CustomRole, Moderator
from ..view import error_embed, success_embed, config_embed

class Customroleevents(Cog):
    def __init__(self, bot: Quotient):
        self.bot = bot  

    @Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        # Avoid processing bot messages or DMs
        if not message.guild or message.author.bot:
            return
        
        # Process custom role logic
        await self.custom_role(message)
        
    async def custom_role(self, message: discord.Message):
        # Query the CustomRole model
        custom_role_instance = await CustomRole.get_or_none(
            guild_id=message.guild.id, name=message.content.lower()
        )
        
        # If no custom role is found, stop processing
        if not custom_role_instance:
            return
        
        # Check if the user is a moderator
        mod = await Moderator.filter(guild_id=message.guild.id, user_id=message.author.id).first()
        if not mod:
            await message.channel.send(embed=error_embed("You must be a moderator to use this command."))
            return
        
        # Get the role from the guild
        role = message.guild.get_role(custom_role_instance.role_id)
        if not role:
            await message.channel.send(embed=error_embed("The custom role does not exist."))
            return
        
        # Check role hierarchy
        if role.position >= message.guild.me.top_role.position:
            await message.channel.send(embed=error_embed("The role is above my highest role."))
            return
        
        # Determine the target user
        target_user = None
        if message.mentions:
            target_user = message.mentions[0]  # First mentioned user
        elif message.reference and message.reference.message_id:
            try:
                referenced_message = await message.channel.fetch_message(message.reference.message_id)
                target_user = referenced_message.author
            except discord.NotFound:
                await message.channel.send(embed=error_embed("The referenced message could not be found."))
                return
        else:
            await message.channel.send(embed=error_embed("You must mention a user or reply to a message."))
            return
        
        # Ensure target_user is a member of the guild
        if not isinstance(target_user, discord.Member):
            await message.channel.send(embed=error_embed("The target user is not a member of this server."))
            return
        
        # Add or remove the role
        try:
            if role in target_user.roles:
                await target_user.remove_roles(role)
                await message.channel.send(embed=success_embed(f"Removed {role.name} from {target_user.mention}."))
            else:
                await target_user.add_roles(role)
                await message.channel.send(embed=success_embed(f"Added {role.name} to {target_user.mention}."))
        except discord.Forbidden:
            await message.channel.send(embed=error_embed("I don't have permission to manage roles."))
        except discord.HTTPException as e:
            await message.channel.send(embed=error_embed(f"An error occurred: {e}"))

