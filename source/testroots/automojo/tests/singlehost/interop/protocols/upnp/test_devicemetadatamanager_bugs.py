"""
    .. module:: test_devicemetadatamanager_bugs
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Test module for DeviceMetadataManager bugs.

    .. moduleauthor:: AutomationX <automation@mojo.com>
"""

import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch

from automojo import testbase
from automojo.interop.protocols.upnp.devicemetadatamanager import DeviceMetadataManager

def test_load_device_description_encoding():
    """
    Test that load_device_description correctly handles file encoding (UTF-8) by reading as binary.
    """
    # Create a temporary directory structure
    tmp_dir = tempfile.mkdtemp()
    cache_root = os.path.join(tmp_dir, "cache")
    os.makedirs(os.path.join(cache_root, "devices"), exist_ok=True)

    # Create a dummy device description file with UTF-8 characters
    device_xml = """<?xml version="1.0"?>
<root xmlns="urn:schemas-upnp-org:device-1-0">
    <specVersion>
        <major>1</major>
        <minor>0</minor>
    </specVersion>
    <device>
        <deviceType>urn:schemas-upnp-org:device:Basic:1</deviceType>
        <friendlyName>Test Device \u00A9</friendlyName>
        <manufacturer>Test Manufacturer</manufacturer>
        <modelName>Test Model</modelName>
        <UDN>uuid:test-udn</UDN>
    </device>
</root>"""

    # Write as UTF-8 bytes
    desc_filename = "test_device.xml"
    full_path = os.path.join(cache_root, "devices", desc_filename) # Wait, code checks cache root then cache root/devices?
    # Code:
    # desc_filename = os.path.join(self._metadata_static_root, device_cache_leaf)
    # if not os.path.exists(desc_filename):
    #     desc_filename = os.path.join(self._metadata_cache_root, device_cache_leaf)

    # So if I pass "test_device.xml", it looks in cache_root/test_device.xml.
    full_path = os.path.join(cache_root, desc_filename)

    with open(full_path, 'wb') as f:
        f.write(device_xml.encode('utf-8'))

    try:
        manager = DeviceMetadataManager(metadata_cache_root=cache_root)

        # We need to mock the mapper registry to avoid dependency issues or just check if it parses without error
        # effectively. The manager calls mapper.create_root_device_description.
        # If we don't have a mapper for "Test Manufacturer", it logs a warning and returns None.
        # This is enough to verify that the file was read successfully and parsed as XML.
        # If encoding was wrong, read() or parse_xml_content might fail if we forced text mode with wrong encoding (though default is usually utf-8).
        # But reading as binary avoids text decoding issues during read.

        # To verify the fix specifically (rb vs r), we rely on the fact that 'rb' works for UTF-8 XML.

        with patch('automojo.interop.protocols.upnp.devicemetadatamanager.DeviceDetailMapperRegistrySingleton') as MockRegistry:
            mock_registry = MockRegistry.return_value
            mock_mapper = MagicMock()
            mock_registry.lookup_device_detail_mapper_safe.return_value = mock_mapper

            manager.load_device_description(desc_filename)

            # Verify lookup was called with "Test Manufacturer", implying XML was parsed
            mock_registry.lookup_device_detail_mapper_safe.assert_called_with("Test Manufacturer")

    finally:
        shutil.rmtree(tmp_dir)
