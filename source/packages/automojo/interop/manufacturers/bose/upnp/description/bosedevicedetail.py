"""
    .. module:: bosedevicedetail
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module containing data description classes that describe Bose UPNP devices.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []

from typing import Dict, List, Optional

from automojo.interop.protocols.upnp.model.description.specversion import SpecVersion
from automojo.interop.protocols.upnp.model.description.basic1devicedesc import (
    Basic1DeviceDesc,
)
from automojo.interop.protocols.upnp.model.description.embeddeddevicedesc import (
    EmbeddedDeviceDesc,
)
from automojo.interop.protocols.upnp.model.description.icondesc import IconDesc
from automojo.interop.protocols.upnp.model.description.serviceevidence import (
    ServiceEvidence,
)

from automojo.interop.manufacturers.bose.upnp.description.bosemultiroomversions import (
    BoseMultiRoomVersions,
)

"""
    <bose:X_MAC>ACBF7199AB83</bose:X_MAC>
    <bose:X_ecoSystem>ECO2</bose:X_ecoSystem>
    <bose:X_productType>taylor</bose:X_productType>
    <bose:X_productColor>1</bose:X_productColor>
    <bose:X_softwareVersion>20.0.11-231aae5</bose:X_softwareVersion>
    <bose:X_multiroomVersions>
        <NowPlaying_Version>
            <major_version>1</major_version>
            <minor_version>0</minor_version>
        </NowPlaying_Version>
        <PlaybackRequest_Version>
            <major_version>1</major_version>
            <minor_version>0</minor_version>
        </PlaybackRequest_Version>
        <ZoneControl_Version>
            <major_version/>
            <minor_version/>
        </ZoneControl_Version>
        <Audio_Payload_Version>
            <major_version>1</major_version>
            <minor_version>0</minor_version>
        </Audio_Payload_Version>
        <AudioControl_Protocol_Version>
            <major_version>2</major_version>
            <minor_version>0</minor_version>
        </AudioControl_Protocol_Version>
        <ClockSync_Protocol_Version>
            <major_version>2</major_version>
            <minor_version>1</minor_version>
        </ClockSync_Protocol_Version>
    </bose:X_multiroomVersions>
"""


class BoseDeviceDetail(Basic1DeviceDesc):
    """
        Specialized device description for Bose products.
    """

    def __init__(
        self,
        *,
        specVersion: SpecVersion,
        deviceType: str,
        friendlyName: str,
        manufacturer: str,
        modelName: str,
        UDN: str,
        mac_addr: str,
        generation: str,
        codename: str,
        color: str,
        software_version: str,
        multi_room: BoseMultiRoomVersions,
        modelNumber: str = "",
        serialNumber: str = "",
        manufacturerURL: str = "",
        modelDescription: str = "",
        modelURL: str = "",
        UPC: str = "",
        presentationURL: str = "",
        iconList: Optional[List[IconDesc]] = None,
        serviceList: Optional[List[ServiceEvidence]] = None,
        deviceList: Optional[List["EmbeddedDeviceDesc"]] = None,
        locationURL: Optional[str] = None,
        **extra: Dict[str, str]
    ):
        """
            Initializes a Bose device detail object.

            :param specVersion: UPnP specification version for the device.
            :param deviceType: Device type string.
            :param friendlyName: Human friendly device name.
            :param manufacturer: Manufacturer name.
            :param modelName: Device model name.
            :param UDN: Unique device name identifier.
            :param mac_addr: MAC address of the device.
            :param generation: Device generation value.
            :param codename: Product code name.
            :param color: Product color.
            :param software_version: Firmware version.
            :param multi_room: Multi room version information.
            :param modelNumber: Optional model number string.
            :param serialNumber: Optional serial number.
            :param manufacturerURL: Optional manufacturer URL.
            :param modelDescription: Optional model description.
            :param modelURL: Optional model URL.
            :param UPC: Optional UPC value.
            :param presentationURL: Optional presentation URL.
            :param iconList: Optional list of icon descriptors.
            :param serviceList: Optional list of service descriptors.
            :param deviceList: Optional list of embedded devices.
            :param locationURL: Optional device location URL.

            :returns: None
        """

        super().__init__(
            specVersion=specVersion,
            deviceType=deviceType,
            friendlyName=friendlyName,
            manufacturer=manufacturer,
            manufacturerURL=manufacturerURL,
            modelDescription=modelDescription,
            modelName=modelName,
            modelNumber=modelNumber,
            modelURL=modelURL,
            serialNumber=serialNumber,
            UDN=UDN,
            UPC=UPC,
            deviceList=deviceList,
            iconList=iconList,
            serviceList=serviceList,
            locationURL=locationURL,
            **extra
        )

        self.mac_addr = mac_addr
        self.generation = generation
        self.codename = codename
        self.color = color
        self.software_version = software_version
        self.multiroom = multi_room

        return
    
    def get_extension_key(self) -> str:
        """
            Generates a unique key that identifies an extension type based on where it was found in a hiearchy of code containers.

            :returns: A unique path like string that is an identifier used to lookup a device type.
        """
        
        extkey = f"{self._manufacturer}/{self._modelName}"
        
        return extkey
