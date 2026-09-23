
from ccai.interop.manufacturers.bose.constants import BOSE_MANUFACTURER_NAME

from ccai.interop.protocols.upnp.generation.upnpdeviceclassgenerator import UpnpDeviceClassGenerator

class BoseDeviceClassGenerator(UpnpDeviceClassGenerator):
    """
        Implementation of the :class:`UpnpDeviceClassGenerator` for Bose manufactured devices.
    """

    @classmethod
    def get_manufacturer(cls) -> str:
        return BOSE_MANUFACTURER_NAME

    @classmethod
    def generate_device_class(cls, description: str) -> str:
        raise NotImplementedError(f"Device class generation is not yet implemented for {cls.__name__}")
    

