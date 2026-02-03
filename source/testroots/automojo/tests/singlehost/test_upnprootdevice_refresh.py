
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from xml.etree.ElementTree import Element
import types

# Ensure source/packages is in sys.path
sys.path.insert(0, os.path.abspath("source/packages"))

# --- Mocking missing dependencies ---
# These mocks are necessary because the environment lacks external dependencies
# like automojo-xmodules, automojo-interop, etc.

# Mock automojo.xmodules
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

# Mock automojo.networking
if "automojo.networking" not in sys.modules:
    sys.modules["automojo.networking"] = MagicMock()
    networking_constants = types.ModuleType("automojo.networking.constants")
    networking_constants.HTTP1_1_LINESEP = b"\r\n"
    sys.modules["automojo.networking.constants"] = networking_constants
    sys.modules["automojo.networking.multicast"] = MagicMock()
    sys.modules["automojo.networking.interfaces"] = MagicMock()

# Mock automojo.errors
if "automojo.errors" not in sys.modules:
    sys.modules["automojo.errors"] = MagicMock()
    sys.modules["automojo.errors.exceptions"] = MagicMock()
    sys.modules["automojo.errors.raising"] = MagicMock()
    sys.modules["automojo.errors.xtraceback"] = MagicMock()

# Mock automojo.waiting
if "automojo.waiting" not in sys.modules:
    sys.modules["automojo.waiting"] = MagicMock()
    sys.modules["automojo.waiting.waitmodel"] = MagicMock()

# Mock automojo.thisapp
if "automojo.thisapp" not in sys.modules:
    sys.modules["automojo.thisapp"] = MagicMock()
    sys.modules["automojo.thisapp.contextpaths"] = MagicMock()
    sys.modules["automojo.thisapp.wellknown"] = MagicMock()

# Mock automojo.interop.constants
if "automojo.interop.constants" not in sys.modules:
    constants_mock = types.ModuleType("automojo.interop.constants")
    constants_mock.DIR_AUTOMOJO_INTEROP = "/tmp"
    sys.modules["automojo.interop.constants"] = constants_mock

# Mock automojo.interop.aspects
if "automojo.interop.aspects" not in sys.modules:
    sys.modules["automojo.interop.aspects"] = MagicMock()

# Unconditionally mock UpnpServiceProxy to avoid it being a MagicMock which causes issues with typing module
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
from automojo.interop.protocols.upnp.model.description.serviceevidence import ServiceEvidence

class TestUpnpRootDeviceRefresh(unittest.TestCase):
    """
    Tests for UpnpRootDevice.refresh_description method.
    """
    def test_refresh_description_missing_urlbase(self):
        """
        Verify that refresh_description correctly sets the URLBase from the device description,
        preventing ValueError when processing relative service URLs.
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
        # device._location is set by initialize, but we are not calling initialize here.
        # refresh_description uses self._location
        device._location = "http://192.168.1.100:8080/description.xml"

        # Mock factory
        factory = MagicMock()

        # Mock DeviceDetailMapper to return a description with a service that has relative URL
        service = ServiceEvidence(
            serviceType="urn:schemas-upnp-org:service:TestService:1",
            serviceId="urn:upnp-org:serviceId:TestService",
            SCPDURL="/service/desc.xml", # Relative URL
            controlURL="/service/control",
            eventSubURL="/service/event"
        )

        # We need a new description object that has this service
        new_desc = Basic1DeviceDesc(
            specVersion=spec_version,
            deviceType="urn:schemas-upnp-org:device:Basic:1",
            friendlyName="Test Device",
            manufacturer="Test Mfg",
            modelName="Test Model",
            UDN="uuid:test-udn",
            locationURL="http://192.168.1.100:8080/description.xml",
            serviceList=[service]
        )

        with patch("automojo.interop.protocols.upnp.mapping.devicedetailmapper.DeviceDetailMapper.create_root_device_description", return_value=new_desc):
            with patch("automojo.interop.protocols.upnp.mapping.devicedetailmapper.DeviceDetailMapper.read_spec_version_and_manufacturer", return_value=(spec_version, "Test Mfg")):
                # Mock requests.get to avoid network call
                with patch("requests.get") as mock_get:
                    mock_get.return_value.status_code = 200
                    mock_get.return_value.text = "<scpd>...</scpd>"

                    # Call refresh_description
                    # It expects docTree: Element. We can pass a dummy element since we mocked create_root_device_description
                    dummy_element = Element("root")

                    try:
                        device.refresh_description("192.168.1.100", factory, dummy_element)
                    except ValueError as e:
                        self.fail(f"Caught unexpected ValueError: {e}")

                    # Check if requests.get was called
                    self.assertTrue(mock_get.called, "requests.get should have been called to fetch service description")

                    # Check if _urlBase is set correctly
                    self.assertEqual(device.URLBase, "http://192.168.1.100:8080")

if __name__ == "__main__":
    unittest.main()
