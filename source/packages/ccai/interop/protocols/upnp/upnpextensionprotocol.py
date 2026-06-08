

"""
    .. module:: upnpextensionprotocol
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: upnpextensionprotocol module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""


__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []

from typing import List, Type

from ccai.errors.exceptions import AbstractMethodError

from ccai.extension.factory.factoryprotocolbase import FactoryProtocolBase
from ccai.interop.protocols.upnp.mapping.devicedetailmapper import DeviceDetailMapper
from ccai.interop.protocols.upnp.generation.upnpdeviceclassgenerator import UpnpDeviceClassGenerator

class UpnpFactoryProtocol(FactoryProtocolBase):
    """
        Extension protocol for device detail mapper.
    """

    factory_protocol_name = "codecraftai-interop-upnp-extension-types"

    @classmethod
    def get_device_detail_mapper_types(cls) -> List[Type[DeviceDetailMapper]]:
        """
            Returns a list of device detail mappers that are registered with this extension protocol.

            :returns: A list of :class:`DeviceDetailMapper` types.
        """
        raise AbstractMethodError("The 'get_device_detail_mapper_types' class method must be implemented for this protocol.")

    @classmethod
    def get_device_generator_types(cls) -> List[Type[UpnpDeviceClassGenerator]]:
        raise AbstractMethodError("The 'get_device_generator_types' class method must be implemented for this protocol.")
