
from typing import Tuple

def normalize_model_name(device_model_name: str) -> str:
    """
        Removes un-interesting or problematic characters from the model name.
        
        :param device_model_name: The device model name to normalize.
        
        :returns: The normalized model name with spaces removed.
        
        :raises ValueError: If device_model_name is None or empty.
    """
    if device_model_name is None:
        raise ValueError("device_model_name cannot be None")
    
    if not device_model_name.strip():
        raise ValueError("device_model_name cannot be empty")
    
    norm_model_name = device_model_name.replace(" ", "")
    return norm_model_name


def parse_device_type(device_type_str: str) -> Tuple[str, str]:
    """
        Parses a device type string and returns the Agency and the Name of the device type.
        
        :param device_type_str: The device type string to parse (e.g., "urn:schemas-upnp-org:device:MediaRenderer:1").
        
        :returns: A tuple containing the agency and device name.
        
        :raises ValueError: If the device_type_str is not a valid device URN format.
    """
    parts = device_type_str.split(":")
    
    if len(parts) < 5:
        errmsg = f"The device string provided '{device_type_str}' does not have the expected format 'urn:agency:device:name:version'."
        raise ValueError(errmsg)
    
    scheme = parts[0]
    agency = parts[1]
    dev_label = parts[2]
    device_name = parts[3]
    # version = parts[4] (not used in return but validates format)

    if scheme.lower() != "urn":
        errmsg = f"The device string provided '{device_type_str}' is not a urn."
        raise ValueError(errmsg)

    if dev_label.lower() != "device":
        errmsg = f"The device string provided '{device_type_str}' is not a device string."
        raise ValueError(errmsg)

    return agency, device_name


def parse_service_type(service_type_str: str) -> Tuple[str, str]:
    """
        Parses a service type string and returns the Agency and the Name of the service type.
        
        :param service_type_str: The service type string to parse (e.g., "urn:schemas-upnp-org:service:ContentDirectory:1").
        
        :returns: A tuple containing the agency and service name.
        
        :raises ValueError: If the service_type_str is not a valid service URN format.
    """
    parts = service_type_str.split(":")
    
    if len(parts) < 5:
        errmsg = f"The service string provided '{service_type_str}' does not have the expected format 'urn:agency:service:name:version'."
        raise ValueError(errmsg)
    
    scheme = parts[0]
    agency = parts[1]
    svc_label = parts[2]
    service_name = parts[3]
    # version = parts[4] (not used in return but validates format)

    if scheme.lower() != "urn":
        errmsg = f"The service string provided '{service_type_str}' is not a urn."
        raise ValueError(errmsg)

    if svc_label.lower() != "service":
        errmsg = f"The service string provided '{service_type_str}' is not a service string."
        raise ValueError(errmsg)

    return agency, service_name

