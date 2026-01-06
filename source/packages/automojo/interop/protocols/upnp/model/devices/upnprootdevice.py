"""
    .. module:: upnprootdevice
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module containing the :class:`UpnpRootDevice` class and associated diagnostic.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
    
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import Dict, List, Optional, Tuple, Union, TYPE_CHECKING

from automojo.xmodules.xlogging.enhancedloggers import getEnhancedLogger
import os
import re
import threading
import traceback
import weakref

from datetime import datetime, timedelta
from urllib.parse import urlparse

from xml.etree.ElementTree import fromstring as xml_fromstring
from xml.etree.ElementTree import Element, ElementTree

import requests

from requests.compat import urljoin

from automojo.errors.exceptions import  ProtocolError

from automojo.interop.protocols.upnp.constants import MSearchRouteKeys, UPNP_DEVICE1_NAMESPACE
from automojo.interop.protocols.upnp.upnperrors import UpnpError
from automojo.interop.protocols.upnp.aliases import StrSvcId, StrSvcType
from automojo.interop.protocols.upnp.constants import TIMEDELTA_RENEWAL_WINDOW, UPNP_HEADERS
from automojo.interop.protocols.upnp.model.description.embeddeddevicedesc import EmbeddedDeviceDesc
from automojo.interop.protocols.upnp.model.devices.upnpdevicebase import UpnpDeviceBase
from automojo.interop.protocols.upnp.model.devices.upnpembeddeddevice import UpnpEmbeddedDevice
from automojo.interop.protocols.upnp.model.upnpdevicedetail import UpnpDeviceDetail


from automojo.interop.protocols.upnp.soap import NS_UPNP_EVENT

from automojo.interop.protocols.upnp.model.services.upnpserviceproxy import UpnpServiceProxy

import automojo.interop.protocols.upnp as upnp_module

from automojo.errors.raising import raise_for_http_status


# Types imported only for type checking purposes
if TYPE_CHECKING:
    from automojo.interop.protocols.upnp.upnppresence import UpnpPresence
    from automojo.interop.protocols.upnp.model.devices.upnpdevicefactory import UpnpDeviceFactory
    

UPNP_DIR = os.path.dirname(upnp_module.__file__)

REGEX_SUBSCRIPTION_TIMEOUT = re.compile("^Second-([0-9]+|infinite)", flags=re.IGNORECASE)

logger = getEnhancedLogger()

def device_description_load(location: str) -> Union[ElementTree, None]:
    """
        Gets the description document from the specified URL and loads the contents into an XML ElementTree.

        :param location: The url of where to get the device description.

        :returns: The XML ElementTree for the XML content from the device description or None.
    """
    docTree = None

    resp: requests.Response = requests.get(location)
    if resp.status_code == 200:
        xmlcontent = resp.content

        docTree = ElementTree(xml_fromstring(xmlcontent))

    return  docTree



def device_description_find_components(location: str, docTree: ElementTree, namespaces: dict = {"": UPNP_DEVICE1_NAMESPACE}) -> Tuple[Element, str, str, str, str, str]:
    """
        Processes the device description and find the device description components.  The device
        description components are the manufacturer, modelName, modelNumber, modelDescription
        and the device description node.

        :param location: The URL location of where the device description document was obtained.
        :param docTree: The XML document ElementTree object.
        :param namespaces: A dictionary of namespaces to use when processing the device description document.

        :returns: A tuple with the (device node, urlBase, manufacturer, modelName, modelNumber, modelDescription)
    """
    # pylint: disable=dangerous-default-value

    devNode = docTree.find("device", namespaces=namespaces)

    urlBase = None
    baseURLNode = devNode.find("URLBase", namespaces=namespaces)
    if baseURLNode is not None:
        urlBase = baseURLNode.text

    url_parts = urlparse(location)
    host = url_parts.netloc

    # If urlBase was not set we need to try to use the schema and host as the urlBase
    if urlBase is None:
        urlBase = "%s://%s" % (url_parts.scheme, host)

    manufacturer = None
    modelName = None
    modelNumber = None
    modelDescription = None

    manufacturerNode = devNode.find("manufacturer", namespaces=namespaces)
    if manufacturerNode is not None:
        manufacturer = manufacturerNode.text

    modelNameNode = devNode.find("modelName", namespaces=namespaces)
    if modelNameNode is not None:
        modelName = modelNameNode.text

    modelNumberNode = devNode.find("modelNumber", namespaces=namespaces)
    if modelNumberNode is not None:
        modelNumber = modelNumberNode.text

    modelDescNode = devNode.find("modelDescription", namespaces=namespaces)
    if modelDescNode is not None:
        modelDescription = modelDescNode.text

    return devNode, urlBase, manufacturer, modelName, modelNumber, modelDescription


class UpnpRootDevice(UpnpDeviceBase):
    """
        The UPNP Root device is the base device for the hierarchy that is
        associated with a unique network devices location.  The :class:`UpnpRootDevice`
        and its subdevices are linked by thier location url.

        http://www.upnp.org/specs/arch/UPnP-arch-DeviceArchitecture-v1.0.pdf
    """

    MANUFACTURER = "unknown"
    MODEL_NUMBER = "unknown"
    MODEL_DESCRIPTION = "unknown"

    SERVICE_NAMES = []

    def __init__(self, presence: "UpnpPresence", device_detail: UpnpDeviceDetail):
        """
            Creates a root device object.
        """
        super(UpnpRootDevice, self).__init__(device_detail)

        self._presence_ref = weakref.ref(presence)

        self._server = None        

        self._specVersion = None

        self._host = None
        self._ip_address = None
        self._routes = None
        self._primary_route = None

        self._auto_subscribe = False
        self._mode = None

        self._root_device_lock = threading.RLock()

        self._subscriptions: Dict[StrSvcType, Tuple[StrSvcId, datetime]] = {}
        self._sid_to_service_lookup: Dict[str, UpnpServiceProxy] = {}
        self._variables = {}
        self._subscription_scheduler_stop = threading.Event()
        self._subscription_scheduler_thread: Optional[threading.Thread] = None

        self._last_alive = datetime.min
        self._last_byebye = datetime.min
        self._available = False

        self._coordinator_ref = None
        self._basedevice_ref = None
        self._extid = None
        self._location = None
        self._configinfo = None
        self._deviceinfo = None

        return

    @property
    def available(self) -> bool:
        """
            Returns the status of the device.
        """
        return self._available

    @property
    def cachecontrol(self) -> str:
        """
            The cache control timeout for the device from the MSEARCH response.
        """
        return self._device_evidence.other.get("CACHE-CONTROL")

    @property
    def embedded_device_descriptions(self) -> List[EmbeddedDeviceDesc]:
        """
            Returns the list of descriptions for the embedded device that are declared for this root device.
        """
        dev_desc_list = []

        dev_desc_list = [devdesc for devdesc in self._device_description.deviceList]

        return dev_desc_list

    @property
    def embedded_devices(self) -> List[UpnpEmbeddedDevice]:
        """
            Returns the list of embedded devices that are declared for this root device.
        """
        devices_list = None

        devices = self._embedded_devices
        if devices is not None:
            devices_list = [dev for dev in devices]

        return devices_list

    @property
    def ext(self) -> str:
        """
            Returns the EXT header reported by the device in the MSEARCH response.
        """
        return self._ext

    @property
    def extra(self) -> dict:
        """
            Returns a dictionary that contains the extra thirdparty headers attached to UPNP MSEARCH responses.
        """
        return self._extra

    @property
    def IPAddress(self) -> str:
        """
            Returns the ip address of the root device that was found when the device responded with its MSEARCH response.
        """
        return self._ip_address

    @property
    def last_alive(self) -> datetime:
        """
            The datetime marker of the last time a UPNP alive or MSEARCH response was received
            from this device.
        """
        return self._last_alive

    @property
    def last_byebye(self) -> datetime:
        """
            The datetime marker of the last time a UPNP byebye was received from this device.
        """
        return self._last_byebye

    @property
    def location(self) -> str:
        """
            The location of the device as specified in the MSEARCH response.
        """
        locurl = self._device_evidence.location
        return locurl

    @property
    def mode(self) -> str:
        """
            The virtual mode assocatied with a device.  A device might present a different set of
            services depending on its current mode of operation.
        """
        return self._mode

    @property
    def modelName(self) -> Union[str, None]:
        """
            The model name of the device as found in the device description or None.
        """
        mname = None
        desc = self._device_description
        if desc is not None:
            mname = desc.modelName
        return mname

    @property
    def modelNumber(self )-> Union[str, None]:
        """
            The model number of the device as found in the device description or None.
        """
        mnumber = None
        desc = self._device_description
        if desc is not None:
            mnumber = desc.modelNumber
        return mnumber

    @property
    def presence(self) -> "UpnpPresence":
        """
            Returns the presence object associated with the UPNP device.
        """
        return self._presence_ref()

    @property
    def coordinator(self):
        """
            Returns the coordinator associated with this device if one is registered.
        """
        coord = None
        if self._coordinator_ref is not None:
            coord = self._coordinator_ref()
        return coord

    @property
    def basedevice(self):
        """
            Returns the landscape base device that this UPnP device extends.
        """
        basedev = None
        if self._basedevice_ref is not None:
            basedev = self._basedevice_ref()
        return basedev

    @property
    def primary_route(self):
        """
            Returns the primary rout for this UPNP devices.
        """
        return self._primary_route

    @property
    def routes(self) -> list:
        """
            A list of routes that can be used to communicate with the device.
        """
        return self._routes

    @property
    def server(self) -> str:
        """
            The 'SERVER' key specified in the MSEARCH response for this device.
        """
        return self._server

    @property
    def extid(self) -> str:
        """
            Returns the coordinator assigned identifier for this device.
        """
        return self._extid

    @property
    def location(self) -> str:
        """
            Returns the location URL where this device can be reached.
        """
        return self._location

    @property
    def services(self) -> List[UpnpServiceProxy]:
        """
            List of service proxies associated with this device.
        """
        services_list = None

        services = self._services
        if services is not None:
            services_list = [svc for svc in services]

        return services_list

    @property
    def serialNumber(self) -> str:
        """
            The serial number number of the device as found in the device description.
        """
        desc = self._device_description
        return desc.serialNumber

    @property
    def USN(self) -> str:
        """
            The USN identifier specified in the MSEARCH response for this device.
        """
        return self._device_evidence.usn

    @property
    def USN_DEV(self) -> str:
        """
            The device component of the USN identifier specified in the MSEARCH response for this device.
        """
        return self._device_evidence.usn_dev

    @property
    def USN_CLS(self) -> str:
        """
            The class component of the USN identifier specified in the MSEARCH response for this device.
        """
        return self._device_evidence.usn_cls

    def as_dict(self, brief=False) -> dict:
        """
            Returns a description of this device as a python dictionary.

            :param brief: A booliean value which indicates if a brief or full description is desired.

            :returns: The python dictionary description of the device.
        """
        dval = super(UpnpRootDevice, self).as_dict(brief=brief)
        dval["IPAddress"] = self.IPAddress
        dval["USN"] = self.USN
        dval["USN_DEV"] = self.USN_DEV
        dval["USN_CLS"] = self.USN_CLS
        return dval


    def events_subscribe(self, service: UpnpServiceProxy, renew: bool = False, timeout: Optional[float] = None) -> Union[Tuple[str, datetime], Tuple[None, None]]:
        """
            Creates a subscription to the events for a UPnP service.

            :param service: The :class:`UpnpServiceProxy` to subscribe to.
            :param renew: Indicates if the subscription is being renewed.
            :param timeout: Optional timeout in seconds for the subscription.

            :returns: ``(sid, expires)`` of the subscription or ``(None, None)`` if no subscription occurred.
        """

        sub_sid = None
        sub_expires = None

        if len(service.SERVICE_EVENT_VARIABLES) > 0:
            service_type = service.SERVICE_TYPE

            new_subscription = False
            current_sid = None
            current_expires = None
            with self._device_lock:
                if service_type not in self._subscriptions:
                    new_subscription = True
                    self._subscriptions[service_type] = (None, None)
                else:
                    current_sid, current_expires = self._subscriptions[service_type]
                    if current_sid is None and current_expires is None:
                        new_subscription = True

            sub_sid, sub_expires = current_sid, current_expires

            check_time = datetime.now() + timedelta(seconds=TIMEDELTA_RENEWAL_WINDOW)
            if sub_expires is not None and check_time > sub_expires:
                renew = True

            if new_subscription or renew:
                svckey = service.get_extension_key()
                service = self._services[svckey]

                subscribe_url = urljoin(self.URLBase, service.eventSubURL)

                presence = self.presence
                if presence is None:
                    raise RuntimeError("Presence reference was lost.")

                host_ip = self._primary_route[MSearchRouteKeys.IP]

                custom_headers = self.get_custom_subscribe_headers()
                renewal_attempted = False
                if renew and current_sid is not None:
                    renewal_attempted = True
                    sub_sid, sub_expires = presence.service_subscribe(
                        host_ip,
                        subscribe_url,
                        timeout,
                        self.process_subscription_callback,
                        custom_headers=custom_headers,
                        sid=current_sid,
                        renew=True
                    )

                if sub_sid is None and renewal_attempted:
                    sub_sid, sub_expires = presence.service_subscribe(
                        host_ip,
                        subscribe_url,
                        timeout,
                        self.process_subscription_callback,
                        custom_headers=custom_headers
                    )

                if sub_sid is None and not renewal_attempted:
                    sub_sid, sub_expires = presence.service_subscribe(
                        host_ip,
                        subscribe_url,
                        timeout,
                        self.process_subscription_callback,
                        custom_headers=custom_headers
                    )

                with self._device_lock:
                    if sub_sid is not None:
                        old_sid, _ = self._subscriptions.get(service_type, (None, None))
                        if old_sid is not None and old_sid != sub_sid:
                            if old_sid in self._sid_to_service_lookup:
                                del self._sid_to_service_lookup[old_sid]
                            self._unregister_subscription_mapping(old_sid)
                        service._update_subscription_details(sub_sid, sub_expires)
                        self._sid_to_service_lookup[sub_sid] = service
                        self._subscriptions[service_type] = (sub_sid, sub_expires)
                        self._register_subscription_mapping(sub_sid)
                    elif new_subscription:
                        service.invalidate_subscription()
                        if service_type in self._subscriptions:
                            del self._subscriptions[service_type]

        return sub_sid, sub_expires

    def events_unsubscribe(self, service: UpnpServiceProxy, subscription_id: Optional[str] = None):
        """
            Unsubscribes from the events for a UPnP service.

            :param service: The :class:`UpnpServiceProxy` to unsubscribe from.
            :param subscription_id: Optional explicit subscription ID to unsubscribe.
        """

        if len(service.SERVICE_EVENT_VARIABLES) > 0:
            if subscription_id is None:
                subscription_id = service.subscription_id

            presence = self.presence
            if presence is None:
                raise RuntimeError("Presence reference was lost.")

            host_ip = self._primary_route[MSearchRouteKeys.IP]
            subscribe_url = urljoin(self.URLBase, service.eventSubURL)

            custom_headers = self.get_custom_subscribe_headers()
            presence.service_unsubscribe(host_ip, subscribe_url, subscription_id, custom_headers=custom_headers)
            service.invalidate_subscription()

            with self._device_lock:
                if subscription_id in self._sid_to_service_lookup:
                    del self._sid_to_service_lookup[subscription_id]
                self._unregister_subscription_mapping(subscription_id)

                svc_type = service.SERVICE_TYPE
                if svc_type in self._subscriptions:
                    self._subscriptions[svc_type] = (None, None)

        return

    subscribe_to_events = events_subscribe
    unsubscribe_to_events = events_unsubscribe

    def get_custom_subscribe_headers(self) -> Optional[Dict[str, str]]:
        """
            An override-able method that allows for customization of the subscribe headers.
        """
        return None

    def lookup_embedded_device(self, device_type: str) -> Union[UpnpEmbeddedDevice, None]:
        """
            Looks up an embedded device by its device type identifier.

            :param device_type: The device type identifier of the embedded device to find.

            :returns: The specified UpnpEmbeddedDevice or None
        """
        device = None

        self._device_lock.acquire()
        try:
            device = self._embedded_devices.get(device_type)
        finally:
            self._device_lock.release()

        return device

    def mark_alive(self):
        """
        Mark the device as alive and update the last seen timestamp.
        """

        self._device_lock.acquire()
        try:
            self._last_alive = datetime.now()
            self._available = True
        finally:
            self._device_lock.release()

        return
    
    def initialize(self, coord_ref: weakref.ReferenceType, basedevice_ref: weakref.ReferenceType, extid: str, location: str, configinfo: dict, deviceinfo: dict):
        """
            Initializes the device with coordinator and landscape references.

            :param coord_ref: Weak reference to the coordinator managing this device.
            :param basedevice_ref: Weak reference to the landscape device this UPnP device extends.
            :param extid: The identifier associated with this device instance.
            :param location: The location URL for the device description.
            :param configinfo: Configuration information for the device.
            :param deviceinfo: Device discovery information.
        """

        self._coordinator_ref = coord_ref
        self._basedevice_ref = basedevice_ref
        self._extid = extid
        self._location = location
        self._configinfo = configinfo
        self._deviceinfo = deviceinfo
        return

    def mark_byebye(self):
        """
        Mark the device as unavailable due to a byebye notification.
        """

        self.mark_unavailable(reason="byebye", byebye=True)

        return

    def mark_unavailable(self, reason: str="mark_unavailable", byebye: bool=False):
        """
            :param byebye: Indicates this method is being called from 'mark_byebye' as a result
                           of a byebye message being received.
        """

        subscription_ids = []
        additional_sids: List[str] = []
        stop_scheduler = self._subscription_scheduler_thread is not None

        self._device_lock.acquire()
        try:
            if byebye:
                self._last_byebye = datetime.now()

            if self._available:

                basedev = self.basedevice
                device_identity = basedev.identity if basedev is not None else self.USN_DEV

                self._available = False
                stop_scheduler = True

                additional_sids = [sid for sid in self._sid_to_service_lookup.keys()]
                subscription_type_list = [st for st in self._subscriptions.keys()]

                for svc_type in subscription_type_list:
                    sub_sid, _ = self._subscriptions[svc_type]

                    svc_obj = self._sid_to_service_lookup.get(sub_sid)

                    if svc_obj is not None:
                        # Call notify_byebye on each service object so we can mark all the
                        # references to variables as expired.
                        svc_obj.invalidate_subscription()

                    # Since we got a byebye, remove the subscription information
                    dbgmsg = "Removing subscription for device {} service {}, because of {}.".format(
                        device_identity, svc_type, reason
                    )
                    logger.debug(dbgmsg)
                    self._unregister_subscription_mapping(sub_sid)
                    if sub_sid is not None:
                        subscription_ids.append(sub_sid)
                        if sub_sid in self._sid_to_service_lookup:
                            del self._sid_to_service_lookup[sub_sid]
                    del self._subscriptions[svc_type]

                self._sid_to_service_lookup.clear()

        finally:
            self._device_lock.release()

        if stop_scheduler:
            self._stop_subscription_scheduler()

        cleanup_ids = list(set(subscription_ids + additional_sids))
        if len(cleanup_ids) > 0:
            self._cleanup_presence_callbacks(cleanup_ids)

        return

    def process_subscription_callback(self, sender_ip, sid: str, headers: dict, body: str):
        """
            This is used by the subscription callback thread to handoff work packets to the a worker thread
            and completes the processing of the subscription callback and routing to a UpnpRootDevice and
            UpnpServiceProxy instance.

            :param sender_ip: The IP address of the entity sending the update
            :param sid: The Subscription ID (sid) associated with the subscription callback
            :param headers: The HTTP headers contained in the callback response.
            :param body: The body content of the HTTP subscription callback.
        """
        # pylint: disable=unused-argument

        service = None

        self._device_lock.acquire()
        try:
            if sid in self._sid_to_service_lookup:
                service = self._sid_to_service_lookup[sid]
        finally:
            self._device_lock.release()

        if service is not None:
            docTree = ElementTree(xml_fromstring(body))

            psetNode = docTree.getroot()

            if psetNode is not None and psetNode.tag == "{%s}propertyset" % NS_UPNP_EVENT:
                propertyNodeList = psetNode.findall("{%s}property" % NS_UPNP_EVENT)

                service._update_event_variables(sender_ip, self.USN_DEV, propertyNodeList) # pylint: disable=protected-access

        return
    
    def _register_subscription_mapping(self, sid: str):
        """
            Registers the subscription with the coordinator so callbacks can be routed.
        """
        coord = self.coordinator
        if coord is not None and sid is not None:
            coord.register_subscription_for_device(sid, self)
        return

    def _unregister_subscription_mapping(self, sid: str):
        """
            Unregisters the subscription from the coordinator so stale entries are removed.
        """
        coord = self.coordinator
        if coord is not None and sid is not None:
            coord.unregister_subscription_for_device(sid)
        return

    def query_device_description(self):
        """
            Queries the UPnP device for its description.
        """
        desc = device_description_load(self.location)
        return desc


    def set_auto_subscribe(self, val, factory: Optional["UpnpDeviceFactory"] = None):
        """
        Enable or disable automatic service subscriptions.
        """

        if val:
            self._auto_subscribe = True
            self.subscribe_to_all_services(factory)
            self._start_subscription_scheduler()
        else:
            self._auto_subscribe = False
            self._stop_subscription_scheduler()
            self._unsubscribe_all_services()

        return

    def subscribe_to_all_services(self, factory: Optional["UpnpDeviceFactory"] = None):
        """
            The 'subscribe_to_all_services' method is overriden by derived objects in order
            to allow for bulk subscription to device services.

            ..note: Use with caution, if auto_subscribe is turned on, subscriptions are automatically
            created when the values of variables are attempted to be consumed via 'wait_for_value' and
            'wait_for_update'
        """

        for svc_name in self.SERVICE_NAMES:
            svc = self.lookup_service(self.MANUFACTURER, svc_name, allow_none=True, factory=factory)
            if svc is not None:
                try:
                    self.subscribe_to_events(svc)
                except Exception:  # pylint: disable=broad-exception-caught
                    errmsg = traceback.format_exc()
                    logger.debug(errmsg)
            else:
                errmsg = "Lookup service failed for mfg={} svc={}".format(self.MANUFACTURER, svc_name)
                logger.debug(errmsg)

        return

    def _cleanup_presence_callbacks(self, subscription_ids: List[str]):
        """
            Remove subscription callbacks from the presence object without contacting the device.
        """
        presence = self.presence
        if presence is None:
            return

        for sid in subscription_ids:
            try:
                presence.discard_subscription_callback(sid)
            except Exception:  # pylint: disable=broad-exception-caught
                logger.debug("Failed to discard subscription callback sid=%s", sid)

        return

    def _find_service_for_subscription(self, service_type: StrSvcType, sid: Optional[str]) -> Optional[UpnpServiceProxy]:
        """
            Locate the service proxy associated with a subscription entry.
        """
        service = None

        self._device_lock.acquire()
        try:
            if sid is not None and sid in self._sid_to_service_lookup:
                service = self._sid_to_service_lookup[sid]
            else:
                for svc_obj in self._services.values():
                    if svc_obj.SERVICE_TYPE == service_type:
                        service = svc_obj
                        break
        finally:
            self._device_lock.release()

        return service

    def _compute_scheduler_wait(self) -> float:
        """
            Determine how long the scheduler should wait before checking subscriptions again.
        """

        wait_seconds = TIMEDELTA_RENEWAL_WINDOW
        now = datetime.now()

        self._device_lock.acquire()
        try:
            if not self._auto_subscribe or len(self._subscriptions) == 0:
                wait_seconds = TIMEDELTA_RENEWAL_WINDOW
            else:
                for _, (_, sub_expires) in self._subscriptions.items():
                    if sub_expires is None:
                        wait_seconds = min(wait_seconds, TIMEDELTA_RENEWAL_WINDOW / 2)
                        continue

                    renew_in = (sub_expires - now).total_seconds() - TIMEDELTA_RENEWAL_WINDOW
                    if renew_in < 0:
                        renew_in = 0

                    wait_seconds = min(wait_seconds, max(renew_in, 1.0))
        finally:
            self._device_lock.release()

        return max(wait_seconds, 1.0)

    def _renew_subscriptions(self):
        """
            Iterate through active subscriptions and renew them ahead of expiry.
        """
        renew_targets: List[Tuple[StrSvcType, str, datetime, UpnpServiceProxy]] = []

        now = datetime.now()
        self._device_lock.acquire()
        try:
            if not self._auto_subscribe or not self._available:
                return

            for svc_type, (sid, expires) in self._subscriptions.items():
                if sid is None or expires is None:
                    continue

                if now + timedelta(seconds=TIMEDELTA_RENEWAL_WINDOW) >= expires:
                    svc_obj = self._find_service_for_subscription(svc_type, sid)
                    if svc_obj is not None:
                        renew_targets.append((svc_type, sid, expires, svc_obj))
        finally:
            self._device_lock.release()

        for svc_type, sid, expires, svc_obj in renew_targets:
            try:
                logger.debug(
                    "Renewing subscription sid=%s svc=%s (expires %s)", sid, svc_type, expires.isoformat()
                )
                svc_obj.renew_subscription()
            except Exception:  # pylint: disable=broad-exception-caught
                logger.debug("Failed to renew subscription sid=%s svc=%s", sid, svc_type)

        return

    def _start_subscription_scheduler(self):
        """
            Start the lightweight scheduler that keeps subscriptions renewed.
        """
        self._device_lock.acquire()
        try:
            if self._subscription_scheduler_thread is not None and self._subscription_scheduler_thread.is_alive():
                return

            self._subscription_scheduler_stop.clear()

            scheduler_thread = threading.Thread(
                name=f"UpnpRootDevice-SubscriptionScheduler-{self.extid}",
                target=self._subscription_scheduler_loop,
                daemon=True
            )
            self._subscription_scheduler_thread = scheduler_thread
            scheduler_thread.start()
        finally:
            self._device_lock.release()

        return

    def _stop_subscription_scheduler(self):
        """
            Stop the subscription renewal scheduler.
        """
        scheduler_thread = None

        self._device_lock.acquire()
        try:
            self._subscription_scheduler_stop.set()
            scheduler_thread = self._subscription_scheduler_thread
            self._subscription_scheduler_thread = None
        finally:
            self._device_lock.release()

        if scheduler_thread is not None and scheduler_thread.is_alive():
            scheduler_thread.join(timeout=5.0)

        return

    def _subscription_scheduler_loop(self):
        """
            Loop that periodically checks subscriptions and renews them.
        """
        while not self._subscription_scheduler_stop.is_set():
            wait_time = self._compute_scheduler_wait()
            self._subscription_scheduler_stop.wait(wait_time)
            if self._subscription_scheduler_stop.is_set():
                break

            try:
                self._renew_subscriptions()
            except Exception:  # pylint: disable=broad-exception-caught
                logger.debug("Subscription scheduler encountered an error.")

        return

    def _unsubscribe_all_services(self):
        """
            Unsubscribe from all known services and clear subscription tracking.
        """
        subscription_entries: List[Tuple[StrSvcType, Optional[str]]] = []

        self._device_lock.acquire()
        try:
            subscription_entries = [(svc_type, sid) for svc_type, (sid, _) in self._subscriptions.items()]
        finally:
            self._device_lock.release()

        for svc_type, sid in subscription_entries:
            svc_obj = self._find_service_for_subscription(svc_type, sid)
            if svc_obj is None:
                continue

            if sid is not None:
                try:
                    self.events_unsubscribe(svc_obj, subscription_id=sid)
                except Exception:  # pylint: disable=broad-exception-caught
                    logger.debug("Failed to unsubscribe sid=%s svc=%s", sid, svc_type)
            else:
                svc_obj.invalidate_subscription()

        subscription_ids = [sid for _, sid in subscription_entries if sid is not None]
        self._cleanup_presence_callbacks(subscription_ids)

        self._device_lock.acquire()
        try:
            self._subscriptions.clear()
            self._sid_to_service_lookup.clear()
        finally:
            self._device_lock.release()

        return

    def switch_modes(self, mode: str):
        """
            Called to trigger the switching of a devices mode of operation.  This function is
            device specific and needs to be overloaded by custom UPNP device implementations.
        """
        self._mode = mode
        raise NotImplementedError("UpnpRootDevice.switchModes must be overloaded by custom UPNP devices.") from None

    def to_json(self, brief=False) -> str:
        """
            Returns a description of this device in JSON format.

            :param brief: A booliean value which indicates if a brief or full description is desired.

            :returns: The JSON description of the device.
        """
        json_str = super(UpnpRootDevice, self).to_json(brief=brief)
        return json_str

    def _enhance_device_detail(self):
        """
            Can be implemented by custom devices in order to be able query for and enhance a devices
            information during the device update process.
        """
        # pylint: disable=no-self-use
        return

    def _locked_populate_embedded_devices(self, factory: "UpnpDeviceFactory", description: EmbeddedDeviceDesc):
        """
            Called in order to process embedded device descriptions and to instantiate embedded device instances.

            NOTE: This method should be called with the device lock held.
        """
        for deviceInfo in description.deviceList:

            devkey = deviceInfo.get_extension_key()

            if devkey not in self._embedded_devices:
                dev_inst = factory.create_embedded_device_instance(deviceInfo)
                self._embedded_devices[devkey] = dev_inst
                self._populate_services_descriptions(deviceInfo)
            else:
                dev_inst = self._embedded_devices[devkey]

            dev_inst.update_description(self._host, self._urlBase, deviceInfo)
        return

    def _locked_process_urlbase_node(self, urlBaseNode: Element, namespaces: Optional[dict] = None):
        """
            Called in order to process the base url information from the device description.

            :param urlBaseNode: The XML Element node that contains the urlBaseNode information.
            :param namespaces: A dictionary of namespaces to use when processing the device description.

            NOTE: This method should be called with the device lock held.
        """
        # pylint: disable=unused-argument

        self._urlBase = urlBaseNode.text.rstrip("/")
        return

    def _matches_model_name(self, modelName: str) -> bool:
        """
            Method used to determine if the modelName passed matches the model name of this device.

            :param modelName: The modelName to evaluate for matching with this device.
        """
        matches = False
        if self.modelName == modelName:
            matches = True

        return matches

    def _matches_model_number(self, modelNumber: str)-> bool:
        """
            Method used to determine if the modelNumber passed matches the model number of this device.

            :param modelNumber: The modelNumber to evaluate for matching with this device.
        """
        matches = False
        if self.modelNumber == modelNumber:
            matches = True

        return matches


    def __str__(self):
        """
            Returns a brief description of the device as a string.
        """
        rtnstr = "%s: USN:%s IP=%s" % (self.modelName, self.USN, self.IPAddress)
        return rtnstr
