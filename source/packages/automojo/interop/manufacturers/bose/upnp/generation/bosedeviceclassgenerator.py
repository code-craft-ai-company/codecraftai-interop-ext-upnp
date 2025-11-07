
from typing import List

from automojo.interop.manufacturers.bose.constants import BOSE_MANUFACTURER_NAME

from automojo.interop.protocols.upnp.generation.upnpdeviceclassgenerator import UpnpDeviceClassGenerator

class BoseDeviceClassGenerator(UpnpDeviceClassGenerator):
    """
        Implementation of the :class:`UpnpDeviceClassGenerator` for Bose manufactured devices.
    """

    @classmethod
    def get_manufacturer(cls) -> str:
        return BOSE_MANUFACTURER_NAME

    @classmethod
    def generate_device_class(description: str) -> str:
        return
    

