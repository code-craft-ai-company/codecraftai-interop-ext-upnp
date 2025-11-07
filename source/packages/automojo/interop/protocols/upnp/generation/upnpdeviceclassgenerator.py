from typing import List

class UpnpDeviceClassGenerator:

    @classmethod
    def get_manufacturer(cls) -> str:
        raise NotImplementedError(f"'get_manufacturer' must be implemented by the '{cls.__name__}' extension")
    
    @classmethod
    def generate_device_class(description: str) -> None:
        return
    
    