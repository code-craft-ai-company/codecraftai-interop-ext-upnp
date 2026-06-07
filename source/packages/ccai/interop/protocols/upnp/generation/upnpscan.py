
import os

import requests


from ccai.interop.protocols.upnp.generation.common import (
    parse_service_type
)
from ccai.interop.protocols.upnp.model.description.basic1devicedesc import Basic1DeviceDesc
from ccai.interop.protocols.upnp.model.description.serviceevidence import ServiceEvidence


def pull_device_description(device_scan_directory: str, device_name: str, device_desc: Basic1DeviceDesc):
    """
        Pulls the device description from a specific device.

        :param device_scan_directory: The device scan root directory to write the device description document to.
        :param device_name: The name of the device being scanned.
        :param device_desc: The device description reported by the UPnP discovery process.
    """
    
    # Create directory structure first - fail fast if this cannot be done
    device_ext_dir = os.path.join(device_scan_directory, device_desc.manufacturer)
    if not os.path.exists(device_ext_dir):
        try:
            os.makedirs(device_ext_dir)
        except (IOError, OSError) as ex:
            raise RuntimeError(f"Failed to create device scan directory '{device_ext_dir}': {ex}")
    
    try:

        device_desc_file = os.path.join(device_ext_dir, f"{device_name}.xml")
        
        location_url = device_desc.locationURL

        resp: requests.Response = requests.get(location_url, timeout=30)
        resp.raise_for_status()  # Raises HTTPError for bad HTTP status codes
        
        try:
            desc_content = resp.content.decode("utf-8")
        except UnicodeDecodeError as ex:
            print(f"Warning: Failed to decode device description content as UTF-8 for {device_name}: {ex}")
            return
            
        with open(device_desc_file, 'w+') as ddf:
            ddf.write(desc_content)
            
    except requests.exceptions.RequestException as ex:
        print(f"Warning: Failed to fetch device description for {device_name} from {location_url}: {ex}")
    except (IOError, OSError) as ex:
        print(f"Warning: Failed to write device description file for {device_name}: {ex}")
    except Exception as ex:
        print(f"Warning: Unexpected error pulling device description for {device_name}: {ex}")
    
    return


def pull_service_description(service_scan_directory: str, device_desc: Basic1DeviceDesc, service_evidence: ServiceEvidence):
    """
        Pulls the service description for a specific service from a device.

        :param service_scan_directory: The service scan root directory to write the service description document to.
        :param device_desc: The description of the device being scanned.
        :param service_evidence: The service evidence of the service to scan.
    """
    service_type = service_evidence.serviceType

    try:
        service_agency, service_name = parse_service_type(service_type)
    except ValueError as parse_err:
        print(f"Warning: Failed to parse service type '{service_type}': {parse_err}")
        return
    
    # Create directory structure first - fail fast if this cannot be done
    service_dir = os.path.join(service_scan_directory, service_agency)
    if not os.path.exists(service_dir):
        try:
            os.makedirs(service_dir)
        except (IOError, OSError) as ex:
            raise RuntimeError(f"Failed to create service scan directory '{service_dir}': {ex}")
    
    # Initialize service_desc_url to avoid NameError in exception handlers
    service_desc_url = "unknown"

    try:

        service_desc_filename = os.path.join(service_dir, f"{service_name.lower()}.xml")

        if not os.path.exists(service_desc_filename):
            base_url = device_desc.baseURL
            if base_url is None:
                print(f"Warning: Device {device_desc.friendlyName} has no baseURL, skipping service description for {service_name}")
                return
            
            scpd_url = service_evidence.SCPDURL
            
            # Validate SCPDURL is not None or empty
            if not scpd_url:
                print(f"Warning: Service {service_name} has no SCPDURL, skipping service description")
                return
            
            # Check if SCPDURL is already an absolute URL
            if scpd_url.startswith(('http://', 'https://')):
                service_desc_url = scpd_url
            else:
                # Construct relative URL
                base_url = base_url.rstrip("/")
                
                # Handle root path case - if scpd_url is just "/" or becomes empty after lstrip
                if scpd_url == "/" or scpd_url.strip("/") == "":
                    service_desc_url = f"{base_url}/"
                else:
                    scpd_url_clean = scpd_url.lstrip('/')
                    service_desc_url = f"{base_url}/{scpd_url_clean}"

            resp: requests.Response = requests.get(service_desc_url, timeout=30)
            resp.raise_for_status()  # Raises HTTPError for bad HTTP status codes
            
            try:
                desc_content = resp.content.decode("utf-8")
            except UnicodeDecodeError as ex:
                print(f"Warning: Failed to decode service description content as UTF-8 for {service_name}: {ex}")
                return
                
            with open(service_desc_filename, 'w+') as sdf:
                sdf.write(desc_content)
                
    except requests.exceptions.RequestException as ex:
        print(f"Warning: Failed to fetch service description for {service_name} from {service_desc_url}: {ex}")
    except (IOError, OSError) as ex:
        print(f"Warning: Failed to write service description file for {service_name}: {ex}")
    except Exception as ex:
        print(f"Warning: Unexpected error pulling service description for {service_name}: {ex}")

    return
