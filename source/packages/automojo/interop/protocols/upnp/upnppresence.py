"""
    .. module:: UpnpPresence
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module containing the :class:`UpnpPresence` class and associated diagnostic.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
    
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import Callable, Dict, List, Optional, Tuple, Union

import copy
import os
import re
import socket
import threading
import uuid
import weakref
from urllib.parse import urlparse

from datetime import datetime, timedelta
from io import BytesIO

import requests

from automojo.errors.raising import raise_for_http_status

from automojo.xmodules.xlogging.enhancedloggers import getEnhancedLogger
from automojo.xmodules.xformatting import indent_lines
from automojo.xmodules.xthreading.looper import Looper
from automojo.xmodules.xthreading.looperpool import LooperPool

from automojo.networking.constants import HTTP1_1_LINESEP, HTTP1_1_END_OF_HEADER
from automojo.networking.multicast import create_multicast_listener_socket_for_iface
from automojo.networking.interfaces import (
    get_all_ipv4_interfaces,
    get_correspondance_ip_address,
    get_ipv4_address,
    get_interface_for_ip,
)

from automojo.interop.protocols.upnp.constants import MSearchTargets, MSearchKeys
from automojo.interop.protocols.upnp.upnpsearchwindow import UpnpSearchWindow
from automojo.interop.protocols.upnp.model.upnpdevicedetail import UpnpDeviceDetail
from automojo.interop.protocols.upnp.devicequerymanager import DeviceQueryManager
from automojo.interop.protocols.upnp.constants import (
    UPNP_DEFAULT_SEARCH_WINDOW_LENGTH,
    UPNP_DEFAULT_SEARCH_MONITOR_INTERVAL,
    UPNP_SUBSCRIPTION_NOTIFY_RESPONSE_OK,
    UPNP_HEADERS
)

from automojo.interop.protocols.upnp.model.upnpdevicehint import UpnpDeviceHint
from automojo.interop.protocols.upnp.model.description.deviceevidence import DeviceEvidence
from automojo.interop.protocols.upnp.model.description.serviceevidence import ServiceEvidence


REGEX_NOTIFY_HEADER = re.compile("NOTIFY[ ]+[*/]+[ ]+HTTP/1")

REGEX_SUBSCRIPTION_TIMEOUT = re.compile("^Seconds?-([0-9]+|infinite)", flags=re.IGNORECASE)

logger = getEnhancedLogger()


class SsdpProtocol:
    """
        SSDP Protocol constants.
    """
    MULTICAST_ADDRESS = '239.255.255.250'
    PORT = 1900

    HEADERS = {
        "ST": MSearchTargets.ROOTDEVICE,
        "Man": "ssdp:discover",
        "MX": "1"
    }


SSDP_IPV6_MULTICAST_ADDRESS_LINK_LOCAL="FF02::C"
SSDP_IPV6_MULTICAST_ADDRESS_SITE_LOCAL="FF05::C"
SSDP_IPV6_MULTICAST_ADDRESS_ORG_LOCAL="FF08::C"
SSDP_IPV6_MULTICAST_ADDRESS_GLOBAL_LOCAL="FF0E::"


def notify_parse_request(content: bytes) -> dict:
    """
        Takes in the content of the NOTIFY request and parses it into a
        python dictionary object.
        
        :param content: Notify request content as bytes.
        
        :returns: A python dictionary with key and values from the Notify request
    """
    content = content.decode('utf-8')

    resp_headers = None
    resp_body = None

    mobj = REGEX_NOTIFY_HEADER.search(content)
    if mobj is not None:
        header_content = None
        body_content = None

        if content.find("\r\n\r\n") > -1:
            header_content, body_content = content.split("\r\n\r\n", 1)
        elif content.find("\n\n") > -1:
            header_content, body_content = content.split("\n\n", 1)
        else:
            header_content = content

        resplines = header_content.splitlines(False)

        # Pop the NOTIFY header
        resplines.pop(0).strip()

        resp_headers = {}
        for nxtline in resplines:
            cidx = nxtline.find(":")
            if cidx > -1:
                key = nxtline[:cidx].upper()
                val = nxtline[cidx+1:].strip()
                resp_headers[key] = val

        if body_content is not None:
            resp_body = body_content

    return resp_headers, resp_body


def parse_http_headers(header_content: bytes) -> Tuple[str, Dict[str, str]]:
    """
        Parses an HTTP header block and returns the request line and
        dictionary of header values.

        :param header_content: Raw bytes of the HTTP header.

        :returns: Tuple of the request line and a dictionary of headers.
    """

    headers = {}
    header_lines = header_content.splitlines(False)

    assert len(header_lines) > 0, "The header content was not a valid HTTP request header."
    req_line = header_lines[0]
    for hline in header_lines[1:]:
        name_end = hline.find(b":")
        if name_end > -1:
            hname = hline[:name_end].upper().decode().strip()
            hval = hline[name_end + 1:].decode().strip()
            headers[hname] = hval

    return req_line, headers


def parse_ssdp_message(content: bytes) -> Dict[str, str]:
    """
        Takes in the content of the response of an MSEARCH request and parses it into a
        python dictionary object.
        
        :param content: MSearch response content as a bytes.
        
        :returns: A python dictionary with key and values from the MSearch response
    """
    content = content.decode('utf-8')

    respinfo = None

    resplines = content.splitlines(False)
    if len(resplines) > 0:
        header = resplines.pop(0).strip()
        if header.startswith("M-SEARCH * HTTP/") or header.startswith("NOTIFY * HTTP/") or header.startswith("HTTP/"):
            respinfo = {}
            for nxtline in resplines:
                cidx = nxtline.find(":")
                if cidx > -1:
                    key = nxtline[:cidx].upper()
                    val = nxtline[cidx+1:].strip()
                    respinfo[key] = val

    return respinfo


class UpnpPresenceId:
    """
        Identifier representing a device and its UPnP device class.
    """

    def __init__(self, device_id: str, device_class: str):
        """
            Construct an identifier for a device and its class.
        """
        self._device_id = device_id
        self._device_class = device_class
        return

    def to_usn(self) -> str:
        """
            Return the USN string for this presence identifier.
        """
        usn = f"uuid:{self._device_id}::{self._device_class}"
        return usn


class UpnpPresence:
    """
        The UpnpPresence class is used to manage the presence of a device on the network using SSDP. The UpnpPresence object
        maintains a multi-cast listening socket and thread that listens for incoming multi-cast SSDP messages allowing the
        UpnpPresence to establish a UPNP device presence on the network.

        The UpnpPresence class also maintains a multip-cast send and receive socket that is associated M-SEARCH activites on
        the network.  The purpose of the seperate M-SEARCH socket is because devices receiving M-SEARCH messages are going to send back
        responses in the form of a reply to the M-SEARCH request and not in the form of a broadcast.  This means we need to listend for
        M-SEARCH responses on the socket that the M-SEARCH messages were sent from.

        The M-SEARCH socket thread containuously calls the socket.recvfrom() method to listen for incoming M-SEARCH messages.  Because the
        socket is thread safe, when a 'discovery' call is made, then the calling thread simply sends the M-SEARCH message on the send side
        of the socket.

        This is a single use object.  Once it has been started and then stopped, it should not be reused.  Create a new
        :class:`UpnpPresence` instance if presence services are needed again.

    """


    def __init__(self, agent_id: Optional[UpnpPresenceId] = None, multicast_address = SsdpProtocol.MULTICAST_ADDRESS,
                 multicast_port = SsdpProtocol.PORT, presence_interfaces: Optional[List[str]] = None, interface_port: int = 80,
                 ttl: int=32):
        """
            :param agent_id: The id that is used to provide a presence for this node.  If not provided, the agent will
            not respond to M-SEARCH events.
            :param ttl: The time to live for the multicast packet
            0 = same host
            1 = same subnet
            32 = same site
            64 = same region
            128 = same continent
            255 = unrestricted scope
        """
        self._agent_id = agent_id

        self._multicast_address = multicast_address
        self._multicast_port = multicast_port
        self._interface_port = interface_port

        self._ttl = ttl

        self._lock = threading.Lock()
        
        self._running = False
        self._stop_called = False

        self._msearch_sock = None
        self._presence_sockets = {}
        self._callback_sockets = {}
        
        self._msearch_thread = None
        self._presence_threads = {}
        self._callback_threads = {}

        self._callback_address_from_iface: Dict[str, Tuple[str, int]] = {}
        
        self._dispatch_pool = None

        self._inactive_devices: Dict[str, DeviceEvidence] = {}
        self._active_devices: Dict[str, DeviceEvidence] = {}

        self._subscription_to_callback: Dict[str, Callable] = {}

        self._query_manager = DeviceQueryManager()

        self._search_windows: Dict[str, UpnpSearchWindow] = {}

        self._embedded_device_notifications_by_usn: Dict[str, List[Callable]] = {}
        self._root_device_notifications_by_usn: Dict[str, List[Callable]] = {}
        self._service_notifications_by_usn: Dict[str, List[Callable]] = {}

        self._presence_interfaces = None
        if presence_interfaces is not None:
            self._presence_interfaces = presence_interfaces
        else:
            # If no interfaces are specified, enumerate IPv4 capable interfaces
            self._presence_interfaces = get_all_ipv4_interfaces()

        return


    @property
    def active_devices(self) -> Dict[str, DeviceEvidence]:
        """
            Return a copy of the currently active devices.
        """
        rtnval = None

        self._lock.acquire()
        try:
            rtnval = copy.deepcopy(self._active_devices)
        finally:
            self._lock.release()

        return rtnval


    @property
    def inactive_devices(self) -> Dict[str, DeviceEvidence]:
        """
            Return a copy of devices that have gone inactive.
        """

        self._lock.acquire()
        try:
            rtnval = copy.deepcopy(self._inactive_devices)
        finally:
            self._lock.release()

        return rtnval


    @property
    def presence_endpoint(self) -> Tuple[str, int]:
        """
            Returns the endpoint that this presence is listening on.
            
            :returns: A tuple containing the IP address and port of the presence socket.
        """
        return self._multicast_address, self._multicast_port


    def discover_devices(self, limit_to: List[UpnpDeviceHint]=None, custom_headers: Optional[Dict[str, str]] = None,
                         window_length: float = UPNP_DEFAULT_SEARCH_WINDOW_LENGTH,
                         monitor_interval: float = UPNP_DEFAULT_SEARCH_MONITOR_INTERVAL) -> UpnpSearchWindow:
        """
            Begin discovery of UPnP devices on the network.
            
            :param limit_to: Optional device hints to limit the search.
            :param custom_headers: Optional additional search headers.
            :param window_length: How long the search window remains active.
            :param monitor_interval: Polling interval for search window updates.
            
            :returns: The created :class:`UpnpSearchWindow` instance.
        """

        st: str = MSearchTargets.ROOTDEVICE

        if not self._running:
            raise RuntimeError("The SSDP Scanner must be running before a discovery can be triggered.  Call 'start'.")

        msearch_msg_lines = [
            b'M-SEARCH * HTTP/1.1',
            b'HOST: %s:%d' % (SsdpProtocol.MULTICAST_ADDRESS.encode("utf-8"), SsdpProtocol.PORT),
            b'ST: %s' % st.encode("utf-8"),
            b'MX: 1',
            b'MAN: "ssdp:discover"'
        ]

        if custom_headers is not None:
            for hname, hval in custom_headers.items():
                hname = hname.upper().encode("utf-8")
                msearch_msg_lines.append(b'%s: %s' % (hname, hval.encode("utf-8")))

        msearch_msg_lines.append(b'')
        msearch_msg_lines.append(b'')

        msearch_msg = b"\r\n".join(msearch_msg_lines)
        
        start = datetime.now()
        end = start + timedelta(seconds=window_length)

        wid = str(uuid.uuid4())

        disco_window = UpnpSearchWindow(self, wid, start, end, monitor_interval, limit_to=limit_to)
        disco_window.start()

        self._lock.acquire()
        try:
            disco_window_ref = weakref.ref(disco_window)
            self._search_windows[wid] = disco_window_ref
        finally:
            self._lock.release()

        sock = self._get_search_socket()

        try:
            sock.sendto(msearch_msg, (self._multicast_address, self._multicast_port))
        except OSError as serr:
            # If we get an OSError while sending, our socket is likely invalid and we need
            # to force the socket to be re-freshed
            self._lock.acquire()
            try:
                if sock is not None:
                    sock.close()

                self._msearch_sock = None
            finally:
                self._lock.release()
            raise

        return disco_window


    def dispatch_embedded_device_notification(self, ifname: str, from_ip: str, usn: str, nt: str, nts: str, msg_info: Dict[str, str]):
        """
            Dispatch a notification to the registered callback functions for an embedded device.
            
            :param usn: The USN of the root device.
            :param msg_info: The message detail of the notification.
        """
        self._lock.acquire()
        try:
            if usn in self._embedded_device_notifications_by_usn:

                # Dont make any calls while holding the upnp presence lock, make a copy of the receipients list
                # and release the lock before dispatching the notifications to registered callbacks
                receipients = [r for r in self._embedded_device_notifications_by_usn[usn]]

                self._lock.release()
                try:
                    for callback in receipients:
                        callback(ifname, from_ip, usn, nt, nts, msg_info)
                finally:
                    self._lock.acquire()

        finally:
            self._lock.release()

        return


    def dispatch_root_device_notification(self, ifname: str, from_ip: str, usn: str, nt: str, nts: str, msg_info: Dict[str, str]):
        """
            Dispatch a notification to the registered callback functions for the root device.
            
            :param usn: The USN of the root device.
            :param msg_info: The message detail of the notification.
        """
        self._lock.acquire()
        try:
            if usn in self._root_device_notifications_by_usn:

                # Dont make any calls while holding the upnp presence lock, make a copy of the receipients list
                # and release the lock before dispatching the notifications to registered callbacks
                receipients = [r for r in self._root_device_notifications_by_usn[usn]]

                self._lock.release()
                try:
                    for callback in receipients:
                        callback(ifname, from_ip, usn, nt, nts, msg_info)
                finally:
                    self._lock.acquire()

        finally:
            self._lock.release()

        return

    def dispatch_service_notification(self, ifname: str, from_ip: str, usn: str, nt: str, nts: str, msg_info: Dict[str, str]):
        """
            Dispatch a notification to the registered callback functions for a device service.
            
            :param ifname: The interface name that the notification was received on.
            :param from_ip: The IP address that the notification was received from.
            :param usn: The USN of the root device.
            :param nt: The NT (Notification Type) header value from the notification.
            :param nts: The NTS (Notification Sub-Type) header value from the notification.
            :param msg_info: The message detail of the notification.
        """
        self._lock.acquire()
        try:
            if usn in self._service_notifications_by_usn:

                # Dont make any calls while holding the upnp presence lock, make a copy of the receipients list
                # and release the lock before dispatching the notifications to registered callbacks
                receipients = [r for r in self._service_notifications_by_usn[usn]]

                self._lock.release()
                try:
                    for callback in receipients:
                        callback(ifname, from_ip, usn, nt, nts, msg_info)
                finally:
                    self._lock.acquire()

        finally:
            self._lock.release()

        return


    def dispatch_subscription_event_callback(self, ifname: str, sid: str, svc_addr: Tuple[str, int], req_headers: Dict[str, str], req_body: str):

        service_event_callback = None
        self._lock.acquire()
        try:
            if sid in self._subscription_to_callback:
                service_event_callback = self._subscription_to_callback[sid]
        finally:
            self._lock.release()

        if service_event_callback is not None:
            service_event_callback(ifname, sid, svc_addr, req_headers, req_body)

        return


    def form_callback_url_for_interface(self, ifname: str) -> Union[str, None]:

        callback_url = None

        self._lock.acquire()
        try:
            if ifname in self._callback_address_from_iface:
                callback_addr, callback_port = self._callback_address_from_iface[ifname]

                callback_url = f"<http://{callback_addr}:{callback_port}/notify>"
        finally:
            self._lock.release()

        return callback_url


    def process_msearch(self, ifname: str, from_endpoint: Tuple[str, int], response: bytes):
        """
            Handle an incoming M-SEARCH message.
        """

        # We only process and respond to M-SEARCH messages if we have been given an identity
        # to respond as
        if self._agent_id is not None:
            from_ip = from_endpoint[0]
            
            msg_info = parse_ssdp_message(response)
            
            if msg_info is not None:
                # Process the M-SEARCH message info
                st = msg_info.get(MSearchKeys.ST, None)
                if st is not None:
                    mx = msg_info.get(MSearchKeys.MX, "1")

                    logger.debug(f"M-SEARCH: ifname={ifname} from={from_ip} ST={st}")

                    # Check the ST header to see if it is a request for the root device
                    if st == MSearchTargets.ROOTDEVICE:

                        # Get the IP that should be used by a specific client to attempt to communicate with the local device
                        # We need to get the IP address that corresponds to the interface that the M-SEARCH request came in on
                        # because we might be listening on multiple networks, if we respond with the wrong IP address, then the
                        # client might not be able to communicate with us.
                        interface_ip = get_correspondance_ip_address(from_ip)

                        # If the ST header is for the root device, then we will respond with our presence
                        usn = self._agent_id.to_usn()
                        server = "Automation Mojo UPnP Presence Agent/1.0"
                        location = f"http://{interface_ip}:{self._interface_port}/upnp/device.xml"

                        response_lines = [
                            b"HTTP/1.1 200 OK",
                            b"ST: upnp:rootdevice",
                            b"USN: %s" % usn.encode("utf-8"),
                            b"SERVER: %s" % server.encode("utf-8"),
                            b"LOCATION: %s" % location.encode("utf-8"),
                            b"CACHE-CONTROL: max-age=1800",
                            b"",
                            b""
                        ]

                        response_msg = HTTP1_1_LINESEP.join(response_lines)

                        sock = self._get_presence_socket(ifname)
                        sock.sendto(response_msg, from_endpoint)

                else:
                    response = response.decode()
                    response = indent_lines(response, 1, indent=4)

                    dbgmsg_lines = [
                        f"M-SEARCH message id not have an 'ST' field from={from_ip}:",
                        response
                    ]

                    dbgmsg = os.linesep.join(dbgmsg_lines)
                    logger.debug(dbgmsg)
            else:
                response = response.decode()
                response = indent_lines(response, 1, indent=4)

                dbgmsg_lines = [
                    f"Unable to process M-SEARCH message from={from_ip}:",
                    response
                ]

                dbgmsg = os.linesep.join(dbgmsg_lines)
                logger.debug(dbgmsg)
        
        return


    def process_notify(self, ifname: str, from_endpoint: Tuple[str, int], message: bytes):
        """
            Process a NOTIFY message from a UPnP device.
        """

        from_ip = from_endpoint[0]


        msg_info = parse_ssdp_message(message)

        if msg_info is not None:
            message_st = msg_info.get(MSearchKeys.ST, None)

            nts = msg_info.get("NTS")

            if MSearchKeys.USN in msg_info:

                if "NT" in msg_info:
                    nt = msg_info["NT"]
                    usn = msg_info["USN"]
                    status = None

                    ntparts = nt.split(":")

                    if nt == 'upnp:rootdevice':

                        if nts is not None:
                            self._update_device("NOTIFY", from_ip, usn, nts, msg_info)

                            self.dispatch_root_device_notification(ifname, from_ip, usn, nt, nts, msg_info)

                            logger.debug(
                                f"NOTIFY - DEVICE: ifname={ifname} nt={nt} usn={usn} from={from_ip}"
                            )
                        else:
                            logger.debug("NTS header missing for root device notification.")
    
                    elif len(ntparts) > 2:
                        nt_comp_group = ntparts[1]
                        nt_comp_type = ntparts[2]

                        if nt_comp_type == "service":
                            if nts is not None:
                                self.dispatch_service_notification(ifname, from_ip, usn, nt, nts, msg_info)

                                logger.debug(
                                    f"NOTIFY - SERVICE ifname={ifname} nt={nt} usn={usn} from={from_ip} service={nt} status={status}"
                                )
                            else:
                                logger.debug("NTS header missing for service notification.")
                        elif nt_comp_type == "device":
                            if nts is not None:
                                # This is an embedded device notification
                                self.dispatch_embedded_device_notification(ifname, from_ip, usn, nt, nts, msg_info)

                                logger.debug(
                                    f"NOTIFY - EMBEDDED DEVICE ifname={ifname} nt={nt} usn={usn} from={from_ip} status=<unknown>"
                                )
                            else:
                                logger.debug("NTS header missing for embedded device notification.")
                        else:
                            logger.debug(
                                f"NOTIFY - UNKNOWN TYPE ifname={ifname} nt={nt} usn={usn} from={from_ip} status=<unknown>"
                            )
                    else:
                        logger.debug(
                            f"NOTIFY - OTHER ifname={ifname} nt={nt} usn={usn} from={from_ip} status=<unknown>"
                        )
                else:
                    logger.debug(f"REPLY: from={from_ip} NT=<not found>")
            else:
                logger.debug(f"REPLY: from={from_ip} USN=<not found>")
        else:
            message = message.decode()
            message = indent_lines(message, 1, indent=4)

            dbgmsg_lines = [
                f"Unable to process NOTIFY message from={from_ip}:",
                message
            ]

            dbgmsg = os.linesep.join(dbgmsg_lines)
            logger.debug(dbgmsg)

        
        return


    def process_msearch_reply(self, from_endpoint: Tuple[str, int], response: bytes):
        """
            Handle a reply to one of our M-SEARCH queries.
        """

        from_ip = from_endpoint[0]

        reply_info = parse_ssdp_message(response)

        if reply_info is not None:
            if MSearchKeys.USN in reply_info:
                if "ST" in reply_info:
                    st = reply_info["ST"]

                    if st == 'upnp:rootdevice':
                        usn = reply_info["USN"]
                        server = reply_info["SERVER"]
                        location = reply_info["LOCATION"]

                        # Update our active device tables with then newly discovered device, pass along the 'ssdp:alive'
                        # notification subtype as a constant.  If a device replies to m-search requests, it is considered alive.
                        self._update_device("M-SEARCH", from_ip, usn, "ssdp:alive", reply_info)
                        
                        active_search_windows: List[UpnpSearchWindow] = []

                        # Check to see if there are any active search windows searching for devices
                        self._lock.acquire()
                        try:
                            for wid, search_window_ref in self._search_windows.items():

                                    search_window: UpnpSearchWindow = search_window_ref()
                                    if search_window is not None:
                                        # If the search window is still active, then add the device to the search window
                                        if search_window.is_active():
                                            active_search_windows.append(search_window)

                        finally:
                            self._lock.release()

                        # If there are any active search windows, then we will need to query the device for its description and then pass the device detail
                        # to the any active search windows.
                        if len(active_search_windows):
                            device_evidence = DeviceEvidence(usn=usn, status="alive", server=server, location=location, ip=from_ip, other=reply_info, presence=self)
                            device_desc = self._query_manager.query_device_description(location)
                            if device_desc is not None:

                                device_detail = UpnpDeviceDetail(device_evidence, device_desc)

                                for search_window in active_search_windows:
                                    search_window.add_device(usn, device_detail)
                            else:
                                logger.error(f"Unable to get device description for {location}.")

            else:
                logger.debug(f"REPLY: from={from_ip} USN=<not found>")
                
        else:
            response = response.decode()
            response = indent_lines(response, 1, indent=4)

            dbgmsg_lines = [
                f"Unable to process M-SEARCH reply message from={from_ip}:",
                response
            ]

            dbgmsg = os.linesep.join(dbgmsg_lines)
            logger.debug(dbgmsg)

        return


    def register_embedded_device_notification_handler(self, usn: str, notify_callback: Callable):
        """
            Register a callback function to be called when an embedded device is found.
            
            :param usn: The USN of the device to register the callback for.
            :param notify_callback: The callback function to call when the device is found.
        """
        self._lock.acquire()
        try:
            if usn in self._embedded_device_notifications_by_usn:
                self._embedded_device_notifications_by_usn[usn].append(notify_callback)
            else:
                self._embedded_device_notifications_by_usn[usn] = [notify_callback]
        finally:
            self._lock.release()
        return


    def register_root_device_notification_handler(self, usn: str, notify_callback: Callable):
        """
            Register a callback function to be called when a root device is found.
            
            :param usn: The USN of the device to register the callback for.
            :param notify_callback: The callback function to call when the device is found.
        """
        self._lock.acquire()
        try:
            if usn in self._root_device_notifications_by_usn:
                self._root_device_notifications_by_usn[usn].append(notify_callback)
            else:
                self._root_device_notifications_by_usn[usn] = [notify_callback]
        finally:
            self._lock.release()
        return


    def register_service_notification_handler(self, usn: str, notify_callback: Callable):
        """
            Register a callback function to be called when a service is found.
            
            :param usn: The USN of the service to register the callback for.
            :param notify_callback: The callback function to call when the service is found.
        """
        self._lock.acquire()
        try:
            if usn in self._service_notifications_by_usn:
                self._service_notifications_by_usn[usn].append(notify_callback)
            else:
                self._service_notifications_by_usn[usn] = [notify_callback]
        finally:
            self._lock.release()
        return


    def search_window_closed(self, window_id: str):
        """
            Called when a search window is closed.  This method is used to remove the search window from the list of
            active search windows.
            
            :param window_id: The ID of the search window that was closed.
        """
        self._lock.acquire()
        try:
            if window_id in self._search_windows:
                del self._search_windows[window_id]
        finally:
            self._lock.release()
        return


    def service_subscribe(self, host_ip: str, subscribe_url: str, subscribe_timeout_secs: Optional[int], service_event_callback: Callable,
                        custom_headers: Optional[Dict[str, str]] = None, sid: Optional[str] = None, renew: bool = False) -> Union[Tuple[None, None], Tuple[str, datetime]]:
        """
            Subscribe to a remote service.

            :param host_ip: The ip address of the interface on the host computer that will be used to communicate with the service.
            :param subscribe_url: The url of the service to use for creating the subscription.
            :param subscribe_timeout_secs: Optional timeout in seconds for the subscription.
            :param service_event_callback: The callback that is called when events occur for the subscription.
            :param custom_headers: A optional set of custom headers to use when creating the subscription
            :param sid: Optional subscription identifier used when renewing an existing subscription.
            :param renew: Indicates if this is a renewal request.

            :returns: A tuple with the 'sid' subscription id of the new subscription and the expiration the subscription.
            :raises ValueError: If the ``TIMEOUT`` header contains an invalid value.
        """

        sub_sid = None
        sub_expires = None

        if renew and sid is None:
            errmsg = "A 'sid' must be provided when renewing a subscription."
            raise ValueError(errmsg)

        ifname = get_interface_for_ip(host_ip)

        callback_url = self.form_callback_url_for_interface(ifname)
        if callback_url is None:
            errmsg = f"No callback url found for ifname={ifname}"
            raise RuntimeError(errmsg) from None

        parsed_url = urlparse(subscribe_url)
        host_header = parsed_url.netloc or parsed_url.hostname or host_ip

        headers = { "HOST": host_header, "User-Agent": UPNP_HEADERS.USER_AGENT}
        if renew:
            headers["SID"] = sid
            if subscribe_timeout_secs is not None:
                headers["TIMEOUT"] = "Seconds-%s" % subscribe_timeout_secs
        else:
            headers.update({"CALLBACK": callback_url, "NT": "upnp:event"})
            if subscribe_timeout_secs is not None:
                headers["TIMEOUT"] = "Seconds-%s" % subscribe_timeout_secs

        if custom_headers is not None:
            headers.update(custom_headers)

        resp: requests.Response = requests.request("SUBSCRIBE", subscribe_url, headers=headers)

        if resp.status_code == 200:
            #============================== Example Expected Response Headers ==============================
            # SID: uuid:RINCON_7828CA09247C01400_sub0000000207
            # TIMEOUT: Second-86400
            # Server: Linux UPnP/1.0 Sonos/62.1-82260-monaco_dev (ZPS13)
            # Connection: close
            resp_headers: Dict[str, str] = {str(hk).upper(): hv for hk, hv in resp.headers.items()}

            nxtheader = None
            try:
                nxtheader = "SID"
                sub_sid = resp_headers[nxtheader]

                nxtheader = "TIMEOUT"
                sub_timeout_str = resp_headers[nxtheader]

                sub_timeout = None
                mobj = REGEX_SUBSCRIPTION_TIMEOUT.match(sub_timeout_str)
                if mobj is not None:
                    timeout_str = mobj.groups()[0]
                    sub_timeout = 86400 if timeout_str == "infinite" else int(timeout_str)

                if sub_sid is not None:
                    if sub_timeout is None:
                        errmsg = f"Invalid timeout value in 'TIMEOUT' header: '{sub_timeout_str}'"
                        raise ValueError(errmsg)

                    sub_expires = datetime.now() + timedelta(seconds=sub_timeout)
                    self._lock.acquire()
                    try:
                        if renew and sid is not None and sid != sub_sid:
                            self._subscription_to_callback.pop(sid, None)
                        self._subscription_to_callback[sub_sid] = service_event_callback
                    finally:
                        self._lock.release()
                
            except KeyError as kerr:
                errmsg = f"Event subscription response was missing in '{nxtheader}' header."
                raise KeyError(errmsg) from kerr
        elif renew and resp.status_code in (404, 412):
            logger.debug("Subscription renewal failed with status %s, attempting recovery.", resp.status_code)
        else:
            ctxmsg = f"While attempting to subscribe to subscribe_url={subscribe_url}"
            raise_for_http_status(resp.status_code, resp.content, ctxmsg)

        return sub_sid, sub_expires
    

    def service_unsubscribe(self, host_ip: str, subscribe_url: str, subscription_id: str, custom_headers: Optional[Dict[str, str]] = None):
        """
            Unsubscribe to a service.

            :param host_ip: The ip address of the interface on the host computer that will be used to communicate with the service.
            :param subscribe_url: The url of the service to use for creating the subscription.
            :param subscription_id: The id of the subscription to unsubscribe from.
            :param custom_headers: A optional set of custom headers to use when creating the subscription
        """

        parsed_url = urlparse(subscribe_url)
        host_header = parsed_url.netloc or parsed_url.hostname or host_ip

        headers = { "HOST": host_header, "User-Agent":  UPNP_HEADERS.USER_AGENT, "SID": subscription_id}

        if custom_headers is not None:
            headers.update(custom_headers)
            
        resp: requests.Response = requests.request("UNSUBSCRIBE", subscribe_url, headers=headers)
        if resp.status_code != 200 and resp.status_code != 412:
            ctxmsg = "Error while unsubscribing from service."
            raise_for_http_status(resp.status_code, resp.content, ctxmsg)

        removal_reason = "UNSUBSCRIBE acknowledged" if resp.status_code == 200 else "subscription already expired"
        removed = False

        self._lock.acquire()
        try:
            removed = subscription_id in self._subscription_to_callback
            self._subscription_to_callback.pop(subscription_id, None)
        finally:
            self._lock.release()

        logger.debug("Subscription cleanup sid=%s removed=%s reason=%s", subscription_id, removed, removal_reason)

        return


    def discard_subscription_callback(self, subscription_id: str):
        """
            Remove a subscription callback handler without issuing an unsubscribe request.

            :param subscription_id: The subscription identifier to remove from the callback table.
        """

        removed = False

        self._lock.acquire()
        try:
            removed = subscription_id in self._subscription_to_callback
            self._subscription_to_callback.pop(subscription_id, None)
        finally:
            self._lock.release()

        logger.debug("Subscription callback discard sid=%s removed=%s", subscription_id, removed)

        return


    def start(self):
        """
            Start background threads for presence monitoring and discovery.
        """

        self._lock.acquire()
        try:

            if self._running:
                raise RuntimeError("SSDP Scanner is already running.")
            
            # If running was False, the we are uninitialed and non of the threads have been created or started, set running
            # to true and begin the startup of all threads.
            self._running = True

            self._lock.release()
            try:
                sgate = threading.Event()

                dispatch_pool = LooperPool(Looper, "am-upnp-dispatch", min_loopers=5, max_loopers=10, highwater=5, daemon=True)
                dispatch_pool.start_pool()

                self._dispatch_pool = dispatch_pool

                for ifname in self._presence_interfaces:

                    # We need a presence thread and callback thread for each interface we want to support
                    sgate.clear()
                    presence_thread = threading.Thread(target=self._thread_entry_for_presence, name=f"am-upnp-presence-{ifname}", args=(sgate, ifname), daemon=True)
                    presence_thread.start()
                    sgate.wait()

                    sgate.clear()
                    callback_thread = threading.Thread(target=self._thread_entry_for_callback, name=f"am-upnp-callback-{ifname}", args=(sgate, ifname), daemon=True)
                    callback_thread.start()
                    sgate.wait()
                
                    self._callback_threads[ifname] = callback_thread
                    self._presence_threads[ifname] = presence_thread

                sgate.clear()
                self._msearch_thread = threading.Thread(target=self._thread_entry_for_msearch, name="am-upnp-search", args=(sgate,), daemon=True)
                self._msearch_thread.start()
                sgate.wait()
            finally:
                self._lock.acquire()

        finally:
            self._lock.release()

        return


    def stop(self) -> None:
        """Stop all running threads and close sockets."""

        if self._stop_called:
            return

        self._stop_called = True
        self._running = False

        self._lock.acquire()
        try:
            for sock in self._presence_sockets.values():
                sock.close()

            for sock in self._callback_sockets.values():
                sock.close()

            if self._msearch_sock is not None:
                self._msearch_sock.close()
        finally:
            self._lock.release()

        for th in self._presence_threads.values():
            th.join()

        for th in self._callback_threads.values():
            th.join()

        if self._msearch_thread is not None:
            self._msearch_thread.join()

        if self._dispatch_pool is not None:
            self._dispatch_pool.shutdown()

        return

    def cleanup(self) -> None:
        """Forcefully clean up sockets and thread references after stopping."""

        self.stop()

        self._lock.acquire()
        try:
            self._presence_sockets.clear()
            self._callback_sockets.clear()
            self._callback_address_from_iface.clear()

            self._msearch_sock = None
        finally:
            self._lock.release()

        self._presence_threads.clear()
        self._callback_threads.clear()
        self._msearch_thread = None

        return


    def _get_callback_socket(self, ifname: str) -> socket.socket:
        """
            Return or create a callback service socket.
        """

        sock = None

        self._lock.acquire()
        try:

            if ifname in self._callback_sockets:
                sock = self._callback_sockets[ifname]
            else:
                ifaddr = get_ipv4_address(ifname)
                if ifaddr is not None:

                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    
                    # Bind to port 0 so we can get an ephimeral port
                    sock.bind((ifaddr, 0))

                    # Get the ephimeral port assigned to our callback socket
                    _, port = sock.getsockname()

                    # Listen with a small backlog of 1
                    sock.listen(1)

                    callback_addr = (ifaddr, port)

                    self._callback_sockets[ifname] = sock
                    self._callback_address_from_iface[ifname] = callback_addr

        finally:
            self._lock.release()

        return sock


    def _get_presence_socket(self, ifname: str) -> socket.socket:
        """
            Return or create the multicast socket for a given interface.
        """

        sock = None

        self._lock.acquire()
        try:
            if ifname not in self._presence_sockets:
                sock: socket.socket = create_multicast_listener_socket_for_iface(
                    ifname,
                    self._multicast_address,
                    self._multicast_port,
                    family=socket.AF_INET,
                    ttl=self._ttl,
                )
                self._presence_sockets[ifname] = sock
            else:
                sock = self._presence_sockets[ifname]
        finally:
            self._lock.release()
            
        return sock


    def _get_search_socket(self) -> socket.socket:
        """
            Return or create the socket used for M-SEARCH operations.
        """

        sock = None

        self._lock.acquire()
        try:
            if self._msearch_sock is None:
                self._msearch_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

            sock = self._msearch_sock
        finally:
            self._lock.release()
            
        return sock


    def _process_callback(self, ifname: str, svc_addr: Tuple[str, int], accepted_sock: socket.socket):
        
        cbbuffer = BytesIO()

        req_headers = None

        headers_length = None
        content_length = None

        message_length = None
        read_so_far = 0
        remaining_length = 1024
        try:
            # Read To Header
            while self._running and remaining_length > 0:
                # Process the requests
                nxtbuff = accepted_sock.recv(remaining_length)
                read_so_far += len(nxtbuff)

                # If we didn't get anything from recv, it means we hit the end of
                # the pipe.  We can exit the read loop.
                if len(nxtbuff) == 0:
                    break

                cbbuffer.write(nxtbuff)

                if req_headers is None:
                    current_content = cbbuffer.getvalue()
                    header_end = current_content.find(HTTP1_1_END_OF_HEADER)
                    if header_end > -1:
                        header_content = current_content[:header_end]
                        headers_length = len(header_content) + len(HTTP1_1_END_OF_HEADER)
                        req_line, req_headers = parse_http_headers(header_content)
                        if "CONTENT-LENGTH" in req_headers:
                            content_length = int(req_headers["CONTENT-LENGTH"])
                            message_length = headers_length + content_length
                
                if message_length is not None:
                    remaining_length = message_length - read_so_far

        finally:
            accepted_sock.sendall(UPNP_SUBSCRIPTION_NOTIFY_RESPONSE_OK)
            accepted_sock.close()

        request = cbbuffer.getvalue()

        cbbuffer.truncate(0)
        cbbuffer.seek(0)

        if headers_length is None:
            logger.error("Callback message missing header terminator. svc_addr=%s", svc_addr)
            return

        req_body = request[headers_length:]
        req_body = req_body.decode("utf-8")

        #TODO: Add package capture support for debugging callback requests

        if "SID" in req_headers:
            sid = req_headers["SID"]

            self.dispatch_subscription_event_callback(ifname, sid, svc_addr, req_headers, req_body)

        else:
            dbgmsg_lines = [
                "Received subscription notification without an SID. svc_addr={}".format(svc_addr),
                "REQUEST HEADERS:"
            ]

            for hdr_key, hdr_val in req_headers.items():
                dbgmsg_lines.append("    {}:{}".format(hdr_key, hdr_val))

            dbgmsg_lines.append("REQUEST BODY:")
            dbgmsg_lines.append(req_body)

            dbgmsg = os.linesep.join(dbgmsg_lines)

            logger.debug(dbgmsg)

        return


    def _thread_entry_for_callback(self, sgate: threading.Event, ifname: str):
        """
            Thread loop used to listen for subscription callbacks.
        """

        sock = self._get_callback_socket(ifname)

        sgate.set()

        while self._running:

            if sock is None:
                sock = self._get_callback_socket(ifname)
                if sock is None:
                    continue

            try:
                # Wait untile we get a connection or the socket is closed on us.
                rcv_sock, rcv_addr =  sock.accept()

                # Queue the callback workpacket for dispatching by the dispatch pool
                wkpacket = (self._process_callback, (ifname, rcv_addr, rcv_sock))
                
                self._dispatch_pool.push_work(wkpacket)

            except socket.timeout:
                dbgmsg = "Our socket timed out.  Don't do anything except loop around and call accept again."
                logger.debug(dbgmsg)

            except Exception as xcpt:
                err_type = type(xcpt).__name__
                logger.exception(
                    "Unexpected %s in callback thread for %s.",
                    err_type,
                    ifname,
                )
                self._lock.acquire()
                try:
                    if sock is not None:
                        sock.close()

                    self._callback_sockets.pop(ifname, None)
                finally:
                    self._lock.release()

                sock = None

        return


    def _thread_entry_for_msearch(self, sgate: threading.Event):
        """
            Thread loop used to send and receive M-SEARCH discovery messages.
        """

        self._msearch_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        sgate.set()

        while self._running:

            sock = self._get_search_socket()

            try:
                resp, addr = sock.recvfrom(1024)

                if resp.startswith(b"HTTP/"):
                    self.process_msearch_reply(addr, resp)
                
                else:
                    logger.debug(resp)

            except socket.timeout:
                pass

            except OSError:
                self._lock.acquire()
                try:
                    if sock is not None:
                        sock.close()

                    self._msearch_sock = None
                finally:
                    self._lock.release()

        return


    def _thread_entry_for_presence(self, sgate: threading.Event, ifname: str):
        """
            Thread loop used to listen for SSDP presence messages.
            
            The presence thread entry point is called when the presence thread is
            started. It listens for incoming SSDP messages and dispatches them.
        """

        sgate.set()

        while self._running:

            sock = self._get_presence_socket(ifname)

            try:
                msg_in, addr = sock.recvfrom(1024)

                if msg_in.startswith(b"M-SEARCH * HTTP/"):
                    self.process_msearch(ifname, addr, msg_in)

                elif msg_in.startswith(b"NOTIFY * HTTP/"):
                    self.process_notify(ifname, addr, msg_in)
                
                else:
                    logger.debug(msg_in)

            except socket.timeout:
                pass

            except Exception as xcpt:
                err_type = type(xcpt).__name__
                logger.exception(
                    "Unexpected %s in presence thread for %s.",
                    err_type,
                    ifname,
                )
                self._lock.acquire()
                try:
                    if sock is not None:
                        sock.close()

                    self._presence_sockets.pop(ifname, None)
                finally:
                    self._lock.release()

        return


    def _update_device(self, context: str, from_ip: str, usn: str, nts: str, msg_info: Dict[str, str]):
        """
            Update the device tables based on an SSDP notification.
        """

        location = msg_info.get("LOCATION")
        server = msg_info.get("SERVER")
        status = "unknown"

        if nts == "ssdp:alive":
            status = 'active'
            
            device_evidence = DeviceEvidence(usn=usn, status=status, server=server, location=location, ip=from_ip, other=msg_info, presence=self)
            
            self._lock.acquire()
            try:
                # If we got an alive message and were able to get a new description from the device,
                # then we know it is now active, remove the old device detail from the inactive devices
                # list and add our new device detail to the active devices list. 
                if usn in self._inactive_devices:
                    del self._inactive_devices[usn]

                self._active_devices[usn] = device_evidence
            finally:
                self._lock.release()

        elif nts == "ssdp:byebye":
            status = 'inactive'

            # this is a device bye-bye
            device_evidence = DeviceEvidence(usn=usn, status=status, server=server, location=location, ip=from_ip, other=msg_info, presence=self)

            self._lock.acquire()
            try:

                if usn in self._active_devices:
                    del self._active_devices[usn]


                self._inactive_devices[usn] = device_evidence
            finally:
                self._lock.release()

        logger.info(
            f"UPDATE DEVICE: context={context} usn={usn} status={status} location={location}"
        )

        return
