
import sys
import os
import unittest
from unittest.mock import MagicMock

# Ensure source/packages is in sys.path
sys.path.insert(0, os.path.abspath("source/packages"))

# --- Mocking missing dependencies ---
# Dependencies are installed by the environment; nothing is mocked at module scope.

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
