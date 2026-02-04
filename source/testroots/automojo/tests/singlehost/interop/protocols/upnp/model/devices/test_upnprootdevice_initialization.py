
import sys
import os
import unittest
from unittest.mock import MagicMock
import types

# Ensure source/packages is in sys.path
sys.path.insert(0, os.path.abspath("source/packages"))

# --- Mocking missing dependencies ---
if "automojo.xmodules" not in sys.modules:
    sys.modules["automojo.xmodules"] = MagicMock()
    sys.modules["automojo.xmodules.xlogging"] = MagicMock()
    sys.modules["automojo.xmodules.xlogging.enhancedloggers"] = MagicMock()
    sys.modules["automojo.xmodules.xlogging.enhancedloggers"].getEnhancedLogger = MagicMock(return_value=MagicMock())
    sys.modules["automojo.xmodules.xlogging.monitoredscope"] = MagicMock()

    sys.modules["automojo.xmodules.eventing"] = MagicMock()
    sys.modules["automojo.xmodules.eventing.eventedvariablesink"] = MagicMock()
    sys.modules["automojo.xmodules.eventing.eventedvariable"] = MagicMock()
    sys.modules["automojo.xmodules.eventing.enumerations"] = MagicMock()

    sys.modules["automojo.xmodules.xconvert"] = MagicMock()

if "automojo.networking" not in sys.modules:
    sys.modules["automojo.networking"] = MagicMock()
    networking_constants = types.ModuleType("automojo.networking.constants")
    networking_constants.HTTP1_1_LINESEP = b"\r\n"
    sys.modules["automojo.networking.constants"] = networking_constants
    sys.modules["automojo.networking.multicast"] = MagicMock()
    sys.modules["automojo.networking.interfaces"] = MagicMock()

if "automojo.errors" not in sys.modules:
    sys.modules["automojo.errors"] = MagicMock()
    sys.modules["automojo.errors.exceptions"] = MagicMock()
    sys.modules["automojo.errors.raising"] = MagicMock()
    sys.modules["automojo.errors.xtraceback"] = MagicMock()

if "automojo.waiting" not in sys.modules:
    sys.modules["automojo.waiting"] = MagicMock()
    sys.modules["automojo.waiting.waitmodel"] = MagicMock()

if "automojo.thisapp" not in sys.modules:
    sys.modules["automojo.thisapp"] = MagicMock()
    sys.modules["automojo.thisapp.contextpaths"] = MagicMock()
    sys.modules["automojo.thisapp.wellknown"] = MagicMock()

if "automojo.interop.constants" not in sys.modules:
    constants_mock = types.ModuleType("automojo.interop.constants")
    constants_mock.DIR_AUTOMOJO_INTEROP = "/tmp"
    sys.modules["automojo.interop.constants"] = constants_mock

if "automojo.interop.aspects" not in sys.modules:
    sys.modules["automojo.interop.aspects"] = MagicMock()

class MockUpnpServiceProxy:
    pass

upnpserviceproxy_mock = types.ModuleType("automojo.interop.protocols.upnp.model.services.upnpserviceproxy")
upnpserviceproxy_mock.UpnpServiceProxy = MockUpnpServiceProxy
sys.modules["automojo.interop.protocols.upnp.model.services.upnpserviceproxy"] = upnpserviceproxy_mock

# --- End Mocking ---

from automojo.interop.protocols.upnp.model.devices.upnprootdevice import UpnpRootDevice
from automojo.interop.protocols.upnp.model.upnpdevicedetail import UpnpDeviceDetail
from automojo.interop.protocols.upnp.model.description.basic1devicedesc import Basic1DeviceDesc
from automojo.interop.protocols.upnp.model.description.specversion import SpecVersion
from automojo.interop.protocols.upnp.model.description.deviceevidence import DeviceEvidence
from automojo.interop.protocols.upnp.constants import MSearchKeys, MSearchRouteKeys

class TestUpnpRootDeviceInitialization(unittest.TestCase):
    """
    Tests for UpnpRootDevice.initialize method.
    """
    def test_initialize_sets_routes(self):
        """
        Verify that initialize correctly populates routes and primary_route from deviceinfo.
        """
        # Setup
        spec_version = SpecVersion(major=1, minor=0)
        desc = Basic1DeviceDesc(
            specVersion=spec_version,
            deviceType="urn:schemas-upnp-org:device:Basic:1",
            friendlyName="Test Device",
            manufacturer="Test Mfg",
            modelName="Test Model",
            UDN="uuid:test-udn",
            locationURL="http://192.168.1.100:8080/description.xml"
        )
        evidence = DeviceEvidence(
            usn="uuid:test-udn::upnp:rootdevice",
            status="ssdp:alive",
            server="Test Server",
            location="http://192.168.1.100:8080/description.xml",
            ip="192.168.1.100",
            other={},
            presence=MagicMock()
        )
        detail = UpnpDeviceDetail(desc, evidence)

        device = UpnpRootDevice(detail)

        # Prepare arguments for initialize
        coord_ref = MagicMock()
        basedevice_ref = MagicMock()
        extid = "test-extid"
        location = "http://192.168.1.100:8080/description.xml"
        configinfo = {}

        # Prepare deviceinfo with ROUTES
        route_info = {
            MSearchRouteKeys.IFNAME: "eth0",
            MSearchRouteKeys.IP: "192.168.1.100"
        }
        deviceinfo = {
            MSearchKeys.IP: "192.168.1.100",
            MSearchKeys.LOCATION: location,
            MSearchKeys.ROUTES: {
                "eth0": route_info
            }
        }

        # Call initialize
        device.initialize(coord_ref, basedevice_ref, extid, location, configinfo, deviceinfo)

        # Assert
        # Currently, UpnpRootDevice does NOT populate routes, so these should FAIL when the bug exists
        # and PASS when the bug is fixed.

        # Checking for the fix: expect populated
        self.assertIsNotNone(device.routes, "routes should be populated")
        self.assertEqual(len(device.routes), 1, "routes should have 1 entry")
        self.assertIsNotNone(device.primary_route, "primary_route should be populated")
        self.assertEqual(device.primary_route[MSearchRouteKeys.IFNAME], "eth0")

if __name__ == "__main__":
    unittest.main()
