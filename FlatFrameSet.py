from FilterSpec import FilterSpec
from FrameSet import FrameSet


class FlatFrameSet(FrameSet):
    def __init__(self,
                 filter_spec: FilterSpec,
                 number_of_frames: int,
                 exposure: float,
                 binning: int,
                 number_complete: int):
        FrameSet.__init__(self, number_of_frames=number_of_frames, binning=binning, number_complete=number_complete)
        self._exposure_seconds: float = exposure
        self._filter = filter_spec

    def get_filter(self) -> FilterSpec:
        return self._filter

    def set_filter(self, filter_spec: FilterSpec):
        self._filter = filter_spec

    def get_exposure(self) -> float:
        return self._exposure_seconds

    def set_exposure(self, exposure: float):
        self._exposure_seconds = exposure

    def type_name_text(self) -> str:
        return "Flat"

    # The numeric type code for THeSkyX for this kind of image.
    # 1=Light, 2=Bias, 3=Dark, 4=Flat
    def camera_image_type_code(self) -> int:
        return 4
