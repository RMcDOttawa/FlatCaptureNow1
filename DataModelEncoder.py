import traceback
from json import JSONEncoder

from BinningSpec import BinningSpec
from FilterSpec import FilterSpec
from FlatFrameTable import FlatFrameTable


class DataModelEncoder(JSONEncoder):

    def default(self, obj):

        if isinstance(obj, FilterSpec):
            return obj.encode()
        if isinstance(obj, BinningSpec):
            return obj.encode()
        if isinstance(obj, FlatFrameTable):
            return obj.encode()

        print(f"DataModelEncoder: unexpected type: {obj}")
        traceback.print_exc()
        return None
