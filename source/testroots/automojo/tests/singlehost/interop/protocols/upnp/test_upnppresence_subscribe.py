import automojo.testbase as testbase
from automojo.testbase.mocking import create_module_patch
from automojo.interop.protocols.upnp import upnppresence


class DummyResponse:
    def __init__(self, status_code: int = 200, headers=None, content: bytes = b""):
        self.status_code = status_code
        self.headers = headers or {"SID": "uuid:test", "TIMEOUT": "Second-30"}
        self.content = content


def test_service_subscribe_immediately_after_start() -> None:
    with create_module_patch(upnppresence, "LooperPool") as pool_patch, \
         create_module_patch(upnppresence, "get_ipv4_address") as ifaddr_patch, \
         create_module_patch(upnppresence, "get_interface_for_ip") as if_for_ip_patch, \
         create_module_patch(upnppresence.requests, "request") as req_patch:

        class DummyPool:
            def start_pool(self):
                return
            def push_work(self, packet):
                return
            def shutdown(self):
                return
        pool_patch.configure(side_effect=lambda *a, **k: DummyPool())
        ifaddr_patch.configure(return_value="127.0.0.1")
        if_for_ip_patch.configure(return_value="lo")
        req_patch.configure(return_value=DummyResponse())

        pres = upnppresence.UpnpPresence(presence_interfaces=["lo"])

        def dummy_start():
            pres._running = True
            pres._dispatch_pool = DummyPool()
            pres._get_callback_socket("lo")

        pres.start = dummy_start

        pres.start()
        try:
            sid, _ = pres.service_subscribe(
                "127.0.0.1",
                "http://example/subscribe",
                30,
                lambda *a, **k: None,
            )
            testbase.assert_equal(sid, "uuid:test")
            testbase.assert_equal("lo" in pres._callback_address_from_iface, True)
        finally:
            pres.stop()
            pres.cleanup()
    return


def test_service_subscribe_renew_uses_sid_headers() -> None:
    captured_headers = []
    renew_headers = {"SID": "uuid:renewed", "TIMEOUT": "Second-10"}

    with create_module_patch(upnppresence, "LooperPool") as pool_patch, \
         create_module_patch(upnppresence, "get_ipv4_address") as ifaddr_patch, \
         create_module_patch(upnppresence, "get_interface_for_ip") as if_for_ip_patch, \
         create_module_patch(upnppresence.requests, "request") as req_patch:

        class DummyPool:
            def start_pool(self):
                return
            def push_work(self, packet):
                return
            def shutdown(self):
                return
        pool_patch.configure(side_effect=lambda *a, **k: DummyPool())
        ifaddr_patch.configure(return_value="127.0.0.1")
        if_for_ip_patch.configure(return_value="lo")
        req_patch.configure(side_effect=lambda *a, **kwargs: captured_headers.append(kwargs["headers"]) or DummyResponse(headers=renew_headers))

        pres = upnppresence.UpnpPresence(presence_interfaces=["lo"])

        def dummy_start():
            pres._running = True
            pres._dispatch_pool = DummyPool()
            pres._get_callback_socket("lo")

        pres.start = dummy_start

        pres.start()
        try:
            sid, _ = pres.service_subscribe(
                "127.0.0.1",
                "http://example/subscribe",
                10,
                lambda *a, **k: None,
                sid="uuid:existing",
                renew=True,
            )
            testbase.assert_equal(sid, "uuid:renewed")
            testbase.assert_equal("CALLBACK" in captured_headers[-1], False)
            testbase.assert_equal("NT" in captured_headers[-1], False)
            testbase.assert_equal(captured_headers[-1]["SID"], "uuid:existing")
            testbase.assert_equal(captured_headers[-1]["TIMEOUT"], "Seconds-10")
        finally:
            pres.stop()
            pres.cleanup()
    return
