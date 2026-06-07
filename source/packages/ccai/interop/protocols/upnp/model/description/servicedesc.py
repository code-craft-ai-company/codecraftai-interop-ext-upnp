
"""
    .. module:: servicedesc
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: servicedesc module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []

from typing import Dict

from xml.etree.ElementTree import fromstring as xml_fromstring

import requests

from ccai.interop.protocols.upnp.constants import UPNP_SERVICE1_NAMESPACE

from ccai.interop.protocols.upnp.model.description.specversion import SpecVersion, process_spec_version
from ccai.interop.protocols.upnp.model.description.serviceaction import ServiceAction, process_action_list
from ccai.interop.protocols.upnp.model.description.servicestatetables import ServiceStateTables, process_state_table

class ServiceDesc:
    """
        Represents a service description in the UPnP protocol.
    """
    
    def __init__(self, *, specVersion: SpecVersion, serviceStateTables: ServiceStateTables, actionsTable: Dict[str, ServiceAction]):
        """
            Initialize a :class:`ServiceDesc` instance.

            :param specVersion: The UPnP specification version.
            :param serviceStateTables: The service state tables for the service.
            :param actionsTable: Mapping of action names to :class:`ServiceAction` objects.
        """

        self.specVersion = specVersion
        self.serviceStateTables = serviceStateTables
        self.actionsTable = actionsTable
        return

    @classmethod
    def load_service_description(cls, serv_desc_file: str) -> "ServiceDesc":
        """
            Loads a service description from a file and processes the service description content.

            :param serv_desc_file: The file path of the service description document to process.
            
            :raises FileNotFoundError: If the service description file cannot be found.
            :raises ValueError: If the service description content is invalid or cannot be processed.
        """
        try:
            with open(serv_desc_file, 'r') as sdf:
                xml_content = sdf.read()

            svcdesc = cls.process_service_description(xml_content)
        except ValueError as ex:
            # Re-raise ValueError with file context
            errmsg = f"Service Description Failure for file '{serv_desc_file}': {str(ex)}"
            raise ValueError(errmsg) from ex
        except FileNotFoundError:
            errmsg = f"Service description file not found: '{serv_desc_file}'"
            raise FileNotFoundError(errmsg)
        except Exception as ex:
            errmsg = f"Unexpected error loading service description from '{serv_desc_file}': {str(ex)}"
            raise ValueError(errmsg) from ex

        return svcdesc

    @classmethod
    def process_service_description(cls, serv_desc_content: str) -> "ServiceDesc":
        """
            Process the service description content to create a service description.

            :param serv_desc_content: The XML content of a service description.
            
            :raises ValueError: If the service description content is invalid or cannot be processed.
        """
        try:
            descDoc = xml_fromstring(serv_desc_content)

            # Extract namespace from the root element if present
            namespaces = {"": UPNP_SERVICE1_NAMESPACE}  # Default fallback
            doc_node_tag = descDoc.tag
            if doc_node_tag.startswith("{") and "}" in doc_node_tag:
                # Extract namespace from the root element tag (format: {namespace}localname)
                closing_brace_pos = doc_node_tag.find("}")
                if closing_brace_pos > 0:  # Must have opening brace at position 0
                    default_ns = doc_node_tag[1:closing_brace_pos]  # Skip the opening {
                    # Only update namespaces if we extracted a non-empty namespace
                    if default_ns:
                        namespaces = {"": default_ns}
                    # If namespace is empty ({}), keep the default UPNP_SERVICE1_NAMESPACE

            specVersionNode = descDoc.find("specVersion", namespaces=namespaces)
            if specVersionNode is None:
                raise ValueError("Service description missing required 'specVersion' element")
            specVersion = process_spec_version(specVersionNode, namespaces=namespaces)

            serviceStateTableNode = descDoc.find("serviceStateTable", namespaces=namespaces)
            if serviceStateTableNode is not None:
                variablesTable, typesTable, eventsTable = process_state_table(serviceStateTableNode, namespaces=namespaces)
            else:
                # No serviceStateTable element means no state variables are defined for this service
                variablesTable, typesTable, eventsTable = {}, {}, {}

            serviceStateTables = ServiceStateTables(variablesTable=variablesTable, typesTable=typesTable, eventsTable=eventsTable)

            actionListNode = descDoc.find("actionList", namespaces=namespaces)
            if actionListNode is not None:
                actionsTable = process_action_list(actionListNode, namespaces=namespaces)
            else:
                # No actionList element means no actions are defined for this service
                actionsTable = {}

            svc_desc = ServiceDesc(
                specVersion=specVersion,
                serviceStateTables=serviceStateTables,
                actionsTable=actionsTable,
            )
        except Exception as ex:
            errmsg = f"Failed to process service description content: {str(ex)}"
            raise ValueError(errmsg) from ex
            
        return svc_desc

    @classmethod
    def query_service_description(cls, serv_desc_url: str) -> "ServiceDesc":
        """
            Downloads and processes the service description document.

            :param serv_desc_url: The url of the service description document to process.
            
            :raises ValueError: If the service description cannot be downloaded or processed.
            :raises requests.RequestException: If there's a network error during the request.
        """
        try:
            resp: requests.Response = requests.get(serv_desc_url, timeout=30)
            resp.raise_for_status()  # Raises HTTPError for bad HTTP status codes
            
            svcdesc = cls.process_service_description(resp.text)
            
        except requests.exceptions.HTTPError as ex:
            errmsg = f"HTTP error downloading service description from '{serv_desc_url}': {ex.response.status_code} {ex.response.reason}"
            raise ValueError(errmsg) from ex
        except requests.exceptions.RequestException as ex:
            errmsg = f"Network error downloading service description from '{serv_desc_url}': {str(ex)}"
            raise ValueError(errmsg) from ex
        except ValueError as ex:
            # Re-raise ValueError from process_service_description with URL context
            errmsg = f"Service Description Failure for URL '{serv_desc_url}': {str(ex)}"
            raise ValueError(errmsg) from ex
        except Exception as ex:
            errmsg = f"Unexpected error downloading service description from '{serv_desc_url}': {str(ex)}"
            raise ValueError(errmsg) from ex

        return svcdesc
