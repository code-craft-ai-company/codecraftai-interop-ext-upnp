import automojo.testbase as testbase

from automojo.testbase.mocking import create_module_patch

from automojo.interop.protocols.upnp import upnppresence
from automojo.interop.protocols.upnp.model.description.deviceevidence import DeviceEvidence


class DummySocket:
    def close(self):
        return


class DummyPool:
    def start_pool(self):
        return

    def push_work(self, packet):
        return

    def shutdown(self):
        return

      
def _create_evidence(presence: upnppresence.UpnpPresence, usn: str, status: str) -> DeviceEvidence:
    return DeviceEvidence(
        usn=usn,
        status=status,
        server="server",
        location="loc",
        ip="1.1.1.1",
        other={},
        presence=presence,
    )

  
def test_start_creates_callback_sockets_when_no_interfaces():
    def fake_presence_socket(self, ifname):
        sock = DummySocket()
        self._presence_sockets[ifname] = sock
        return sock

    def fake_callback_socket(self, ifname):
        sock = DummySocket()
        self._callback_sockets[ifname] = sock
        self._callback_address_from_iface[ifname] = ("1.1.1.1", 1234)
        return sock

    def fake_presence_thread(self, sgate, ifname):
        fake_presence_socket(self, ifname)
        sgate.set()
        return

    def fake_callback_thread(self, sgate, ifname):
        fake_callback_socket(self, ifname)
        sgate.set()
        return

    def fake_msearch_thread(self, sgate):
        sgate.set()
        return

    with create_module_patch(upnppresence, "get_all_ipv4_interfaces") as if_patch, \
         create_module_patch(upnppresence, "LooperPool") as pool_patch:

        if_patch.configure(return_value=["eth0"])
        pool_patch.configure(return_value=DummyPool())

        upnppresence.UpnpPresence._get_presence_socket = fake_presence_socket
        upnppresence.UpnpPresence._get_callback_socket = fake_callback_socket
        upnppresence.UpnpPresence._thread_entry_for_presence = fake_presence_thread
        upnppresence.UpnpPresence._thread_entry_for_callback = fake_callback_thread
        upnppresence.UpnpPresence._thread_entry_for_msearch = fake_msearch_thread

        scanner = upnppresence.UpnpPresence()
        scanner.start()
        testbase.assert_equal("eth0" in scanner._callback_sockets, True)
        scanner.stop()
        scanner.cleanup()

    return

  
def test_active_and_inactive_device_types() -> None:
    presence = upnppresence.UpnpPresence()

    active = _create_evidence(presence, "usn1", "active")
    inactive = _create_evidence(presence, "usn2", "inactive")

    presence._active_devices["usn1"] = active
    presence._inactive_devices["usn2"] = inactive

    actives = presence.active_devices
    inactives = presence.inactive_devices

    testbase.assert_equal(all(isinstance(v, DeviceEvidence) for v in actives.values()), True)
    testbase.assert_equal(all(isinstance(v, DeviceEvidence) for v in inactives.values()), True)
    return

