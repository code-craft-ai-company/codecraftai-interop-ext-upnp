

"""
    .. module:: wellknown
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: wellknown module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []

import threading

from automojo.interop.protocols.upnp.generation.deviceclassgeneratorregistry import DeviceClassGeneratorRegistry
from automojo.interop.protocols.upnp.mapping.devicedetailmapperregistry import DeviceDetailMapperRegistry

_lock = threading.Lock()


DEVICE_CLASS_GENERATOR_REGISTRY_SINGLETON = None
DEVICE_DETAIL_MAPPER_REGISTRY_SINGLETON = None


def DeviceClassGeneratorRegistrySingleton() -> DeviceClassGeneratorRegistry:
    """
        Singleton for the device class generator registry.

        :returns: The global :class:`DeviceClassGeneratorRegistry` instance.
    """
    global DEVICE_CLASS_GENERATOR_REGISTRY_SINGLETON

    if DEVICE_CLASS_GENERATOR_REGISTRY_SINGLETON is None:
        with _lock:
            if DEVICE_CLASS_GENERATOR_REGISTRY_SINGLETON is None:
                DEVICE_CLASS_GENERATOR_REGISTRY_SINGLETON = DeviceClassGeneratorRegistry()

    return DEVICE_CLASS_GENERATOR_REGISTRY_SINGLETON



def DeviceDetailMapperRegistrySingleton() -> DeviceDetailMapperRegistry:
    """
        Singleton for the device detail mapper registry.

        :returns: The global :class:`DeviceDetailMapperRegistry` instance.
    """
    global DEVICE_DETAIL_MAPPER_REGISTRY_SINGLETON

    if DEVICE_DETAIL_MAPPER_REGISTRY_SINGLETON is None:
        with _lock:
            if DEVICE_DETAIL_MAPPER_REGISTRY_SINGLETON is None:
                DEVICE_DETAIL_MAPPER_REGISTRY_SINGLETON = DeviceDetailMapperRegistry()

    return DEVICE_DETAIL_MAPPER_REGISTRY_SINGLETON
