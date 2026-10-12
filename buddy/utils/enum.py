from enum import Enum
from typing import Any


class ExtendedEnum(Enum):
    @classmethod
    def values_list(cls: Any) -> list[Any]:
        return [member.value for member in cls]

    @classmethod
    def from_str(cls: Any, str_to_convert_to_enum: str | None) -> Any | None:
        """Convert a string value to an enum object. Case Sensitive"""

        if str_to_convert_to_enum is None:
            return None

        if str_to_convert_to_enum in cls._value2member_map_:
            return cls._value2member_map_.get(str_to_convert_to_enum)
        else:
            raise NotImplementedError(
                f"{str_to_convert_to_enum} is not a member of {cls}: {cls._value2member_map_.keys()}"
            )
