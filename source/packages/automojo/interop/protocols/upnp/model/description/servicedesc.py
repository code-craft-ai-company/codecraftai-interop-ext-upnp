
"""
    .. module:: servicedesc
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: servicedesc module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []

from typing import Dict

from xml.etree.ElementTree import fromstring as xml_fromstring

import requests

from automojo.interop.protocols.upnp.constants import UPNP_SERVICE1_NAMESPACE

from automojo.interop.protocols.upnp.model.description.specversion import SpecVersion, process_spec_version
from automojo.interop.protocols.upnp.model.description.serviceaction import ServiceAction, process_action_list
from automojo.interop.protocols.upnp.model.description.servicestatetables import ServiceStateTables, process_state_table

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
            Downloads and processes the service description document.

            :param serv_desc_file: The file path of the service description document to process.
        """
        svcdesc = None

        namespaces = {"": UPNP_SERVICE1_NAMESPACE}

        with open(serv_desc_file, 'r') as sdf:
            xml_content = sdf.read()

            try:
                descDoc = xml_fromstring(xml_content)

                specVersionNode = descDoc.find("specVersion", namespaces=namespaces)
                specVersion = process_spec_version(specVersionNode, namespaces=namespaces)

                serviceStateTableNode = descDoc.find("serviceStateTable", namespaces=namespaces)
                variablesTable, typesTable, eventsTable = process_state_table(serviceStateTableNode, namespaces=namespaces)

                serviceStateTables = ServiceStateTables(variablesTable=variablesTable, typesTable=typesTable, eventsTable=eventsTable)

                actionListNode = descDoc.find("actionList", namespaces=namespaces)
                actionsTable = process_action_list(actionListNode, namespaces=namespaces)

                svcdesc = ServiceDesc(
                    specVersion=specVersion,
                    serviceStateTables=serviceStateTables,
                    actionsTable=actionsTable,
                )
            except Exception:
                print("Service Description Failure: %s" % serv_desc_file)
                raise

        return svcdesc

    @classmethod
    def query_service_description(cls, serv_desc_url: str) -> "ServiceDesc":
        """
            Downloads and processes the service description document.

            :param serv_desc_url: The url of the service description document to process.
        """
        svcdesc = None

        resp: requests.Response = requests.get(serv_desc_url)
        if resp.status_code == 200:
            svcdesc = {}

            namespaces = {"": UPNP_SERVICE1_NAMESPACE}

            try:
                xml_content = resp.text
                descDoc = xml_fromstring(xml_content)

                specVersionNode = descDoc.find("specVersion", namespaces=namespaces)
                specVersion = process_spec_version(specVersionNode, namespaces=namespaces)

                serviceStateTableNode = descDoc.find("serviceStateTable", namespaces=namespaces)
                variablesTable, typesTable, eventsTable = process_state_table(serviceStateTableNode, namespaces=namespaces)

                serviceStateTables = ServiceStateTables(variablesTable=variablesTable, typesTable=typesTable, eventsTable=eventsTable)

                actionListNode = descDoc.find("actionList", namespaces=namespaces)
                actionsTable = process_action_list(actionListNode, namespaces=namespaces)

                svcdesc = ServiceDesc(
                    specVersion=specVersion,
                    serviceStateTables=serviceStateTables,
                    actionsTable=actionsTable,
                )
            except Exception:
                print("Service Description Failure: %s" % serv_desc_url)
                raise

        return svcdesc
