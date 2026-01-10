
"""
    .. module:: basic1devicedesc
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: basic1devicedesc module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""


__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import Any, Dict, List, Optional, TYPE_CHECKING

import json

from automojo.xmodules.xlogging.enhancedloggers import getEnhancedLogger

from automojo.networking.constants import HTTP1_1_LINESEP

from automojo.interop.protocols.upnp.model.description.icondesc import IconDesc
from automojo.interop.protocols.upnp.model.description.serviceevidence import ServiceEvidence
from automojo.interop.protocols.upnp.model.description.specversion import SpecVersion

if TYPE_CHECKING:
    from automojo.interop.protocols.upnp.model.description.embeddeddevicedesc import EmbeddedDeviceDesc


logger = getEnhancedLogger()


def xml_format_basic1_device_desc(iconList: Optional[List[IconDesc]] = None, serviceList: Optional[List[ServiceEvidence]] = None,
                                  deviceList: Optional[List["EmbeddedDeviceDesc"]] = None, indent: str = "") -> str:
    """
        Create an XML representation of a basic device description.

        :param iconList: Optional list of icon descriptors.
        :param serviceList: Optional list of service descriptors.
        :param deviceList: Optional list of embedded device descriptors.
        :param indent: String used to indent the XML.

        :returns: XML string for the device description.
    """

    desc_lines = [
        f'{indent}<?xml version="1.0"?>',
        f'{indent}<root xmlns="urn:schemas-upnp-org:device-1-0">',
        f'{indent}    <specVersion>',
        f'{indent}        <major>1</major>',
        f'{indent}        <minor>0</minor>',
        f'{indent}    </specVersion>',
        f'{indent}    <URLBase>%(URLBase)s</URLBase>',
        f'{indent}    <device>',
        f'{indent}        <deviceType>urn:schemas-upnp-org:device:Basic:1</deviceType>',
        f'{indent}        <friendlyName>%(friendlyName)s</friendlyName>',
        f'{indent}        <manufacturer>%(manufacturer)s</manufacturer>',
        f'{indent}        <manufacturerURL>%(manufacturerURL)s</manufacturerURL>',
        f'{indent}        <modelDescription>%(modelDescription)s</modelDescription>',
        f'{indent}        <modelName>%(modelName)s</modelName>',
        f'{indent}        <modelNumber>%(modelNumber)s</modelNumber>',
        f'{indent}        <modelURL>%(modelURL)s</modelURL>',
        f'{indent}        <serialNumber>%(serialNumber)s</serialNumber>',
        f'{indent}        <UDN>%(UDN)s</UDN>',
        f'{indent}        <UPC>%(UPC)s</UPC>',
    ]

    if iconList is not None and len(iconList) > 0:
        desc_lines.extend([
            f'{indent}        <iconList>'
        ])
        
        icon_indent = indent + "            "
        for icon in iconList:
            desc_lines.append(icon.as_xml(indent=icon_indent))

        desc_lines.extend([
            f'{indent}        </iconList>'
        ])

    if serviceList is not None and len(serviceList) > 0:
        desc_lines.extend([
            f'{indent}        <serviceList>'
        ])
        
        service_indent = indent + "            "
        for service in serviceList:
            desc_lines.append(service.as_xml(indent=service_indent))

        desc_lines.extend([
            f'{indent}        </serviceList>'
        ])
    
    if deviceList is not None and len(deviceList) > 0:
        desc_lines.extend([
            f'{indent}        <deviceList>'
        ])
        
        device_indent = indent + "            "
        for device in deviceList:
            desc_lines.append(device.as_xml(indent=device_indent))

        desc_lines.extend([
            f'{indent}        </deviceList>'
        ])

    desc_lines.extend([
        f'{indent}        <presentationURL>%(presentationURL)s</presentationURL>',
        f'{indent}    </device>',
        f'{indent}</root>'
    ])

    desc = '\n'.join(desc_lines)

    return desc


class Basic1DeviceDesc:
    """
        Class representing a UPnP Basic 1 device description.
    """

    def __init__(self, *, specVersion: SpecVersion, deviceType: str, friendlyName: str, manufacturer: str, modelName: str, UDN: str,
                 modelNumber: str="", serialNumber: str="", manufacturerURL: str="", modelDescription: str = "", modelURL: str = "", UPC: str="", presentationURL: str="",
                 iconList: Optional[List[IconDesc]] = None, serviceList: Optional[List[ServiceEvidence]] = None, deviceList: Optional[List['EmbeddedDeviceDesc']] = None,
                 locationURL: Optional[str]=None, **extras: dict):
        """
            Create a new :class:`Basic1DeviceDesc` instance.
        """

        self._deviceType = deviceType
        self._specVersion = specVersion
        self._friendlyName = friendlyName
        self._manufacturer = manufacturer
        self._manufacturerURL = manufacturerURL
        self._modelDescription = modelDescription
        self._modelName = modelName
        self._modelNumber = modelNumber
        self._serialNumber = serialNumber
        self._UDN = UDN
        self._UPC = UPC
        self._modelURL = modelURL
        self._presentationURL = presentationURL

        self.iconList: List[IconDesc] = iconList if iconList is not None else []
        self.deviceList: List["EmbeddedDeviceDesc"] = deviceList if deviceList is not None else []
        self.serviceList: List[ServiceEvidence] = serviceList if serviceList is not None else []
        
        self._locationURL = locationURL
        self._baseURL = locationURL

        if locationURL is not None:
            endScheme = locationURL.find("://")
            if endScheme > -1:
                endScheme += 3
                startLeaf = locationURL.find("/", endScheme)
                if startLeaf > -1:
                    self._baseURL = locationURL[:startLeaf]
        else:
            dbgmsg = "Device description without a locationURL, this could be an embedded device"
            logger.debug(dbgmsg)

        self._extras = extras
        return


    @property
    def baseURL(self) -> str:
        """
            The base URL that should be used to make request for service and embedded device descriptions.
        """
        rntval = self._baseURL if self._baseURL is not None else ""
        return rtnval

    @property
    def deviceType(self) -> str:
        """
            The type of the device, typically in the format 'urn:schemas-upnp-org:device:Basic:1'.
        """
        return self._deviceType
    
    @property
    def extras(self) -> Dict[str, Any]:
        """
            Additional metadata or information about the device.
        
            :returns: Dictionary containing additional metadata.
        """
        return self._extras

    @property
    def friendlyName(self) -> str:  # noqa: A003
        """
            The friendly name of the device.
        
            :returns: String representing the friendly name of the device.
        """
        return self._friendlyName
    
    @property
    def locationURL(self) -> Optional[str]:
        """
            The URL of the device's location on the network.
            This is typically used to access the device's web interface or API.
        """
        return self._locationURL

    @property
    def manufacturer(self) -> str:
        """
            The manufacturer of the device.
        
            :returns: String representing the manufacturer of the device.
        """
        return self._manufacturer
    @property
    def manufacturerURL(self) -> str:   # noqa: A003
        """
            The URL of the manufacturer's website.
        
            :returns: String representing the manufacturer's URL.
        """
        return self._manufacturerURL
    @property
    def modelDescription(self) -> str:
        """
            The description of the device model.
        
            :returns: String representing the model description.
        """
        return self._modelDescription
    
    @property
    def modelName(self) -> str:
        """
            The name of the device model.

            :returns: String representing the model name.
        """
        return self._modelName
    
    @property
    def modelNumber(self) -> str:
        """
            The model number of the device.
        
            :returns: String representing the model number.
        """
        return self._modelNumber
    
    @property
    def modelURL(self) -> str:
        """
            The URL of the device model.
        
            :returns: String representing the model URL.
        """
        return self._modelURL

    @property
    def presentationURL(self) -> str:
        """
            The URL for the device's presentation page.
        
            :returns: String representing the presentation URL.
        """
        return self._presentationURL

    @property
    def serialNumber(self) -> str:
        """
            The serial number of the device.
        
            :returns: String representing the serial number.
        """
        return self._serialNumber
    
    @property
    def specVersion(self) -> SpecVersion:
        """
            The specification version of the UPnP device description.
        
            :returns: SpecVersion object representing the specification version.
        """
        return self._specVersion
    
    @property
    def UDN(self) -> str:
        """
            The Unique Device Name (UDN) of the device.
        
            :returns: String representing the UDN.
        """
        return self._UDN

    @property
    def UPC(self) -> str:
        """
            The Universal Product Code (UPC) of the device.
        
            :returns: String representing the UPC.
        """
        return self._UPC

    def add_icon(self, icon: "IconDesc"):
        """
            Add an icon to the device description.
        
            :param icon: IconDesc object representing the icon to be added.
        """
        self.iconList.append(icon)
        return
    
    def add_device(self, device: "EmbeddedDeviceDesc"):
        """
            Add an embedded device to the device description.
        
            :param device: EmbeddedDeviceInfo object representing the device to be added.
        """
        self.deviceList.append(device)
        return

    def add_service(self, service: "ServiceEvidence"):
        """
            Add a service to the device description.
        
            :param service: ServiceInfo object representing the service to be added.
        """
        self.serviceList.append(service)
        return

    def as_dict(self, brief: bool = False) -> Dict[str, Any]:
        """
            Convert the Basic1DeviceDesc object to a dictionary.
        
            :returns: Dictionary representation of the Basic1DeviceDesc object.
        """
        desc = {  
            "deviceType": self.deviceType,
            "specVersion": self.specVersion.as_dict(),
            "friendlyName": self.friendlyName,
            "manufacturer": self.manufacturer,
            "manufacturerURL": self.manufacturerURL,
            "modelDescription": self.modelDescription,
            "modelName": self.modelName,
            "modelNumber": self.modelNumber,
            "serialNumber": self.serialNumber,
            "UDN": self.UDN,
            "UPC": self.UPC,
            "modelURL": self.modelURL,
            "presentationURL": self.presentationURL
        }

        if self.locationURL is not None:
            desc["locationURL"] = self.locationURL

        if not brief:
            if self.iconList is not None and len(self.iconList) > 0:
                desc["iconList"] = [icon.as_dict() for icon in self.iconList]

            if self.serviceList is not None and len(self.serviceList) > 0:
                desc["serviceList"] = [service.as_dict() for service in self.serviceList]
            
            if self.deviceList is not None and len(self.deviceList) > 0:
                desc["deviceList"] = [device.as_dict() for device in self.deviceList]
        
            if self.extras is not None and len(self.extras) > 0:
                desc.update(self.extras)

        return desc
    
    def get_extension_key(self) -> str:
        """
            Generates a unique key that identifies an extension type based on where it was found in a hiearchy of code containers.

            :returns: A unique path like string that is an identifier used to lookup a device type.
        """
        
        extkey = f"{self._manufacturer}/{self._modelName}/{self._modelNumber}"
        
        return extkey
    
    def to_json(self, brief: bool = False) -> str:
        """
            Convert the Basic1DeviceDesc object to a JSON string.
        
            :param brief: If True, returns a brief representation of the device description.
            
            :returns: JSON string representation of the Basic1DeviceDesc object.
        """
        
        dict_val = self.as_dict(brief=brief)

        json_val = json.dumps(dict_val, indent=4)
        
        return json_val

    def to_xml(self, indent="") -> str:
        """
            Convert the Basic1DeviceDesc object to an XML string.
        
            :param indent: Indentation for the XML string.

            :returns: XML string representation of the Basic1DeviceDesc object.
        """
        
        desc_template = xml_format_basic1_device_desc(
            iconList=self.iconList,
            serviceList=self.serviceList,
            deviceList=self.deviceList,
            indent=indent
        )
        
        # Substitute placeholder values with actual device properties
        # Ensure all values are strings and handle None values
        substitution_values = {
            'URLBase': self.baseURL or '',
            'friendlyName': self.friendlyName or '',
            'manufacturer': self.manufacturer or '',
            'manufacturerURL': self.manufacturerURL or '',
            'modelDescription': self.modelDescription or '',
            'modelName': self.modelName or '',
            'modelNumber': self.modelNumber or '',
            'modelURL': self.modelURL or '',
            'serialNumber': self.serialNumber or '',
            'UDN': self.UDN or '',
            'UPC': self.UPC or '',
            'presentationURL': self.presentationURL or ''
        }
        
        try:
            desc = desc_template % substitution_values
        except (KeyError, TypeError) as e:
            raise ValueError(f"Failed to format XML template: {e}") from e
        
        return desc

    def __str__(self) -> str:
        """
            Convert the Basic1DeviceDesc object to a string.
        
            :returns: String representation of the Basic1DeviceDesc object.
        """
        
        sval = f'Basic1DeviceDesc(friendlyName={self.friendlyName}, modelName={self.modelName}, modelNumber={self.modelNumber}, serialNumber={self.serialNumber}, UDN={self.UDN}, UPC={self.UPC}, presentationURL={self.presentationURL})'
        
        return sval
