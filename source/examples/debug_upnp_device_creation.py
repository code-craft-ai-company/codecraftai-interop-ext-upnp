
import time

from ccai.presence.wellknown import ConfiguredSuperFactorySingleton

from ccai.interop.protocols.upnp.upnppresence import UpnpPresence
from ccai.interop.protocols.upnp.model.devices.upnpdevicefactory import UpnpDeviceFactory

def main_debug_upnp_discovery():
    """
        Debug the  UPnP discovery process.
    """

    super_factory = ConfiguredSuperFactorySingleton()
    super_factory.add_factory_module("ccai.interop.manufacturers.bose.boseupnpextension")

    scanner = UpnpPresence()
    
    scanner.start()

    # Perform a discovery
    print("")
    print("---------- STARTING DISCOVERY ----------")
    disco_window = scanner.discover_devices()
    disco_window.wait()

    print("")
    print("------------ DEVICES FOUND -------------")
    for usn, device in disco_window.devices_found.items():
        device_evidence = device.evidence
        device_desc = device.description
        print(f"Device: {usn}")
        print(f"  Location: {device_evidence.location}")
        print(f"  Model: {device_desc.modelName}")
        print(f"  Manufacturer: {device_desc.manufacturer}")
        print(f"  Serial Number: {device_desc.serialNumber}")
        print("")
    print("")

    device_factory = UpnpDeviceFactory()

    print("")
    print("------------ CREATING DEVICES -------------")
    for usn, device in disco_window.devices_found.items():
        upnp_device = device_factory.create_root_device_instance(device)

        print(f"Device: {upnp_device.USN}")


if __name__ == "__main__":
    main_debug_upnp_discovery()
