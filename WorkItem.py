# A work item is one set of flat frames with identical characteristics
# e.g. "16 flat frames with filter number 2, binned 1x1, target adu 25000 within 10%"
from FilterSpec import FilterSpec


class WorkItem:
    def __init__(self, number_of_frames: int, filter_spec: FilterSpec, binning: int,
                 target_adus: float, adu_tolerance: float):
        self._number_of_frames: int = number_of_frames
        self._filter_spec: FilterSpec = filter_spec
        self._binning: int = binning
        self._target_adu: float = target_adus
        self._adu_tolerance: float = adu_tolerance
        self._num_completed: int = 0

    def get_number_of_frames(self) -> int:
        return self._number_of_frames

    def get_filter_spec(self) -> FilterSpec:
        return self._filter_spec

    def get_binning(self) -> int:
        return self._binning

    def get_target_adu(self) -> float:
        return self._target_adu

    def get_adu_tolerance(self) -> float:
        return self._adu_tolerance

    def get_num_completed(self) -> int:
        return self._num_completed

    def set_num_completed(self, completed: int):
        self._num_completed = completed

    def hybrid_filter_name(self) -> str:
        fs: FilterSpec = self._filter_spec
        return f"{fs.get_slot_number()}: {fs.get_name()}"

    def __str__(self):
        return f"{self._number_of_frames} with {self._filter_spec.get_name()} at {self._binning} to {self._target_adu}"
