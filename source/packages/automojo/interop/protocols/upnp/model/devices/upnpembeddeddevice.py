"""
    .. module:: upnpembeddeddevice
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module containing the :class:`UpnpEmbeddedDevice` class and associated diagnostic.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
    
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


import threading

from automojo.errors.exceptions import SemanticError

from automojo.interop.protocols.upnp.model.devices.upnpdevicebase import UpnpDeviceBase

class UpnpEmbeddedDevice(UpnpDeviceBase):
    """
        The UPNP Embedded device is the base device for the hierarchy that is
        associated with a unique network devices location.  The :class:`UpnpEmbeddedDevice`
        and its subdevices are linked by thier location url.

        http://www.upnp.org/specs/arch/UPnP-arch-DeviceArchitecture-v1.0.pdf
    """

    def __init__(self, embedded_device_desc=None):
        """
            Creates an embedded device object.
            
            :param embedded_device_desc: Optional embedded device description. If None, the device
                                        will be initialized with minimal information and updated later.
        """
        if embedded_device_desc is not None:
            # If we have a description, create a minimal device detail for parent initialization
            from automojo.interop.protocols.upnp.model.upnpdevicedetail import UpnpDeviceDetail
            device_detail = UpnpDeviceDetail(embedded_device_desc, None)  # No evidence for embedded devices
            super(UpnpEmbeddedDevice, self).__init__(device_detail)
        else:
            # For embedded devices without initial description, we need to initialize manually
            # since we can't create a valid UpnpDeviceDetail without proper evidence
            # Call the grandparent constructor to avoid UpnpDeviceBase's device_detail requirement
            super(UpnpDeviceBase, self).__init__()
            
            # Initialize attributes that UpnpDeviceBase would normally set
            self._device_detail = None
            self._device_description = None
            self._device_evidence = None
            
            # Set default class attributes
            self.MANUFACTURER = "unknown"
            self.MODEL_NUMBER = "unknown"
            self.MODEL_DESCRIPTION = "unknown"
            
            self._host = None
            self._urlBase = None
            
            self._device_lock = threading.RLock()
            
            self._embedded_devices = {}
            self._services_descriptions = {}
            self._services = {}
            self._service_descriptions = {}
            self._embedded_device_descriptions = {}
        
        return

    def update_description(self, host, baseUrl, description):
        """
            Updates the embedded devices description.
        """
        self._host = host
        self._urlBase = baseUrl
        self._device_description = description
        return

    def _populate_embedded_devices(self, factory, description):
        """
            This method is overloaded to prohibit the poplulation of embedded devices insided embedded devices.
        """
        # pylint: disable=no-self-use,unused-argument
        raise SemanticError("Embedded devices inside an embedded device is currently not supported.")
