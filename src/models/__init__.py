from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from core import Quotient

from tortoise import models


class BaseDbModel(models.Model):
    """Base Model for all tortoise models"""

    class Meta:
        abstract = True

    # Add a method to handle dynamic attributes
    def set_dynamic_attribute(self, name: str, value: Any):
        setattr(self, name, value)

# Removed bot attribute as it is dynamically assigned in Bot.py

from .esports import *
from .helpers import *
from .misc import *
