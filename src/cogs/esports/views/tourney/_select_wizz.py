from __future__ import annotations
import discord
from discord.ui import Select
from core import Context
from models import Tourney
from ._base import TourneyView
from ._wiz import TourneySetupWizard
from ._editor import TourneyEditor
import asyncio

class TselectSetup(TourneyView):
    record: Tourney

    def __init__(self, ctx: Context):
        super().__init__(ctx, timeout=None)
        self.ctx = ctx
        self.record = None

    async def get_tourney_record(self):
        # Placeholder: Replace with your DB query, e.g., fetch latest tournament
        return await Tourney.filter(guild_id=self.ctx.guild.id).first()

    @property
    def select_options(self):
        options = [discord.SelectOption(label="Create Tournament", value="_create_t", emoji="🏆")]
        if self.record or asyncio.get_event_loop().run_until_complete(self.get_tourney_record()):
            options.append(discord.SelectOption(label="Edit Tournament", value="_edit_t", emoji="📝"))
        return options

    @discord.ui.select(placeholder="Select a Configuration", options=[])
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Only the command author can use this menu!", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        value = select.values[0]
        await self.handle_view(interaction, value)

    async def handle_view(self, interaction: discord.Interaction, value: str):
        try:
            if value == "_create_t":
                view = TourneySetupWizard(self.ctx)
                content = "Please fill out the tournament details below:"
                print("Received value: 1")
            elif value == "_edit_t":
                self.record = self.record or await self.get_tourney_record()
                if not self.record:
                    return await interaction.followup.send("No tournament found to edit!", ephemeral=True)
                view = TourneyEditor(self.ctx, self.record)  # Pass record
                content = "Please edit the tournament details below:"
                print("Received value: 2")

            await interaction.followup.send(
                content=content,
                view=view,
                embed=view.initial_message(),
                ephemeral=False
            )
        except (discord.Forbidden, Exception) as e:
            await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)