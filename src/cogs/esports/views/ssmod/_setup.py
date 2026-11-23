from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core import Quotient

import discord
from datetime import datetime

from core import Context
from models import SSVerify
from utils import emote

from ...views.base import EsportsBaseView
from ._edit import SSmodEditor
from ._wiz import SetupWizard


class SsmodMainView(EsportsBaseView):
    def __init__(self, ctx: Context):
        super().__init__(ctx, timeout=120, title="Screenshots Manager")  # Extended timeout for better UX

        self.ctx = ctx
        self.bot: Quotient = ctx.bot

    async def initial_message(self):
        records = await SSVerify.filter(guild_id=self.ctx.guild.id).order_by("id")
        if not records:
            self.children[-2].disabled = True  # Disable "Change Settings" if no records

        # Format records with cleaner layout
        _to_show = [f"`{idx}.` {_.__str__()}" for idx, _ in enumerate(records, start=1)]
        _sm = "\n".join(_to_show) if _to_show else "No screenshot verifications set up yet.\nClick **Setup** to create one!"

        # Modernized embed
        _e = discord.Embed(
            color=self.bot.color,
            title="Screenshot Verification Manager",
            url=self.ctx.config.SERVER_LINK
        )
        _e.description = (
            f"Welcome to the Screenshot Verification Manager!\n"
            f"Configure and manage screenshot verification for your server.\n\n"
            f"**Current Configurations**\n{_sm}"
        )
        _e.set_thumbnail(url=self.bot.user.display_avatar.url)
        _e.set_footer(text=f"Managed by VersatileX • Need help? Click ❓")
        _e.timestamp = datetime.utcnow()  # Add timestamp for freshness
        return _e

    @discord.ui.button(
        label="New Setup",
        custom_id="setup_ssverify_button",
        emoji="<:emoji_1744363953332:1360185749064126537>",
        style=discord.ButtonStyle.primary  # Blue button for primary action
    )
    async def setup_ssverify_button(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.defer()

        if not await self.ctx.is_premium_guild():
            if await SSVerify.filter(guild_id=self.ctx.guild.id).exists():
                return await self.ctx.premium_mango(
                    "You need VersatileX Premium to set up more than one screenshot verification."
                )

        view = SetupWizard(self.ctx)
        _e = view.initial_message()
        view.message = await interaction.followup.send(embed=_e, view=view)

    @discord.ui.button(
        label="Edit Settings",
        custom_id="edit_ssmod_config",
        emoji="<a:emoji_1744364042370:1360186122231218382>",
        style=discord.ButtonStyle.secondary  # Grey for secondary action
    )
    async def edit_ssmod_config(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.defer()

        records = await SSVerify.filter(guild_id=self.ctx.guild.id).order_by("id")
        if not records:
            return await interaction.followup.send(
                embed=discord.Embed(
                    color=discord.Color.red(),
                    description="No configurations available to edit. Set up a new one first!"
                ),
                ephemeral=True
            )

        _view = SSmodEditor(self.ctx, records)
        await _view._add_buttons(self.ctx)
        _view.message = await interaction.followup.send(embed=await _view.initial_embed(records[0]), view=_view)

    @discord.ui.button(
        emoji="❓",
        custom_id="info_ssmod_button",
        style=discord.ButtonStyle.green  # Green for help/FAQ
    )
    async def stop_ssmod_button(self, interaction: discord.Interaction, button: discord.Button):
        _e = discord.Embed(
            color=self.bot.color,
            title="❓ Screenshot Manager Help",
            url=self.ctx.config.SERVER_LINK
        )
        _e.description = (
            "Quick guide to managing screenshot verifications:\n\n"
            "1. **Set Up a New Verification**:\n"
            "   Use the `New Setup` button to create a new verification flow.\n"
            "2. **Edit Existing Settings**:\n"
            "   Modify configurations with the `Edit Settings` button.\n"
            "3. **Custom Filters**:\n"
            "   Tailor verifications for specific apps or screenshot types.\n"
            f"**Need more help?** Join our [Support Server]({self.ctx.config.SERVER_LINK})!"
        )
        _e.set_footer(text="We're here to assist!")
        await interaction.response.send_message(embed=_e, ephemeral=True)