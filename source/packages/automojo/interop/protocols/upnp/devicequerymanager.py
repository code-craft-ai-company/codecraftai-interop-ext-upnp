
"""
    .. module:: devicequerymanager
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: devicequerymanager module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""


__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import Optional

from automojo.xmodules.xlogging.enhancedloggers import getEnhancedLogger
import os

from http import HTTPStatus
from xml.etree.ElementTree import fromstring as parse_xml_content

import requests

from automojo.interop.protocols.upnp.constants import UPNP_DEVICE1_NAMESPACE
from automojo.interop.protocols.upnp.mapping.devicedetailmapper import DeviceDetailMapper

from automojo.interop.protocols.upnp.model.description.basic1devicedesc import Basic1DeviceDesc
from automojo.interop.protocols.upnp.model.description.servicedesc import ServiceDesc

from automojo.interop.protocols.upnp.wellknown import DeviceDetailMapperRegistrySingleton


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

    def query_device_description(self, query_url: str) -> Optional[Basic1DeviceDesc]:
        """
            Query a UPnP device for its description XML.

            :param query_url: URL from which to request the device description.

            :returns: Parsed :class:`Basic1DeviceDesc` or ``None`` on failure.
        """

        device_desc = None

        try:
            resp: requests.Response = requests.get(query_url, timeout=2)

            if resp.status_code == HTTPStatus.OK:

                try:
                    default_namespaces = {"": UPNP_DEVICE1_NAMESPACE}
                    xml_content = resp.content.decode("utf-8")
                    root_el = parse_xml_content(xml_content)
                    
                    spec_ver, manufacturer = DeviceDetailMapper.read_spec_version_and_manufacturer(root_el, default_namespaces)
                    
                    if spec_ver is not None and manufacturer is not None:

                        mapper = self._mapper_registry.lookup_device_detail_mapper_safe(manufacturer)
                        
                        if mapper is not None:
                            device_desc = mapper.create_root_device_description(root_el, default_namespaces, spec_ver, locationURL=query_url)
                        else:
                            # Log warning about unknown manufacturer but don't fail completely
                            logger.warning(f"No device detail mapper found for manufacturer '{manufacturer}'. Device description parsing skipped.")
                    
                except Exception as parse_err:
                    err_msg = f"Error parsing device description XML: {parse_err}"
                    logger.error(err_msg)

        except Exception as req_err:
            err_msg_lines = [
                f"Error querying device at {query_url}:"
            ]
            err_msg_lines.extend(f"{req_err}".splitlines(False))

            err_msg = os.linesep.join(err_msg_lines)
            logger.error(err_msg)

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
