import unittest
import sys
from unittest.mock import MagicMock
import weakref

# Mock automojo.xmodules
mock_xmodules = MagicMock()
mock_logger = MagicMock()
mock_xmodules.xlogging.enhancedloggers.getEnhancedLogger.return_value = mock_logger
sys.modules['automojo.xmodules'] = mock_xmodules
sys.modules['automojo.xmodules.xlogging'] = mock_xmodules.xlogging
sys.modules['automojo.xmodules.xlogging.enhancedloggers'] = mock_xmodules.xlogging.enhancedloggers
sys.modules['automojo.xmodules.xlogging.monitoredscope'] = MagicMock()
sys.modules['automojo.xmodules.eventing'] = MagicMock()
sys.modules['automojo.xmodules.eventing.eventedvariablesink'] = MagicMock()
sys.modules['automojo.xmodules.eventing.eventedvariable'] = MagicMock()
sys.modules['automojo.xmodules.eventing.enumerations'] = MagicMock()
sys.modules['automojo.xmodules.xconvert'] = MagicMock()

# Mock automojo.errors
mock_errors = MagicMock()
sys.modules['automojo.errors'] = mock_errors
sys.modules['automojo.errors.exceptions'] = MagicMock()
sys.modules['automojo.errors.raising'] = MagicMock()
sys.modules['automojo.errors.xtraceback'] = MagicMock()

# Mock automojo.interop.constants
mock_interop_constants = MagicMock()
mock_interop_constants.DIR_AUTOMOJO_INTEROP = "/tmp/automojo/interop"
sys.modules['automojo.interop.constants'] = mock_interop_constants

# Mock automojo.interop.aspects
mock_interop_aspects = MagicMock()
sys.modules['automojo.interop.aspects'] = mock_interop_aspects

# Mock automojo.networking
mock_networking = MagicMock()
mock_networking.constants.HTTP1_1_LINESEP = b'\r\n'
sys.modules['automojo.networking'] = mock_networking
sys.modules['automojo.networking.constants'] = mock_networking.constants

# Mock automojo.waiting
mock_waiting = MagicMock()
sys.modules['automojo.waiting'] = mock_waiting
sys.modules['automojo.waiting.waitmodel'] = MagicMock()

# Mock automojo.thisapp
mock_thisapp = MagicMock()
sys.modules['automojo.thisapp'] = mock_thisapp
sys.modules['automojo.thisapp.contextpaths'] = MagicMock()
sys.modules['automojo.thisapp.wellknown'] = MagicMock()

# Mock UpnpServiceProxy
class MockUpnpServiceProxy:
    pass

mock_service_proxy_module = MagicMock()
mock_service_proxy_module.UpnpServiceProxy = MockUpnpServiceProxy
sys.modules['automojo.interop.protocols.upnp.model.services.upnpserviceproxy'] = mock_service_proxy_module

# Mock requests
mock_requests = MagicMock()
sys.modules['requests'] = mock_requests
mock_requests_compat = MagicMock()
from urllib.parse import urljoin
mock_requests_compat.urljoin = urljoin
sys.modules['requests.compat'] = mock_requests_compat
sys.modules['requests.exceptions'] = MagicMock()


from automojo.interop.protocols.upnp.model.devices.upnprootdevice import UpnpRootDevice
from automojo.interop.protocols.upnp.model.upnpdevicedetail import UpnpDeviceDetail
from automojo.interop.protocols.upnp.model.description.basic1devicedesc import Basic1DeviceDesc
from automojo.interop.protocols.upnp.model.description.deviceevidence import DeviceEvidence
from automojo.interop.protocols.upnp.model.description.specversion import SpecVersion
from automojo.interop.protocols.upnp.constants import MSearchKeys, MSearchRouteKeys

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
