from typing import Any
from tortoise.expressions import F, RawSQL  # Import RawSQL for handling custom expressions

from tortoise.fields.base import Field


class ArrayField(Field, list):
    def __init__(self, field: Field, **kwargs) -> None:
        super().__init__(**kwargs)
        self.sub_field = field
        self.SQL_TYPE = "%s[]" % field.SQL_TYPE

    def to_python_value(self, value: Any) -> Any:
        return list(map(self.sub_field.to_python_value, value))

    def to_db_value(self, value: Any, instance: Any) -> Any:
        if isinstance(value, (F, RawSQL)):  # Allow database expressions like ArrayRemove
            return value
        if not isinstance(value, (list, tuple)):  # Ensure value is iterable
            raise ValueError(f"Expected a list or tuple, got {type(value).__name__}")
        return [self.sub_field.to_db_value(val, instance) for val in value]
