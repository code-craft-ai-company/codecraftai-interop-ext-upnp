import unittest
import sys
from unittest.mock import MagicMock
import weakref

# Mock ccai.xmodules
mock_logger = MagicMock()

# Mock ccai.errors
mock_errors = MagicMock()

# Mock ccai.interop.constants
mock_interop_constants = MagicMock()
mock_interop_constants.DIR_CCAI_INTEROP = "/tmp/ccai/interop"

# Mock ccai.interop.aspects
mock_interop_aspects = MagicMock()

# Mock ccai.networking
mock_networking = MagicMock()
mock_networking.constants.HTTP1_1_LINESEP = b'\r\n'

# Mock ccai.waiting
mock_waiting = MagicMock()

# Mock ccai.thisapp
mock_thisapp = MagicMock()

# Mock UpnpServiceProxy
class MockUpnpServiceProxy:
    pass

mock_service_proxy_module = MagicMock()
mock_service_proxy_module.UpnpServiceProxy = MockUpnpServiceProxy

# Mock requests
mock_requests = MagicMock()
mock_requests_compat = MagicMock()
from urllib.parse import urljoin
mock_requests_compat.urljoin = urljoin


from ccai.interop.protocols.upnp.model.devices.upnprootdevice import UpnpRootDevice
from ccai.interop.protocols.upnp.model.upnpdevicedetail import UpnpDeviceDetail
from ccai.interop.protocols.upnp.model.description.basic1devicedesc import Basic1DeviceDesc
from ccai.interop.protocols.upnp.model.description.deviceevidence import DeviceEvidence
from ccai.interop.protocols.upnp.model.description.specversion import SpecVersion
from ccai.interop.protocols.upnp.constants import MSearchKeys, MSearchRouteKeys

class TestUpnpRootDeviceInitialization(unittest.TestCase):

    def test_initialization_updates_evidence(self):
        # 1. Setup dummy evidence (mimicking UpnpCoordinator._create_root_device)
        dummy_location = "http://unknown/description.xml"
        dummy_usn = "uuid:dummy::upnp:rootdevice"
        dummy_ip = "0.0.0.0"

        spec_version = SpecVersion(major=1, minor=0)
        device_desc = Basic1DeviceDesc(
            specVersion=spec_version,
            deviceType="urn:schemas-upnp-org:device:Basic:1",
            friendlyName="Dummy Device",
            manufacturer="DummyMfg",
            modelName="DummyModel",
            modelNumber="1",
            modelDescription="Dummy Description",
            UDN="uuid:dummy",
            serialNumber="",
            manufacturerURL="",
            modelURL="",
            UPC="",
            presentationURL=""
        )

        # We need a presence object for DeviceEvidence
        mock_presence = MagicMock()
        device_evidence = DeviceEvidence(
            usn=dummy_usn,
            status="ssdp:alive",
            server="Unknown/1.0 UPnP/1.0 Unknown/1.0",
            location=dummy_location,
            ip=dummy_ip,
            other={},
            presence=mock_presence
        )

        device_detail = UpnpDeviceDetail(device_desc, device_evidence)

        # 2. Create device, PASS mock_presence!
        device = UpnpRootDevice(device_detail, presence=mock_presence)

        # Verify initial state
        self.assertEqual(device.location, dummy_location)
        self.assertEqual(device.USN, dummy_usn)

        # 3. Prepare real deviceinfo (mimicking UpnpCoordinator._update_root_device -> initialize)
        real_location = "http://192.168.1.100:80/desc.xml"
        real_usn_dev = "uuid:real-uuid"
        real_usn_cls = "upnp:rootdevice"
        real_ip = "192.168.1.100"

        deviceinfo = {
            MSearchKeys.IP: real_ip,
            MSearchKeys.LOCATION: real_location,
            MSearchKeys.USN_DEV: real_usn_dev,
            MSearchKeys.USN_CLS: real_usn_cls,
            MSearchKeys.ROUTES: {}
        }

        # Mock references
        class DummyObject:
            pass
        coord_ref = weakref.ref(DummyObject())
        basedevice_ref = weakref.ref(DummyObject())
        extid = "some_ext_id"
        configinfo = {}

        # 4. Call initialize
        device.initialize(coord_ref, basedevice_ref, extid, real_location, configinfo, deviceinfo)

        # 5. Verify updated state

        # IP Address should be updated (UpnpRootDevice.initialize does this already)
        self.assertEqual(device.IPAddress, real_ip, "IP Address should be updated")

        # device_location property (returns _location) should be updated (UpnpRootDevice.initialize does this)
        self.assertEqual(device.device_location, real_location, "device_location should be updated")

        # BUG FIXED: location property (returns _device_evidence.location) should be updated
        self.assertEqual(device.location, real_location, "location property should be updated from evidence")

        # BUG FIXED: USN_DEV property (returns _device_evidence.usn_dev) should be updated
        # USN_DEV strips "uuid:" prefix if present
        expected_usn_dev = real_usn_dev.replace("uuid:", "")
        self.assertEqual(device.USN_DEV, expected_usn_dev, "USN_DEV should be updated")

if __name__ == '__main__':
    unittest.main()
