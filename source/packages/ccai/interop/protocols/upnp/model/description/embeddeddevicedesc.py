
"""
    .. module:: embeddeddevicedesc
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: embeddeddevicedesc module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""


__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from typing import List, Optional

from ccai.interop.protocols.upnp.model.description.specversion import SpecVersion
from ccai.interop.protocols.upnp.model.description.icondesc import IconDesc
from ccai.interop.protocols.upnp.model.description.serviceevidence import ServiceEvidence

from ccai.interop.protocols.upnp.model.description.basic1devicedesc import Basic1DeviceDesc


class EmbeddedDeviceDesc(Basic1DeviceDesc):
    """
        EmbeddedDeviceDesc is a class that represents an embedded device description in UPnP.
        It inherits from :class:`Basic1DeviceDesc` and adds additional attributes and methods specific to embedded devices.
    """

    def __init__(self, *, specVersion: SpecVersion, deviceType: str, friendlyName: str, manufacturer: str, modelName: str, modelNumber: str,
                 UDN: str, serialNumber: str="", manufacturerURL: str="", modelDescription: str = "", modelURL: str = "", UPC: str="",
                presentationURL: str="", iconList: Optional[List[IconDesc]] = None, serviceList: Optional[List[ServiceEvidence]] = None,
                locationURL: Optional[str]=None, deviceList: Optional[List['EmbeddedDeviceDesc']] = None, **extras: dict):
        """
            Initialize the embedded device description structure.
        """
        super().__init__(specVersion=specVersion, deviceType=deviceType, friendlyName=friendlyName, manufacturer=manufacturer, manufacturerURL=manufacturerURL,
                         modelDescription=modelDescription, modelName=modelName, modelNumber=modelNumber, modelURL=modelURL, serialNumber=serialNumber, UDN=UDN,
                         UPC=UPC, presentationURL=presentationURL, deviceList=deviceList, iconList=iconList, serviceList=serviceList, locationURL=locationURL, **extras)
        return
