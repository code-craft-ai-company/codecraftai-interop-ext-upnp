

"""
    .. module:: upnpdevicehint
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: upnpdevicehint module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""


__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ccai.interop.protocols.upnp.model.upnpdevicedetail import UpnpDeviceDetail

class UpnpDeviceHint:
    """
        A class to represent a UPnP device hint.
    """

    def __init__(self, hint: str):
        """
            Initialize the UPnP device hint.

            :param hint: The configured hint string.
        """
        self._hint = hint
        return
    
    def get_hint(self) -> str:
        """
            Get the hint that can be used to identify a Upnp device.

            :returns: The hint for the UPnP device.
        """
        return self._hint

    def matches(self, exhibit: "UpnpDeviceDetail") -> bool:
        """
            Check if the hint provided by the user configuration matches the device exhibit.

            :param exhibit: The UPnP device detail to check against.

            :returns: ``True`` if the hint matches the device exhibit, ``False`` otherwise.
        """
        # Validate inputs
        if not self._hint or not self._hint.strip():
            return False
            
        if exhibit is None or exhibit.evidence is None:
            return False

        # Normalize hint for comparison (case-insensitive)
        hint_normalized = self._hint.strip().lower()
        
        # Check USN for exact match or as a component (not just substring)
        usn = exhibit.evidence.usn
        if usn is not None:
            usn_normalized = usn.lower()
            
            # Check for exact match first
            if hint_normalized == usn_normalized:
                return True
            
            # Check if hint matches a USN component (separated by :: or :)
            # USN format is typically: uuid:device-UUID::urn:schemas-upnp-org:device:deviceType:version
            usn_parts = usn_normalized.replace('::', ':').split(':')
            if hint_normalized in usn_parts:
                return True
            
            # Check if hint matches the device UUID part (after uuid:)
            if usn_normalized.startswith('uuid:'):
                uuid_part = usn_normalized[5:]  # Remove 'uuid:' prefix
                # Split by '::' to get just the UUID part (before device type)
                uuid_only = uuid_part.split('::')[0] if '::' in uuid_part else uuid_part
                if hint_normalized == uuid_only:
                    return True

        return False
