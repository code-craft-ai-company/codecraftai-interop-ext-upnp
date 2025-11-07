
"""
    .. module:: deviceclassgeneratorregistry
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: deviceclassgeneratorregistry module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []

from typing import Dict, Type, Union


from automojo.presence.wellknown import ConfiguredSuperFactorySingleton

from automojo.interop.protocols.upnp.generation.upnpdeviceclassgenerator import UpnpDeviceClassGenerator
from automojo.interop.protocols.upnp.upnpextensionprotocol import UpnpFactoryProtocol


class DeviceClassGeneratorRegistry:
    """
        Registry for device class generators.
    """

    def __init__(self):
        """
            Initializes the device class registery class.
        """

        self._generators: Dict[str, UpnpDeviceClassGenerator] = {}

        self._initialize_generator_table()
        
        return
    
    def _initialize_generator_table(self):
        """
            Initializes the mapper table with the default device detail mappers.
        """

        super_factory = ConfiguredSuperFactorySingleton()

        generator_type: Type[UpnpDeviceClassGenerator]

        for generator_type in super_factory.iterate_override_types_for_each(UpnpFactoryProtocol.get_device_generator_types):
            manufacturer_name = generator_type.get_manufacturer().upper()
            if len(manufacturer_name) > 0 and manufacturer_name not in self._generators:
                self._generators[manufacturer_name] = generator_type

        return

    def lookup_device_class_generator(self, manufacturer: str) -> Union[UpnpDeviceClassGenerator, None]:
        """
            Get the device class generator for a specific device manufacturer.
        """
        generator = None
        
        manufacturer = manufacturer.upper()
        if manufacturer in self._generators:
            generator = self._generators[manufacturer]

        return generator
