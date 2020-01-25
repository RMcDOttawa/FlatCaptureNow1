import json
import traceback
from json import JSONDecoder

from BinningSpec import BinningSpec
from FilterSpec import FilterSpec
from FlatFrameTable import FlatFrameTable


class DataModelDecoder(JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    @staticmethod
    def object_hook(obj):
        result = None

        if '_type' not in obj:
            return obj

        custom_type_name = obj['_type']
        if custom_type_name == "FilterSpec":
            result = FilterSpec.decode(obj)
        elif custom_type_name == "BinningSpec":
            result = BinningSpec.decode(obj)
        elif custom_type_name == "FlatFrameTable":
            result = FlatFrameTable.decode(obj)
        else:
            # We've forgotten to implement one of our custom decoders if we get here
            print(f"** Unknown custom object type in decoder: {custom_type_name}")
            traceback.print_exc()
        return result
