"""
    .. module:: upnpprotocolextension
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module containing the upnpprotocolextension functionality.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""
__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import Optional, Union

import weakref

from automojo.landscaping.protocolextensions.protocolextension import ProtocolExtension

from automojo.interop.protocols.upnp import UpnpAgent


class UpnpProtocolExtension(UpnpAgent, ProtocolExtension):
    """
        UPNP agent integrated as a protocol extension for a landscape device.
    """

    def __init__(self, manufacturer: str, modelNumber: str, modelDescription):
        """
            Constructs an :class:`UpnpProtocolExtension` instance.

            :param manufacturer: The manufacturer string.
            :param modelNumber: The model number identifier.
            :param modelDescription: Human readable model description.
        """
        UpnpAgent.__init__(self, manufacturer, modelNumber, modelDescription)
        ProtocolExtension.__init__(self)
        return
    
    def initialize(self, coord_ref: weakref.ReferenceType, basedevice_ref: weakref.ReferenceType, extid: str, location: str, configinfo: dict):
        """
            Initializes the landscape device extension. It is not required to call this function in order to use an SSHAgent, it is used
            when an agent is attached to a LandscapeDevice as a device extension.

            :param coord_ref: A weak reference to the coordinator that is managing interactions through this
            device extension.
            :param extid: A unique reference that can be used to identify this device via the coordinator even if its location changes.
            :param location: The location reference where this device can be found via the coordinator.
            :param configinfo: The configuration information dictionary from the landscape file for the specified host.
        """
        ProtocolExtension.initialize(self, coord_ref, basedevice_ref, extid, location, configinfo)
        return
