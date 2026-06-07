
import sys
import os
import unittest
from unittest.mock import MagicMock
import types

# Ensure source/packages is in sys.path
sys.path.insert(0, os.path.abspath("source/packages"))

# --- Mocking missing dependencies ---
if "ccai.xmodules" not in sys.modules:
    sys.modules["ccai.xmodules"] = MagicMock()
    sys.modules["ccai.xmodules.xlogging"] = MagicMock()
    sys.modules["ccai.xmodules.xlogging.enhancedloggers"] = MagicMock()
    sys.modules["ccai.xmodules.xlogging.enhancedloggers"].getEnhancedLogger = MagicMock(return_value=MagicMock())
    sys.modules["ccai.xmodules.xlogging.monitoredscope"] = MagicMock()

    sys.modules["ccai.xmodules.eventing"] = MagicMock()
    sys.modules["ccai.xmodules.eventing.eventedvariablesink"] = MagicMock()
    sys.modules["ccai.xmodules.eventing.eventedvariable"] = MagicMock()
    sys.modules["ccai.xmodules.eventing.enumerations"] = MagicMock()

    sys.modules["ccai.xmodules.xconvert"] = MagicMock()

if "ccai.networking" not in sys.modules:
    sys.modules["ccai.networking"] = MagicMock()
    networking_constants = types.ModuleType("ccai.networking.constants")
    networking_constants.HTTP1_1_LINESEP = b"\r\n"
    sys.modules["ccai.networking.constants"] = networking_constants
    sys.modules["ccai.networking.multicast"] = MagicMock()
    sys.modules["ccai.networking.interfaces"] = MagicMock()

if "ccai.errors" not in sys.modules:
    sys.modules["ccai.errors"] = MagicMock()
    sys.modules["ccai.errors.exceptions"] = MagicMock()
    sys.modules["ccai.errors.raising"] = MagicMock()
    sys.modules["ccai.errors.xtraceback"] = MagicMock()

if "ccai.waiting" not in sys.modules:
    sys.modules["ccai.waiting"] = MagicMock()
    sys.modules["ccai.waiting.waitmodel"] = MagicMock()

if "ccai.thisapp" not in sys.modules:
    sys.modules["ccai.thisapp"] = MagicMock()
    sys.modules["ccai.thisapp.contextpaths"] = MagicMock()
    sys.modules["ccai.thisapp.wellknown"] = MagicMock()

if "ccai.interop.constants" not in sys.modules:
    constants_mock = types.ModuleType("ccai.interop.constants")
    constants_mock.DIR_CCAI_INTEROP = "/tmp"
    sys.modules["ccai.interop.constants"] = constants_mock

if "ccai.interop.aspects" not in sys.modules:
    sys.modules["ccai.interop.aspects"] = MagicMock()

class MockUpnpServiceProxy:
    pass

upnpserviceproxy_mock = types.ModuleType("ccai.interop.protocols.upnp.model.services.upnpserviceproxy")
upnpserviceproxy_mock.UpnpServiceProxy = MockUpnpServiceProxy
sys.modules["ccai.interop.protocols.upnp.model.services.upnpserviceproxy"] = upnpserviceproxy_mock

# --- End Mocking ---

from ccai.interop.protocols.upnp.model.devices.upnprootdevice import UpnpRootDevice
from ccai.interop.protocols.upnp.model.upnpdevicedetail import UpnpDeviceDetail
from ccai.interop.protocols.upnp.model.description.basic1devicedesc import Basic1DeviceDesc
from ccai.interop.protocols.upnp.model.description.specversion import SpecVersion
from ccai.interop.protocols.upnp.model.description.deviceevidence import DeviceEvidence
from ccai.interop.protocols.upnp.constants import MSearchKeys, MSearchRouteKeys

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
