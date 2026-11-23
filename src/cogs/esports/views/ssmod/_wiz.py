from __future__ import annotations

import discord
from datetime import datetime

import config
from core import Context
from models import SSVerify
from utils import keycap_digit as kd

from ...views.base import EsportsBaseView
from ._buttons import *

__all__ = ("SetupWizard",)


class SetupWizard(EsportsBaseView):
    def __init__(self, ctx: Context):
        super().__init__(ctx, timeout=180)  # Extended timeout for complex setup

        self.ctx = ctx
        self.record = None

        # Add buttons in logical order
        self.add_item(SetChannel(ctx))
        self.add_item(SetRole(ctx))
        self.add_item(RequiredSS(ctx))
        self.add_item(ScreenshotType(ctx))
        self.add_item(PageName(ctx))
        self.add_item(PageLink(ctx))
        self.add_item(AllowSame())
        self.add_item(DiscardButton())
        self.add_item(SaveButton(ctx))

    def initial_message(self):
        if not self.record:
            self.record = SSVerify(guild_id=self.ctx.guild.id)

        # Modernized embed
        _e = discord.Embed(
            color=self.ctx.bot.color,
            title="Setup Screenshot Verification",
            url=config.SERVER_LINK,
            description=(
                "Configure your screenshot verification below.\n"
                "Set all required fields (*) and press **Save** to complete.\n"
                "_Need help? Join our [Support Server]({0})_".format(config.SERVER_LINK)
            )
        )

        # Progress indicator
        required_fields = [
            self.record.channel_id,
            self.record.role_id,
            self.record.required_ss,
            self.record.ss_type,
            self.record.channel_name,
        ]
        progress = sum(1 for field in required_fields if field)
        _e.set_footer(
            text=f"Progress: {progress}/5 required fields | VersatileX",
            icon_url=self.ctx.author.display_avatar.url
        )
        _e.timestamp = datetime.utcnow()

        # Field definitions with clearer formatting
        fields = {
            "Channel*": getattr(self.record.channel, "mention", "`Not set`"),
            "Role*": getattr(self.record.role, "mention", "`Not set`"),
            "Required Screenshots*": f"{self.record.required_ss or '`Not set`'}",
            "Screenshot Type*": "Not set" if not self.record.ss_type else self.record.ss_type.value.title(),
            "Page Name*": self.record.channel_name or "`Not set`",
            "Page URL": "`Not set (optional)`" if self.record.channel_link == config.SERVER_LINK else f"[Click Here]({self.record.channel_link})",
            "Allow Same Screenshot": "Yes" if self.record.allow_same else "`No`",
        }

        for idx, (name, value) in enumerate(fields.items(), start=1):
            _e.add_field(
                name=f"{kd(idx)} {name}",
                value=f"{value}",
                inline=True if idx % 2 == 1 else False  # Two columns for compactness
            )

        return _e

    async def refresh_view(self):
        _e = self.initial_message()

        # Enable Save button only when all required fields are set
        required_fields = [
            self.record.channel_id,
            self.record.role_id,
            self.record.required_ss,
            self.record.ss_type,
            self.record.channel_name,
        ]
        self.children[-1].disabled = not all(required_fields)

        try:
            self.message = await self.message.edit(embed=_e, view=self)
        except discord.HTTPException:
            await self.on_timeout()

    # Optional: Add a help button
    @discord.ui.button(
        emoji="❓",
        style=discord.ButtonStyle.green,
        row=2  # Place in a new row if needed
    )
    async def help_button(self, interaction: discord.Interaction, button: discord.Button):
        _e = discord.Embed(
            color=self.ctx.bot.color,
            title="❓ Setup Wizard Help",
            description=(
                "Steps to configure screenshot verification:\n"
                "1. **Channel**: Set where verification messages are sent.\n"
                "2. **Role**: Choose the role awarded upon verification.\n"
                "3. **Required Screenshots**: Specify how many screenshots are needed.\n"
                "4. **Screenshot Type**: Select the type (e.g., app-specific).\n"
                "5. **Page Name**: Define a name for the verification page.\n"
                "6. **Page URL**: Add an optional link for reference.\n"
                "7. **Allow Same Screenshot**: Toggle if duplicates are allowed.\n\n"
                f"**Stuck?** Join our [Support Server]({config.SERVER_LINK})!"
            )
        )
        await interaction.response.send_message(embed=_e, ephemeral=True)