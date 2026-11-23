from __future__ import annotations
from contextlib import suppress
import discord
from core import Context
import re
from utils import truncate_string

class TourneyChannelcall:
    def __init__(self, ctx: Context, custom_view: discord.ui.View):
        self.ctx = ctx
        self.custom_view = custom_view

    async def info_channel(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild

        channel_name = f"{self.custom_view.channel_name or 'tourney'}info"[:100].lower().replace(" ", "-")
        
        # Find or create category
        category = None
        if self.custom_view.category_name:
            category = discord.utils.get(guild.categories, name=self.custom_view.category_name)
            if not category:
                try:
                    category = await guild.create_category(self.custom_view.category_name, reason=f"Created by {self.ctx.author}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    await interaction.followup.send(f"Failed to create category: {str(e)}", ephemeral=True)
                    return

        # Set permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False , mention_everyone=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            self.ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }

        try:
            # Create channel
            new_channel = await guild.create_text_channel(
                name=channel_name,
                topic="Info channel for the tournament",
                overwrites=overwrites,
                category=category,
                reason=f"Created by {self.ctx.author}"
            )
            
            # Send messages
            await interaction.followup.send(f"Created {new_channel.mention} for tournament info!", ephemeral=True)
        

        except (discord.Forbidden, discord.HTTPException) as e:
            await interaction.followup.send(f"Failed to create channel: {str(e)}", ephemeral=True)

    async def update_channel(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if not guild:
            await interaction.followup.send("This command must be used in a server.", ephemeral=True)
            return

        channel_name = f"{self.custom_view.channel_name or 'tourney'}update"[:100].lower().replace(" ", "-")
        
        # Find or create category
        category = None
        if self.custom_view.category_name:
            category = discord.utils.get(guild.categories, name=self.custom_view.category_name)
            if not category:
                try:
                    category = await guild.create_category(self.custom_view.category_name, reason=f"Created by {self.ctx.author}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    await interaction.followup.send(f"Failed to create category: {str(e)}", ephemeral=True)
                    return

        # Set permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False, mention_everyone=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            self.ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }

        try:
            # Create channel
            new_channel = await guild.create_text_channel(
                name=channel_name,
                topic="Update channel for the tournament",
                overwrites=overwrites,
                category=category,
                reason=f"Created by {self.ctx.author}"
            )
            
            # Send messages
            await interaction.followup.send(f"Created {new_channel.mention} for tournament updates!", ephemeral=True)
            await new_channel.send("**Stay tuned for updates.**")

        except (discord.Forbidden, discord.HTTPException) as e:
            await interaction.followup.send(f"Failed to create channel: {str(e)}", ephemeral=True)
            
            
    async def road_map(self, interaction: discord.Interaction) -> None:        
        guild = interaction.guild
        
        name = f"{self.custom_view.channel_name or 'tourney'}roadmap"[:100].lower().replace(" ", "-")
        category = None
        
        category = None
        if self.custom_view.category_name:
            category = discord.utils.get(guild.categories, name=self.custom_view.category_name)
            if not category:
                try:
                    category = await guild.create_category(self.custom_view.category_name, reason=f"Created by {self.ctx.author}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    await interaction.followup.send(f"Failed to create category: {str(e)}", ephemeral=True)
                    return
                
        #set permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False , mention_everyone=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            self.ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        try:
            # Create channel
            new_channel = await guild.create_text_channel(
                name=name,
                topic="Roadmap channel for the tournament",
                overwrites=overwrites,
                category=category,
                reason=f"Created by {self.ctx.author}"
            )
            
            # Send messages
            await interaction.followup.send(f"Created {new_channel.mention} for tournament roadmap!", ephemeral=True)
            msg = await new_channel.send("## Update Soon")
            await msg.add_reaction("🗺️")
            await msg.reply("**100 React For Roadmap**")

        except (discord.Forbidden, discord.HTTPException) as e:
            await interaction.followup.send(f"Failed to create channel: {str(e)}", ephemeral=True)  
            
    
    async def schedule_chan(self, interaction: discord.Interaction) -> None:        
        guild = interaction.guild
        
        name = f"{self.custom_view.channel_name or 'tourney'}schedule"[:100].lower().replace(" ", "-")
        category = None
        
        category = None
        if self.custom_view.category_name:
            category = discord.utils.get(guild.categories, name=self.custom_view.category_name)
            if not category:
                try:
                    category = await guild.create_category(self.custom_view.category_name, reason=f"Created by {self.ctx.author}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    await interaction.followup.send(f"Failed to create category: {str(e)}", ephemeral=True)
                    return
                
        #set permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False , mention_everyone=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            self.ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        try:
            # Create channel
            new_channel = await guild.create_text_channel(
                name=name,
                topic="Schedule channel for the tournament",
                overwrites=overwrites,
                category=category,
                reason=f"Created by {self.ctx.author}"
            )
            
            # Send messages
            await interaction.followup.send(f"Created {new_channel.mention} for tournament schedule!", ephemeral=True)
            msg = await new_channel.send("## Update Soon")
            await msg.add_reaction("📅")
            await msg.reply("**100 React For Schedule**")

        except (discord.Forbidden, discord.HTTPException) as e:
            await interaction.followup.send(f"Failed to create channel: {str(e)}", ephemeral=True)
            
    async def rules_chan(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        
        name = f"{self.custom_view.channel_name or 'tourney'}rules"[:100].lower().replace(" ", "-")
        category = None
        
        category = None
        if self.custom_view.category_name:
            category = discord.utils.get(guild.categories, name=self.custom_view.category_name)
            if not category:
                try:
                    category = await guild.create_category(self.custom_view.category_name, reason=f"Created by {self.ctx.author}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    await interaction.followup.send(f"Failed to create category: {str(e)}", ephemeral=True)
                    return
                
        #set permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False, mention_everyone=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            self.ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        try:
            # Create channel
            new_channel = await guild.create_text_channel(
                name=name,
                topic="Rules channel for the tournament",
                overwrites=overwrites,
                category=category,
                reason=f"Created by {self.ctx.author}"
            )
            
            # Send messages
            await interaction.followup.send(f"Created {new_channel.mention} for tournament rules!", ephemeral=True)
           

        except (discord.Forbidden, discord.HTTPException) as e:
            await interaction.followup.send(f"Failed to create channel: {str(e)}", ephemeral=True)
            
    
    async def prize_distributaion_chan(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        
        name = f"{self.custom_view.channel_name or 'tourney'}prize-distribution"[:100].lower().replace(" ", "-")
        category = None
        
        category = None
        if self.custom_view.category_name:
            category = discord.utils.get(guild.categories, name=self.custom_view.category_name)
            if not category:
                try:
                    category = await guild.create_category(self.custom_view.category_name, reason=f"Created by {self.ctx.author}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    await interaction.followup.send(f"Failed to create category: {str(e)}", ephemeral=True)
                    return
                
        #set permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False , mention_everyone=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            self.ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        try:
            # Create channel
            new_channel = await guild.create_text_channel(
                name=name,
                topic="Prize distribution channel for the tournament",
                overwrites=overwrites,
                category=category,
                reason=f"Created by {self.ctx.author}"
            )
            
            # Send messages
            await interaction.followup.send(f"Created {new_channel.mention} for tournament prize distribution!", ephemeral=True)
            await new_channel.send("## Update Soon")

        except (discord.Forbidden, discord.HTTPException) as e:
            await interaction.followup.send(f"Failed to create channel: {str(e)}", ephemeral=True)
    
    async def how_to_register(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        
        name = f"{self.custom_view.channel_name or 'tourney'}how-to-register"[:100].lower().replace(" ", "-")
        category = None
        
        category = None
        if self.custom_view.category_name:
            category = discord.utils.get(guild.categories, name=self.custom_view.category_name)
            if not category:
                try:
                    category = await guild.create_category(self.custom_view.category_name, reason=f"Created by {self.ctx.author}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    await interaction.followup.send(f"Failed to create category: {str(e)}", ephemeral=True)
                    return
                
        #set permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False , mention_everyone=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            self.ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        try:
            # Create channel
            new_channel = await guild.create_text_channel(
                name=name,
                topic="How to register channel for the tournament",
                overwrites=overwrites,
                category=category,
                reason=f"Created by {self.ctx.author}"
            )
            
            # Send messages
            await interaction.followup.send(f"Created {new_channel.mention} for tournament how to register!", ephemeral=True)
            await new_channel.send("Welcome to the tournament how to register channel!\nStay tuned for updates.")

        except (discord.Forbidden, discord.HTTPException) as e:
            await interaction.followup.send(f"Failed to create channel: {str(e)}", ephemeral=True)
    
    async def tag_check(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        
        name = f"{self.custom_view.channel_name or 'tourney'}tag-chacek"[:100].lower().replace(" ", "-")
        category = None
        
        category = None
        if self.custom_view.category_name:
            category = discord.utils.get(guild.categories, name=self.custom_view.category_name)
            if not category:
                try:
                    category = await guild.create_category(self.custom_view.category_name, reason=f"Created by {self.ctx.author}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    await interaction.followup.send(f"Failed to create category: {str(e)}", ephemeral=True)
                    return
                
        #set permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False ,mention_everyone=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            self.ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        try:
            # Create channel
            new_channel = await guild.create_text_channel(
                name=name,
                topic="Tag chacek channel for the tournament",
                overwrites=overwrites,
                category=category,
                reason=f"Created by {self.ctx.author}"
            )
            
            # Send messages
            await interaction.followup.send(f"Created {new_channel.mention} for tournament tag chacek!", ephemeral=True)
            

        except (discord.Forbidden, discord.HTTPException) as e:
            await interaction.followup.send(f"Failed to create channel: {str(e)}", ephemeral=True)
            
            
    async def register_here(self , interaction : discord.Interaction) -> None:
        guild = interaction .guild
        
        name = f"{self.custom_view.channel_name or 'tourney'}register-here"[:100].lower().replace(" ", "-")
        category = None
        
        category = None
        if self.custom_view.category_name:
            category = discord.utils.get(guild.categories, name=self.custom_view.category_name)
            if not category:
                try:
                    category = await guild.create_category(self.custom_view.category_name, reason=f"Created by {self.ctx.author}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    await interaction.followup.send(f"Failed to create category: {str(e)}", ephemeral=True)
                    return
                
        #set permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False , mention_everyone=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            self.ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        try:
            # Create channel
            new_channel = await guild.create_text_channel(
                name=name,
                topic="Register here channel for the tournament",
                overwrites=overwrites,
                category=category,
                reason=f"Created by {self.ctx.author}"
            )
            
            # Send messages
            await interaction.followup.send(f"Created {new_channel.mention} for tournament register here!", ephemeral=True)
            await new_channel.send("## Update Soon")

        except (discord.Forbidden, discord.HTTPException) as e:
            await interaction.followup.send(f"Failed to create channel: {str(e)}", ephemeral=True)
            
          
    async def confirm_team(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if not guild:
            await interaction.followup.send("This command must be used in a server.", ephemeral=True)
            return
        

        name = f"{self.custom_view.channel_name or 'tourney'}confirm-team"[:100].lower().replace(" ", "-")
        category = None
        if self.custom_view.category_name:
            category = discord.utils.get(guild.categories, name=self.custom_view.category_name)
            if not category:
                try:
                    category = await guild.create_category(self.custom_view.category_name, reason=f"Created by {self.ctx.author}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    await interaction.followup.send(f"Failed to create category: {str(e)}", ephemeral=True)
                    return
                
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False, mention_everyone=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            self.ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        try:
            # Create channel
            new_channel = await guild.create_text_channel(
                name=name,
                topic="Confirm team channel for the tournament",
                overwrites=overwrites,
                category=category,
                reason=f"Created by {self.ctx.author}"
            )
            
            # Send messages
            await interaction.followup.send(f"Created {new_channel.mention} for tournament confirm team!", ephemeral=True)
          

        except (discord.Forbidden, discord.HTTPException) as e:
            await interaction.followup.send(f"Failed to create channel: {str(e)}", ephemeral=True)
            
    async def support_chat(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if not guild:
            await interaction.followup.send("This command must be used in a server.", ephemeral=True)
            return
        
        name = f"{self.custom_view.channel_name or 'tourney'}support-chat"[:100].lower().replace(" ", "-")
        category = None
        
        category = None
        if self.custom_view.category_name:
            category = discord.utils.get(guild.categories, name=self.custom_view.category_name)
            if not category:
                try:
                    category = await guild.create_category(self.custom_view.category_name, reason=f"Created by {self.ctx.author}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    await interaction.followup.send(f"Failed to create category: {str(e)}", ephemeral=True)
                    return
                
        #set permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, mention_everyone=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            self.ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        try:
            # Create channel
            new_channel = await guild.create_text_channel(
                name=name,
                topic="Support chat channel for the tournament",
                overwrites=overwrites,
                category=category,
                reason=f"Created by {self.ctx.author}"
            )
            
            # Send messages
            await interaction.followup.send(f"Created {new_channel.mention} for tournament support chat!", ephemeral=True)
          

        except (discord.Forbidden, discord.HTTPException) as e:
            await interaction.followup.send(f"Failed to create channel: {str(e)}", ephemeral=True)
            
    async def support_voice(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if not guild:
            await interaction.followup.send("This command must be used in a server.", ephemeral=True)
            return

        # Check bot permissions
        required_perms = discord.Permissions(manage_channels=True, view_channel=True, manage_permissions=True)
        if not guild.me.guild_permissions >= required_perms:
            await interaction.followup.send(
                "I need `Manage Channels`, `View Channels`, and `Manage Permissions` permissions to create a voice channel.",
                ephemeral=True
            )
            return

        # Safely access custom_view attributes
        channel_name = getattr(self.custom_view, "channel_name", "tourney") or "tourney"
        category_name = getattr(self.custom_view, "category_name", None)

        # Create a valid channel name (max 100 chars, lowercase, replace spaces with hyphens)
        name = f"{channel_name}-support-voice"[:100].lower().replace(" ", "-")
        name = re.sub(r"[^a-z0-9-]", "", name)  # Remove invalid characters

        # Handle category
        category = None
        if category_name:
            category = discord.utils.get(guild.categories, name=category_name)
            if not category:
                try:
                    category = await guild.create_category(
                        category_name, reason=f"Created by {self.ctx.author}"
                    )
                except discord.Forbidden:
                    await interaction.followup.send(
                        "I don't have permission to create a category.", ephemeral=True
                    )
                    return
                except discord.HTTPException as e:
                    await interaction.followup.send(
                        f"Failed to create category: {str(e)}", ephemeral=True
                    )
                    return

        # Set permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=True, connect=True, speak=True , mention_everyone=False
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, manage_channels=True, manage_permissions=True, connect=True, speak=True
            ),
            self.ctx.author: discord.PermissionOverwrite(
                view_channel=True, manage_channels=True, connect=True, speak=True
            ),
        }

        try:
            # Create voice channel
            new_channel = await guild.create_voice_channel(
                name=name,
                overwrites=overwrites,
                category=category,
                reason=f"Created by {self.ctx.author}"
            )
            await interaction.followup.send(
                f"Created {new_channel.mention} for tournament support voice!", ephemeral=True
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "I don't have permission to create a voice channel.", ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"Failed to create voice channel: {str(e)}", ephemeral=True
            )