
import unittest
from unittest.mock import MagicMock, patch
from xml.etree.ElementTree import Element

# Ensure source/packages is in sys.path

# The package's dependencies are installed by the environment; nothing is mocked at module scope,
# because injecting fakes into sys.modules poisons every module imported after this one.

from ccai.interop.protocols.upnp.model.devices.upnprootdevice import UpnpRootDevice
from ccai.interop.protocols.upnp.model.upnpdevicedetail import UpnpDeviceDetail
from ccai.interop.protocols.upnp.model.description.basic1devicedesc import Basic1DeviceDesc
from ccai.interop.protocols.upnp.model.description.specversion import SpecVersion
from ccai.interop.protocols.upnp.model.description.deviceevidence import DeviceEvidence
from ccai.interop.protocols.upnp.model.description.serviceevidence import ServiceEvidence

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

        with patch("ccai.interop.protocols.upnp.mapping.devicedetailmapper.DeviceDetailMapper.create_root_device_description", return_value=new_desc):
            with patch("ccai.interop.protocols.upnp.mapping.devicedetailmapper.DeviceDetailMapper.read_spec_version_and_manufacturer", return_value=(spec_version, "Test Mfg")):
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
