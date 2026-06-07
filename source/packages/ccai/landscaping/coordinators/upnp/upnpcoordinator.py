"""
    .. module:: upnpcoordinator
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Contains the UpnpCoordinator which is used for managing connectivity upnp devices visible in the automation landscape.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from typing import Dict, List, Optional, TYPE_CHECKING, Tuple, Union

import os
import threading
import traceback
import uuid
import weakref

import yaml

from requests.exceptions import ConnectionError

from ccai.errors.exceptions import ConfigurationError, SemanticError
from ccai.landscaping.friendlyidentifier import FriendlyIdentifier

from ccai.thisapp.wellknown import ThisApplicationSingleton
from ccai.thisapp.contextpaths import ContextPaths

from ccai.networking.interfaces import get_interface_for_ip
from ccai.networking.trafficcapturecontext import TrafficCaptureContext

import ccai.interop.protocols.upnp as upnp_module

from ccai.landscaping.coordinatorbase import CoordinatorBase
from ccai.landscaping.landscapedevice import LandscapeDevice
from ccai.landscaping.extensions.protocol.upnpprotocolextension import UpnpProtocolExtension
from ccai.landscaping.extensions.protocol.protocolextension import ProtocolExtension

from ccai.interop.protocols.upnp.model.devices.upnprootdevice import UpnpRootDevice
from ccai.interop.protocols.upnp.model.devices.upnprootdevice import device_description_load
from ccai.interop.protocols.upnp.model.devices.upnprootdevice import device_description_find_components

from ccai.interop.protocols.upnp.model.devices.upnpdevicefactory import UpnpDeviceFactory
from ccai.interop.protocols.upnp.upnppresence import UpnpPresence
from ccai.interop.protocols.upnp.constants import MSearchKeys, MSearchRouteKeys
from ccai.interop.protocols.upnp.model.upnpdevicehint import UpnpDeviceHint
from ccai.interop.protocols.upnp.model.services.upnpserviceproxy import UpnpServiceProxy
from ccai.interop.protocols.upnp.constants import UPNP_DEVICE1_NAMESPACE


# Types imported only for type checking purposes
if TYPE_CHECKING:
    from ccai.landscaping.landscape import Landscape

EMPTY_LIST = []

UPNP_DIR = os.path.dirname(upnp_module.__file__)


class UpnpCoordinator(CoordinatorBase):
    """
        The UpnpCoordinator utilizes the expected device declarations of type 'network/upnp' to establish and maintain connectivity
        and interoperability with UPNP based network devices.  The UpnpCoordinator will scan all interfaces except for the excluded
        interfaces.  It relies on :class:`UpnpPresence` for SSDP discovery, notifications, and subscription callbacks.
    """
    # pylint: disable=attribute-defined-outside-init

    def __init__(self, lscape: "Landscape", control_point=None, workers: int = 5):
        """
            Initializes the :class:`UpnpCoordinator` instance.

            :param lscape: Landscape this coordinator is associated with.
            :param control_point: Optional UPNP control point object.
            :param workers: Number of worker threads to create.
        """
        super(UpnpCoordinator, self).__init__(lscape, control_point=control_point, workers=workers)

        this_app = ThisApplicationSingleton()
        context = this_app.context
        self._upnp_cache_dir = context.lookup(ContextPaths.RUNTIME_HOME_DIRECTORY, default=os.path.expanduser("~/mjr"))
        self._local_udn = uuid.getnode()

        return

    def _initialize(self, *_args, presence=None, workers: int = 5, **_kwargs):
        """
            Called by the CoordinatorBase constructor to perform the one time initialization of the coordinator Singleton
            of a given type.

            :param presence: An optional UpnpPresence instance for device discovery. If None, a new instance will be created.
            :param workers: The number of worker threads to spin up for handling work packets.
        """
        # pylint: disable=arguments-differ

        # ============================ Fixed Variables ============================
        # These variables are fixed at the start of the UpnpCoordinator and because
        # they are fixed, we don't protect them with the all.

        if presence is None:
            self._presence = UpnpPresence()
        else:
            self._presence = presence

        self._worker_count = workers

        self._factory = UpnpDeviceFactory()

        self._running = False
        self._allow_unknown_devices = False
        self._upnp_recording = True


        # ======================= Coordinator Lock Variables =======================
        # These variables are protected and read/write synchronized by the coordinator
        # lock.  They are all prefixed with _cl_ so it is easy to identify in code
        # if the lock is being held properly when the variables are being accessed.

        # Initialize the coordinator lock
        self._coord_lock = threading.RLock()

        # Initialize the children lookup table
        self._cl_children = {}

        # A lookup table from USN -> devinfo for devices that were declared as
        # watched devices, the watched devices are devices that will be monitored
        # under special constraints and the coordinator will ensure they are found
        # during startup and will expend thread resources to ensure they are updated
        self._cl_watched_devices = {}


        # A reverse lookup table that can lookup the device hint from its USN
        self._cl_usn_to_hint = {}

        # Callback capture management dictionaries
        self._cl_callback_traffic_capture_from = {}

        # A cache for dynamic protocol extension classes to prevent memory leaks
        self._cl_dynamic_extension_classes = {}

        self._match_table = {
            "modelName": ('upnp', UpnpRootDevice._matches_model_name), # pylint: disable=protected-access
            "modelNumber": ('upnp', UpnpRootDevice._matches_model_number) # pylint: disable=protected-access
        }

        self._excluded_interfaces = ["lo"]

        # Track registered presence handlers to avoid duplicate registration
        self._cl_registered_root_device_notifications = set()

        # Initialize scan result storage
        self._found_devices = {}
        self._available_devices = {}
        self._unavailable_devices = []

        return

    def establish_connectivity(self, activation_params):
        """
            Called by the :class:`LandscapeOperationalLayer` in order for the coordinator to be able to
            verify connectivity with devices.

            :param activation_params: Activation parameters used during initialization.
        """
        lscape = self.landscape

        allow_missing_devices = getattr(activation_params, "allow_missing_devices", False)
        allow_unknown_devices = getattr(activation_params, "allow_unknown_devices", False)

        query_devices = {}
        device_configs = lscape.get_device_configs()
        for dev_config in device_configs:
            dev_type = dev_config.get("deviceType")
            if dev_type != "network/upnp":
                continue

            identifier = dev_config.get("hint", "")
            if len(identifier) == 0:
                identifier = dev_config.get("USN", "")
            if len(identifier) == 0:
                continue

            query_devices[identifier] = dev_config

        required_devices = None
        if not allow_missing_devices and len(query_devices) > 0:
            required_devices = [identifier for identifier in query_devices.keys()]

        exclude_interfaces = ["lo"]

        this_app = ThisApplicationSingleton()
        context = this_app.context
        runtime_exclude_interfaces = context.lookup(ContextPaths.UPNP_EXCLUDE_INTERFACES)
        if runtime_exclude_interfaces is not None:
            exclude_interfaces = runtime_exclude_interfaces

        found_devices, matching_devices, missing_devices = self.startup_scan(
            query_devices=query_devices,
            required_devices=required_devices,
            watchlist=None,
            exclude_interfaces=exclude_interfaces,
            allow_unknown_devices=allow_unknown_devices
        )

        results = []

        hint_to_device = {}
        for devinfo in matching_devices.values():
            hint_key = devinfo.get("HINT")
            if hint_key:
                hint_to_device[hint_key] = devinfo

        for identifier in query_devices.keys():
            if identifier in hint_to_device:
                devinfo = hint_to_device[identifier]
                ipaddr = devinfo.get(MSearchKeys.IP)
                results.append((identifier, ipaddr, True, None, None, None))
            else:
                results.append((identifier, None, False, None, None, None))

        for missing in missing_devices:
            missing_key = missing if isinstance(missing, str) else str(missing)
            if missing_key not in query_devices:
                results.append((missing_key, None, False, None, None, None))

        return results

    @property
    def local_udn(self) -> str:
        """
            Returns a local UDN for this device.
        """
        return self._local_udn

    @property
    def presence(self) -> UpnpPresence:
        """
            Returns the UpnpPresence instance used for device discovery.
        """
        return self._presence

    @property
    def watch_devices(self) -> List[LandscapeDevice]:
        """
            Returns a list of the devices being watched by the UPNP coordinator.
        """
        wlist = []

        self._coord_lock.acquire()
        try:
            wlist = [wd for wd in self._cl_watched_devices.values()]
        finally:
            self._coord_lock.release()

        return wlist

    def create_callback_traffic_capture_context(self, fromip: str):
        """
            Creates a :class:`TrafficCaptureContext` for capturing callback
            traffic from the specified IP address.

            :param fromip: Source IP address of the callback traffic.

            :returns: The created :class:`TrafficCaptureContext` instance.
        """
        identifier = uuid.uuid4()
        context = TrafficCaptureContext(self, identifier, fromip, self.destroy_callback_traffic_capture_context)

        self._coord_lock.acquire()
        try:
            if fromip in self._cl_callback_traffic_capture_from:
                self._cl_callback_traffic_capture_from[fromip][context.identifier] = context
            else:
                self._cl_callback_traffic_capture_from[fromip] = {context.identifier: context}
        finally:
            self._coord_lock.release()

        return context

    def destroy_callback_traffic_capture_context(self, context: TrafficCaptureContext):
        """
            Destroys a traffic capture context previously created for callback
            monitoring.

            :param context: The context object to destroy.
        """
        fromip = context.fromip
        identifier = context.identifier

        self._coord_lock.acquire()
        try:
            if fromip in self._cl_callback_traffic_capture_from:
                fromip_table = self._cl_callback_traffic_capture_from[fromip]
                if identifier in fromip_table:
                    del fromip_table[identifier]
        finally:
            self._coord_lock.release()

        return

    def capture_subscription_callback(self, sender_ip: str, headers: dict, body: bytes):
        """
            Captures subscription callback traffic for diagnostics.

            :param sender_ip: The IP address of the sender.
            :param headers: The HTTP headers associated with the callback.
            :param body: The body content of the callback request.
        """
        capture_to = None
        self._coord_lock.acquire()
        try:
            if sender_ip in self._cl_callback_traffic_capture_from:
                capture_to = [cc for cc in self._cl_callback_traffic_capture_from[sender_ip].values()]
        finally:
            self._coord_lock.release()

        if capture_to is not None:
            for cc in capture_to:
                cc.append_capture(headers, body)

        return

    def establish_presence(self):
        """
            Establishes presence subscriptions for all watched devices.
        """
        watched_devices = self.watch_devices

        for wdev in watched_devices:
            wdev.upnp.set_auto_subscribe(True, factory=self._factory)

        return

    def lookup_callback_url_for_interface(self, ifname: str) -> str:
        """
            The callback url that is utilized by devices to determine the URL that should be used as a callback
            for a given network interface.

            :param ifname: The interface name of the interface to get the callback url for.

            :returns: Returns the callback url being monitored by the coordinator for a given interface.
        """
        callback_url = None

        if self._presence is not None:
            callback_url = self._presence.form_callback_url_for_interface(ifname)

        return callback_url

    def _build_device_info_from_detail(self, device_detail: "UpnpDeviceDetail") -> dict:
        """
            Build a device info dictionary from a device detail object.

            :param device_detail: The UPnP device detail object.

            :returns: A dictionary in the format expected by the coordinator.
        """
        evidence = device_detail.evidence
        ip_addr = evidence.ip
        usn = evidence.usn
        usn_dev = evidence.usn_dev
        usn_cls = evidence.usn_cls
        if usn_dev is None or usn_cls is None:
            parsed_dev, parsed_cls = self._split_usn(usn)
            if usn_dev is None:
                usn_dev = parsed_dev
            if usn_cls is None:
                usn_cls = parsed_cls
        ifname = get_interface_for_ip(ip_addr) if ip_addr else None

        routes = {}
        if ifname is not None and ip_addr is not None:
            routes[ifname] = {
                MSearchRouteKeys.IFNAME: ifname,
                MSearchRouteKeys.IP: ip_addr
            }

        device_info = {
            MSearchKeys.IP: ip_addr,
            MSearchKeys.LOCATION: evidence.location,
            MSearchKeys.USN: usn,
            MSearchKeys.USN_DEV: usn_dev,
            MSearchKeys.USN_CLS: usn_cls,
            "HINT": device_detail.hint.get_hint() if device_detail.hint is not None else None,
            MSearchKeys.ROUTES: routes
        }

        return device_info

    def _match_hints_to_discovered(self, hints: List[UpnpDeviceHint], discovered_devices: Dict[str, "UpnpDeviceDetail"]):
        """
            Match hints to discovered devices using first-match semantics.

            :param hints: List of hints to match.
            :param discovered_devices: Mapping of USN to device detail.

            :returns: List of tuples (hint, usn, device_info).
        """
        matches = []
        used_usns = set()

        for hint in hints:
            for usn, device_detail in discovered_devices.items():
                if usn in used_usns:
                    continue
                if usn is None:
                    self.logger.debug("Discovered device entry missing USN; skipping.")
                    continue
                if len(usn) == 0:
                    self.logger.debug("Discovered device entry has empty USN; skipping.")
                    continue
                if hint.matches(device_detail):
                    used_usns.add(usn)
                    device_detail.set_hint(hint)
                    device_info = self._build_device_info_from_detail(device_detail)
                    matches.append((hint, usn, device_info))
                    break

        return matches

    def lookup_device_by_mac(self, mac: str) -> Union[LandscapeDevice, None]:
        """
            Lookup a UPNP device by its MAC address.

            :param mac: The mac address of the device to search for.

            :returns: The device found with the associated MAC address or None
        """

        found = None

        self._coord_lock.acquire()
        try:
            for nxtdev in self._cl_children.values():
                if mac == nxtdev.MACAddress:
                    found = nxtdev.basedevice
                    break
        finally:
            self._coord_lock.release()

        return found

    def lookup_device_by_upnp_hint(self, hint: str) -> Union[UpnpRootDevice, None]:
        """
            Lookup a UPNP device by its hint id.

            :param hint: The hint of the device to search for.

            :returns: The device found with the associated hint address or None
        """

        found = None
        hint_obj = hint if isinstance(hint, UpnpDeviceHint) else UpnpDeviceHint(hint)

        self._coord_lock.acquire()
        try:
            for nxtdev in self._cl_children.values():
                dev_detail = nxtdev.device_detail
                if hint_obj.matches(dev_detail):
                    found = nxtdev
                    break
            
            if found is None:
                errmsg_lines = [
                    "lookup_device_by_upnp_hint did not find a device for hint={}.".format(hint),
                    "DEVICE USN(s):"
                ]
                for nxtdev in self._cl_children.values():
                    errmsg_lines.append(nxtdev.USN)
                errmsg = os.linesep.join(errmsg_lines)
                self.logger.debug(errmsg)

        finally:
            self._coord_lock.release()

        return found
    
    def lookup_device_by_upnp_usn(self, usn: str) -> Union[UpnpRootDevice, None]:
        """
            Lookup a UPNP device by its USN id.

            :param usn: The USN of the device to search for.

            :returns: The device found with the associated USN address or None
        """

        found = None

        self._coord_lock.acquire()
        try:
            for nxtdev in self._cl_children.values():
                if nxtdev.USN.find(usn) > -1:
                    found = nxtdev
                    break
            
            if found is None:
                errmsg_lines = [
                    "lookup_device_by_upnp_usn did not find a device for usn={}.".format(usn),
                    "DEVICE USN(s):"
                ]
                for nxtdev in self._cl_children.values():
                    errmsg_lines.append(nxtdev.USN)
                errmsg = os.linesep.join(errmsg_lines)
                self.logger.debug(errmsg)

        finally:
            self._coord_lock.release()

        return found

    def lookup_device_list_by_usn(self, usnlist: List[str]) -> List[LandscapeDevice]:
        """
            Lookup a list of UPNP devices by their USN id.

            :param usnlist: A list of USN identifiers for devices to search for.

            :returns: A list of devices found with USN(s) in the usn search list.
        """
        found = []

        self._coord_lock.acquire()
        try:
            for usn in usnlist:
                for nxtdev in self._cl_children.values():
                    if usn == nxtdev.USN:
                        found.append(nxtdev)
        finally:
            self._coord_lock.release()

        return found

    def startup_scan(self, query_devices: Dict[str, dict], required_devices: Optional[List[str]] = None,
                           watchlist: Optional[List[str]] = None, exclude_interfaces: Optional[List] = None,
                            response_timeout: float = 20, pre_msearch_timeout=20, retry: int = 2, 
                            upnp_recording: bool = False, allow_unknown_devices: bool = False):
        """
            Starts up and initializes the UPNP coordinator by utilizing UpnpPresence for device discovery.

            :param query_devices: A dictionary of upnp device hints to search for.
            :param required_devices: A list of required device hints that we will setup watching and updates for.
            :param watchlist: A list of device hints to watch for presence updates.
            :param exclude_interfaces: Network interfaces that will be excluded from the search for devices.
            :param response_timeout: A timeout to wait for device discovery responses.
            :param pre_msearch_timeout: Timeout for pre-search activities.
            :param retry: The number of retry attempts to make before giving up on finding devices.
            :param upnp_recording: Forces the updating or recording of device descriptions from devices found on the network.
            :param allow_unknown_devices: Whether to allow devices not in the configuration.
        """
        # pylint: disable=dangerous-default-value

        if exclude_interfaces is None:
            exclude_interfaces = []

        self._allow_unknown_devices = allow_unknown_devices
        self._upnp_recording = upnp_recording
        self._excluded_interfaces = exclude_interfaces

        lscape = self.landscape

        if self._running:
            raise RuntimeError("UpnpCoordinator.startup_scan called twice, The UpnpCoordinator is already running.") from None

        if query_devices is None:
            query_devices = {}

        found_devices = {}
        matching_devices = {}
        missing_devices = []

        # Start the UpnpPresence for device discovery
        if not self._presence.is_running:
            # Filter out excluded interfaces from presence monitoring
            presence_interfaces = [ifname for ifname in self._presence.presence_interfaces 
                                 if ifname not in exclude_interfaces]
            self._presence.start(presence_interfaces=presence_interfaces)

        # Convert query_devices to UpnpDeviceHint objects for discovery
        device_hints = []
        for device_hint in query_devices.keys():
            device_hints.append(UpnpDeviceHint(device_hint))

        required_hints = []
        if required_devices is not None:
            for devhint in required_devices:
                if isinstance(devhint, UpnpDeviceHint):
                    required_hints.append(devhint)
                else:
                    required_hints.append(UpnpDeviceHint(str(devhint)))

        if device_hints:
            query_hint_keys = [hint.get_hint() for hint in device_hints]
            seen_query_hints = set()
            duplicate_query_hints = set()
            for hint in query_hint_keys:
                if hint in seen_query_hints:
                    duplicate_query_hints.add(hint)
                else:
                    seen_query_hints.add(hint)
            if len(duplicate_query_hints) > 0:
                errmsg_lines = [
                    "Duplicate hints found in query devices.",
                    "DUPLICATE QUERY HINTS:"
                ]
                for hint in sorted(duplicate_query_hints):
                    errmsg_lines.append(f"    {hint}")
                errmsg = os.linesep.join(errmsg_lines)
                raise SemanticError(errmsg) from None

        if required_hints:
            required_hint_keys = [hint.get_hint() for hint in required_hints]
            seen_required_hints = set()
            duplicate_required_hints = set()
            for hint in required_hint_keys:
                if hint in seen_required_hints:
                    duplicate_required_hints.add(hint)
                else:
                    seen_required_hints.add(hint)
            if len(duplicate_required_hints) > 0:
                errmsg_lines = [
                    "Duplicate hints found in required devices.",
                    "DUPLICATE REQUIRED HINTS:"
                ]
                for hint in sorted(duplicate_required_hints):
                    errmsg_lines.append(f"    {hint}")
                errmsg = os.linesep.join(errmsg_lines)
                raise SemanticError(errmsg) from None

        if required_hints:
            query_hint_keys = {hint.get_hint() for hint in device_hints}
            required_hint_keys = {hint.get_hint() for hint in required_hints}
            missing_from_query = required_hint_keys - query_hint_keys
            if len(missing_from_query) > 0:
                errmsg_lines = [
                    "Required devices must be included in query_devices.",
                    "MISSING FROM QUERY:"
                ]
                for hint in sorted(missing_from_query):
                    errmsg_lines.append(f"    {hint}")
                errmsg = os.linesep.join(errmsg_lines)
                raise ConfigurationError(errmsg) from None

        # Perform device discovery using UpnpPresence
        discovery_window = self._presence.discover_devices(
            limit_to=device_hints,
            window_length=response_timeout
        )

        # Wait for discovery to complete
        discovery_window.wait()

        discovered_devices = discovery_window.devices_found

        # Build a mapping of hints to discovered devices, matching one device per hint
        # Required hints are matched first to ensure they are consumed before optional hints.
        combined_hints = list(required_hints)
        seen_hint_keys = {h.get_hint() for h in combined_hints}
        for hint in device_hints:
            hint_key = hint.get_hint()
            if hint_key not in seen_hint_keys:
                combined_hints.append(hint)
                seen_hint_keys.add(hint_key)

        matches = self._match_hints_to_discovered(combined_hints, discovered_devices)
        query_hint_keys = {hint.get_hint() for hint in device_hints}
        for hint, usn, device_info in matches:
            found_devices[usn] = device_info
            if hint.get_hint() in query_hint_keys:
                matching_devices[usn] = device_info

        # Add remaining discovered devices to the found list
        for usn, device_detail in discovered_devices.items():
            if usn not in found_devices:
                found_devices[usn] = self._build_device_info_from_detail(device_detail)

        # Check for missing required devices
        if required_hints:
            matched_hint_ids = {id(hint) for hint, _usn, _info in matches}

            for devhint in required_hints:
                if id(devhint) not in matched_hint_ids:
                    missing_devices.append(devhint)

        if len(missing_devices) > 0:
            errmsg_list = [
                "Error devices missing from configuration.",
                "MISSING DEVICES:"
            ]
            for devhint in missing_devices:
                errmsg_list.append("    %s" % devhint)
            errmsg = os.linesep.join(errmsg_list)
            self.logger.error(errmsg)
            raise ConfigurationError(errmsg) from None

        config_lookup = lscape._internal_get_upnp_device_config_lookup_table() # pylint: disable=protected-access

        # Update root devices with discovered information
        for usn, dval in matching_devices.items():
            addr = dval[MSearchKeys.IP]
            location = dval[MSearchKeys.LOCATION]
            devhint = dval.get("HINT")
            self._update_root_device(lscape, config_lookup, addr, location, devhint, dval)
            usn = dval.get(MSearchKeys.USN)
            if usn is None:
                usn_dev = dval.get(MSearchKeys.USN_DEV)
                usn_cls = dval.get(MSearchKeys.USN_CLS)
                if usn_dev is not None and usn_cls is not None:
                    usn = f"uuid:{usn_dev}::{usn_cls}"
            self._register_root_device_notification(usn)

        # Setup watchlist devices
        if watchlist is not None and len(watchlist) > 0:
            for hint in watchlist:
                wdev = self.lookup_device_by_upnp_hint(hint)
                if wdev is not None:
                    self._cl_watched_devices[hint] = wdev.basedevice

        self._log_scan_results(found_devices, matching_devices, missing_devices)

        self._device_cache_update(matching_devices)

        self._found_devices = found_devices
        self._available_devices = matching_devices
        self._unavailable_devices = missing_devices

        self._start_all_threads()

        return found_devices, matching_devices, missing_devices

    def shutdown(self):
        """
            Shuts down the coordinator and cleans up resources including the UpnpPresence.
        """
        registered_usns = []
        self._coord_lock.acquire()
        try:
            registered_usns = list(self._cl_registered_root_device_notifications)
            self._cl_registered_root_device_notifications.clear()
        finally:
            self._coord_lock.release()

        if self._presence is not None and self._presence.is_running:
            self._presence.stop()
            self._presence.cleanup()
        if self._presence is not None:
            for usn in registered_usns:
                self._presence.unregister_root_device_notification_handler(usn, self._handle_root_device_notification)

        self._running = False

        return

    def wakeup_device(self, usn, dev_hint):
        """
            Attempts to wake up a device using implementation specific means.

            :param usn: The USN of the device to wake.
            :param dev_hint: Additional hint information about the device.
            
            :raises: NotImplementedError indicating this functionality is not yet implemented.
        """
        raise NotImplementedError("Device wakeup functionality is not yet implemented for UPnP coordinator")

    def _create_root_device(self, manufacturer: str, model_name: str, model_number: str, model_description: str) -> UpnpRootDevice:
        """
            Create a root UPNP device using the provided manufacturer and modelNumber provided.  If no
            device is found for the provided manufacturer and model_number then a generic UPNP root device
            will be instantiated using the manufacturer, model_number and model_description.

            :param manufacturer: The manufacturer of the root device to instantiate.
            :param model_name: The modelName of the root device to instantiate.
            :param model_number: The model_number of the root device to instantiate.
            :param model_description: The description to give to a device when it is instantiated.

            :returns: A upnp root device instance.
        """
        # Create a minimal device detail object for the factory method
        from ccai.interop.protocols.upnp.model.upnpdevicedetail import UpnpDeviceDetail
        from ccai.interop.protocols.upnp.model.description.basic1devicedesc import Basic1DeviceDesc
        from ccai.interop.protocols.upnp.model.description.deviceevidence import DeviceEvidence
        from ccai.interop.protocols.upnp.model.description.specversion import SpecVersion
        
        # Create spec version (UPnP 1.0)
        spec_version = SpecVersion(major=1, minor=0)
        
        # Create minimal device description with the provided parameters
        device_desc = Basic1DeviceDesc(
            specVersion=spec_version,
            deviceType="urn:schemas-upnp-org:device:Basic:1",
            friendlyName=f"{manufacturer} {model_name}",
            manufacturer=manufacturer,
            modelName=model_name,
            modelNumber=model_number,
            modelDescription=model_description,
            UDN=f"uuid:{self._local_udn}",
            serialNumber="",
            manufacturerURL="",
            modelURL="",
            UPC="",
            presentationURL=""
        )
        
        # Create minimal device evidence (this would normally come from discovery)
        device_evidence = DeviceEvidence(
            usn=f"uuid:{self._local_udn}::upnp:rootdevice",
            status="ssdp:alive",
            server="Unknown/1.0 UPnP/1.0 Unknown/1.0",
            location="http://unknown/description.xml",
            ip="0.0.0.0",
            other={},
            presence=self._presence
        )
        
        # Create device detail object that the factory expects
        device_detail = UpnpDeviceDetail(device_desc, device_evidence)
        
        dev = self._factory.create_root_device_instance(device_detail)

        if type(dev) is UpnpRootDevice:
            dev = UpnpProtocolExtension(device_detail, self._presence)
        elif isinstance(dev, UpnpRootDevice) and not isinstance(dev, ProtocolExtension):
            # If the device is a UpnpRootDevice but not a ProtocolExtension, we need to
            # dynamically mixin the ProtocolExtension capability so the device can be
            # fully integrated into the landscape as an extension.

            base_cls = dev.__class__
            new_cls = None

            self._coord_lock.acquire()
            try:
                if base_cls in self._cl_dynamic_extension_classes:
                    new_cls = self._cl_dynamic_extension_classes[base_cls]
                else:
                    # Define the dynamic class name
                    cls_name = f"{base_cls.__name__}ProtocolExtension"

                    # Define the initialize method wrapper to ensure both initializers are called
                    def initialize_wrapper(self, coord_ref, basedevice_ref, extid, location, configinfo, deviceinfo):
                        # Call base class initialize (UpnpRootDevice logic)
                        base_cls.initialize(self, coord_ref, basedevice_ref, extid, location, configinfo, deviceinfo)
                        # Call ProtocolExtension initialize (Extension logic)
                        ProtocolExtension.initialize(self, coord_ref, basedevice_ref, extid, location, configinfo, deviceinfo=deviceinfo)

                    # Define the __init__ wrapper to handle initialization
                    def init_wrapper(self, device_detail, presence=None):
                        try:
                            # Try initializing base class with presence
                            base_cls.__init__(self, device_detail, presence)
                        except TypeError:
                            # Fallback if base class doesn't accept presence
                            base_cls.__init__(self, device_detail)
                            if presence is not None:
                                # Assuming UpnpRootDevice method is available
                                self.set_presence(presence)

                        ProtocolExtension.__init__(self)

                    # Create the new class
                    new_cls = type(cls_name, (base_cls, ProtocolExtension), {
                        "__init__": init_wrapper,
                        "initialize": initialize_wrapper,
                        "__module__": base_cls.__module__
                    })
                    self._cl_dynamic_extension_classes[base_cls] = new_cls
            finally:
                self._coord_lock.release()

            dev = new_cls(device_detail, self._presence)

        return dev

    def _device_cache_update(self, found_device: dict):
        """
            Updates the on-disk cache with information about the devices
            that were discovered.

            :param found_device: Mapping of device hints to device data.
        """
        if not os.path.exists(self._upnp_cache_dir):
            os.makedirs(self._upnp_cache_dir)

        for fdev_usn in found_device:
            fdev_info = found_device[fdev_usn]
            fdev_filename = os.path.join(self._upnp_cache_dir, fdev_usn)
            with open(fdev_filename, 'w') as dcf:
                yaml.dump(fdev_info, dcf)

        return

    def _device_cache_verify_device_info(self, device_hint: str, device_filename: str, device_info: dict):
        """
            Verifies cached device information by loading the device description and ensuring the UDN matches the expected hint.

            :param device_hint: The identifier hint for the device.
            :param device_filename: Path to the cached device file.
            :param device_info: Parsed device information from the cache.

            :returns: ``True`` if the cached information is valid.
        """

        valid = False

        if MSearchKeys.USN_DEV in device_info and "LOCATION" in device_info:
            location_url = device_info["LOCATION"]

            try:
                dev_desc = device_description_load(location_url)
                if dev_desc is not None:
                    namespaces = {"": UPNP_DEVICE1_NAMESPACE}

                    root_element = dev_desc.getroot()
                    udn_element = root_element.find("device/UDN", namespaces=namespaces)
                    if udn_element is not None:
                        udn_full = udn_element.text.lstrip("uuid:")
                        if udn_full.find(device_hint) < 0:
                            try:
                                os.remove(device_filename)
                            except FileNotFoundError:
                                pass  # File already removed or doesn't exist
                        else:
                            valid = True
            except ConnectionError:
                pass

        # If we can't connect to validate, remove the cached file
        if not valid:
            try:
                os.remove(device_filename)
            except FileNotFoundError:
                pass  # File already removed or doesn't exist

        return valid

    def _log_scan_results(self, found_devices: dict, matching_devices:dict , missing_devices: list):
        """
            Logs the results of the device scan.

            :param found_devices: A list of found devices.
            :param matching_devices: A list of devices matching the expected devices listed in the upnp_hint_list.
            :param missing_devices: A list of USN(s) for devices that were not found.
        """
        devmsg_lines = ["FOUND DEVICES:"]
        for dkey, dval in found_devices.items():
            hint = dval.get("HINT") if isinstance(dval, dict) else None
            if hint is not None:
                devmsg_lines.append("    %s (hint=%s)" % (dkey, hint))
            else:
                devmsg_lines.append("    %s" % dkey)
        devmsg_lines.append("")

        devmsg_lines.append("MATCHING DEVICES:")
        for dkey, dval in matching_devices.items():
            hint = dval.get("HINT") if isinstance(dval, dict) else None
            if hint is not None:
                devmsg_lines.append("    %s (hint=%s)" % (dkey, hint))
            else:
                devmsg_lines.append("    %s" % dkey)
        devmsg_lines.append("")

        if len(missing_devices) > 0:
            devmsg_lines.append("MISSING DEVICES:")
            for dkey in missing_devices:
                devmsg_lines.append("    %s" % dkey)
            devmsg_lines.append("")

        devmsg = os.linesep.join(devmsg_lines)
        self.logger.info(devmsg)

        return

    def _normalize_name(self, name: str) -> str:
        """
            Normalizes a name by removing non-alphanumeric characters.

            :param name: A name to normalize.

            :returns: The normalized name with all the non-alphanumeric characters removed.
        """
        # pylint: disable=no-self-use

        normal_chars = [ nc for nc in name if str.isalnum(nc) ]
        normal_name = ''.join(normal_chars)

        return normal_name

    def _process_device_alive_notification(self, ip_addr, usn_device: str, host: str, request_info: dict):
        """
            Processes a device alive notification when given the USN and dictionary of header keys and values.

            :param ip_addr: The IP address of the device.
            :param usn_device: The USN of the device which the notification is from.
            :param host: The host header from the notification.
            :param request_info: The headers from the notification request.
        """

        if MSearchKeys.LOCATION not in request_info:
            self.logger.error("Device alive notification missing LOCATION header for USN: %s", usn_device)
            return

        location = request_info[MSearchKeys.LOCATION]

        # Get a reference to the landscape
        lscape = self.landscape

        self._activate_root_device(lscape, usn_device, ip_addr, location, request_info)

        return

    def _process_device_byebye_notification(self, ip_addr, usn_device: str, host: str, request_info: dict):
        """
            Processes a device byebye notification when given the USN and dictionary of header keys and values.

            :param ip_addr: The IP address of the device.
            :param usn_device: The USN of the device which the notification is from.
            :param host: The host header from the notification.
            :param request_info: The headers from the notification request.
        """

        location = "Unknown"
        if MSearchKeys.LOCATION in request_info:
            location = request_info[MSearchKeys.LOCATION]

        # Get a reference to the landscape
        lscape = self.landscape

        self._deactivate_root_device(lscape, usn_device, ip_addr, location, request_info)

        return

    def _register_root_device_notification(self, usn: Optional[str]):
        """
            Register for root device notifications for a given USN.

            :param usn: The full USN string for the device.
        """
        if self._presence is None or usn is None:
            return

        usn_device, usn_class = self._split_usn(usn)
        if usn_device is not None and usn_class is not None:
            usn = f"uuid:{usn_device}::{usn_class}"

        should_register = False
        self._coord_lock.acquire()
        try:
            if usn not in self._cl_registered_root_device_notifications:
                self._cl_registered_root_device_notifications.add(usn)
                should_register = True
        finally:
            self._coord_lock.release()

        if should_register:
            self._presence.register_root_device_notification_handler(usn, self._handle_root_device_notification)

        return

    def _split_usn(self, usn: str) -> Tuple[Optional[str], Optional[str]]:
        """
            Split a USN string into device and class components.

            :param usn: The USN string to split.

            :returns: Tuple of (usn_device, usn_class).
        """
        usn_device = None
        usn_class = None

        if usn and "::" in usn:
            parts = usn.split("::")
            if len(parts) >= 1 and parts[0]:
                usn_device = parts[0].lstrip("uuid:")
            if len(parts) >= 2:
                usn_class = parts[1]

        return usn_device, usn_class

    def _handle_root_device_notification(self, ifname: str, from_ip: str, usn: str, nt: str, nts: str, msg_info: dict):
        """
            Handles root device notifications received by the UpnpPresence.

            :param ifname: Interface name the notification was received on.
            :param from_ip: The IP address of the sender.
            :param usn: The USN from the notification.
            :param nt: The NT value from the notification.
            :param nts: The NTS value from the notification.
            :param msg_info: The parsed notification headers.
        """
        usn_device, usn_class = self._split_usn(usn)
        if usn_device is None or usn_class is None:
            self.logger.warning("Malformed USN in notification: %s", usn)
            return

        request_info = dict(msg_info)
        request_info[MSearchKeys.IP] = from_ip
        request_info[MSearchKeys.USN] = usn
        request_info[MSearchKeys.USN_DEV] = usn_device
        request_info[MSearchKeys.USN_CLS] = usn_class

        if ifname is None:
            ifname = get_interface_for_ip(from_ip)

        if ifname is not None:
            request_info[MSearchKeys.ROUTES] = {
                ifname: {
                    MSearchRouteKeys.IFNAME: ifname,
                    MSearchRouteKeys.IP: from_ip
                }
            }

        host = request_info.get("HOST", "")

        if nts == "ssdp:alive" and usn_class == "upnp:rootdevice":
            self._process_device_alive_notification(from_ip, usn_device, host, request_info)
            self._coord_lock.acquire()
            try:
                if usn is not None:
                    self._available_devices[usn] = request_info
                    self._found_devices[usn] = request_info
                if usn in self._unavailable_devices:
                    self._unavailable_devices.remove(usn)
            finally:
                self._coord_lock.release()
        elif nts == "ssdp:byebye" and usn_class == "upnp:rootdevice":
            self._process_device_byebye_notification(from_ip, usn_device, host, request_info)
            self._coord_lock.acquire()
            try:
                if usn in self._available_devices:
                    del self._available_devices[usn]
                if usn not in self._unavailable_devices:
                    self._unavailable_devices.append(usn)
            finally:
                self._coord_lock.release()

        return

    def _process_service_alive_notification(self, ip_addr, usn_device: str, usn_class: str, host: str, request_info: dict):
        """
            Handles a service alive notification for a UPNP service.

            :param ip_addr: IP address of the device.
            :param usn_device: Device USN value.
            :param usn_class: Service class USN value.
            :param host: Host header from the notification.
            :param request_info: Dictionary of header values from the request.
        """
        return

    def _process_service_byebye_notification(self, ip_addr, usn_device: str, usn_class: str, host: str, request_info: dict):
        """
            Handles a service byebye notification for a UPNP service.

            :param ip_addr: IP address of the device.
            :param usn_device: Device USN value.
            :param usn_class: Service class USN value.
            :param host: Host header from the notification.
            :param request_info: Dictionary of header values from the request.
        """
        return

    def _start_all_threads(self):
        """
            Starts the UPnP coordinator in presence-driven mode.
        """
        self._running = True

        if self._presence is None:
            return

        for devinfo in self._available_devices.values():
            usn = devinfo.get(MSearchKeys.USN)
            if usn is None:
                usn_dev = devinfo.get(MSearchKeys.USN_DEV)
                usn_cls = devinfo.get(MSearchKeys.USN_CLS)
                if usn_dev is not None and usn_cls is not None:
                    usn = f"uuid:{usn_dev}::{usn_cls}"
            self._register_root_device_notification(usn)

        return

    def _activate_root_device(self, lscape: "Landscape", usn_device: str, ip_addr: str, location: str, deviceinfo: dict):
        """
            Marks a device as active or creates it if unknown devices are
            allowed.

            :param lscape: The landscape instance.
            :param usn_device: Device USN string.
            :param ip_addr: IP address of the device.
            :param location: Location URL of the device description.
            :param deviceinfo: Parsed device information from discovery.
        """

        dev = self.lookup_device_by_upnp_usn(usn_device)
        if dev is not None:
            # Mark the device active
            dev.mark_alive()
        elif self._allow_unknown_devices:
            config_lookup = lscape._internal_get_upnp_device_config_lookup_table() # pylint: disable=protected-access

            usn_dev = deviceinfo[MSearchKeys.USN_DEV]

            marked_as_skip = False
            if usn_dev in config_lookup:
                configinfo = config_lookup[usn_dev]
                if "skip" in configinfo and configinfo["skip"]:
                    marked_as_skip = True

            if not marked_as_skip:
                devhint = None
                self._coord_lock.acquire()
                try:
                    devhint = self._cl_usn_to_hint.get(usn_device)
                finally:
                    self._coord_lock.release()

                if devhint is not None:
                    self._update_root_device(lscape, config_lookup, ip_addr, location, devhint, deviceinfo)

        return

    def _deactivate_root_device(self, lscape: "Landscape", usn_device: str, ip_addr: str, location: str, deviceinfo: dict):
        """
            Marks a device as inactive when a byebye notification is
            received.

            :param lscape: The landscape instance.
            :param usn_device: Device USN string.
            :param ip_addr: IP address of the device.
            :param location: Location URL of the device description.
            :param deviceinfo: Parsed device information from discovery.
        """
        dev = self.lookup_device_by_upnp_usn(usn_device)
        if dev is not None:
            # Mark the device inactive
            dev.mark_byebye()

        return

    def _update_root_device(self, lscape, config_lookup: dict, ip_addr: str, location: str, devhint: str, deviceinfo: dict):
        """
            Updates a UPNP root device.

            :param lscape: The landscape singleton instance.
            :param config_lookup: A configuration lookup table that can be used to lookup configuration information for upnp devices.
            :param ip_addr: The IP address of the device to update.
            :param location: The location URL associated with the device.
            :param deviceinfo: The device information from the msearch response headers.
            :param devhint: The identifier hint used to identify the device.
        """

        usn_dev = deviceinfo.get(MSearchKeys.USN_DEV)
        if usn_dev:
            try:
                usn_cls = deviceinfo.get(MSearchKeys.USN_CLS)
                if usn_cls is None:
                    usn_full = deviceinfo.get(MSearchKeys.USN)
                    _, usn_cls = self._split_usn(usn_full)
                if usn_cls is None:
                    usn_cls = "upnp:rootdevice"

                configinfo = None
                if usn_dev in config_lookup:
                    configinfo = config_lookup[usn_dev]

                docTree = device_description_load(location)

                try:
                    # {urn:schemas-upnp-org:device-1-0}root
                    namespaces = {"": UPNP_DEVICE1_NAMESPACE}

                    deviceDescParts = device_description_find_components(location, docTree, namespaces=namespaces)
                    devNode, urlBase, manufacturer, modelName, modelNumber, modelDescription = deviceDescParts

                    dev_extension = None
                    skip_device = False
                    should_refresh = False
                    
                    # Acquire the lock before we decide if the location exists in the children table
                    self._coord_lock.acquire()
                    try:
                        if location not in self._cl_children:
                            # Unlock while we do some expensive stuff, we have already decided to
                            # create the device
                            self._coord_lock.release()
                            try:
                                try:
                                    # We create the device
                                    dev_extension = self._create_root_device(manufacturer, modelName, modelNumber, modelDescription)
                                except Exception:
                                    # Handle potential None values in error message formatting
                                    mfg_str = manufacturer if manufacturer is not None else "<unknown>"
                                    name_str = modelName if modelName is not None else "<unknown>"
                                    model_str = modelNumber if modelNumber is not None else "<unknown>"
                                    desc_str = modelDescription if modelDescription is not None else "<unknown>"
                                    errmsg = "ERROR: Unable to create device mfg=%s name=%s model=%s desc=%s\nTRACEBACK:\n" % (mfg_str, name_str, model_str, desc_str)
                                    errmsg += traceback.format_exc()
                                    self.logger.error(errmsg)
                                    raise

                                if isinstance(dev_extension, UpnpRootDevice):
                                    dev_extension.record_description(ip_addr, urlBase, manufacturer, modelName, docTree, devNode, namespaces=namespaces, upnp_recording=self._upnp_recording)

                                coord_ref = weakref.ref(self)

                                basedevice: LandscapeDevice = lscape._internal_lookup_device_by_hint(devhint)
                                if basedevice is None:
                                    if self._allow_unknown_devices:
                                        dev_type = "network/upnp"
                                        dev_config_info = {
                                            "deviceType": dev_type,
                                            "deviceClass": "unknown",
                                            "upnp": {
                                                "hint": usn_dev,
                                                "modelName": modelName,
                                                "modelNumber": modelNumber
                                            },
                                            "USN_DEV": usn_dev,
                                            "USN_CLS": usn_cls
                                        }
                                        dfid = FriendlyIdentifier(usn_dev, devhint)
                                        basedevice = lscape._create_landscape_device(dfid, dev_type, dev_config_info)
                                    else:
                                        skip_device = True

                                if basedevice is not None:
                                    basedevice.update_full_identifier(usn_dev)
                                    basedevice = lscape._enhance_landscape_device(basedevice, dev_extension)

                                    basedevice_ref = weakref.ref(basedevice)

                                    dev_extension.initialize(coord_ref, basedevice_ref, usn_dev, location, configinfo, deviceinfo)

                                    # Refresh the description
                                    dev_extension.refresh_description(ip_addr, self._factory, docTree.getroot(), namespaces=namespaces)
                                    dev_extension.mark_alive()

                                    basedevice.attach_extension("upnp", dev_extension)

                                    basedevice.initialize_features()
                                    basedevice.update_match_table(self._match_table)

                                    lscape._internal_activate_device(devhint)
                            finally:
                                self._coord_lock.acquire()

                            if skip_device:
                                infomsg = "Skipping device usn={} location={}".format(usn_dev, location)
                                self.logger.info(infomsg)
                            # If the device is still not in the table, add it
                            elif location not in self._cl_children:
                                self._cl_children[location] = dev_extension

                            self._cl_usn_to_hint[usn_dev] = devhint

                        else:
                            dev_extension = self._cl_children[location]
                            should_refresh = True
                    finally:
                        self._coord_lock.release()

                    if should_refresh and dev_extension is not None:
                        # Refresh the description
                        dev_extension.refresh_description(ip_addr, self._factory, docTree.getroot(), namespaces=namespaces)

                except SemanticError:
                    # Always allow semantic errors to propagate, semantic errors represent
                    # misuse of a test framework API and can be definitively classified
                    # as a test code bug that needs to be fixed.
                    raise

                except Exception:  # Allow system exceptions like KeyboardInterrupt to propagate
                    exmsg = traceback.format_exc()
                    errmsg_lines = [
                        "ERROR: Unable to create or initialize device for. IP: %s LOCATION: %s" % (ip_addr, location),
                        exmsg
                    ]
                    for k, v in deviceinfo.items():
                        errmsg_lines.append("    %s: %s" % (k, v))

                    errmsg = os.linesep.join(errmsg_lines)
                    self.logger.error(errmsg)

            except SemanticError:
                # Always allow semantic errors to propagate, semantic errors represent
                # misuse of a test framework API and can be definitively classified
                # as a test code bug that needs to be fixed.
                raise

            except Exception:  # Allow system exceptions like KeyboardInterrupt to propagate
                exmsg = traceback.format_exc()
                errmsg_lines = [
                    "ERROR: Unable to load device description for. IP: %s LOCATION: %s" % (ip_addr, location),
                    exmsg
                ]
                for k, v in deviceinfo.items():
                    errmsg_lines.append("    %s: %s" % (k, v))

                errmsg = os.linesep.join(errmsg_lines)
                self.logger.error(errmsg)

        usn = deviceinfo.get(MSearchKeys.USN)
        if usn is None:
            usn_dev = deviceinfo.get(MSearchKeys.USN_DEV)
            usn_cls = deviceinfo.get(MSearchKeys.USN_CLS)
            if usn_dev is not None and usn_cls is not None:
                usn = f"uuid:{usn_dev}::{usn_cls}"
        self._register_root_device_notification(usn)

        return
