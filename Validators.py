from typing import Optional


class Validators:
    # Validate floating point number such as latitude, longitude
    @classmethod
    def valid_float_in_range(cls, proposed_value: str, min_value: float, max_value: float) -> Optional[float]:
        """Validate that a string is a floating point number in a given range"""
        result: Optional[float] = None
        try:
            converted: float = float(proposed_value)
            if (converted >= min_value) and (converted <= max_value):
                result = converted
        except ValueError:
            # Let result go back as "none", indicating error
            pass
        return result

    # Validate integer number

    @classmethod
    def valid_int_in_range(cls, proposed_value: str, min_value: int, max_value: int) -> Optional[int]:
        """Validate that a string is an integer in a given range"""
        result: Optional[int] = None
        try:
            converted: int = int(proposed_value)
            if (converted >= min_value) and (converted <= max_value):
                result = converted
        except ValueError:
            # Let result go back as "none", indicating error
            pass
        return result
