#
#  Class used to manage dithering flat frames if requested.
#  One object will be created at the start of a set and updated after each frame acquired.
#  The object keeps track of the target location, calculates the slight move needed for
#   each frame, and executes the move.
#
#   Dithering is done in concentric circles.  Within a set:
#       - The first image is taken centred on the target
#       - Then 8 images are taken at 90-degree corners on a radius around the target
#       - Then subsequent images are taken at double the radius and double the number
#           of images around the centre (8 at 2xr, 16 at 3xr, etc)
#       - If and when a maximum radius is exceeded, it starts again from the centre, but
#         with the starting position of the 4 90-degree corners randomly rotated
#
# The dithering logic, calculating a ring of points around the target, is taken from
# the "DitherProTrack" script written by Richard S. Wright Jr of Software Bisque
#
# All the dithering calculations are performed around a reference point of zero,
# and calculated in radians. The radian value is converted to degrees and added to the
# original target location to produce the usable outputs.
#
import math


class Ditherer:

    # Create with center target of light source, dither radius and max
    def __init__(self, start_alt_deg: float,  # Altitude, degrees
                 start_az_deg: float,  # Azimuth, degrees
                 dither_radius_as: float,  # Radius, arc seconds
                 max_radius_as: float):  # Max radius, arc seconds
        # print(f"Dither from centre {start_alt_deg}, {start_az_deg}")
        self._start_alt_deg: float = start_alt_deg
        self._start_az_deg: float = start_az_deg
        self._dither_radius_as: float = dither_radius_as
        self._dither_radius_rad: float = math.radians(self._dither_radius_as / (60.0 * 60.0))
        self._max_radius_as: float = max_radius_as
        self._max_radius_rad: float = math.radians(self._max_radius_as / (60.0 * 60.0))
        self._count_in_set: int = 0
        # The following are the running variables that change with each
        # call, tracking the spiraling offset out from zero.  These are
        # reset to start a new dither
        self._angle_rad = 3 * math.pi   # Radians. More than 2-pi triggers new cycle
        self._steps = 4   # New cycle will double this to start at 8 steps
        self._current_radius_rad = 0     # Current radius in radians

    def reset(self):
        """Reset dithering to original target centre"""
        self._count_in_set: int = 0
        self._angle_rad = 3 * math.pi   # More than 2-pi to trigger new cycle
        self._steps = 4   # New cycle will double this to start at 8 steps
        self._current_radius_rad = 0     # Current radius in radians
        # print(f"reset dither")

    def get_start_alt(self) -> float:
        return self._start_alt_deg

    def get_start_az(self) -> float:
        return self._start_az_deg

    def __str__(self):
        return f"from ({self._start_alt_deg:.4f}, {self._start_az_deg:.4f})" \
               + f", radius {self._dither_radius_as}'' to {self._max_radius_as}''"

    # Actual computations for dithering

    # Return instructions on whether and how to move the scope for a frame.
    #       For the first time called, don't move it, as it is on-target
    #       After that, move to a given alt-az, which is on the dithering radius near the target

    def next_frame(self) -> (bool, float, float):
        """Get move instructions for next frame"""
        self._count_in_set += 1
        # print(f"next_frame, number {self._count_in_set} in set")
        if self._count_in_set == 1:
            # First frame since reset, we don't move the scope
            move_scope = False
            to_alt = self._start_alt_deg
            to_az = self._start_az_deg
            # print("  Using start location")
        else:
            # We're beyond the first frame, so we are dithering
            (x_offset, y_offset) = self.calc_next_dither_offset()
            # Convert offset in radians to degrees then offset original location
            to_alt = self._start_alt_deg + math.degrees(x_offset)
            to_az = self._start_az_deg + math.degrees(y_offset)
            move_scope = True
            # print(f"  Using ({to_alt}, {to_az})")
        # print(f"Dither {move_scope}, {to_alt}, {to_az}")
        return move_scope, to_alt, to_az

    # Calculate the x and y offsets, in radians, for the next dithered frame.
    # We distribute positions around a ring a given radius from zero, a given number
    # of positions (we'll call steps) around the ring.  If we are beyond the desired number
    # of steps, we increase the radius.  If we are beyond the max radius, we return to the
    # center zero position and start over

    def calc_next_dither_offset(self) -> (float, float):
        """Calc next dither offset from (0,0) in radians"""
        # print(f"calc_next_dither_location old angle= {self._angle_rad}")
        if self._angle_rad > (2 * math.pi):
            # print(f"  Angle {self._angle_rad} > 2pi, resetting")
            self._angle_rad = 0.0   # Reset rotation
            self._steps *= 2.0  # Double steps on circle
            # print(f"  Steps increased to {self._steps}")
            self._current_radius_rad += self._dither_radius_rad  # Increment radius of circle by dither space
            # print(f"  Radius increased to {self._current_radius_rad}")
            if self._current_radius_rad > self._max_radius_rad:
                # We've grown the circle larger than the specified maximum.  Reset to first
                self._steps = 8.0
                self._current_radius_rad = self._dither_radius_rad
                # print(f"  Radius too large, reset to {self._current_radius_rad}")
        else:
            self._angle_rad += ((math.pi * 2.0) / self._steps)  # Next step in same circle
            # print(f"  Angle in same circle rotated to {self._angle_rad}")

        # Compute next dither location
        x_offset = math.cos(self._angle_rad) * self._current_radius_rad
        y_offset = math.sin(self._angle_rad) * self._current_radius_rad
        # print(f"Returning offsets ({x_offset},{y_offset})")
        return x_offset, y_offset
