
"""
    .. module:: upnpdevicedetail
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: upnpdevicedetail module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""


__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from typing import Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from ccai.interop.protocols.upnp.model.upnpdevicehint import UpnpDeviceHint

from ccai.interop.protocols.upnp.model.description.basic1devicedesc import Basic1DeviceDesc
from ccai.interop.protocols.upnp.model.description.deviceevidence import DeviceEvidence


class UpnpDeviceDetail:
    """
        Class to represent UPnP device details.
    """

    def __init__(self, description: Union[Basic1DeviceDesc, None], evidence: DeviceEvidence, hint: Optional["UpnpDeviceHint"] = None):
        """
            Initialize the UPnP device details.

            :param description: Parsed device description object or ``None``.
            :param evidence: Evidence about the UPnP device from discovery.
            :param hint: Optional hint that matched this device.
        """
        self._evidence = evidence
        self._description = description
        self._hint = hint
        return
    
    @property
    def evidence(self) -> DeviceEvidence:
        """
            Get the UPnP device evidence from the las M-Search response or Notify message.

            :returns: The UPnP device evidence.
        """
        return self._evidence
    
    @property
    def description(self) -> Union[Basic1DeviceDesc, None]:
        """
            Get the UPnP device description for the device or None if the device description was not available.

            :returns: The last UPnP device description obtained for the device or ``None`` if a device description has not been obtained.
        """
        return self._description

    @property
    def hint(self) -> Optional["UpnpDeviceHint"]:
        """
            Get the hint that matched this device, if available.

            :returns: The matching :class:`UpnpDeviceHint` or ``None``.
        """
        return self._hint

    def set_hint(self, hint: Optional["UpnpDeviceHint"]):
        """
            Set the hint that matched this device.

            :param hint: The matching :class:`UpnpDeviceHint` or ``None``.
        """
        self._hint = hint
        return
    
    def generate_extension_key(self) -> str:
        """
            Generates a unique key that identifies an extension type based on where
            it was found in a hiearchy of code containers.

            :returns: A unique path like string that is an identifier used to lookup a device type.
            
            :raises ValueError: If the device description is not available.
        """
        if self._description is None:
            raise ValueError("Cannot generate extension key: device description is not available")
        
        extkey = self._description.get_extension_key()
        return extkey
    
