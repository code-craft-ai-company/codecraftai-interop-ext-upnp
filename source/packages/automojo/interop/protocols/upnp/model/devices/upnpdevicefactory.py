"""
    .. module:: UpnpDeviceFactory
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module containing the :class:`UpnpDeviceFactory` class and associated diagnostic.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
    
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import Union

from automojo.errors.exceptions import SemanticError

from automojo.extension.resource.resourceextension import (
    collect_resource_extensions_under_code_container,
    collect_resource_extensions_under_folder
)

from automojo.xmodules.ximport import import_by_name
from automojo.xmodules.xcollections.context import Context

from automojo.interop.protocols.upnp.model.description.basic1devicedesc import Basic1DeviceDesc
from automojo.interop.protocols.upnp.model.description.embeddeddevicedesc import EmbeddedDeviceDesc
from automojo.interop.protocols.upnp.model.description.serviceevidence import ServiceEvidence

from automojo.interop.protocols.upnp.model.upnpdevicedetail import UpnpDeviceDetail

from automojo.interop.protocols.upnp.model.devices.upnpembeddeddevice import UpnpEmbeddedDevice
from automojo.interop.protocols.upnp.model.devices.upnprootdevice import UpnpRootDevice
from automojo.interop.protocols.upnp.model.services.upnpserviceproxy import UpnpServiceProxy

from automojo.interop.protocols.upnp.extensions import standard as standard_extensions


class UpnpDeviceFactory:
    """
        The :class:`UpnpDeviceFactory` object is a singleton object that manages the cataloging and instantiation
        of code generated UPnP device and service extensions.  We utilize code generated device classes and
        service proxy classes because that makes each class of device and each method on those classes
        individually isolatable and debugable.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        """
            Constructs new instances of the UpnpDeviceFactory object from the :class:`UpnpDeviceFactory`.
            This is a singlton object that is used to register and instantiate UPNP devices based on
            their devicetype id.
        """
        if cls._instance is None:
            cls._instance = super(UpnpDeviceFactory, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
            Initializes the Singleton initializer class
        """
        thisType = type(self)
        if not thisType._initialized:
            thisType._initialized = True

            self._dyn_embedded_device_registry = {}
            self._dyn_root_device_registry = {}
            self._dyn_service_registry = {}
            self._std_embedded_device_registry = {}
            self._std_root_device_registry = {}
            self._std_service_registry = {}

            gcontext = Context() 

            dyn_ext_module = None
            dyn_ext_module_name = gcontext.lookup("/upnp/extensions/dynamic/module")
            if dyn_ext_module_name is not None:
                dyn_ext_module = import_by_name(dyn_ext_module_name)

            dyn_ext_folder = gcontext.lookup("/upnp/extensions/dynamic/folder")

            if dyn_ext_module is not None:
                self._scan_for_device_extensions_under_code_container(dyn_ext_module, self._dyn_root_device_registry)
                self._scan_for_service_extensions_under_code_container(dyn_ext_module, self._dyn_service_registry)
            elif dyn_ext_folder is not None:
                self._scan_for_device_extensions_under_folder(dyn_ext_folder, self._dyn_root_device_registry)
                self._scan_for_service_extensions_under_folder(dyn_ext_folder, self._dyn_service_registry)
            
            self._scan_for_device_extensions_under_code_container(standard_extensions, self._std_root_device_registry)
            self._scan_for_service_extensions_under_code_container(standard_extensions, self._std_service_registry)

        return

    def create_embedded_device_instance(self, embedded_device_desc: EmbeddedDeviceDesc) -> UpnpEmbeddedDevice:
        """
            Method that is called to create an instance of an extension for a specific UPnP embedded device. If an
            embedded device extension is not found matching the specified parameters then a generic UpnpEmbeddedDevice
            instance is created and returned.

            :param embedded_device_desc: The device detail object that contains the information about the device.

            :returns: An instance of an embedded device extension of a specific manaufacturer or a default generic
                      UpnpEmbeddedDevice.
        """
        deviceClass = UpnpEmbeddedDevice

        extkey = embedded_device_desc.get_extension_key()
        if extkey in self._dyn_embedded_device_registry:
            deviceClass = self._dyn_embedded_device_registry[extkey]
        elif extkey in self._std_embedded_device_registry:
            deviceClass = self._std_embedded_device_registry[extkey]
        
        return deviceClass()

    def create_root_device_instance(self, device_detail: UpnpDeviceDetail) -> UpnpRootDevice:
        """
            Method that is called to create an instance of an extension for a specific UPnP root device.  If a device
            extension is not found matching the specified parameters then a generic UpnpRootDevice instance is
            created and returned.

            :param device_detail: The device detail object that contains the information about the device.
            
            :returns: An instance of an root device extension of a specific manaufacturer or a default generic
                      UpnpRootDevice.
        """

        deviceClass = UpnpRootDevice

        extkey = device_detail.generate_extension_key()

        if extkey in self._dyn_root_device_registry:
            deviceClass = self._dyn_root_device_registry[extkey]
        elif extkey in self._std_root_device_registry:
            deviceClass = self._std_root_device_registry[extkey]

        dev_inst = deviceClass(device_detail)

        return dev_inst

    def create_service_instance(self, service_desc: ServiceEvidence) -> Union[UpnpServiceProxy, None]:
        """
            Method that is called to create an instance of an extension for a specific UPnP service proxy.  If a
            service proxy extension is not found matching the specified parameters then None is returned.

            :param service_desc: The service description object that contains the information about the service.

            :returns: An instance of an root device extension of a specific manaufacturer or a default generic
                      UpnpRootDevice.
        """
        serviceInst = None

        extkey = service_desc.get_extension_key()
        if extkey in self._dyn_service_registry:
            serviceClass = self._dyn_service_registry[extkey]
            serviceInst = serviceClass()
        elif extkey in self._std_service_registry:
            serviceClass = self._std_service_registry[extkey]
            serviceInst = serviceClass()

        return serviceInst


    def get_device_detail_processor(self, device_desc: Basic1DeviceDesc) -> UpnpDeviceDetail:
        """
            Method that is called to create an instance of an extension for a specific UPnP device detail processor.
            If a device detail processor extension is not found matching the specified parameters then None is
            returned.

            :param device_desc: The device description object that contains the information about the device.

            :returns: An instance of an root device extension of a specific manaufacturer or a default generic
                      UpnpRootDevice.
        """
        dev_inst = None

        extkey = device_desc.get_extension_key()
        if extkey in self._dyn_root_device_registry:
            dev_inst = self._dyn_root_device_registry[extkey]
        elif extkey in self._std_root_device_registry:
            dev_inst = self._std_root_device_registry[extkey]

        return dev_inst


    def _register_root_device(self, extkey, extcls, device_table):
        """
            Method that registers the extension class of a specific type of root device.
        """
        if extkey not in device_table:
            device_table[extkey] = extcls
        else:
            raise SemanticError("A root device extension with the key=%r was already registered. (%s)" % (extkey, extcls)) from None
        return

    def _register_service(self, extkey, extcls, service_table):
        """
            Method that registers the extension class of a specific type of service proxy.
        """
        if extkey not in service_table:
            service_table[extkey] = extcls
        else:
            service_table[extkey] = extcls
        return

    def _scan_for_device_extensions_under_code_container(self, container, device_table):
        """
            Method that scans a code container and its descendants for UpnpRootDevice objects.
        """
        extcoll = collect_resource_extensions_under_code_container(container, UpnpRootDevice)
        for _, extcls in extcoll:
            if hasattr(extcls, "EXTENSION_KEY"):
                extkey = getattr(extcls, "EXTENSION_KEY"),
                self._register_root_device(extkey, extcls, device_table)
        return

    def _scan_for_service_extensions_under_code_container(self, container, service_table):
        """
            Method that scans a code container and its descendants for UpnpServiceProxy objects.
        """
        extcoll = collect_resource_extensions_under_code_container(container, UpnpServiceProxy)
        for _, extcls in extcoll:
            if hasattr(extcls, "EXTENSION_KEY"):
                extkey = getattr(extcls, "EXTENSION_KEY")
                self._register_service(extkey, extcls, service_table)
        return
    
    def _scan_for_device_extensions_under_folder(self, directory, device_table):
        """
            Method that scans a code container and its descendants for UpnpRootDevice objects.
        """
        extcoll = collect_resource_extensions_under_folder(directory, UpnpRootDevice)
        for _, extcls in extcoll:
            if hasattr(extcls, "EXTENSION_KEY"):
                extkey = getattr(extcls, "EXTENSION_KEY")
                self._register_root_device(extkey, extcls, device_table)
        return

    def _scan_for_service_extensions_under_folder(self, directory, service_table):
        """
            Method that scans a code container and its descendants for UpnpServiceProxy objects.
        """
        extcoll = collect_resource_extensions_under_folder(directory, UpnpServiceProxy)
        for _, extcls in extcoll:
            if hasattr(extcls, "EXTENSION_KEY"):
                extkey = getattr(extcls, "EXTENSION_KEY")
                self._register_service(extkey, extcls, service_table)
        return
