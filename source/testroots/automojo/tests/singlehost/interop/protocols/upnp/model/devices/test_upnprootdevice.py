import threading
import weakref
from datetime import datetime, timedelta

import automojo.testbase as testbase

from automojo.interop.protocols.upnp.constants import MSearchRouteKeys
from automojo.interop.protocols.upnp.model.devices.upnprootdevice import UpnpRootDevice


class DummyService:
    SERVICE_EVENT_VARIABLES = {"evt": object()}
    SERVICE_TYPE = "dummy:type"

    def __init__(self):
        self.eventSubURL = "/event"
        self.subscriptionId = None
        self.updated = []
        self.invalidated = False

    def get_extension_key(self):
        return "dummy"

    def _update_subscription_details(self, sid, expires):
        self.subscriptionId = sid
        self.updated.append((sid, expires))

    def invalidate_subscription(self):
        self.invalidated = True
        self.subscriptionId = None


def _build_root_device(presence, service: DummyService) -> UpnpRootDevice:
    device = object.__new__(UpnpRootDevice)
    device._device_lock = threading.RLock()
    device._subscriptions = {}
    device._sid_to_service_lookup = {}
    device._services = {service.get_extension_key(): service}
    device._primary_route = {MSearchRouteKeys.IP: "127.0.0.1"}
    device._presence_ref = weakref.ref(presence)
    device._coordinator_ref = None
    device._basedevice_ref = None
    device._urlBase = "http://device"
    return device


def test_events_subscribe_passes_sid_on_renewal() -> None:
    service = DummyService()

    class RecordingPresence:
        def __init__(self):
            self.calls = []

        def service_subscribe(self, host_ip, subscribe_url, subscribe_timeout_secs, callback, custom_headers=None, sid=None, renew=False):
            self.calls.append({"sid": sid, "renew": renew, "timeout": subscribe_timeout_secs})
            return sid or "uuid:new", datetime.now() + timedelta(seconds=30)

    presence = RecordingPresence()
    device = _build_root_device(presence, service)

    existing_sid = "uuid:old"
    expiry = datetime.now() + timedelta(seconds=20)
    device._subscriptions[service.SERVICE_TYPE] = (existing_sid, expiry)
    device._sid_to_service_lookup[existing_sid] = service

    sid, new_expiry = device.events_subscribe(service, renew=True, timeout=15)

    testbase.assert_equal(len(presence.calls), 1)
    testbase.assert_equal(presence.calls[0]["sid"], existing_sid)
    testbase.assert_equal(presence.calls[0]["renew"], True)
    testbase.assert_equal(presence.calls[0]["timeout"], 15)
    testbase.assert_equal(sid, existing_sid)
    testbase.assert_not_equal(new_expiry, None)
    testbase.assert_equal(device._sid_to_service_lookup.get(existing_sid), service)
    testbase.assert_equal(service.invalidated, False)
    testbase.assert_equal(device._subscriptions[service.SERVICE_TYPE][0], existing_sid)
    return


def test_events_subscribe_recovers_after_renewal_failure() -> None:
    service = DummyService()

    class RecoveringPresence:
        def __init__(self):
            self.calls = []

        def service_subscribe(self, host_ip, subscribe_url, subscribe_timeout_secs, callback, custom_headers=None, sid=None, renew=False):
            self.calls.append({"sid": sid, "renew": renew})
            if renew:
                return None, None
            return "uuid:new", datetime.now() + timedelta(seconds=40)

    presence = RecoveringPresence()
    device = _build_root_device(presence, service)

    existing_sid = "uuid:recover-old"
    expiry = datetime.now() + timedelta(seconds=20)
    device._subscriptions[service.SERVICE_TYPE] = (existing_sid, expiry)
    device._sid_to_service_lookup[existing_sid] = service

    sid, new_expiry = device.events_subscribe(service, renew=True, timeout=20)

    testbase.assert_equal(len(presence.calls), 2)
    testbase.assert_equal(presence.calls[0]["renew"], True)
    testbase.assert_equal(presence.calls[0]["sid"], existing_sid)
    testbase.assert_equal(presence.calls[1]["renew"], False)
    testbase.assert_equal(sid, "uuid:new")
    testbase.assert_not_equal(new_expiry, None)
    testbase.assert_equal(existing_sid in device._sid_to_service_lookup, False)
    testbase.assert_equal(device._sid_to_service_lookup.get("uuid:new"), service)
    testbase.assert_equal(service.invalidated, False)
    testbase.assert_equal(device._subscriptions[service.SERVICE_TYPE][0], "uuid:new")
    return
