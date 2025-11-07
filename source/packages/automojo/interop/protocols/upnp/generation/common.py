
from typing import Tuple

def normalize_model_name(device_model_name: str):
    """
        Removes un-interesting or problematic characters from the model name.
    """
    norm_model_name = device_model_name.replace(" ", "")
    return  norm_model_name


def parse_device_type(device_type_str: str) -> Tuple[str, str]:
    """
        Parses a device type string and returns the Agency and the Name of the device type.
    """
    scheme, agency, dev_label, device_name = device_type_str.split(":", maxsplit=3)

    if scheme.lower() != "urn":
        errmsg = f"The device string provided '{device_type_str}' is not a urn."
        raise ValueError(errmsg)

    if dev_label.lower() != "device":
        errmsg = f"The device string provided '{device_type_str}' is not a device string."
        raise ValueError(errmsg)

    device_name = device_name.replace(":", "")

    return agency, device_name


def parse_service_type(service_type_str: str) -> Tuple[str, str]:
    """
        Parses a service type string and returns the Agency and the Name of the service type.
    """
    scheme, agency, svc_label, service_name = service_type_str.split(":", maxsplit=3)

    if scheme.lower() != "urn":
        errmsg = f"The service string provided '{service_type_str}' is not a urn."
        raise ValueError(errmsg)

    if svc_label.lower() != "service":
        errmsg = f"The service string provided '{service_type_str}' is not a service string."
        raise ValueError(errmsg)

    service_name = service_name.replace(":", "")

    return agency, service_name

