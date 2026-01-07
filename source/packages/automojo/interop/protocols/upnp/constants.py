
"""
    .. module:: constants
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: constants module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""


__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []

import os
import platform

from automojo.interop.constants import DIR_AUTOMOJO_INTEROP
from automojo.networking.constants import HTTP1_1_LINESEP

UPNP_DEVICE1_NAMESPACE = "urn:schemas-upnp-org:device-1-0"
UPNP_DEVICE1_NAMESPACE_PREFIX = "{" + UPNP_DEVICE1_NAMESPACE + "}"

UPNP_DEVICE1_NAMESPACE_PREFIX_END = len(UPNP_DEVICE1_NAMESPACE_PREFIX)

UPNP_SERVICE1_NAMESPACE = "urn:schemas-upnp-org:service-1-0"

UPNP_DEFAULT_SEARCH_WINDOW_LENGTH = float(20)
UPNP_DEFAULT_SEARCH_MONITOR_INTERVAL = float(2)

TIMEDELTA_RENEWAL_WINDOW = 120


DIR_METADATA = os.path.join(DIR_AUTOMOJO_INTEROP, "protocols", "upnp", "metadata")
DIR_METADATA_DEVICES = os.path.join(DIR_METADATA, "devices")
DIR_METADATA_EMBEDDED_DEVICES = os.path.join(DIR_METADATA, "embeddeddevices")
DIR_METADATA_SERVICES = os.path.join(DIR_METADATA, "services")

class UPNP_HEADERS:
    """
        Default HTTP headers used by the UPNP implementation.
    """
    USER_AGENT = "AutomationMojo/1.0 UPNP Test Package"
    SERVER = "{},{},AutomationKit/1.0".format(platform.system(), platform.release())


UPNP_SUBSCRIPTION_NOTIFY_RESPONSE_OK = HTTP1_1_LINESEP.join([
    b'HTTP/1.1 200 OK',
    b'Connection: close',
    b'Content-Length: 0',
    b'Content-Type: text/html',
    b'Server: ' + UPNP_HEADERS.SERVER.encode() + b',UPnP/1.0',
    b''
])


class MSearchTargets:
    """
        MSearch target constants.
    """
    ROOTDEVICE = "upnp:rootdevice"
    ALL="ssdp:all"


class MSearchKeys:
    """
        MSearch dictionary or header keys that MSearch response data items are stored under.
    """
    CACHE_CONTROL = "CACHE-CONTROL"
    EXT = "EXT"
    LOCATION = "LOCATION"
    NTS = "NTS"
    SERVER = "SERVER"
    ST = "ST"
    MX = "MX"
    USN = "USN"
    USN_DEV = "USN_DEV"
    USN_CLS = "USN_CLS"

    IP = "IP"
    ROUTES = "ROUTES"


class MSearchRouteKeys:
    """
        The dictionary keys that MSearch interface routing information is stored under.
    """
    IFNAME = "LOCAL_IFNAME"
    IP = "LOCAL_IP"

