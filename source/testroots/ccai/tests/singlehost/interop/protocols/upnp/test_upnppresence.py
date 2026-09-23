"""
    .. module:: test_upnppresence
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Tests for SSDP header parsing, the M-SEARCH thread socket handling, subscription event dispatch
               and the search window matching performed on behalf of :class:`UpnpPresence`.
"""

from typing import List

import threading

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from ccai import testbase

from ccai.interop.protocols.upnp.model.description.deviceevidence import DeviceEvidence
from ccai.interop.protocols.upnp.model.upnpdevicedetail import UpnpDeviceDetail
from ccai.interop.protocols.upnp.model.upnpdevicehint import UpnpDeviceHint
from ccai.interop.protocols.upnp.upnppresence import parse_http_headers, UpnpPresence
from ccai.interop.protocols.upnp.upnpsearchwindow import UpnpSearchWindow, UpnpSearchWindowState


class FakeSearchWindowOwner:
    """
        Stands in for the :class:`UpnpPresence` that owns a search window and reports device evidence.  It
        records the IDs of the search windows that report themselves closed.
    """

    def __init__(self):
        self.closed_windows: List[str] = []
        return

    def search_window_closed(self, window_id: str):
        """
            Records a search window closing.

            :param window_id: The ID of the search window that closed.
        """
        self.closed_windows.append(window_id)
        return


def test_parse_http_headers_empty_content():
    """
        Verify that parse_http_headers raises ValueError for empty content, and that content made only of
        newlines does not crash with an AssertionError or IndexError.
    """
    # Case 1: Empty content
    raised = None
    try:
        parse_http_headers(b"")
    except ValueError as xcpt:
        raised = xcpt

    testbase.assert_true(raised is not None, "ValueError raised for empty content")

    # Case 2: Only newlines (header end but no lines).  Any exception other than ValueError propagates
    # and errors the test.
    try:
        parse_http_headers(b"\r\n\r\n")
    except ValueError:
        # Rejecting header content that has no request line is an acceptable outcome.
        pass

    return


def test_thread_entry_for_msearch_socket_overwrite():
    """
        Verify that _thread_entry_for_msearch closes an existing socket before overwriting it.
    """
    with patch('ccai.interop.protocols.upnp.upnppresence.DeviceQueryManager'):
        presence = UpnpPresence()

        # Pre-create a socket as if discover_devices was called
        mock_sock = MagicMock()
        presence._msearch_sock = mock_sock

        # Mock socket.socket to return a new socket
        new_sock = MagicMock()

        with patch('socket.socket', return_value=new_sock):
            # Stop the receive loop immediately
            presence._running = False

            sgate = threading.Event()
            presence._thread_entry_for_msearch(sgate)

            # Check if old socket was closed
            mock_sock.close.assert_called_once()

            # Check if new socket is assigned
            testbase.assert_true(presence._msearch_sock is new_sock, "the new search socket is assigned")

    return


def test_search_window_matching_devices_keyed_by_usn():
    """
        A search window limited to a hint completes once a found device matches the hint, and records the
        matching device under the device's USN rather than under the hint string.
    """
    owner = FakeSearchWindowOwner()

    device_usn = "uuid:device1::urn:schemas-upnp-org:device:MediaRenderer:1"
    evidence = DeviceEvidence(
        usn=device_usn,
        status="ssdp:alive",
        server="Linux UPnP/1.0",
        location="http://192.168.1.10:8080/description.xml",
        ip="192.168.1.10",
        other={},
        presence=owner
    )
    device = UpnpDeviceDetail(None, evidence)
    hint = UpnpDeviceHint("device1")

    start = datetime.now()
    end = start + timedelta(seconds=30)
    window = UpnpSearchWindow(owner, "window-1", start, end, 0.01, limit_to=[hint])
    window.add_device(device_usn, device)

    window.start()
    closed = window.wait(timeout=10)

    testbase.assert_true(closed, "the search window closed before the wait timed out")
    testbase.assert_equal(window._window_state, UpnpSearchWindowState.COMPLETED)

    matching = window.matching_devices
    testbase.assert_equal(list(matching.keys()), [device_usn])
    testbase.assert_true(matching[device_usn] is device, "the matching entry is the device detail that was found")
    testbase.assert_equal(owner.closed_windows, ["window-1"])

    return


def test_dispatch_subscription_event_callback_signatures():
    """
        Verify that subscription callbacks support both 4-arg and 5-arg signatures.
    """
    presence = UpnpPresence()

    captured = {}

    def callback_five(ifname, sid, svc_addr, headers, body):
        captured["five"] = (ifname, sid, svc_addr, headers, body)

    def callback_four(sender_ip, sid, headers, body):
        captured["four"] = (sender_ip, sid, headers, body)

    def callback_varargs(*args):
        captured["varargs"] = args

    presence._subscription_to_callback["sid5"] = callback_five
    presence._subscription_to_callback["sid4"] = callback_four
    presence._subscription_to_callback["sidva"] = callback_varargs

    svc_addr = ("10.1.1.5", 4567)
    headers = {"SID": "sid5"}
    body = b"<prop>1</prop>"

    presence.dispatch_subscription_event_callback("eth0", "sid5", svc_addr, headers, body)
    presence.dispatch_subscription_event_callback("eth0", "sid4", svc_addr, headers, body)
    presence.dispatch_subscription_event_callback("eth0", "sidva", svc_addr, headers, body)

    five_ifname, five_sid, five_svc_addr, five_headers, five_body = captured["five"]
    testbase.assert_equal(five_ifname, "eth0")
    testbase.assert_equal(five_sid, "sid5")
    testbase.assert_equal(five_svc_addr, svc_addr)
    testbase.assert_equal(five_headers, headers)
    testbase.assert_equal(five_body, body)

    four_sender_ip, four_sid, four_headers, four_body = captured["four"]
    testbase.assert_equal(four_sender_ip, "10.1.1.5")
    testbase.assert_equal(four_sid, "sid4")
    testbase.assert_equal(four_headers, headers)
    testbase.assert_equal(four_body, body)

    va_ifname, va_sid, va_svc_addr, va_headers, va_body = captured["varargs"]
    testbase.assert_equal(va_ifname, "eth0")
    testbase.assert_equal(va_sid, "sidva")
    testbase.assert_equal(va_svc_addr, svc_addr)
    testbase.assert_equal(va_headers, headers)
    testbase.assert_equal(va_body, body)

    return
