# Class to send and receive commands (Javascript commands and text responses) to the
# server running TheSkyX
import socket
from datetime import datetime
from random import random
from time import sleep

from PyQt5.QtCore import QMutex

from Validators import Validators


class TheSkyX:
    MAX_RECEIVE_SIZE = 1024

    _server_mutex = QMutex()

    def __init__(self, server_address: str, port_number: int):
        self._server_address = server_address
        self._port_number = int(port_number)
        self._selected_filter_index = -1

    # Get the autosave-path string from the camera.
    # Return a success flag and the path string, and an error message if needed
    def get_camera_autosave_path(self) -> (bool, str, str):
        """Get file autosave path on server from TheSkyX"""
        command_with_return = "var path=ccdsoftCamera.AutoSavePath;" \
                              + "var Out;" \
                              + "Out=path+\"\\n\";"
        (success, path_result, message) = self.send_command_with_return(command_with_return)
        return success, path_result, message

    # Tell TheSkyX to connect to the camera
    def connect_to_camera(self) -> (bool, str):
        """Connect TheSkyX server to camera"""
        command_line = "ccdsoftCamera.Connect();"
        (success, message) = self.send_command_no_return(command_line)
        return success, message

    # Tell TheSkyX to disconnect from the camera
    def disconnect_camera(self) -> (bool, str):
        """Disconnect TheSkyX from the camera"""
        command_line = "ccdsoftCamera.Disconnect();"
        (success, message) = self.send_command_no_return(command_line)
        return success, message

    # Tell TheSkyX to connect to the filter wheel
    def connect_to_filter_wheel(self) -> (bool, str):
        """Ask TheSkyX server to connect to the filter wheel"""
        command_line = "ccdsoftCamera.filterWheelConnect();"
        (success, message) = self.send_command_no_return(command_line)
        return success, message

    # Tell TheSkyX to select a specified filter
    def select_filter(self, filter_index: int) -> (bool, str):
        """Send filter selection that will be used for the next taken image"""
        self._selected_filter_index = filter_index
        command_line = f"ccdsoftCamera.FilterIndexZeroBased={filter_index};"
        (success, message) = self.send_command_no_return(command_line)
        return success, message

    # Tell TheSkyX to take a bias frame at given binning to the camera
    def take_bias_frame(self, binning: int, auto_save_file: bool, asynchronous: bool) -> (bool, str):
        """Take a bias frame"""
        command: str = "ccdsoftCamera.Autoguider=false;"  # Use main camera
        command += f"ccdsoftCamera.Asynchronous={self.js_bool(asynchronous)};"  # Async or wait?
        command += "ccdsoftCamera.Frame=2;"  # Type "2" is bias frame
        command += "ccdsoftCamera.ImageReduction=0;"
        command += "ccdsoftCamera.ToNewWindow=false;"
        command += "ccdsoftCamera.ccdsoftAutoSaveAs=0;"
        command += f"ccdsoftCamera.AutoSaveOn={self.js_bool(auto_save_file)};"
        command += f"ccdsoftCamera.BinX={binning};"
        command += f"ccdsoftCamera.BinY={binning};"
        command += "ccdsoftCamera.ExposureTime=0;"
        command += "var cameraResult = ccdsoftCamera.TakeImage();"
        (success, returned_value, message) = self.send_command_with_return(command)
        if success:
            return_parts = returned_value.split("|")
            assert (len(return_parts) > 0)
            if return_parts[0] == "0":
                pass  # Result indicates success
            else:
                success = False
                message = return_parts[0]
        return success, message

    # Set the camera cooling on or off and, if on, set the target temperature
    def set_camera_cooling(self, cooling_on: bool, target_temperature: float) -> (bool, str):
        """Turn camera cooling on or off, and set target temperature"""
        target_temperature_command = ""
        if cooling_on:
            target_temperature_command = f"ccdsoftCamera.TemperatureSetPoint={target_temperature};"
        command_with_return = f"{target_temperature_command}" \
                              + f"ccdsoftCamera.RegulateTemperature={self.js_bool(cooling_on)};" \
                              + f"ccdsoftCamera.ShutDownTemperatureRegulationOnDisconnect=" \
                              + f"{self.js_bool(False)};"
        (success, message) = self.send_command_no_return(command_with_return)
        return success, message

    # Get temperature from camera
    # Return success, temperature, error-message

    # simulated_temp_rise: float = 0
    # simulated_temp_counter: int = 0

    # Get temperature of the CCD camera.
    # Return a tuple with command success, temperature, error message

    def get_camera_temperature(self) -> (bool, float, str):
        """Retrieve the current CCD temperature from the camera"""

        command_with_return = "var temp=ccdsoftCamera.Temperature;" \
                              + "var Out;" \
                              + "Out=temp+\"\\n\";"
        temperature = 0
        (success, temperature_result, message) = self.send_command_with_return(command_with_return)
        if success:
            temperature = Validators.valid_float_in_range(temperature_result, -270, +200)
            if temperature is None:
                success = False
                temperature = 0
                message = "Invalid Temperature Returned"
        return success, temperature, message

    # Set up the camera parameters for an image (don't actually take the image)
    #  (success, message) = server.set_camera_image(frame_type, binning, exposure_seconds)
    def set_camera_image(self,
                         frame_type_code: int,  # light,bias,dark,flat = 1,2,3,4
                         binning: int,
                         exposure_seconds: float) -> (bool, str):
        """Set the various image settings necessary to take an image"""
        command_with_no_return = "ccdsoftCamera.Autoguider = false;" \
                                 + f"ccdsoftCamera.Frame = {frame_type_code};" \
                                 + "ccdsoftCamera.ImageReduction = 0;" \
                                 + "ccdsoftCamera.ToNewWindow=false;" \
                                 + "ccdsoftCamera.AutoSaveOn=true;" \
                                 + "ccdsoftCamera.Delay = 0;" \
                                 + f"ccdsoftCamera.BinX = {binning};" \
                                 + f"ccdsoftCamera.BinY = {binning};"
        if frame_type_code == 2:
            command_with_no_return += f"ccdsoftCamera.ExposureTime = 0;"
        else:
            command_with_no_return += f"ccdsoftCamera.ExposureTime = {exposure_seconds};"

        (success, message) = self.send_command_no_return(command_with_no_return)
        return success, message

    # Start taking image, asynchronously (i.e. command returns right away, doesn't wait for image)
    def start_image_asynchronously(self) -> (bool, str):
        """Begin asynch image acquisition (returns immediately, leaving camera working)"""
        command_with_no_return = "ccdsoftCamera.Asynchronous=true;" \
                                 + "var cameraResult = ccdsoftCamera.TakeImage();" \
                                 + "var Out;" \
                                 + "Out=cameraResult+\"\\n\";"

        (success, result, message) = self.send_command_with_return(command_with_no_return)
        if success and (result != "0"):
            success = False
            message = f"Error {result} from camera"
        return success, message

    #        (complete_check_successful, is_complete, message) = server.get_exposure_is_complete()
    # Ask the camera if the asynchronous exposure we started is complete
    # Return command-success,  is-complete,  error-message
    def get_exposure_is_complete(self) -> (bool, bool, str):
        """Ask camera if previously-started asynch image acquisition is complete"""
        command_with_no_return = "var complete = ccdsoftCamera.IsExposureComplete;" \
                                 + "var Out;" \
                                 + "Out=complete+\"\\n\";"

        (command_success, result, message) = self.send_command_with_return(command_with_no_return)
        if command_success:
            if result == "0":
                is_complete = False
            elif result == "1":
                is_complete = True
            else:
                # Something has gone wrong - e.g. the user aborted the image directly in TheSkyX
                # the result string will contain an explanation, usually terminated by "|".
                # Treat this is an exception.
                command_success = False
                message = result.split("|")[0]
                is_complete = True
        else:
            is_complete = False

        return command_success, is_complete, message

    # Send Abort to camera to stop the image in progress
    def abort_image(self) -> (bool, str):
        """Tell camera to abort image acquisition in progress"""
        command_line = "ccdsoftCamera.Abort();"
        (success, message) = self.send_command_no_return(command_line)
        return success, message

    # Send a command to the server and get a returned result value
    # Return a 3-ple:  success flag,  response,  error message if any
    def send_command_with_return(self, command: str) -> (bool, str, str):
        """Send a command to TheSkyX that returns a value"""
        command_packet = "/* Java Script */" \
                         + "/* Socket Start Packet */" \
                         + command \
                         + "/* Socket End Packet */"
        (success, returned_result, message) = self.send_command_packet(command_packet)
        return success, returned_result, message

    # Send a command to the server with no returned value needed
    # Return a 2-ple:  success flag,    error message if any
    def send_command_no_return(self, command: str):
        """Send a command that does not return a value"""
        command_packet = "/* Java Script */" \
                         + "/* Socket Start Packet */" \
                         + command \
                         + "/* Socket End Packet */"
        (success, returned_result, message) = self.send_command_packet(command_packet)
        return success, message

    # Send command packet and read response
    # Return a 3-ple:  success flag,  response,  error message if any
    def send_command_packet(self, command_packet: str):
        """Send packet to TheSkyX over socket and read response from socket"""
        result = ""
        success = False
        message = ""
        address_tuple = (self._server_address, self._port_number)
        TheSkyX._server_mutex.lock()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as the_socket:
            try:
                the_socket.connect(address_tuple)
                bytes_to_send = bytes(command_packet, 'utf-8')
                the_socket.sendall(bytes_to_send)
                returned_bytes = the_socket.recv(TheSkyX.MAX_RECEIVE_SIZE)
                result_lines = returned_bytes.decode('utf=8') + "\n"
                parsed_lines = result_lines.split("\n")
                if len(parsed_lines) > 0:
                    result = parsed_lines[0]
                    success = True
            except socket.gaierror as ge:
                success = False
                result = ""
                message = ge.strerror
            except ConnectionRefusedError as cr:
                success = False
                result = ""
                message = cr.strerror
        TheSkyX._server_mutex.unlock()
        return success, result, message

    # Convert a bool to a string in javascript-bool format (lowercase)
    @staticmethod
    def js_bool(value: bool) -> str:
        """Convert bool to string used in JavaScript for server commands"""
        return "true" if value else "false"

    # Get the cooler power level.
    # Return (success, power, message)
    def get_cooler_power(self) -> (bool, float, str):
        """Retrieve current power level of CCD cooler from camera"""
        command_with_return = "var power=ccdsoftCamera.ThermalElectricCoolerPower;" \
                              + "var Out;" \
                              + "Out=power+\"\\n\";"
        (success, power_result, message) = self.send_command_with_return(command_with_return)
        return success, power_result, message

    # Take a flat frame, don't keep it, just return the average ADU of the result
    # Return success, adu value, error message

    # def get_flat_frame_avg_adus(self, exposure_length: float, binning: int) -> (bool, float, str):
    #     """Take and discard a flat frame, return its average ADU value"""
    #     (success, result_adus, message) = self.take_flat_frame(exposure_length, binning, False)
    #     return success, result_adus, message

    # Take a flat frame, return the average ADUs.  Auto-save to disk or not, as requested
    # Return success, adu value, error message

    # flat_frame_calculate_simulation = True  # Calc a value instead of using camera, for testing
    flat_frame_calculate_simulation = False  # Use camera to capture actual flats and ADUs
    flat_frame_simulation_delay = 1
    remember_average_adus = 0

    def take_flat_frame(self, exposure_length: float, binning: int,
                        asynchronous: bool, autosave_file: bool) -> (bool, str):
        """Take a flat frame with given specifications"""
        message: str = ""
        if self.flat_frame_calculate_simulation:
            success = True
            self.remember_average_adus = self.calc_simulated_adus(exposure=exposure_length, binning=binning)
            sleep(self.flat_frame_simulation_delay)
        else:
            # Have camera start to acquire an image
            command = "ccdsoftCamera.Autoguider=false;"  # Use main camera
            command += f"ccdsoftCamera.Asynchronous={self.js_bool(asynchronous)};"  # Wait for camera?
            command += f"ccdsoftCamera.Frame=4;"  # Type "4" is flat frame
            command += "ccdsoftCamera.ImageReduction=0;"
            command += "ccdsoftCamera.ToNewWindow=false;"
            command += "ccdsoftCamera.ccdsoftAutoSaveAs=0;"
            command += f"ccdsoftCamera.AutoSaveOn={self.js_bool(autosave_file)};"
            command += f"ccdsoftCamera.BinX={binning};"
            command += f"ccdsoftCamera.BinY={binning};"
            command += f"ccdsoftCamera.ExposureTime={exposure_length};"
            command += "var cameraResult = ccdsoftCamera.TakeImage();"
            (success, returned_value, message) = self.send_command_with_return(command)

        return success, message

    def get_adus_from_last_image(self) -> (bool, float, str):
        """ Get the ADU average of the just-acquired image"""
        message: str = ""
        average_adus = 100
        if self.flat_frame_calculate_simulation:
            success = True
            average_adus = self.remember_average_adus
        else:
            # Get active image and ask for its average pixel value
            command = "ccdsoftCameraImage.AttachToActive();" \
                      + "var averageAdu = ccdsoftCameraImage.averagePixelValue();" \
                      + "var Out;" \
                      + "Out=averageAdu+\"\\n\";"
            (success, command_returned_value, message) = self.send_command_with_return(command)
            # print(f"ADU query returned: {command_returned_value}, {command_returned_value}, {message}")
            if success:
                (success, message) = self.check_for_error_in_return_value(command_returned_value)
                if success:
                    # Returned value should be the number we want.  Convert it carefully
                    try:
                        average_adus = float(command_returned_value)
                    except ValueError:
                        success = False
                        average_adus = 0
                        message = f"Invalid ADU value \"{command_returned_value}\" from camera"
        return success, average_adus, message

    # Save the just-acquired frome to the folder set up in TheSkyX's AutoSave path

    def save_acquired_frame_to_autosave(self,
                                        filter_name: str,
                                        exposure: float,
                                        binning: int,
                                        sequence: int) -> (bool, str):
        """Ask TheSkyX to save the last acquired image to the defined file location"""
        file_name = self.generate_save_file_name(filter_name, exposure, binning, sequence)
        command = "cam = ccdsoftCamera;" \
                  + "img = ccdsoftCameraImage;" \
                  + "img.AttachToActiveImager();" \
                  + "asp = cam.AutoSavePath;" \
                  + f"img.Path = asp + '/{file_name}';" \
                  + "var Out=img.Save();" \
                  + "Out += \"\\n\";"
        (success, returned_value, message) = self.send_command_with_return(command)
        if success:
            (success, message) = self.check_for_error_in_return_value(returned_value)
        if not success:
            print(f"Unable to save file {file_name}: {returned_value}")
        return success, message

    # Since TheSkyX is running on this computer, we can give it a path name that
    # we have acquired here. Save the just-acquired frame there.

    def save_acquired_frame_to_local_directory(self,
                                               directory_path: str,
                                               filter_name: str,
                                               exposure: float,
                                               binning: int,
                                               sequence: int) -> (bool, str):
        file_name = self.generate_save_file_name(filter_name, exposure, binning, sequence)
        full_path = f"{directory_path}/{file_name}"
        command = "cam = ccdsoftCamera;" \
                  + "img = ccdsoftCameraImage;" \
                  + "img.AttachToActiveImager();" \
                  + f"img.Path = \'{full_path}';" \
                  + "var Out=img.Save();" \
                  + "Out += \"\\n\";"
        (success, returned_value, message) = self.send_command_with_return(command)
        if success:
            (success, message) = self.check_for_error_in_return_value(returned_value)
        if not success:
            print(f"Unable to save file {file_name}: {returned_value}")
        return success, message

    #
    # Generate a "last part" of the file name for the flat frame we're going to save.
    # Since there will be a large number of files in the destination folder, we'll name them
    # with a convention to make them easy to sort afterward.
    #
    # e.g. would be 20200129-200420-Flat-Luminance-3.2s-1x1.tif
    #   where the above fields are date, time, filter, exposure (to 1 decimal), binning
    #

    @staticmethod
    def generate_save_file_name(filter_name: str,
                                exposure: float,
                                binning: int,
                                sequence: int) -> str:
        now = datetime.now()
        date_and_time_part = now.strftime("%Y%m%d-%H%M%S")
        exposure_part = f"{round(exposure, 1):.1f}"
        binning_part = f"{binning}x{binning}"
        return f"{date_and_time_part}-Flat-{filter_name}-{exposure_part}-{binning_part}-{sequence}.fit"

    # One of the peculiarities of the TheSkyX tcp interface.  Sometimes you get "success" back
    # from the socket, but the returned string contains an error encoded in the text message.
    # The "success" meant that the server was successful in sending this error text to you, not
    # that all is well.  Awkward.  We check for that, and return a better "success" indicator
    # and a message of any failure we found.

    @staticmethod
    def check_for_error_in_return_value(returned_text: str) -> (bool, str):
        """Check for TheSkyX errors that are encoded in the return value string"""
        returned_text_upper = returned_text.upper()
        success = False
        message = ""
        if returned_text_upper.startswith("TYPEERROR: PROCESS ABORTED"):
            message = "Camera Aborted"
        elif returned_text_upper.startswith("TYPEERROR:"):
            message = returned_text
        elif returned_text_upper.startswith("TYPEERROR: CFITSIO ERROR"):
            message = "File save folder doesn't exist or not writeable"
        else:
            success = True
        return success, message

    # to facilitate testing, we can pretend there is a camera taking a flat frame.  This helps testing
    # because using the real camera would require setting up the scope for flat frames - enabling the
    # light panel, or doing the "white t-shirt" setup.
    # To simulate, we'll calculate the flat given the exposure, binning, and filter, using a linear
    # regression formula calculated separately based on real data, and adding some random noise so
    # we can see the in-session adjustments of varying results taking effect.

    # We accept filter indices of:
    #       0   Red, 2x2 binning only
    #       1   Green, 2x2
    #       2   Blue, 2x2
    #       3   Luminance, 1x1 only
    #       4   Hydrogen-alpha, 1x1

    SIMULATION_NOISE_FRACTION = .05  # 10% noise

    def calc_simulated_adus(self, exposure: float, binning: int):
        """Calculate a simulated ADU result from a flat frame, using regression on previous data"""
        # Get the regression values.  Only have them for certain data.
        filter_index = self._selected_filter_index
        if (binning == 1) and (filter_index == 3):
            # Luminance, binned 1x1
            slope = 721.8
            intercept = 19817
        elif (binning == 2) and (filter_index == 0):
            # Red filter, binned 2x2
            slope = 7336.7
            intercept = -100.48
        elif (binning == 2) and (filter_index == 1):
            # Green filter, binned 2x2
            slope = 11678
            intercept = -293.09
        elif (binning == 2) and (filter_index == 2):
            # Blue filter, binned 2x2
            slope = 6820.4
            intercept = 1858.3
        elif (binning == 1) and (filter_index == 4):
            # H-alpha filter, binned 1x1
            slope = 67.247
            intercept = 2632.7
        else:
            print(f"calc_simulated_adus({exposure},{binning}) unexpected inputs")
            slope = 721.8
            intercept = 19817
        calculated_result = slope * exposure + intercept

        # Now we'll put a small percentage noise into the value so it has some variability
        rand_factor_zero_centered = self.SIMULATION_NOISE_FRACTION * (random() - 0.5)
        noisy_result = calculated_result + rand_factor_zero_centered * calculated_result

        clipped_at_16_bits = min(noisy_result, 65535)
        return clipped_at_16_bits

    # Get the current position, in alt-az coordinates, of the telescope.
    # This will require connecting the scope, then asking for the position.
    # Both might fail, check for that.

    def get_scope_alt_az(self) -> (bool, float, float, str):
        """Get the current alt-az position of the telescope"""
        return_alt: float = 0
        return_az: float = 0
        (success, message) = self.connect_to_telescope()
        if success:
            # Make command to read alt/az
            command = "sky6RASCOMTele.GetAzAlt();" \
                      + "var Out=sky6RASCOMTele.dAlt + '/' + sky6RASCOMTele.dAz;" \
                      + "Out += \"\\n\";"
            (success, returned_value, message) = self.send_command_with_return(command)
            if success:
                (success, message) = self.check_for_error_in_return_value(returned_value)
            if success:
                # Parse results from returned message
                parts = returned_value.split("/")
                if len(parts) == 2:
                    try:
                        return_alt = float(parts[0])
                        return_az = float(parts[1])
                    except:
                        message = "Bad response"
                        success = False
                else:
                    message = "Bad data from TheSkyX"

        return success, return_alt, return_az, message

    # Tell TheSkyX to connect to the telescope mount

    def connect_to_telescope(self) -> (bool, str):
        """Connect TheSkyX server to telescope mount"""
        command_line = "sky6RASCOMTele.Connect();"
        (success, message) = self.send_command_no_return(command_line)
        return success, message

    # Start scope slewing to given alt-az coordinates.  Alt-ax, not RA-Dec, because
    # the original use of this method was to slew to a flat frame light panel, which is
    # at a fixed location in the observatory and doesn't move with the sky
    # Slewing is asynchronous. This just starts the slew - must poll for completion

    def start_slew_to(self, alt: float, az: float) -> (bool, str):
        # print(f"start_slew_to({alt},{az})")
        command_line = "sky6RASCOMTele.Connect();" \
                       + f"Out=sky6RASCOMTele.SlewToAzAlt({az},{alt},'');" \
                       + "Out += \"\\n\";"
        (success, returned_value, message) = self.send_command_with_return(command_line)
        if success:
            (success, message) = self.check_for_error_in_return_value(returned_value)
            self.fake_slew_timer = 0
        return success, message

    simulate_slew = True
    fake_slew_timer = 0
    fake_slew_time_taken = 10

    # Determine if the slew, started above, has completed.  Note that the variables
    # above this line can be used to simulate a slew for testing without annoying the scope

    # Return success, slew_complete.

    def slew_is_complete(self) -> (bool, bool):
        """Determine if the slew, recently started, has finished"""
        success = True
        is_complete = False

        if self.simulate_slew:
            self.fake_slew_timer += 0.5
            is_complete = self.fake_slew_timer >= self.fake_slew_time_taken
            # print(f"Simulate slew completion, elapsed {self.fake_slew_timer}")
        else:
            # Actually poll the mount for slew status
            command_line = f"Out=sky6RASCOMTele.IsSlewComplete;" \
                           + "Out += \"\\n\";"
            (success, returned_value, message) = self.send_command_with_return(command_line)
            if success:
                (success, message) = self.check_for_error_in_return_value(returned_value)
                if success:
                    result_as_int = int(returned_value)
                    is_complete = result_as_int != 0
        return success, is_complete

    # Abort the slew that is in progress
    def abort_slew(self) -> (bool, str):
        """Abort the slew that is asynchronously underway"""
        command_line = f"Out=sky6RASCOMTele.Abort();" \
                       + "Out += \"\\n\";"
        (success, returned_value, message) = self.send_command_with_return(command_line)
        if success:
            (success, message) = self.check_for_error_in_return_value(returned_value)
        return success, message
