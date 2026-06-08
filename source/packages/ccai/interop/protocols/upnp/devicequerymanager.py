
"""
    .. module:: devicequerymanager
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: devicequerymanager module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""


__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from typing import Optional

from ccai.xmodules.xlogging.enhancedloggers import getEnhancedLogger
import os

from http import HTTPStatus
from xml.etree.ElementTree import fromstring as parse_xml_content

import requests

from ccai.errors.raising import raise_for_http_status
from ccai.interop.protocols.upnp.constants import UPNP_DEVICE1_NAMESPACE
from ccai.interop.protocols.upnp.mapping.devicedetailmapper import DeviceDetailMapper

from ccai.interop.protocols.upnp.model.description.basic1devicedesc import Basic1DeviceDesc
from ccai.interop.protocols.upnp.model.description.servicedesc import ServiceDesc

from ccai.interop.protocols.upnp.wellknown import DeviceDetailMapperRegistrySingleton


logger = getEnhancedLogger()


class DeviceQueryManager:
    """
        The :class:`DeviceQueryManager` is a class that manages the querying of device details from UPnP devices.  It is used
        by the :class:`UpnpSearchWindow`to query devices for thier device descriptions in order to provide the additional information
        needed to combine the :class:`UpnpDeviceEvidence` and UpnpDeviceDescription into a :class:`UpnpDeviceDetail` object.
    """

    def __init__(self):
        """
            Initialize the query manager and cache the mapper registry.
        """
        self._mapper_registry = DeviceDetailMapperRegistrySingleton()
        return

    def query_device_description(self, query_url: str, timeout: float = 30.0) -> Optional[Basic1DeviceDesc]:
        """
            Query a UPnP device for its description XML.

            :param query_url: URL from which to request the device description.
            :param timeout: Timeout in seconds for the HTTP request (default: 30.0).

            :returns: Parsed :class:`Basic1DeviceDesc` or ``None`` on failure.
        """

        device_desc = None
        resp = None

        try:
            resp = requests.get(query_url, timeout=timeout)
            
            # Check for HTTP errors and handle them appropriately
            try:
                ctxmsg = f"While querying device description from {query_url}"
                raise_for_http_status(resp.status_code, resp.content, ctxmsg)
            except Exception as http_err:
                logger.warning(f"HTTP error {resp.status_code} when querying device description from {query_url}: {http_err}")
                return None

            try:
                default_namespaces = {"": UPNP_DEVICE1_NAMESPACE}
                # Pass content as bytes to allow ElementTree to handle encoding from XML declaration
                root_el = parse_xml_content(resp.content)
                
                spec_ver, manufacturer = DeviceDetailMapper.read_spec_version_and_manufacturer(root_el, default_namespaces)
                
                if spec_ver is None or manufacturer is None:
                    logger.warning(f"Failed to extract spec version or manufacturer from device description at {query_url}")
                    return None

                mapper = self._mapper_registry.lookup_device_detail_mapper_safe(manufacturer)
                
                if mapper is None:
                    # Log warning about unknown manufacturer but don't fail completely
                    logger.warning(f"No device detail mapper found for manufacturer '{manufacturer}'. Device description parsing skipped.")
                    return None
                
                # Create the device description using the appropriate mapper
                device_desc = mapper.create_root_device_description(root_el, default_namespaces, spec_ver, locationURL=query_url)
                
            except Exception as parse_err:
                err_msg = f"Error parsing device description XML from {query_url}: {parse_err}"
                logger.error(err_msg)

        except requests.exceptions.RequestException as req_err:
            err_msg = f"Network error querying device at {query_url}: {req_err}"
            logger.error(err_msg)
        except Exception as general_err:
            # Handle any other unexpected errors (but not HTTP errors which are handled above)
            err_msg = f"Unexpected error querying device description from {query_url}: {general_err}"
            logger.error(err_msg)
        finally:
            # Always close the response to prevent resource leaks
            if resp is not None:
                try:
                    resp.close()
                except Exception:
                    pass  # Ignore errors when closing response

        return device_desc
    
    def query_service_description(self, query_url: str) -> Optional[ServiceDesc]:
        """
            Queries the service description from the given service URL.

            :param query_url: The URL of the service to query.

            :returns: Parsed :class:`ServiceDesc` or ``None`` if the query fails.
        """
        service_desc = None

        try:
            service_desc = ServiceDesc.query_service_description(query_url)
        except Exception as query_err:
            err_msg_lines = [
                f"Error querying service description at {query_url}:"
            ]
            err_msg_lines.extend(f"{query_err}".splitlines(False))

            err_msg = os.linesep.join(err_msg_lines)
            logger.error(err_msg)

        return service_desc
