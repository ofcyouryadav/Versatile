import discord
from utils import emote as em

tick = em.check
cross = em.xmark
def error_embed(message: str) -> discord.Embed:
    """
    Create an error embed with the given message.
    """
    embed = discord.Embed(
        title="",
        description=f"{cross} | {message}",
        color=discord.Color.red()
    )
    return embed
def success_embed(message: str) -> discord.Embed:
    """
    Create a success embed with the given message.
    """
    embed = discord.Embed(
        title="",
        description=f"{tick} | {message}",
        color=discord.Color.green()
    )
    return embed

def config_embed(roles: list, guild: discord.Guild) -> discord.Embed:
    embed = discord.Embed(title=f"custom role for {guild.name}", color=discord.Color.green())
    if not roles:
        embed.description = "No Custom Roles Setuped."
        return embed
    for role in roles:
        discord_role = guild.get_role(role.role_id)
        if discord_role:
            
            embed.add_field(name=discord_role.name, value=f"ID: {discord_role.id}", inline=False)
        else:
            embed.add_field(name="Unknown Role", value=f"ID: {role.role_id}", inline=False)     
            
    return embed        
