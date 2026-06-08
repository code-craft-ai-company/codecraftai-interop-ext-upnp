"""
    .. module:: upnpdeviceevidence
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module containing the UpnpDeviceEvidence object which profides basic contact information about
    the presence of a UPNP device that is available on the network.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
    
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []

from typing import Dict, Optional, TYPE_CHECKING

import json
import weakref

from datetime import datetime

if TYPE_CHECKING:
    from ccai.interop.protocols.upnp.upnppresence import UpnpPresence


class DeviceEvidence:
    """
        A :class:`UpnpDeviceEvidence` object is an object used to track evidence of the current state of UPnP devices on a network.
    """

    def __init__(self, *, usn: str, status: str, server: str, location: str, ip: str, other: Dict[str, str], presence: "UpnpPresence"):
        """
            Initialize evidence describing a detected device.

            :param usn: The unique service name for the device.
            :param status: Current status string.
            :param server: Server header reported by the device.
            :param location: URL of the device description document.
            :param ip: IP address where the device was discovered.
            :param other: Dictionary of additional headers.
            :param presence: UpnpPresence instance that reported the device.
        """
        self._usn = usn
        self._status = status
        self._server = server
        self._location = location
        self._ip = ip
        self._other = other
        self._presence_ref = weakref.ref(presence)
        self._timestamp = datetime.now()
        return
    
    @property
    def location(self) -> str:
        """
            The location of the device on the network.  This is typically a URL that can be used to access
            the device's web interface or API.
        """
        return self._location
    
    @property
    def other(self) -> Dict[str, str]:
        """
            A dictionary of other information about the device.  This can include things like the device's
            manufacturer, model number, and other metadata.
        """
        return self._other
    
    @property
    def ip(self) -> str:
        """
            The IP address of the device on the network.  This is typically a string in the format
        """
        return self._ip

    @property
    def presence(self) -> Optional["UpnpPresence"]:
        """
            The UpnpPresence object that recognized the device on the network and created this evidence object.
            Returns None if the presence object has been garbage collected.
        """
        return self._presence_ref()

    @property
    def server(self) -> str:
        """
            The server that is hosting the device.  This is typically a string that identifies the server
            software and version number.
        """
        return self._server

    @property
    def status(self) -> str:
        """
            The status of the device.  This is typically a string that indicates whether the device is
            online or offline.
        """
        return self._status

    @property
    def timestamp(self) -> datetime:
        """
            The timestamp of when this evidence of the devices state was created.
        """
        return self._timestamp

    @property
    def usn(self) -> str:
        """
            The USN (Unique Service Name) of the device.  This is typically a string that uniquely identifies
            the device on the network.
        """
        return self._usn
    
    @property
    def usn_dev(self) -> str:
        """
            The device component of the USN identifier. This is the UUID part before the '::' separator.
        """
        if "::" in self._usn:
            parts = self._usn.split("::", 1)  # Split only on first occurrence
            if len(parts) >= 1:
                p0strip = parts[0].strip()
                if len(p0strip) > 0:
                    dev_part = p0strip
            else:
                # Fallback for malformed USN (empty first part, e.g., starts with "::")
                # Log warning for debugging purposes
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("Malformed USN encountered (empty device part): '%s'", self._usn)
                # Return a meaningful fallback instead of the malformed USN
                dev_part = "unknown-device"
        else:
            # For USNs without "::", the entire USN should be the device UUID
            # This handles root device USNs that don't include "::upnp:rootdevice"
            dev_part = self._usn
        
        # Remove the "uuid:" prefix if present
        if dev_part.startswith("uuid:"):
            return dev_part[5:]  # Remove "uuid:" prefix (5 characters)
        else:
            # If no "uuid:" prefix, validate that we have a reasonable device identifier
            # Return as-is but log a warning for debugging purposes
            return dev_part
    
    @property
    def usn_cls(self) -> str:
        """
            The class component of the USN identifier. This is the service type part after the '::' separator.
        """
        if "::" in self._usn:
            parts = self._usn.split("::")
            if len(parts) > 1:
                return parts[1]
            else:
                # Fallback for malformed USN - return default
                return "upnp:rootdevice"
        else:
            return "upnp:rootdevice"
    
    def as_dict(self) -> Dict[str, str]:
        """
            Convert the DeviceEvidence object to a dictionary.

            :returns: Dictionary representation of the DeviceEvidence object.
        """
        rtnval = {
            "usn": self._usn,
            "status": self._status,
            "server": self._server,
            "location": self._location,
            "ip": self._ip,
            "other": self._other,
            "timestamp": self._timestamp.isoformat()
        }

        return rtnval

    def to_json(self) -> str:
        """
            Convert the DeviceEvidence object to a JSON string.

            :returns: JSON string representation of the DeviceEvidence object.
        """
        dict_val = self.as_dict()
        
        json_val = json.dumps(dict_val, indent=4)

        return json_val

    
