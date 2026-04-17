"""
    .. module:: upnpprotocolextension
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module containing the upnpprotocolextension functionality.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""
__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import Optional

import weakref

from automojo.landscaping.extensions.protocol.protocolextension import ProtocolExtension

from automojo.interop.protocols.upnp.model.devices.upnprootdevice import UpnpRootDevice
from automojo.interop.protocols.upnp.upnppresence import UpnpPresence
from automojo.interop.protocols.upnp.model.upnpdevicedetail import UpnpDeviceDetail    


class UpnpProtocolExtension(UpnpRootDevice, ProtocolExtension):
    """
        UPNP agent integrated as a protocol extension for a landscape device.
    """

    def __init__(self, device_detail: "UpnpDeviceDetail", presence: Optional["UpnpPresence"] = None):
        """
            Constructs an :class:`UpnpProtocolExtension` instance.

            :param device_detail: The device detail object that contains the information about the device.
            :param presence: Optional UpnpPresence instance for device discovery.
        """
        UpnpRootDevice.__init__(self, device_detail, presence)
        ProtocolExtension.__init__(self)
        return
    
    def initialize(self, coord_ref: weakref.ReferenceType, basedevice_ref: weakref.ReferenceType, extid: str, location: str, configinfo: dict, deviceinfo: dict):
        """
            Initializes the landscape device extension. It is not required to call this function in order to use an SSHAgent, it is used
            when an agent is attached to a LandscapeDevice as a device extension.

            :param coord_ref: A weak reference to the coordinator that is managing interactions through this
            device extension.
            :param basedevice_ref: A weak reference to the base landscape device.
            :param extid: A unique reference that can be used to identify this device via the coordinator even if its location changes.
            :param location: The location reference where this device can be found via the coordinator.
            :param configinfo: The configuration information dictionary from the landscape file for the specified host.
            :param deviceinfo: The device information dictionary from the discovery process.
        """
        UpnpRootDevice.initialize(self, coord_ref, basedevice_ref, extid, location, configinfo, deviceinfo)
        ProtocolExtension.initialize(self, coord_ref, basedevice_ref, extid, location, configinfo, deviceinfo)
        return
