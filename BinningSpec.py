# The specification of a possible camera binning value, as stored in the preferences file.
# A list of such specs is stored in the preferences file, one for each (possible) binning
# We store whether this binning is available at all (e.g. I never use 4x4 and don't want it
# to show up in the user interface, where it would be unnecessary clutter), and whether it
# is selected by default in a new session (e.g. I always want 1x1 selected, but 2x2 I must choose)


class BinningSpec:
    def __init__(self, binning: int, available: bool, default: bool):
        # Available and default can't both be true.
        assert not (available and default)
        self._binning_value: int = binning
        self._is_available: bool = available
        self._is_default: bool = default

    # Getters and setters

    def get_binning_value(self):
        return self._binning_value

    def set_binning_value(self, value: int):
        self._binning_value = value

    def get_is_available(self):
        return self._is_available

    def set_is_available(self, value: bool):
        self._is_available = value

    def get_is_default(self):
        return self._is_default

    def set_is_default(self, value: bool):
        self._is_default = value

    def __str__(self) -> str:
        return f"BS<{self.get_binning_value()},{self.get_is_available()},{self.get_is_default()}>"

    # Encode and decode for JSON

    def encode(self):
        """Encode BinningSpec as JSON object"""
        return {
            "_type": "BinningSpec",
            "_value": self.__dict__
        }

    @classmethod
    def decode(cls, obj):
        """Decode JSON object dict to BinningSpec"""
        assert (obj["_type"] == "BinningSpec")
        value_dict = obj["_value"]
        binning: int = value_dict["_binning_value"]
        is_available: bool = value_dict["_is_available"]
        is_default: bool = value_dict["_is_default"]
        return BinningSpec(binning, is_available, is_default)
