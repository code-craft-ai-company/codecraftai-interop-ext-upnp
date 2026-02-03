
import threading
import unittest
from unittest.mock import MagicMock, patch

try:
    from automojo.landscaping.coordinators.upnp.upnpcoordinator import UpnpCoordinator
    from automojo.interop.protocols.upnp.constants import MSearchKeys
except ImportError:
    UpnpCoordinator = None

class TestUpnpCoordinatorLocking(unittest.TestCase):

    def setUp(self):
        if UpnpCoordinator is None:
            self.skipTest("UpnpCoordinator not available")

    def test_refresh_description_called_without_lock(self):
        # Mock dependencies
        lscape = MagicMock()
        lscape._internal_get_upnp_device_config_lookup_table.return_value = {}

        # We need to ensure UpnpCoordinator doesn't do real initialization that requires network
        with patch('automojo.landscaping.coordinators.upnp.upnpcoordinator.UpnpPresence'), \
             patch('automojo.landscaping.coordinators.upnp.upnpcoordinator.UpnpDeviceFactory'):

            coordinator = UpnpCoordinator(lscape)
            # Manually set workers if needed, or rely on defaults

            # Populate _cl_children to simulate existing device
            location = "http://192.168.1.100:80/description.xml"
            mock_device = MagicMock()

            # Access protected member
            coordinator._cl_children[location] = mock_device

            # Track locking
            real_lock = coordinator._coord_lock
            coordinator._coord_lock = MagicMock()
            coordinator._coord_lock.acquire.side_effect = real_lock.acquire
            coordinator._coord_lock.release.side_effect = real_lock.release

            # We want to check if lock is held during refresh_description.
            # Since mock doesn't easily expose "is locked" for RLock, we can verify call order.

            # But checking real lock state is better.

            # Let's use the wrapper approach from my reproduction script but using MagicMock wraps?
            # Or just assume the logic I verified is correct.

            # Just verifying call order:
            # 1. acquire
            # 2. release
            # 3. refresh_description
            # 4. acquire (not strictly needed in else block anymore? No, it's not re-acquired!)

            # Wait, my fix REMOVED re-acquire in else block?
            # No, I used:
            # finally: release()
            # if should_refresh: refresh()

            # So call order:
            # 1. acquire
            # 2. release
            # 3. refresh

            # Setup arguments
            config_lookup = {}
            ip_addr = "192.168.1.100"
            devhint = "uuid:device-uuid"
            deviceinfo = {
                MSearchKeys.USN_DEV: "uuid:device-uuid",
                MSearchKeys.USN_CLS: "upnp:rootdevice",
                "LOCATION": location
            }

            with patch('automojo.landscaping.coordinators.upnp.upnpcoordinator.device_description_load') as mock_load, \
                 patch('automojo.landscaping.coordinators.upnp.upnpcoordinator.device_description_find_components') as mock_find:

                mock_load.return_value = MagicMock()
                mock_find.return_value = (MagicMock(), "http://base", "Mfg", "Model", "1.0", "Desc")

                coordinator._update_root_device(lscape, config_lookup, ip_addr, location, devhint, deviceinfo)

                # Verify refresh_description was called
                mock_device.refresh_description.assert_called_once()

                # Verify lock interactions
                # We expect acquire called at start
                # release called in finally

                # And refresh called AFTER release.

                # We can check that using a mock manager
                manager = MagicMock()
                manager.attach_mock(coordinator._coord_lock, 'lock')
                manager.attach_mock(mock_device.refresh_description, 'refresh')

                # Expected order: lock.acquire, ..., lock.release, refresh

                # Note: acquire might be called multiple times if nested (but here likely once)
                # But release MUST be called before refresh.

                call_args_list = manager.mock_calls
                # find index of last release
                last_release_idx = -1
                refresh_idx = -1

                for i, call in enumerate(call_args_list):
                    if call[0] == 'lock.release':
                        last_release_idx = i
                    elif call[0] == 'refresh':
                        refresh_idx = i

                assert refresh_idx > last_release_idx, "refresh_description was called before lock release!"
