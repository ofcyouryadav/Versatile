import os
import traceback

import discord

if __name__ == "__main__":
    from core import bot
    
    
    # Initialize the reminders system   
    if not hasattr(bot, "reminders"):
        bot.reminders = bot.get_cog("Reminders")  # E   nsure the Reminders cog is loadedx          

    if not bot.config.DISCORD_TOKEN:
        raise RuntimeError(
            "Set DISCORD_TOKEN in your environment or src/config.py. "
            "Copy src/config.example.py to src/config.py to get started."
        )

    bot.run(bot.config.DISCORD_TOKEN)

                                                
    
