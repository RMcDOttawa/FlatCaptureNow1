#  General network utilities
import re
import socket
import sys


class RmNetUtils:
    WAKE_ON_LAN_PORT = 9
    MAC_ADDRESS_LENGTH = 6
    IP4_ADDRESS_LENGTH = 4

    @classmethod
    def parse_ip4_address(cls, proposed_value: str) -> [int]:
        """Validate an IPv4 address string and parse into components array"""
        result: [int] = None
        accumulate: [int] = []
        tokens: [str] = proposed_value.split(".")
        if len(tokens) == RmNetUtils.IP4_ADDRESS_LENGTH:
            valid: bool = True
            for this_token in tokens:
                try:
                    token_parsed: int = int(this_token)
                    if (token_parsed >= 0) & (token_parsed <= 255):
                        accumulate.append(token_parsed)
                    else:
                        # Number is out of acceptable range
                        valid = False
                        break
                except ValueError:
                    valid = False
                    break
                finally:
                    pass
            if valid:
                result = accumulate
        return result

    @classmethod
    def valid_ip_address(cls, proposed_value: str) -> bool:
        """Return whether a string is a syntactically valid IPv4 address"""
        address_bytes: [int] = RmNetUtils.parse_ip4_address(proposed_value)
        return address_bytes is not None

    @classmethod
    def valid_server_address(cls, proposed_value: str) -> bool:
        """Return whether a given string is a valid IPv4 address or host name"""
        result: bool = False
        if RmNetUtils.valid_ip_address(proposed_value):
            result = True
        elif RmNetUtils.valid_host_name(proposed_value):
            result = True
        return result

    @classmethod
    def valid_host_name(cls, proposed_value: str) -> bool:
        """Determine if string is a syntactically valid host name"""
        host_name_trimmed: str = proposed_value.strip()
        valid: bool = False
        if (len(host_name_trimmed) > 0) & (len(host_name_trimmed) <= 253):
            tokens: [str] = host_name_trimmed.split(".")
            valid: bool = True
            for this_token in tokens:
                this_token_upper = this_token.upper()
                if len(this_token_upper) <= 0 | len(this_token_upper) > 63:
                    valid = False
                    break
                else:
                    # Length OK.Check for valid characters
                    match = re.match(r"^[A-Z0-9\\-]+$", this_token_upper)
                    if match is None:
                        # Contains bad characters, fail
                        valid = False
                        break
                    else:
                        # Valid characters. Can't begin with a hyphen
                        if this_token_upper.startswith("-"):
                            valid = False
                            break
        return valid

    @classmethod
    def parse_mac_address(cls, proposed_address: str) -> str:
        """Validate string as MAC address and return in a standardized format"""
        uppercase = proposed_address.upper()
        cleaned = uppercase.replace("-", "") \
            .replace(".", "") \
            .replace(":", "")
        result = None
        if len(cleaned) == (2 * RmNetUtils.MAC_ADDRESS_LENGTH):
            match = re.match(r"^[A-Z0-9]+$", cleaned)
            if match is not None:
                result = cleaned
        return result

    @classmethod
    def valid_mac_address(cls, proposed_address: str) -> bool:
        """Determine if given string is a valid MAC address"""
        clean_mac_address: str = RmNetUtils.parse_mac_address(proposed_address)
        return clean_mac_address is not None

    # Test whether we can open a socket to a given server.
    # Return a tuple with a success indicator (bool) and a message if unsuccessful

    @classmethod
    def test_connection(cls, address_string: str, port_number: str) -> [bool, str]:
        """Open a test connection to given server and return whether it was successful"""

        success: bool = False
        message: str = "(Uncaught Error)"
        try:
            # Create socket
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Connect to address and port
            test_socket.connect((address_string, int(port_number)))
            # success
            success = True
            test_socket.close()
        except socket.gaierror:
            message = "Unknown server"
        except ConnectionRefusedError:
            message = "Connection refused"
        except TimeoutError:
            message = "Connection timed out"
        except Exception as ex:
            print("Unexpected error:", sys.exc_info()[0])
            print(type(ex))
            print(ex.args)
            print(ex)
            raise
        return [success, message]

    @classmethod
    def send_wake_on_lan(cls, broadcast_address: str, mac_address: str) -> (bool, str):
        """Broadcast Wake-on-LAN packet with given MAC address"""

        success: bool = False
        message = "(Unknown Error)"
        try:
            magic_packet = RmNetUtils.make_magic_packet(mac_address)
            # Create UDP socket
            wol_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            wol_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            # Send magic packet to broadcast
            server_address = (broadcast_address, RmNetUtils.WAKE_ON_LAN_PORT)
            bytes_sent = wol_socket.sendto(magic_packet, server_address)
            # success if we get here
            if bytes_sent == len(magic_packet):
                success = True
            else:
                message = "Transmission Error"
            wol_socket.close()
        except socket.gaierror as ge:
            print(f"gaiError {ge.errno}: {ge.strerror}")
            message = "Error sending WOL"
        except Exception as ex:
            print("Unexpected error:", sys.exc_info()[0])
            print(type(ex))
            print(ex.args)
            print(ex)
            raise
        return [success, message]

    # Make up the "Magic Packet" that triggers a wake-on-lan response
    # A magic packet consists of 102 bytes laid out as follows:
    #       6 bytes of all FF FF FF FF FF FF
    #       16 repetitions of the 6-byte MAC address
    #       all as internal bytes, strings represented in hex

    @classmethod
    def make_magic_packet(cls, mac_address: str) -> bytes:
        """Create a 'magic packet' for a Wake-on-lan broadcast for given MAC address"""
        mac_address_part = RmNetUtils.parse_mac_address(mac_address)
        assert (len(mac_address_part) == (2 * RmNetUtils.MAC_ADDRESS_LENGTH))  # 2* for hex string
        leading_ff_part = "FF" * 6
        magic_as_hex = leading_ff_part + 16 * mac_address_part
        result = bytes.fromhex(magic_as_hex)
        assert (len(result) == 102)
        return result

    # Make an educated guess if the given server address is the same computer
    # as the one we're running on.  We'll use the following approach:
    #       If address is "localhost", just say Yes
    #       If address is hard-coded IP "127.0.0.1", say Yes
    #       Otherwise, try to resolve the IP address and compare it to our IP address
    #       If all else fails, say "no"

    @classmethod
    def address_is_this_computer(cls, server_address: str) -> bool:
        clean_address = server_address.strip().upper()
        if clean_address == "LOCALHOST":
            return True
        elif clean_address == "127.0.0.1":
            return True
        elif cls.valid_ip_address(clean_address):
            this_computer_ip_address = RmNetUtils.get_our_ip_address()
            return clean_address == this_computer_ip_address
        elif cls.valid_host_name(clean_address):
            this_computer_ip_address = RmNetUtils.get_our_ip_address()
            other_computer_ip_address = RmNetUtils.ip_for_host_name(clean_address)
            return this_computer_ip_address == other_computer_ip_address
        else:
            return False
        pass

    @classmethod
    def get_our_ip_address(cls) -> str:
        try:
            host_name = socket.gethostname()
            host_ip = socket.gethostbyname(host_name)
            return host_ip
        except:
            return ""

    @classmethod
    def ip_for_host_name(cls, host_name: str) -> str:
        try:
            host_ip = socket.gethostbyname(host_name)
            return host_ip
        except:
            return ""
