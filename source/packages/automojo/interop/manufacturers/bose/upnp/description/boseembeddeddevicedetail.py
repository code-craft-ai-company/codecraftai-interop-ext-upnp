

"""
    .. module:: boseembeddeddevicedetail
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: boseembeddeddevicedetail module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []

from typing import Dict, List, Optional

from automojo.interop.protocols.upnp.model.description.specversion import SpecVersion
from automojo.interop.protocols.upnp.model.description.embeddeddevicedesc import EmbeddedDeviceDesc
from automojo.interop.protocols.upnp.model.description.icondesc import IconDesc
from automojo.interop.protocols.upnp.model.description.serviceevidence import ServiceEvidence

from automojo.interop.manufacturers.bose.upnp.description.bosedevicedetail import BoseDeviceDetail
from automojo.interop.manufacturers.bose.upnp.description.bosemultiroomversions import BoseMultiRoomVersions

class BoseEmbeddedDeviceDetail(BoseDeviceDetail):
    """
        The BoseEmbeddedDeviceDetail object is a specialized version of the BoseDeviceDetail object that
        is used to represent embedded devices.  Embedded devices are devices that are not directly
        accessible on the network, but are instead accessed through another device.
    """
    
    def __init__(self, *, specVersion: SpecVersion, deviceType: str, friendlyName: str, manufacturer: str, modelName: str, UDN: str,
                 mac_addr: str, generation: str, codename: str, color: str, software_version: str, multi_room: Optional[BoseMultiRoomVersions],
                 modelNumber: str = "", serialNumber: str = "", manufacturerURL: str = "", modelDescription: str = "", modelURL: str = "",
                 UPC: str = "", presentationURL: str = "", iconList: Optional[List[IconDesc]] = None, serviceList: Optional[List[ServiceEvidence]] = None,
                 deviceList: Optional[List['EmbeddedDeviceDesc']] = None, locationURL: Optional[str] = None, **extra: Dict[str, str]):
        """
            Initializes the embedded device detail.

            :param specVersion: UPnP specification version for the device.
            :param deviceType: Device type string.
            :param friendlyName: The friendly name of the device.
            :param manufacturer: Name of the device manufacturer.
            :param modelName: Model name for the device.
            :param UDN: Unique device name.
            :param mac_addr: MAC address for the device.
            :param generation: Device generation string.
            :param codename: Product code name.
            :param color: Device color value.
            :param software_version: Device software version.
            :param multi_room: Multi room version information or None if not available.
            :param modelNumber: Optional model number string.
            :param serialNumber: Optional serial number.
            :param manufacturerURL: Optional manufacturer URL.
            :param modelDescription: Optional model description text.
            :param modelURL: Optional model URL.
            :param UPC: Optional UPC value.
            :param presentationURL: Optional presentation URL.
            :param iconList: Optional list of device icons.
            :param serviceList: Optional list of service evidence objects.
            :param deviceList: Optional list of embedded devices.

            :returns: None
        """
        
        super().__init__(specVersion=specVersion, deviceType=deviceType, friendlyName=friendlyName,
                         manufacturer=manufacturer, modelName=modelName,
                         modelNumber=modelNumber, serialNumber=serialNumber,
                         UDN=UDN, mac_addr=mac_addr, generation=generation,
                         codename=codename, color=color,
                         software_version=software_version,
                         multi_room=multi_room,
                         manufacturerURL=manufacturerURL,
                         modelDescription=modelDescription,
                         modelURL=modelURL,
                         UPC=UPC,
                         presentationURL=presentationURL,
                         iconList=iconList,
                         serviceList=serviceList,
                         deviceList=deviceList,
                         locationURL=locationURL,
                         **extra)
        return

