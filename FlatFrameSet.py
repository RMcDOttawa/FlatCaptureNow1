from FilterSpec import FilterSpec
from FrameSet import FrameSet


class FlatFrameSet(FrameSet):
    def __init__(self,
                 filter: FilterSpec,
                 number_of_frames: int,
                 exposure: float,
                 binning: int,
                 number_complete: int):
        FrameSet.__init__(self, number_of_frames=number_of_frames, binning=binning, number_complete=number_complete)
        self._exposure_seconds: float = exposure
        self._filter = filter

    def get_filter(self) -> FilterSpec:
        return self._filter

    def set_filter(self, filter: FilterSpec):
        self._filter = filter

    def get_exposure(self) -> float:
        return self._exposure_seconds

    def set_exposure(self, exposure: float):
        self._exposure_seconds = exposure