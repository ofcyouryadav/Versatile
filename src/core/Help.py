from __future__ import annotations

from difflib import get_close_matches
from typing import List, Mapping
from collections import namedtuple

import discord
from discord.ext import commands


# Configuration
class Config:
    SERVER_LINK = "https://discord.gg/bFVKBdbNBN"
    BOT_INVITE = "https://discord.com/oauth2/authorize?client_id=1321690284551049256&permissions=8&integration_type=0&scope=bot"


config = Config()


# Placeholder Guild class
class Guild:
    id: int
    is_premium: bool
    premium_end_time: int

    @classmethod
    async def get_or_none(cls, pk: int) -> 'Guild | None':
        guild = Guild()
        guild.id = pk
        guild.is_premium = False
        guild.premium_end_time = 1617753600
        return guild if pk % 2 == 0 else None


# LinkButton view for embeds
class LinkButton(discord.ui.View):
    def __init__(self, links: List['Link']):
        super().__init__()
        for link in links:
            self.add_item(discord.ui.Button(label=link.name, url=link.url, emoji=link.emoji))


Link = namedtuple("Link", ["name", "url", "emoji"])


# Utility functions
def discord_timestamp(timestamp: int) -> str:
    return f"<t:{timestamp}:R>"


def truncate_string(text: str, max_length: int) -> str:
    return text[:max_length] + "..." if len(text) > max_length else text


# Base Cog class
class Cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.qualified_name = self.__class__.__name__

    def get_commands(self):
        return [cmd for cmd in self.bot.commands if cmd.cog == self]


# Custom HelpCommand
class HelpCommand(commands.HelpCommand):
    def __init__(self) -> None:
        super().__init__(
            verify_checks=False,
            command_attrs={
                "cooldown": commands.CooldownMapping.from_cooldown(1, 8.0, commands.BucketType.member),
                "help": "Shows help about the bot, a command, or a category",
            },
        )

    @property
    def color(self):
        return self.context.bot.color if hasattr(self.context.bot, 'color') else discord.Color.blue()

    async def send_bot_help(self, mapping: Mapping[Cog, List[commands.Command]]):
        ctx = self.context

        hidden = ("HelpCog", "Dev" ,"ScrimsCog")

        embed = discord.Embed(color=self.color)

        server = f"[Support Server]({config.SERVER_LINK})"
        p = f"[Privacy & policy](https://docs.google.com/document/d/1j2NanGw-F-1wGsl77w15yTc9lVL12D7i7wucxOi7D6g/edit?usp=sharing)"
        embed.description = f"{server} & {p}\n\n"

        print(f"Guild ID: {ctx.guild.id}")
        try:
            guild = await Guild.get_or_none(pk=ctx.guild.id)
            print(f"Guild fetched: {guild}")
        except Exception as e:
            print(f"Database error: {e}")
            guild = None

        if guild and guild.is_premium:
            embed.description += f"<a:top_user:807911932299837460> [__Server Premium ending:__]({config.SERVER_LINK}) {discord_timestamp(guild.premium_end_time)}"

        

        total_length = len(embed.description)
        for cog, cmds in mapping.items():
            if cog and cog.qualified_name not in hidden and await self.filter_commands(cmds, sort=True):
                # Filter out hidden commands
                command_list = [f"`{cmd}`" for cmd in cog.get_commands() if not cmd.hidden]
                print(f"Cog: {cog.qualified_name}, Commands: {command_list}")  # Debug
                value = ", ".join(command_list)
                if not value:
                    continue
                if len(value) > 1024:
                    truncated = []
                    current_length = 0
                    for cmd in command_list:
                        if current_length + len(cmd) + 2 <= 1000:
                            truncated.append(cmd)
                            current_length += len(cmd) + 2
                        else:
                            break
                    value = ", ".join(truncated) + ", ..."
                embed.add_field(
                    inline=False,
                    name=cog.qualified_name.title(),
                    value=value,
                )
                total_length += len(cog.qualified_name.title()) + len(value) + 10
                if total_length > 5500:
                    embed.add_field(
                        name="Note",
                        value="Some categories omitted due to size limits.",
                        inline=False,
                    )
                    break

        links = [
            Link(name="Support", url=config.SERVER_LINK, emoji=None),
        ]

        valid_links = [link for link in links if link.url]
        if not valid_links:
            embed.add_field(name="Error", value="No valid links available.", inline=False)
        else:
            await ctx.send(embed=embed, view=LinkButton(valid_links))

    async def send_group_help(self, group: commands.Group):
        prefix = self.context.prefix

        if not group.commands:
            return await self.send_command_help(group)

        embed = discord.Embed(color=self.color)

        embed.title = f"{group.qualified_name} {group.signature}"
        _help = group.help or "No description provided..."

        _cmds = "\n".join(f"`{prefix}{c.qualified_name}` : {truncate_string(c.short_doc, 60)}" for c in group.commands)

        embed.description = f"> {_help}\n\n**Subcommands**\n{_cmds}"

        embed.set_footer(text=f'Use "{prefix}help <command>" for more information.')

        if group.aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join(f"`{aliases}`" for aliases in group.aliases),
                inline=False,
            )

        examples = []
        if group.extras:
            if _gif := group.extras.get("gif"):
                embed.set_image(url=_gif)

            if _ex := group.extras.get("examples"):
                examples = [f"{self.context.prefix}{i}" for i in _ex]

        if examples:
            examples_str = "\n".join(examples)
            embed.add_field(name="Examples", value=f"```{examples_str}```")

        await self.context.send(embed=embed)

    async def send_cog_help(self, cog: Cog):
        embed = discord.Embed(color=self.color, title=f"{cog.qualified_name.title()}")
        c = 0
        for cmd in cog.get_commands():
            if not cmd.hidden:
                _brief = "No Information..." if not cmd.short_doc else truncate_string(cmd.short_doc, 60)
                embed.add_field(name=cmd.qualified_name, value=_brief, inline=True)
                c += 1
        embed.set_footer(text=f"Total commands: {c}")
        await self.context.send(embed=embed)

    async def send_command_help(self, cmd: commands.Command):
        embed = discord.Embed(color=self.color)
        embed.title = "Command: " + cmd.qualified_name

        examples = []

        alias = ",".join((f"`{alias}`" for alias in cmd.aliases)) if cmd.aliases else "No aliases"
        _text = (
            f"**Description:** {cmd.help or 'No help found...'}\n"
            f"**Usage:** `{self.get_command_signature(cmd)}`\n"
            f"**Aliases:** {alias}\n"
            f"**Examples:**"
        )

        if cmd.extras:
            if _gif := cmd.extras.get("gif"):
                embed.set_image(url=_gif)

            if _ex := cmd.extras.get("examples"):
                examples = [f"{self.context.prefix}{i}" for i in _ex]

        examples_str = "\n".join(examples) if examples else "Command has no examples"
        _text += f"```{examples_str}```"

        embed.description = _text

        await self.context.send(embed=embed)

    async def command_not_found(self, string: str):
        message = f"Could not find the `{string}` command. "
        commands_list = (str(cmd) for cmd in self.context.bot.walk_commands())

        if dym := "\n".join(get_close_matches(string, commands_list)):
            message += f"Did you mean...\n{dym}"

        return message



