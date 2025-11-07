
"""
    .. module:: devicedetailmapperregistry
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: devicedetailmapperregistry module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []

from typing import Dict, Type


from automojo.presence.wellknown import ConfiguredSuperFactorySingleton

from automojo.interop.protocols.upnp.mapping.devicedetailmapper import DeviceDetailMapper
from automojo.interop.protocols.upnp.upnpextensionprotocol import UpnpFactoryProtocol


class DeviceDetailMapperRegistry:
    """
        Registry for device detail processors.
    """

    def __init__(self):
        """
            Initializes the Singleton initializer class
        """

        self._mappers: Dict[str, DeviceDetailMapper] = {}

        self.initialize_mapper_table()
        
        return
    
    def initialize_mapper_table(self):
        """
            Initializes the mapper table with the default device detail mappers.
        """

        super_factory = ConfiguredSuperFactorySingleton()

        mapper_type: Type[DeviceDetailMapper]

        for mapper_type in super_factory.iterate_override_types_for_each(UpnpFactoryProtocol.get_device_detail_mapper_types):
            manufacturer_name = mapper_type.get_manufacturer().upper()
            if len(manufacturer_name) > 0 and manufacturer_name not in self._mappers:
                self._mappers[manufacturer_name] = mapper_type

        return

    def lookup_device_detail_mapper(self, manufacturer: str) -> DeviceDetailMapper:
        """
            Get the detail mapper for a specific device manufacturer.
        """
        mapper = DeviceDetailMapper
        
        manufacturer = manufacturer.upper()
        if manufacturer in self._mappers:
            mapper = self._mappers[manufacturer]

        return mapper
