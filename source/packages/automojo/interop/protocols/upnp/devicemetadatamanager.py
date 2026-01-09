
from typing import Union

import os

from xml.etree.ElementTree import fromstring as parse_xml_content

from automojo.xmodules.xlogging.enhancedloggers import getEnhancedLogger

from automojo.interop.constants import DIR_AUTOMOJO_INTEROP
from automojo.interop.protocols.upnp.constants import (
    DIR_METADATA,
    DIR_METADATA_DEVICES,
    DIR_METADATA_EMBEDDED_DEVICES,
    DIR_METADATA_SERVICES,
    UPNP_DEVICE1_NAMESPACE
)

from automojo.interop.protocols.upnp.mapping.devicedetailmapper import DeviceDetailMapper
from automojo.interop.protocols.upnp.model.description.basic1devicedesc import Basic1DeviceDesc
from automojo.interop.protocols.upnp.model.description.servicedesc import ServiceDesc
from automojo.interop.protocols.upnp.model.description.serviceevidence import ServiceEvidence

from automojo.interop.protocols.upnp.generation.common import (
    parse_service_type
)

from automojo.interop.protocols.upnp.wellknown import DeviceDetailMapperRegistrySingleton

logger = getEnhancedLogger()


class DeviceMetadataManager:

    def __init__(self, metadata_cache_root: str, update_metadata: bool = False):
        self._metadata_cache_root = metadata_cache_root
        self._metadata_cache_devices = os.path.join(metadata_cache_root, "devices")
        self._metadata_cache_services = os.path.join(metadata_cache_root, "services")

        self._metadata_static_root = DIR_METADATA
        self._metadata_static_devices = DIR_METADATA_DEVICES
        self._metadata_static_embedded_devices = DIR_METADATA_EMBEDDED_DEVICES
        self._metadata_static_services = DIR_METADATA_SERVICES
        
        self._update_metadata = update_metadata

        self._mapper_registry = DeviceDetailMapperRegistrySingleton()
        return


    def load_device_description(self, device_cache_leaf: str) -> Union[Basic1DeviceDesc, None]:
        """
            Load a UPnP device description from an xml description file.

            :param device_cache_leaf: Leaf path of the device description file to load.

            :returns: Parsed :class:`Basic1DeviceDesc`.
        """

        device_desc = None

        desc_filename = os.path.join(self._metadata_static_root, device_cache_leaf)
        if not os.path.exists(desc_filename):
            desc_filename = os.path.join(self._metadata_cache_root, device_cache_leaf)

        # Check if the file exists before attempting to open it
        if not os.path.exists(desc_filename):
            logger.warning(f"Device description file not found: {device_cache_leaf}")
            return None

        try:
            with open(desc_filename, 'r') as ddf:
                desc_content = ddf.read()

                try:
                    default_namespaces = {"": UPNP_DEVICE1_NAMESPACE}
                    root_el = parse_xml_content(desc_content)
                    
                    spec_ver, manufacturer = DeviceDetailMapper.read_spec_version_and_manufacturer(root_el, default_namespaces)
                    
                    if spec_ver is not None and manufacturer is not None:
                        mapper = self._mapper_registry.lookup_device_detail_mapper_safe(manufacturer)
                        
                        if mapper is not None:
                            device_desc = mapper.create_root_device_description(root_el, default_namespaces, spec_ver, locationURL=desc_filename)
                        else:
                            # No specific mapper found for this manufacturer, log and skip
                            logger.warning("No device detail mapper found for manufacturer '%s'. Skipping device description processing.", manufacturer)
                    
                except Exception as parse_err:
                    err_msg = f"Error parsing device description XML: {parse_err}"
                    logger.error(err_msg)

        except (FileNotFoundError, IOError) as file_err:
            err_msg = f"Error reading device description file '{desc_filename}': {file_err}"
            logger.error(err_msg)

        return device_desc
    

    def load_service_description(self, service_evidence: ServiceEvidence) -> Union[ServiceDesc, None]:
        """
            Load a service description from the device service cache.

            :param service_evidence: Service evidence containing the service type information.

            :returns: Parsed :class:`ServiceDesc` or None if not found or invalid.
        """
        service_type = service_evidence.serviceType

        try:
            service_agency, service_name = parse_service_type(service_type)
        except ValueError as parse_err:
            logger.warning(f"Invalid service type format '{service_type}': {parse_err}")
            return None

        service_agency = service_agency.lower()
        service_name = service_name.lower()

        service_desc_filename = None

        # First try the static metadata services directory
        service_dir = os.path.join(self._metadata_static_services, service_agency)
        service_desc_filename = os.path.join(service_dir, f"{service_name}.xml")
        if not os.path.exists(service_desc_filename):
            # Then try the cache services directory
            service_dir = os.path.join(self._metadata_cache_services, service_agency)
            service_desc_filename = os.path.join(service_dir, f"{service_name}.xml")

        desc_content = None

        if os.path.exists(service_desc_filename):
            try:
                desc_content = ServiceDesc.load_service_description(service_desc_filename)
            except (ValueError, FileNotFoundError) as load_err:
                logger.error(f"Error loading service description from '{service_desc_filename}': {load_err}")
                return None
        else:
            logger.warning(f"Service description file not found: {service_desc_filename}")

        return desc_content