from __future__ import annotations

import discord
from tortoise import fields

from models import BaseDbModel

__all__ = ("BotCustomization",)


class BotCustomization(BaseDbModel):
    """Model to store per-guild bot customization settings"""

    class Meta:
        table = "bot_customization"

    guild_id = fields.BigIntField(pk=True, index=True)
    custom_avatar_url = fields.TextField(null=True)
    custom_banner_url = fields.TextField(null=True)
    custom_bio = fields.TextField(null=True)

    @property
    def _guild(self) -> discord.Guild:
        return self.bot.get_guild(self.guild_id)

    @property
    def avatar_display(self) -> str:
        """Return display text for avatar"""
        return self.custom_avatar_url if self.custom_avatar_url else "Default"

    @property
    def banner_display(self) -> str:
        """Return display text for banner"""
        return self.custom_banner_url if self.custom_banner_url else "Default"

    @property
    def bio_display(self) -> str:
        """Return display text for bio"""
        return self.custom_bio if self.custom_bio else "Default"
