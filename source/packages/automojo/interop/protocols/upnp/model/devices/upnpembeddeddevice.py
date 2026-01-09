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

    def __init__(self, embedded_device_desc):
        """
            Creates an embedded device object.
            
            :param embedded_device_desc: The embedded device description from the parent device's description.
                                        This parameter is required as embedded devices are always created
                                        from actual device descriptions.
        """
        # Embedded devices inherit evidence from their parent device, but we need to initialize
        # with the embedded device description. Since we don't have evidence at construction time,
        # we'll initialize manually and set evidence later via update_description.
        
        # Call parent constructor first with None device_detail since embedded devices
        # inherit evidence from their parent device
        super().__init__(device_detail=None)
        
        # Initialize core attributes
        self._device_detail = None  # Will be set when evidence is available
        self._device_description = embedded_device_desc
        self._device_evidence = None  # Will be set when linked to parent
        
        # Set manufacturer info from description
        self.MANUFACTURER = "unknown"
        self.MODEL_NUMBER = "unknown" 
        self.MODEL_DESCRIPTION = "unknown"
        
        if embedded_device_desc.manufacturer is not None:
            self.MANUFACTURER = embedded_device_desc.manufacturer
        
        if embedded_device_desc.modelNumber is not None:
            self.MODEL_NUMBER = embedded_device_desc.modelNumber

        if embedded_device_desc.modelDescription is not None:
            self.MODEL_DESCRIPTION = embedded_device_desc.modelDescription

        self._host = None
        self._urlBase = None
        self._device_lock = threading.RLock()
        self._embedded_devices = {}
        self._services = {}
        
        # Initialize service and device description tables like UpnpDeviceBase does
        # Clear any existing entries from parent and populate with embedded device data
        self._service_descriptions.clear()
        serviceList = embedded_device_desc.serviceList
        if serviceList is not None:
            for serviceInfo in serviceList:
                svckey = serviceInfo.get_extension_key()
                self._service_descriptions[svckey] = serviceInfo

        self._embedded_device_descriptions.clear()
        deviceList = embedded_device_desc.deviceList
        if deviceList is not None:
            for deviceInfo in deviceList:
                devkey = deviceInfo.get_extension_key()
                self._embedded_device_descriptions[devkey] = deviceInfo
        
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
