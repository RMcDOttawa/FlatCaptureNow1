# Class to send and receive commands (Javascript commands and text responses) to the
# server running TheSkyX
import socket
from random import random
from time import sleep

from PyQt5.QtCore import QMutex

from Validators import Validators


class TheSkyX:
    MAX_RECEIVE_SIZE = 1024

    _server_mutex = QMutex()

    def __init__(self, server_address: str, port_number: int):
        # print(f"TheSkyX/init({server_address},{port_number})")
        self._server_address = server_address
        self._port_number = int(port_number)
        self._selected_filter_index = -1

    # Get the autosave-path string from the camera.
    # Return a success flag and the path string, and an error message if needed
    def get_camera_autosave_path(self) -> (bool, str):
        # print("TheSkyX/get_camera_autosave_path")
        command_with_return = "var path=ccdsoftCamera.AutoSavePath;" \
                              + "var Out;" \
                              + "Out=path+\"\\n\";"
        (success, path_result, message) = self.send_command_with_return(command_with_return)
        return success, path_result, message

    # Tell TheSkyX to connect to the camera
    def connect_to_camera(self) -> (bool, str):
        command_line = "ccdsoftCamera.Connect();"
        (success, message) = self.send_command_no_return(command_line)
        return success, message

    # Tell TheSkyX to disconnect from the camera
    def disconnect_camera(self) -> (bool, str):
        command_line = "ccdsoftCamera.Disconnect();"
        (success, message) = self.send_command_no_return(command_line)
        return success, message

    # Tell TheSkyX to connect to the filter wheel
    def connect_to_filter_wheel(self) -> (bool, str):
        # print("connect_to_filter_wheel")
        command_line = "ccdsoftCamera.filterWheelConnect();"
        (success, message) = self.send_command_no_return(command_line)
        return success, message

    # Tell TheSkyX to select a specified filter
    def select_filter(self, filter_index: int) -> (bool, str):
        self._selected_filter_index = filter_index
        # print(f"select_filter({filter_index})")
        command_line = f"ccdsoftCamera.FilterIndexZeroBased={filter_index};"
        # print(f"  Sending command: {command_line}")
        (success, message) = self.send_command_no_return(command_line)
        return success, message

    # Tell TheSkyX to take a bias frame at given binning to the camera
    def take_bias_frame(self, binning: int, auto_save_file: bool, asynchronous: bool) -> (bool, str):
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
        # print(f"take-bias-frame result: {returned_value}")
        return success, message

    # Set the camera cooling on or off and, if on, set the target temperature
    def set_camera_cooling(self, cooling_on: bool, target_temperature: float) -> (bool, str):
        # print(f"set_camera_cooling({cooling_on},{target_temperature})")
        target_temperature_command = ""
        if cooling_on:
            target_temperature_command = f"ccdsoftCamera.TemperatureSetPoint={target_temperature};"
        command_with_return = target_temperature_command \
                              + f"ccdsoftCamera.RegulateTemperature={self.js_bool(cooling_on)};" \
                              + f"ccdsoftCamera.ShutDownTemperatureRegulationOnDisconnect={self.js_bool(False)};"
        (success, message) = self.send_command_no_return(command_with_return)
        return success, message

    # Get temperature from camera
    # Return success, temperature, error-message

    # simulated_temp_rise: float = 0
    # simulated_temp_counter: int = 0

    # Get temperature of the CCD camera.
    # Return a tuple with command success, temperature, error message

    def get_camera_temperature(self) -> (bool, float, str):
        # print(f"get_camera_temperature()")

        # For testing, return a constant temperature a few times, then gradually let it rise
        # to test if the "abort on temperature rising above a threshold" feature is OK
        # TheSkyX.simulated_temp_counter += 1
        # if TheSkyX.simulated_temp_counter > 3:
        #     TheSkyX.simulated_temp_rise += 0.5
        # print(f"get_camera_temperature  returning simulated temperature of {TheSkyX.simulated_temp_rise}")
        # return (True, TheSkyX.simulated_temp_rise, "Simulated temperature")

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
        # print(f"set_camera_image({frame_type_code},{binning},{exposure_seconds})")
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
        # print("start_image_asynchronously")
        command_with_no_return = "ccdsoftCamera.Asynchronous=true;" \
                                 + "var cameraResult = ccdsoftCamera.TakeImage();" \
                                 + "var Out;" \
                                 + "Out=cameraResult+\"\\n\";"

        (success, result, message) = self.send_command_with_return(command_with_no_return)
        # print(f"   Returned result: {result}")
        if success and (result != "0"):
            success = False
            message = f"Error {result} from camera"
        return success, message

    #        (complete_check_successful, is_complete, message) = server.get_exposure_is_complete()
    # Ask the camera if the asynchronous exposure we started is complete
    # Return command-success,  is-complete,  error-message
    def get_exposure_is_complete(self) -> (bool, bool, str):
        # print("get_exposure_is_complete")

        command_with_no_return = "var complete = ccdsoftCamera.IsExposureComplete;" \
                                 + "var Out;" \
                                 + "Out=complete+\"\\n\";"

        (command_success, result, message) = self.send_command_with_return(command_with_no_return)
        # print(f"   Returned result: {result}")
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

        # print(f"      Success={command_success},complete={is_complete},message={message}")
        return command_success, is_complete, message

    # Send Abort to camera to stop the image in progress
    def abort_image(self) -> (bool, str):
        # print("abort_image")
        command_line = "ccdsoftCamera.Abort();"
        (success, message) = self.send_command_no_return(command_line)
        return success, message

    # Send a command to the server and get a returned result value
    # Return a 3-ple:  success flag,  response,  error message if any
    def send_command_with_return(self, command: str):
        # print(f"send_command_with_return({command})")
        command_packet = "/* Java Script */" \
                         + "/* Socket Start Packet */" \
                         + command \
                         + "/* Socket End Packet */"
        (success, returned_result, message) = self.send_command_packet(command_packet)
        return success, returned_result, message

    # Send a command to the server with no returned value needed
    # Return a 2-ple:  success flag,    error message if any
    def send_command_no_return(self, command: str):
        # print(f"send_command_with_return({command})")
        command_packet = "/* Java Script */" \
                         + "/* Socket Start Packet */" \
                         + command \
                         + "/* Socket End Packet */"
        (success, returned_result, message) = self.send_command_packet(command_packet)
        # print(f"send_command_with_return, ignoring returned result: {returned_result}")
        return success, message

    # Send command packet and read response
    # Return a 3-ple:  success flag,  response,  error message if any
    def send_command_packet(self, command_packet: str):
        # print(f"send_command_packet({command_packet})")
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
        return "true" if value else "false"

    # Get the cooler power level.
    # Return (success, power, message)
    def get_cooler_power(self) -> (bool, float, str):
        # print("get_cooler_power")
        command_with_return = "var power=ccdsoftCamera.ThermalElectricCoolerPower;" \
                              + "var Out;" \
                              + "Out=power+\"\\n\";"
        (success, power_result, message) = self.send_command_with_return(command_with_return)
        return success, power_result, message

    # Take a flat frame, don't keep it, just return the average ADU of the result
    # Return success, adu value, error message

    def get_flat_frame_avg_adus(self, exposure_length: float, binning: int) -> (bool, float, str):
        # print(f"get_flat_frame_avg_adus({exposure_length},{binning})")
        (success, result_adus, message) = self.take_flat_frame(exposure_length, binning, False)
        return success, result_adus, message

    # Take a flat frame, return the average ADUs.  Auto-save to disk or not, as requested
    # Return success, adu value, error message

    flat_frame_calculate_simulation = True  # Calc a value instead of using camera, for testing
    flat_frame_simulation_delay = 1

    def take_flat_frame(self, exposure_length: float, binning: int, autosave_file: bool) -> (bool, float, str):
        # print(f"take_flat_frame({exposure_length},{binning},{autosave_file})")
        success: bool = False
        average_adus: int = 0
        message: str = ""
        if self.flat_frame_calculate_simulation:
            success = True
            average_adus = self.calc_simulated_adus(exposure=exposure_length, binning=binning)
            sleep(self.flat_frame_simulation_delay)
        else:
            # Have camera acquire an image
            command = "ccdsoftCamera.Autoguider=false;"  # Use main camera
            command += f"ccdsoftCamera.Asynchronous=false;"  # Wait for camera
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

            # If that worked, ask TheSkyX to calculate the average pixel value of the just-acquired image
            if success:
                (success, message) = self.check_for_error_in_return_value(returned_value)
                if success:
                    # Get active image and ask for its average pixel value
                    command = "ccdsoftCameraImage.AttachToActive();" \
                              + "var averageAdu = ccdsoftCameraImage.averagePixelValue();" \
                              + "var Out;" \
                              + "Out=averageAdu+\"\\n\";"
                    (success, command_returned_value, message) = self.send_command_with_return(command)
                    print(f"ADU query returned: {command_returned_value}, {returned_value}, {message}")
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

    # One of the peculiarities of the TheSkyX tcp interface.  Sometimes you get "success" back
    # from the socket, but the returned string contains an error encoded in the text message.
    # The "success" meant that the server was successful in sending this error text to you, not
    # that all is well.  Awkward.  We check for that, and return a better "success" indicator
    # and a message of any failure we found.

    @staticmethod
    def check_for_error_in_return_value(returned_text: str) -> (bool, str):
        returned_text_upper = returned_text.upper()
        success = False
        message = ""
        if returned_text_upper.startswith("TYPEERROR: PROCESS ABORTED"):
            message = "Camera Aborted"
        elif returned_text_upper.startswith("TYPEERROR:"):
            message = returned_text
        else:
            success = True
        return (success, message)

    # to facilitate testing, we are pretending there is a camera taking a flat frame.
    # we'll calculate the flat given the exposure, binning, and filter, using a linear
    # regression formula calculated separately based on real data, and adding some random noise
    # We accept filter indices of:
    #       0   Red, 2x2 binning only
    #       1   Green, 2x2
    #       2   Blue, 2x2
    #       3   Luminance, 1x1 only
    #       4   Hydrogen-alpha, 1x1

    SIMULATION_NOISE_FRACTION = .01      # 1% noise

    def calc_simulated_adus(self, exposure: float, binning: int):
        # Get the regression values.  Only have them for certain data.
        filter_index = self._selected_filter_index
        slope: float = 0
        intercept: float = 0
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
            assert False
        calculated_result = slope * exposure + intercept
        # print(f"calc_simulated_adus({exposure},{binning}) calculated {calculated_result}")

        # Now we'll put a small percentage noise into the value so it has some variability
        rand_factor_zero_centered = self.SIMULATION_NOISE_FRACTION * (random() - 0.5)
        noisy_result = calculated_result + rand_factor_zero_centered * calculated_result
        # print(f"  Rand factor: {rand_factor_zero_centered}, noisy result: {noisy_result}")
        clipped_at_16_bits =  min(noisy_result, 65535)
        return clipped_at_16_bits
