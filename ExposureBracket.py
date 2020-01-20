# Object used to find and refine the exposure time needed for a target ADU level
# We record the current exposure time, but also the last one and the ADU level it
# produced - so we can do a binary search to hone the exposure time as frames are taken


class ExposureBracket:

    # Eventually the following constants will be replaced with values in Preferences
    INITIAL_EXPOSURE_GUESS = 10.0    # Arbitrary, probably right ballpark
    INITIAL_EXPOSURE_LOW_BOUND = 0.001
    INITIAL_EXPOSURE_HIGH_BOUND = 60

    def __init__(self):
        self._exposure_high: float = ExposureBracket.INITIAL_EXPOSURE_HIGH_BOUND
        self._exposure_low: float = ExposureBracket.INITIAL_EXPOSURE_LOW_BOUND

    # @classmethod
    # def create(cls, low_end: float, high_end: float):
    #     new = ExposureBracket()
    #     new._exposure_high = high_end
    #     new._exposure_low = low_end
    #     return new

    # Getters and Setters

    def get_exposure_high(self):
        return self._exposure_high

    def set_exposure_high(self, exposure: float):
        self._exposure_high = exposure

    def get_exposure_low(self):
        return self._exposure_low

    def set_exposure_low(self, exposure: float):
        self._exposure_low = exposure

    def mean_exposure(self) -> float:
        return (self._exposure_low + self._exposure_high) / 2.0

    def __str__(self):
        return f"Bracket: <{self._exposure_low},{self._exposure_high}>"
