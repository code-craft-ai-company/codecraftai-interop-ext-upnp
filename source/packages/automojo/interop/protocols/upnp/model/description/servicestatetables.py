
"""
    .. module:: servicestatetables
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: servicestatetables module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []

from typing import Optional

from xml.etree.ElementTree import Element

def process_state_table(service_state_table_el: Element, namespaces: Optional[dict] = None) -> tuple:
    """
        Parse the ``serviceStateTable`` element of a service description.

        :param service_state_table_el: Element containing the state table.
        :param namespaces: Optional namespace mapping for XML parsing.

        :returns: Tuple of (variablesTable, typesTable, eventsTable) dictionaries.
        
        :raises ValueError: If required XML elements are missing or invalid.
    """
    # pylint: disable=no-self-use
    variablesTable = {}
    typesTable = {}
    eventsTable = {}

    state_variable_el_list = service_state_table_el.findall("stateVariable", namespaces=namespaces)
    for state_variable_el in state_variable_el_list:
        # Get variable name with proper null checking
        nameNode = state_variable_el.find("name", namespaces=namespaces)
        if nameNode is None or nameNode.text is None:
            raise ValueError("State variable missing required 'name' element")
        name = nameNode.text
        
        # Get data type with proper null checking
        dataTypeNode = state_variable_el.find("dataType", namespaces=namespaces)
        if dataTypeNode is None or dataTypeNode.text is None:
            raise ValueError(f"State variable '{name}' missing required 'dataType' element")
        dataType = dataTypeNode.text

        varInfo = { "name": name, "dataType": dataType}
        if name.startswith("A_ARG_TYPE_"):
            typesTable[name] = varInfo
        else:
            variablesTable[name] = varInfo

            sendEvents = "no"
            if "sendEvents" in state_variable_el.attrib:
                sendEvents = state_variable_el.attrib["sendEvents"]

            if sendEvents == "yes":
                eventsTable[name] = varInfo

    return variablesTable, typesTable, eventsTable


class ServiceVariableDesc:
    """
        Represents a state variable in a UPnP service description.
    
        This class is used to represent a state variable in a UPnP service description. It can be extended to include methods for manipulating state variables.
    """
    
    def __init__(self, *, name: str, dataType: str, sendEvents: bool = False):
        """
            Create a :class:`ServiceVariableDesc` instance.
        """

        self.name = name
        self.dataType = dataType
        self.sendEvents = sendEvents
        return
    
    def as_dict(self) -> dict:
        """
            Convert the ServiceVariableDesc object to a dictionary.
        
            :returns: Dictionary representation of the ServiceVariableDesc object.
        """
        rtnval = {
            "name": self.name,
            "dataType": self.dataType,
            "sendEvents": self.sendEvents
        }

        return rtnval
    

class ServiceStateTables:
    """
        Represents the ServiceStateTable in a UPnP service description.
    
        This class is used to manage the state variables of a UPnP service.  It can be extended to include methods for manipulating state variables.
    """
    
    def __init__(self, *, variablesTable=None, typesTable=None, eventsTable=None):
        """
            Initialize tables describing a service's state variables.
        """

        self.variablesTable = variablesTable if variablesTable is not None else {}
        self.typesTable = typesTable if typesTable is not None else {}
        self.eventsTable = eventsTable if eventsTable is not None else {}
        return
