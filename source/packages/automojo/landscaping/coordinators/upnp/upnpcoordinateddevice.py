"""
    .. module:: upnpcoordinateddevice
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module containing the upnpcoordinateddevice functionality.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""
__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []

from typing import Optional

from automojo.interop.protocols.upnp.model.devices.upnprootdevice import UpnpRootDevice

from automojo.interop.protocols.upnp.model.upnpdevicedetail import UpnpDeviceDetail

class UpnpCoordinatedDevice(UpnpRootDevice):
    """
        Wraps a UPNP root device that can be managed by a coordinator.
    """

    def __init__(self, device_detail: UpnpDeviceDetail, presence: Optional["UpnpPresence"] = None):
        """
            Initializes a :class:`UpnpCoordinatedDevice`.

            :param device_detail: The UPNP device description.
        """
        super().__init__(device_detail, presence=presence)

        self._coordinator_ref = None
        return

    
