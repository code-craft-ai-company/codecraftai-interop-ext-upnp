
"""
    .. module:: boseupnpextension
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: boseupnpextension module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []

from typing import List, Type


from automojo.interop.protocols.upnp.upnpextensionprotocol import UpnpFactoryProtocol
from automojo.extension.factory.factoryextension import FactoryExtension
from automojo.interop.protocols.upnp.mapping.devicedetailmapper import DeviceDetailMapper

from automojo.interop.manufacturers.bose.upnp.mapping.bosedevicedetailmapper import BoseDeviceDetailMapper

class BoseUpnpExtensionProtocol(UpnpFactoryProtocol, FactoryExtension):
    """
        Extension protocol for Bose devices.
    """

    @classmethod
    def get_device_detail_mapper_types(cls) -> List[Type[DeviceDetailMapper]]:
        """
            Returns a list of device detail mappers that are registered with this
            extension protocol.

            :returns: List of :class:`DeviceDetailMapper` types supported by the
                      protocol.
        """
        types = [ BoseDeviceDetailMapper ]
        return types
    
