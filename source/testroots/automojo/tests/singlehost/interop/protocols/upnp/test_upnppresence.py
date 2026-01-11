import unittest
import socket
import threading
from unittest.mock import MagicMock, patch
from automojo.interop.protocols.upnp.upnppresence import parse_http_headers, UpnpPresence
from automojo.interop.protocols.upnp.upnpsearchwindow import UpnpSearchWindow, UpnpSearchWindowState
from automojo.interop.protocols.upnp.model.upnpdevicehint import UpnpDeviceHint
from automojo.interop.protocols.upnp.model.upnpdevicedetail import UpnpDeviceDetail

class TestUpnpPresence(unittest.TestCase):

    def test_parse_http_headers_empty_content(self):
        """
        Verify that parse_http_headers raises ValueError instead of crashing with AssertionError or IndexError
        when content is empty or contains only newlines.
        """
        # Case 1: Empty content
        try:
            parse_http_headers(b"")
        except ValueError:
            pass # Expected behavior
        except Exception as e:
            self.fail(f"Unexpected exception: {e}")

        # Case 2: Only newlines (header end but no lines)
        try:
            parse_http_headers(b"\r\n\r\n")
        except ValueError:
            pass # Expected behavior
        except Exception as e:
            self.fail(f"Unexpected exception: {e}")

    @patch('automojo.interop.protocols.upnp.upnppresence.DeviceQueryManager')
    def test_thread_entry_for_msearch_socket_overwrite(self, mock_dqm):
        """
        Verify that _thread_entry_for_msearch closes existing socket before overwriting it.
        """
        presence = UpnpPresence()

        # Pre-create a socket as if discover_devices was called
        mock_sock = MagicMock()
        presence._msearch_sock = mock_sock

        # Mock socket.socket to return a new socket
        new_sock = MagicMock()

        with patch('socket.socket', return_value=new_sock):
             # We want to run _thread_entry_for_msearch but stop it quickly
             presence._running = False # Stop the loop immediately

             # But we need sgate to be set
             sgate = threading.Event()

             # Call the method
             presence._thread_entry_for_msearch(sgate)

             # Check if old socket was closed
             mock_sock.close.assert_called_once()

             # Check if new socket is assigned
             self.assertEqual(presence._msearch_sock, new_sock)

    def test_search_window_matching_devices_keys(self):
        """
        Verify that matching_devices uses USNs as keys.
        """
        presence = MagicMock()
        # Create a hint
        hint = MagicMock()
        hint.get_hint.return_value = "hint_string"
        hint.matches.return_value = True

        # Create a device
        device = MagicMock()
        device.usn = "uuid:device1"

        # Create search window
        # Mocking time.sleep to break the loop by forcing state change
        with patch('time.sleep', side_effect=lambda x: setattr(window, '_window_state', UpnpSearchWindowState.COMPLETED)):
             window = UpnpSearchWindow(presence, "id", 0, 100, 0.1, limit_to=[hint])

             # Manually inject device found
             with window._lock:
                 window._devices_found = {device.usn: device}
                 window._window_state = UpnpSearchWindowState.ACTIVE

             sgate = threading.Event()
             try:
                 window._monitor_thread_entry(sgate)
             except Exception:
                 pass

        # Check matching_devices
        # Correct expectation: key is "uuid:device1"

        print(f"Matching devices keys: {window.matching_devices.keys()}")
        self.assertNotIn("hint_string", window.matching_devices.keys())
        self.assertIn("uuid:device1", window.matching_devices.keys())

if __name__ == '__main__':
    unittest.main()
