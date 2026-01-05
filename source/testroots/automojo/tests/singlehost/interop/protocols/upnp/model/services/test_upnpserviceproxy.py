import weakref
from datetime import datetime, timedelta

import automojo.testbase as testbase

from automojo.interop.protocols.upnp.model.services.upnpserviceproxy import UpnpServiceProxy


class DummyDevice:
    def __init__(self, *, subscribe_result=None):
        self.subscribe_calls = []
        self.unsubscribe_calls = []
        self._subscribe_result = subscribe_result or ("uuid:new", datetime.now() + timedelta(seconds=60))

    def subscribe_to_events(self, service, renew=False):
        self.subscribe_calls.append({"service": service, "renew": renew})
        return self._subscribe_result

    def unsubscribe_to_events(self, service):
        self.unsubscribe_calls.append(service)


class DummyProxy(UpnpServiceProxy):
    SERVICE_TYPE = "dummy:service"
    SERVICE_EVENT_VARIABLES = {}


def test_renew_subscription_uses_renewal_path() -> None:
    device = DummyDevice()
    proxy = DummyProxy()
    proxy._device_ref = weakref.ref(device)
    proxy._update_subscription_details("uuid:old", datetime.now())

    proxy.renew_subscription()

    testbase.assert_equal(len(device.unsubscribe_calls), 0)
    testbase.assert_equal(len(device.subscribe_calls), 1)
    testbase.assert_equal(device.subscribe_calls[0]["renew"], True)
    testbase.assert_equal(proxy._subscription_id, "uuid:new")
    return


def test_renew_subscription_clears_state_on_failure() -> None:
    device = DummyDevice(subscribe_result=(None, None))
    proxy = DummyProxy()
    proxy._device_ref = weakref.ref(device)
    proxy._update_subscription_details("uuid:old", datetime.now())

    proxy.renew_subscription()

    testbase.assert_equal(proxy._subscription_id, None)
    testbase.assert_equal(proxy._subscription_expiration, None)
    testbase.assert_equal(len(device.subscribe_calls), 1)
    return
