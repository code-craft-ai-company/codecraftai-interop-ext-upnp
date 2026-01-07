
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


from automojo.thisapp.wellknown import ConfiguredSuperFactorySingleton

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

        self._mappers: Dict[str, Type[DeviceDetailMapper]] = {}

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

    def lookup_device_detail_mapper(self, manufacturer: str) -> Type[DeviceDetailMapper]:
        """
            Get the detail mapper class for a specific device manufacturer.
            
            :param manufacturer: The manufacturer name to look up a mapper for.
            
            :returns: The device detail mapper class for the manufacturer.
            
            :raises KeyError: If no mapper is found for the specified manufacturer.
        """
        manufacturer = manufacturer.upper()
        if manufacturer in self._mappers:
            return self._mappers[manufacturer]
        else:
            raise KeyError(f"No device detail mapper found for manufacturer: '{manufacturer}'")

    def lookup_device_detail_mapper_safe(self, manufacturer: str) -> Type[DeviceDetailMapper]:
        """
            Get the detail mapper class for a specific device manufacturer, returning None if not found.
            
            :param manufacturer: The manufacturer name to look up a mapper for.
            
            :returns: The device detail mapper class for the manufacturer, or None if not found.
        """
        manufacturer = manufacturer.upper()
        return self._mappers.get(manufacturer, None)
