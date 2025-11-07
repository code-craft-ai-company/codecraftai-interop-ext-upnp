"""
    .. module:: upnpdevice
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module containing the :class:`UpnpDevice` class and associated diagnostic.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
    
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import Dict, List, Optional, Union, TYPE_CHECKING

from automojo.xmodules.xlogging.enhancedloggers import getEnhancedLogger
import threading

import requests

from automojo.interop.protocols.upnp.constants import UPNP_HEADERS
from automojo.interop.protocols.upnp.model.upnpdevicedetail import UpnpDeviceDetail

from automojo.interop.protocols.upnp.upnperrors import UpnpServiceNotAvailableError

from automojo.interop.protocols.upnp.model.services.upnpserviceproxy import UpnpServiceProxy

from automojo.interop.protocols.upnp.model.description.deviceevidence import DeviceEvidence
from automojo.interop.protocols.upnp.model.description.basic1devicedesc import Basic1DeviceDesc
from automojo.interop.protocols.upnp.model.description.embeddeddevicedesc import EmbeddedDeviceDesc
from automojo.interop.protocols.upnp.model.description.servicedesc import ServiceDesc


# Types imported only for type checking purposes
if TYPE_CHECKING:
    from automojo.interop.protocols.upnp.model.devices.upnpdevicefactory import UpnpDeviceFactory


logger = getEnhancedLogger()


class UpnpDeviceBase:
    """
        The UPNP Root device is the base device for the hierarchy that is
        associated with a unique network devices location.  The :class:`RootDevice`
        and its subdevices are linked by thier location url.

        http://www.upnp.org/specs/arch/UPnP-arch-DeviceArchitecture-v1.0.pdf
    """

    MANUFACTURER = "unknown"
    MODEL_NUMBER = "unknown"
    MODEL_DESCRIPTION = "unknown"

    def __init__(self, device_detail: UpnpDeviceDetail):
        """
            Creates a root device object.
        """
        super(UpnpDeviceBase, self).__init__()

        self._device_detail = device_detail
        self._device_description = device_detail.description
        self._device_evidence = device_detail.evidence

        if self.device_description.manufacturer is not None:
            self.MANUFACTURER = self.device_description.manufacturer
        
        if self.device_description.modelNumber is not None:
            self.MODEL_NUMBER = self.device_description.modelNumber

        if self.device_description.modelDescription is not None:
            self.MODEL_DESCRIPTION = self.device_description.modelDescription

        self._host = None
        self._urlBase: str = None

        self._device_lock = threading.RLock()

        self._embedded_devices = {}
        
        self._services_descriptions = {}
        self._services = {}
        
        # We must have an initial device description in order to be able to create a
        # device instance.   Processes the serviceList and deviceList in the device
        # description to populate the service description and embedded device description
        # lookup tables.
        self._service_descriptions = {}
        serviceList = self._device_description.serviceList
        if serviceList is not None:
            for serviceInfo in serviceList:
                svckey = serviceInfo.get_extension_key()
                self._service_descriptions[svckey] = serviceInfo

        self._embedded_device_descriptions = {}
        deviceList = self._device_description.deviceList
        if deviceList is not None:
            for deviceInfo in self._device_description.deviceList:
                devkey = deviceInfo.get_extension_key()
                self._embedded_device_descriptions[devkey] = deviceInfo

        return

    @property
    def device_description(self) -> Union[Basic1DeviceDesc, None]:
        """
            Returns the device description from the UPNP device.
        """
        return self._device_description

    @property
    def device_detail(self) -> UpnpDeviceDetail:
        """
            Returns the device detail object that contains the device description and evidence.
        """
        return self._device_detail

    @property
    def device_evidence(self) -> DeviceEvidence:
        """
            Returns the device evidence from the UPNP device.
        """
        return self._device_evidence

    @property
    def host(self) -> str:
        """
            Returns the host associated with the UPNP device.
        """
        return self._host

    @property
    def services(self) -> List[UpnpServiceProxy]:
        """
            Returns a list of service proxies associated with the UPNP device.
        """
        service_list = None

        self._device_lock.acquire()
        try:
            service_list = [svc for svc in self._services.values()]
        finally:
            self._device_lock.release()

        return service_list

    @property
    def services_descriptions(self):
        """
            Returns a table of service descriptions associated with the UPNP device.
        """
        return self._services_descriptions

    @property
    def URLBase(self) -> str:
        """
            Returns the base URL for the UPNP device that is used with any relative URLs in devices or service
            description documents.
        """
        return self._urlBase

    def as_dict(self, brief=False):
        """
            Creates a dictionary description of the device and its sub devices and services.
        """
        rtnval = None
        
        self._device_lock.acquire()
        try:
            rtnval = self._device_description.as_dict(brief=brief)
        finally:
            self._device_lock.release()

        return rtnval

    def assemble_device(self, factory: "UpnpDeviceFactory"):
        """
            Assembles any additional information needed for the device to transition to an operational state.  This is
            called after the device has been created and the root device description has been loaded.  The root device
            description contains brief information about services so it is necessary to formalize a way to take a device
            with incomplete information and retrieve the extended information needed for full operation.

            :param factory: The UpnpDeviceFactory that is used to create the device.
        """
        
        # When we enhance the device, we go out and retrieve the service descriptions and populate the
        # service descriptions table.  We also populate the embedded device descriptions table.
        self._populate_services_descriptions(self._device_description)

        for device_desc in self._device_description.deviceList:

            self._populate_embedded_device_descriptions(factory, device_desc)

        return

    def get_service_description(self, serviceType: str, extra_headers: Optional[Dict[str, str]] = None) -> ServiceDesc:
        """
            Gets the service description for the specified service type.

            :param serviceType: The service type to lookup the service description for.

            :returns: Returns the description information for the service type if found or None if not found.
        """
        svc_desc = None

        for nxtsvc in self._device_description.serviceList:
            if nxtsvc.serviceType == serviceType:
                fullurl = self.URLBase.rstrip("/") + "/" + nxtsvc.SCPDURL.lstrip("/")

                headers = {
                    "User-Agent": UPNP_HEADERS.USER_AGENT
                }

                if extra_headers is not None:
                    headers.update(extra_headers)

                resp: requests.Response = requests.get(fullurl, headers=headers)
                if resp.status_code == 200:
                    svc_content = resp.text
                    svc_desc = ServiceDesc.query_service_description(svc_content)
                    break

        return svc_desc

    def lookup_service(self, service_key: str, allow_none: bool=False, factory: Optional["UpnpDeviceFactory"] = None) -> Union[UpnpServiceProxy, None]:
        """
            Looks up a service proxy using the service key specified.

            :param service_key: The key identifying the service to lookup.
            :param allow_none: If ``True``, no exception is raised when the service cannot be found.
            :param factory: Optional factory used to create a service instance when one does not exist.

            :returns: The service proxy for the provided key or ``None``.
        """
        svc = None

        self._device_lock.acquire()
        try:
            if service_key in self._services:
                svc = self._services[service_key]

            elif factory is not None:
                svc_desc = self._service_descriptions[service_key]

                self._device_lock.release()
                try:
                    svc = factory.create_service_instance(svc_desc)
                finally:
                    self._device_lock.acquire()

                if svc is not None:
                    self._services[service_key] = svc
        finally:
            self._device_lock.release()

        if svc is None and not allow_none:
            errmsg = "The service service_key={} was not found or is not available.".format(service_key)
            raise UpnpServiceNotAvailableError(errmsg)

        return svc

    def to_json(self, brief=False):
        """
            Creates a json description of the device and its sub devices and services.
        """
        rtnval = None
        
        self._device_lock.acquire()
        try:
            rtnval = self._device_description.as_json(brief=brief)
        finally:
            self._device_lock.release()

        return rtnval

    def _populate_embedded_device_descriptions(self, factory: "UpnpDeviceFactory", device_description: EmbeddedDeviceDesc):
        """
            Takes in a device description and processes it for embedded devices.

            :param factory: The :class:`UpnpDeviceFactory` used to instantiate embedded devices when the
                            UPNP device description is processed.
            :param device_description: The :class:`EmbeddedDeviceDesc` object describing the embedded device.
        """
        devkey = device_description.get_extension_key()
        
        dev_instance: "UpnpDeviceBase" = factory.create_embedded_device_instance(
            device_description=device_description,
            urlBase=self._urlBase,
            host=self._host
        )

        self._device_lock.acquire()
        try:
            if devkey not in self._embedded_device_descriptions:
                self._embedded_device_descriptions[devkey] = device_description

            self._embedded_devices[devkey] = dev_instance
        finally:
            self._device_lock.release()

        dev_instance.enhance_device(factory)

        return

    def _populate_services_descriptions(self, device_description: Basic1DeviceDesc):
        """
            Takes in a device description and processes it for service descriptions.

            :param device_description: The Basic1DeviceDesc object that contains information about the device and its services. This could be the
                                       root device description or an embedded device description.

        """

        service_descriptions = {}

        # pylint: disable=protected-access
        for serviceInfo in device_description.serviceList:

            service_url = serviceInfo.SCPDURL
            if service_url is not None and not service_url.startswith("http"):
                if self._urlBase is None:
                    raise ValueError("The URLBase for the device must be set before processing service descriptions.")

                service_url = self._urlBase.rstrip("/") + "/" + service_url.lstrip("/")

                svc_desc_resp: requests.Response = requests.get(service_url)
                if svc_desc_resp.status_code == 200:
                    # If we were able to obtain the service description document, then we can process it in order to
                    # get the extended service description information needed to lookup any pre-existing code generated
                    # service interop proxy classes.

                    svckey = serviceInfo.get_extension_key()

                    service_descriptions[svckey] = ServiceDesc.query_service_description(service_url)

        self._device_lock.acquire()
        try:
            self._services_descriptions = service_descriptions
        finally:
            self._device_lock.release()

        return

    
