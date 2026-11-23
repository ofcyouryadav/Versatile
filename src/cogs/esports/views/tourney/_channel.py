from __future__ import annotations
from contextlib import suppress
import discord
from core import Context
from utils import emote, inputs, regional_indicator1 as ri, truncate_string
from ._base import TourneyButton
from ._callback_channel import TourneyChannelcall

class TourneyChannel(discord.ui.Select):
    def __init__(self, ctx: Context, view: discord.ui.View) -> None:
        self.ctx = ctx
        self.custom_view = view  # Store the TourneyView instance

        options = [
            discord.SelectOption(
                label="Info Channel",
                value="info_channel",
                description="Create an info channel for the tournament.",
            ),
            discord.SelectOption(
                label="Update Channel",
                value="update_channel",
                description="Create an update channel for this tournament.",
            ),
            discord.SelectOption(label="roadmap", value="roadmap", description="Create a roadmap channel for this tournament."),
            discord.SelectOption(label="Schedule", value="schedule", description="Create a schedule channel for this tournament."),
            discord.SelectOption(label="rules", value="rules", description="Create a rules channel for this tournament."),
            discord.SelectOption(label="Prize Distribution", value="prize_distribution", description="Create a prize distribution channel for this tournament."),
            discord.SelectOption(label="how to register", value="how_to_register", description="Create a how to register channel for this tournament."),
            discord.SelectOption(label="tag-check ", value="tag-check", description="Create a tag-check channel for this tournament."),
            discord.SelectOption(label="register here", value="register here", description="Create a register here channel for this tournament."),
            discord.SelectOption(label="Confirm-teams", value="Confirm-teams", description="Create a Confirm-teams channel for this tournament."),
            discord.SelectOption(label="support-chat(text channel)", value="support-chat", description="Create a support-chat channel for this tournament."),
            discord.SelectOption(label="support-voice", value="support-voice", description="Create a support-voice channel for this tournament."),
        ]

        super().__init__(
            placeholder="Select Channel Types",
            min_values=1,
            max_values=len(options),  # Allow selecting all options (e.g., 2)
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        # Instantiate TourneyChannelcall with ctx and custom_view
        caller = TourneyChannelcall(self.ctx, self.custom_view)

        # Process each selected option
        for selected_value in self.values:
            if selected_value == "info_channel":
                await caller.info_channel(interaction)
            elif selected_value == "update_channel":
                await caller.update_channel(interaction)
            elif selected_value == "roadmap":
                await caller.road_map(interaction)   
            elif selected_value == "schedule":
                await caller.schedule_chan(interaction) 
            elif selected_value == "rules":
                await caller.rules_chan(interaction)
            elif selected_value == "prize_distribution":
                await caller.prize_distributaion_chan(interaction)
            elif selected_value == "how_to_register":
                await caller.how_to_register(interaction)
            elif selected_value == "tag-check": 
                await caller.tag_check(interaction)  
            elif selected_value == "register here": 
                await caller.register_here(interaction)
            elif selected_value == "Confirm-teams":
                await caller.confirm_team(interaction)                          
            elif selected_value == "support-chat":
                await caller.support_chat(interaction)
            elif selected_value == "support-voice":
                await caller.support_voice(interaction)
                    
class ChannelNameModal(discord.ui.Modal, title="Set Channel Name"):
    channel_name = discord.ui.TextInput(
        label="Channel Name",
        placeholder="Enter the custom channel name",
        max_length=100,
        required=True,
    )

    def __init__(self, view: discord.ui.View):
        super().__init__()
        self.custom_view = view

    async def on_submit(self, interaction: discord.Interaction):
        self.custom_view.channel_name = self.channel_name.value
        await interaction.response.send_message(
            f"Channel name set to: {self.channel_name.value}", ephemeral=True
        )

class CategoryNameModal(discord.ui.Modal, title="Set Category Name"):
    category_name = discord.ui.TextInput(
        label="Category Name",
        placeholder="Enter the category name",
        max_length=100,
        required=True,
    )

    def __init__(self, view: discord.ui.View):
        super().__init__()
        self.custom_view = view

    async def on_submit(self, interaction: discord.Interaction):
        self.custom_view.category_name = self.category_name.value
        await interaction.response.send_message(
            f"Category name set to: {self.category_name.value}", ephemeral=True
        )

class TourneyView(discord.ui.View):
    def __init__(self, ctx: Context):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.channel_name = None
        self.category_name = None

        # Add the select menu
        self.add_item(TourneyChannel(ctx, self))

    @discord.ui.button(label="Set Channel Name", style=discord.ButtonStyle.primary)
    async def set_channel_name(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ChannelNameModal(self))

    @discord.ui.button(label="Set Category Name", style=discord.ButtonStyle.primary)
    async def set_category_name(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CategoryNameModal(self))