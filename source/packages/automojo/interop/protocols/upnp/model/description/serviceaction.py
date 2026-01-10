
"""
    .. module:: serviceaction
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: serviceaction module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []

from typing import Dict, Optional

from xml.etree.ElementTree import Element

def process_action_list(actionListNode: Element, namespaces: Optional[dict] = None) -> Dict[str, dict]:
    """
        Processes the node action list and creates a dictionary of the actions supported by the service.

        :param actionListNode: The parent node for all the action list node.
        :param namespaces: A dictionary of namespaces to use when processing the XML.
        
        :returns: Dictionary mapping action names to action information dictionaries.
        
        :raises ValueError: If required XML elements are missing or invalid.
    """
    # pylint: disable=no-self-use
    actionTable = {}

    actionNodeList = actionListNode.findall("action", namespaces=namespaces)
    for actionNode in actionNodeList:
        # Get action name with proper null checking
        actionNameNode = actionNode.find("name", namespaces=namespaces)
        if actionNameNode is None or actionNameNode.text is None:
            raise ValueError("Action missing required 'name' element")
        actionName = actionNameNode.text
        
        actionArgs = {}

        argumentListNode = actionNode.find("argumentList", namespaces=namespaces)
        if argumentListNode is not None:
            argumentNodeList = argumentListNode.findall("argument", namespaces=namespaces)
            for argumentNode in argumentNodeList:
                # Get argument name with proper null checking
                argNameNode = argumentNode.find("name", namespaces=namespaces)
                if argNameNode is None or argNameNode.text is None:
                    raise ValueError(f"Argument in action '{actionName}' missing required 'name' element")
                argName = argNameNode.text
                
                # Get argument direction with proper null checking
                argDirectionNode = argumentNode.find("direction", namespaces=namespaces)
                if argDirectionNode is None or argDirectionNode.text is None:
                    raise ValueError(f"Argument '{argName}' in action '{actionName}' missing required 'direction' element")
                argDirection = argDirectionNode.text.strip().lower()
                
                # Validate direction is a valid UPnP direction
                if argDirection not in ("in", "out"):
                    raise ValueError(f"Argument '{argName}' in action '{actionName}' has invalid direction '{argDirectionNode.text}'. Must be 'in' or 'out'.")

                argRelStateVar = None
                argRelStateNode = argumentNode.find("relatedStateVariable", namespaces=namespaces)
                if argRelStateNode is not None and argRelStateNode.text is not None:
                    argRelStateVar = argRelStateNode.text.strip()
                    # If the text is empty after stripping, treat as None
                    if not argRelStateVar:
                        argRelStateVar = None

                actionArgs[argName] = {
                    "name": argName,
                    "direction": argDirection,
                    "relatedStateVariable": argRelStateVar
                    }

        actionTable[actionName] = {
                "name": actionName,
                "arguments" : actionArgs
            }

    return actionTable

class ServiceAction:
    """
        Represents a list of actions for a UPnP service.
        This class is used to manage the actions that can be performed on a UPnP service.
    """

    def __init__(self, actions=None):
        """
            Initializes the ServiceActionList with an optional list of actions.

            :param actions: A list of action names (optional).
        """
        self.actions = actions if actions is not None else []

    
