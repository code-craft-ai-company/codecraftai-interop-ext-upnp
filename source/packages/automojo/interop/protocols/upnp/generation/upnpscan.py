
import os

import requests


from automojo.interop.protocols.upnp.generation.common import (
    parse_service_type
)
from automojo.interop.protocols.upnp.model.description.basic1devicedesc import Basic1DeviceDesc
from automojo.interop.protocols.upnp.model.description.serviceevidence import ServiceEvidence


def pull_device_description(device_scan_directory: str, device_name: str, device_desc: Basic1DeviceDesc):
    """
        Pulls the device description from a specific device.

        :param device_scan_directory: The device scan root directory to write the device description document to.
        :param device_name: The name of the device being scanned.
        :param device_desc: The device description reported by the UPnP discovery process.
    """
    
    device_ext_dir = os.path.join(device_scan_directory, device_desc.manufacturer)
    if not os.path.exists(device_ext_dir):
        os.makedirs(device_ext_dir)

    device_desc_file = os.path.join(device_ext_dir, f"{device_name}.xml")
    
    location_url = device_desc.locationURL

    resp: requests.Response = requests.get(location_url)
    if resp.status_code == 200:
        desc_content = resp.content.decode("utf-8")
        with open(device_desc_file, 'w+') as ddf:
            ddf.write(desc_content)
    
    return


def pull_service_description(service_scan_directory: str, device_desc: Basic1DeviceDesc, service_evidence: ServiceEvidence):
    """
        Pulls the service description for a specific service from a device.

        :param service_scan_directory: The service scan root directory to write the service description document to.
        :param device_desc: The description of the device being scanned.
        :param service_evidence: The service evidence of the service to scan.
    """
    service_type = service_evidence.serviceType

    service_agency, service_name = parse_service_type(service_type)

    service_dir = os.path.join(service_scan_directory, service_agency)
    if not os.path.exists(service_dir):
        os.makedirs(service_dir)

    service_desc_filename = os.path.join(service_dir, f"{service_name.lower()}.xml")

    if not os.path.exists(service_desc_filename):
        base_url = device_desc.baseURL.rstrip("/")
        service_desc_url = f"{base_url}/{service_evidence.SCPDURL.lstrip('/')}"

        resp: requests.Response = requests.get(service_desc_url)
        if resp.status_code == 200:
            desc_content = resp.content.decode("utf-8")
            with open(service_desc_filename, 'w+') as sdf:
                sdf.write(desc_content)

    return
