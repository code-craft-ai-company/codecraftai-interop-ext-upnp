
import time


from ccai.presence.wellknown import ConfiguredSuperFactorySingleton

from ccai.interop.protocols.upnp.upnppresence import UpnpPresence

def main_debug_upnp_discovery():
    """
        Debug the  UPnP discovery process.
    """

    super_factory = ConfiguredSuperFactorySingleton()
    super_factory.add_factory_module("ccai.interop.manufacturers.bose.boseupnpextension")

    scanner = UpnpPresence()
    
    scanner.start()

    last_discovery = 0
    last_report = 0

    while True:

        try:
            now = time.time()

            discovery_interval = now - last_discovery
            if discovery_interval > 120:
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

                last_discovery = time.time()

            report_interval = now - last_report
            if report_interval > 240:
                active_devices = scanner.active_devices

                if len(active_devices) > 0:            
                    print("")
                    print("------------- ACTIVE DEVICES -------------")
                    for di, usn in enumerate(active_devices):
                        print(f"{di + 1}: {usn}")
                    print("")

                last_report = time.time()

        except OSError as err:
            # Keep the debug discovery loop running across transient network errors, but report them.
            print(f"OSError during discovery loop: {err}")

        print("Tick")
        time.sleep(5)
        print("Tock")
        time.sleep(5)


if __name__ == "__main__":
    main_debug_upnp_discovery()
