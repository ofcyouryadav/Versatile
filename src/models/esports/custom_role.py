from tortoise import fields
from tortoise.models import Model

class CustomRole(Model):
    class Meta:
        table = "custom_role"

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField()
    role_id = fields.BigIntField()
    name = fields.CharField(max_length=255)

class Moderator(Model):
    class Meta:
        table = "moderator"
        unique_together = (("guild_id", "user_id"),)  # Enforce uniqueness on guild_id and user_id

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField()
    user_id = fields.BigIntField()
