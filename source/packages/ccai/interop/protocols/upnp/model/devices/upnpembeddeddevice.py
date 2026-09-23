"""
    .. module:: upnpembeddeddevice
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module containing the :class:`UpnpEmbeddedDevice` class and associated diagnostic.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
    
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from ccai.errors.exceptions import SemanticError

from ccai.interop.protocols.upnp.model.devices.upnpdevicebase import UpnpDeviceBase

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
        # Validate required parameter
        if embedded_device_desc is None:
            raise ValueError("embedded_device_desc parameter is required and cannot be None")
        
        # Embedded devices need special handling since they don't have their own device_detail
        # at construction time. We need to create a minimal device_detail to satisfy the parent constructor.
        from ccai.interop.protocols.upnp.model.upnpdevicedetail import UpnpDeviceDetail
        from ccai.interop.protocols.upnp.model.description.deviceevidence import DeviceEvidence
        
        # Validate that embedded_device_desc has required UDN attribute
        if not hasattr(embedded_device_desc, 'UDN') or embedded_device_desc.UDN is None:
            raise ValueError("embedded_device_desc must have a valid UDN attribute")
        
        # Create a minimal device evidence for embedded devices
        # Embedded devices don't have their own network presence, so we create placeholder evidence
        temp_evidence = DeviceEvidence(
            usn=f"uuid:{embedded_device_desc.UDN}::upnp:rootdevice",
            status="embedded",  # Special status for embedded devices
            server="Embedded/1.0",
            location="embedded://localhost/embedded",  # Placeholder location
            ip="127.0.0.1",  # Placeholder IP
            other={},
            presence=None  # Embedded devices don't have their own presence
        )
        
        # Create a device detail with the minimal evidence
        temp_device_detail = UpnpDeviceDetail(embedded_device_desc, temp_evidence)
        
        # Call parent constructor with the device detail
        super().__init__(device_detail=temp_device_detail)
        
        # The parent constructor will have set up the basic structure, but we need to
        # override some attributes specific to embedded devices
        
        # Clear and repopulate service descriptions with embedded device data
        self._service_descriptions = {}
        serviceList = embedded_device_desc.serviceList
        if serviceList is not None:
            for serviceInfo in serviceList:
                svckey = serviceInfo.get_extension_key()
                self._service_descriptions[svckey] = serviceInfo

        # Clear and repopulate embedded device descriptions
        self._embedded_device_descriptions = {}
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
