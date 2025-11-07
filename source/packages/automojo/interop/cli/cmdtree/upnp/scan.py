
from typing import List

import os

import click

from automojo.presence.wellknown import ConfiguredSuperFactorySingleton

from automojo.interop.constants import DEFAULT_INCLUDED_FACTORY_MODULES
from automojo.interop.protocols.upnp.generation.common import (
    normalize_model_name
)

from automojo.interop.protocols.upnp.generation.upnpscan import (
    pull_device_description,
    pull_service_description
)

from automojo.interop.protocols.upnp.upnppresence import UpnpPresence
from automojo.runtime.runtimevariables import AM_RUNTIME_VARIABLES

@click.command("scan")
@click.option("--window-length", default=30.0, help="Specify a scan window length in seconds.")
@click.option("factory_modules", "--factory-module", multiple=True, default=DEFAULT_INCLUDED_FACTORY_MODULES, help="Specify one or more modules to scan for factories.")
def command_am_interop_upnp_scan(window_length: float, factory_modules: List[str]):

    super_factory = ConfiguredSuperFactorySingleton()

    for fmod in factory_modules:
        super_factory.add_factory_module(fmod)
    
    scanner = UpnpPresence()
    
    scanner.start()
    
    # Perform a discovery
    print("")
    print("---------- STARTING DISCOVERY ----------")
    disco_window = scanner.discover_devices(window_length=window_length)
    disco_window.wait()

    device_scan_directory = os.path.join(AM_RUNTIME_VARIABLES.AM_PRESENCE_DIRECTORY, "scan", "upnp", "devices")
    if not os.path.exists(device_scan_directory):
        os.makedirs(device_scan_directory)
    
    service_scan_directory = os.path.join(AM_RUNTIME_VARIABLES.AM_PRESENCE_DIRECTORY, "scan", "upnp", "services")
    if not os.path.exists(service_scan_directory):
        os.makedirs(service_scan_directory)

    print("")
    print("------------ PROCESSING DEVICES AND SERVICES -------------")
    for usn, device in disco_window.devices_found.items():
        device_evidence = device.evidence
        device_desc = device.description

        device_name = normalize_model_name(device_desc.modelName)
        print(f"Processing Device: {usn} ({type(device_desc).__name__})")
        print(f"  Location: {device_evidence.location}")
        print(f"  Model: {device_desc.modelName}")
        print(f"  Manufacturer: {device_desc.manufacturer}")
        print(f"  Serial Number: {device_desc.serialNumber}")
        print("")

        pull_device_description(device_scan_directory, device_name, device_desc)

        for service_evidence in device_desc.serviceList:
            pull_service_description(service_scan_directory, device_desc, service_evidence)

    return

