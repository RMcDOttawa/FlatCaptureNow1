# The specification of a filter, as stored in the preferences file.
# A list of such specs is stored in the preferences file, one for each (possible) filter wheel slot


class FilterSpec:
    def __init__(self, slot: int, name: str, used: bool):
        # Instance variables
        self._slot_number: int = slot
        self._is_used: bool = used
        self._name: str = name

    # Getters and setters

    def get_slot_number(self):
        return self._slot_number

    def set_slot_number(self, value: str):
        self._slot_number = value

    def get_is_used(self):
        return self._is_used

    def set_is_used(self, value: bool):
        self._is_used = value

    def get_name(self):
        return self._name

    def set_name(self, value: str):
        self._name = value

    def __str__(self) -> str:
        return f"FS<{self.get_slot_number()},{self.get_name()},{self.get_is_used()}>"

   # Encode for JSON
    def encode(self):
        return {
            "_type": "FilterSpec",
            "_value": self.__dict__
        }

    @classmethod
    def decode(cls, obj):
        # print(f"FilterSpec/decode({obj}")
        assert (obj["_type"] == "FilterSpec")
        value_dict = obj["_value"]
        slot_number: int = value_dict["_slot_number"]
        name: str = value_dict["_name"]
        used: bool = value_dict["_is_used"]
        return FilterSpec(slot_number, name, used)
