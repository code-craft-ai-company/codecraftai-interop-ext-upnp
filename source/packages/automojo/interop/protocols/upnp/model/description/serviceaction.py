
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

def process_action_list(actionListNode: Element, namespaces: Optional[dict] = None) -> Dict[str, "ServiceAction"]:
    """
        Processes the node action list and creates a dictionary of the actions supported by the service.

        :param actionListNode: The parent node for all the action list node.
        :param namespaces: A dictionary of namespaces to use when processing the XML.
    """
    # pylint: disable=no-self-use
    actionTable = {}

    actionNodeList = actionListNode.findall("action", namespaces=namespaces)
    for actionNode in actionNodeList:
        actionName = actionNode.find("name", namespaces=namespaces).text
        actionArgs = {}

        argumentListNode = actionNode.find("argumentList", namespaces=namespaces)
        if argumentListNode is not None:
            argumentNodeList = argumentListNode.findall("argument", namespaces=namespaces)
            for argumentNode in argumentNodeList:
                argName = argumentNode.find("name", namespaces=namespaces).text
                argDirection = argumentNode.find("direction", namespaces=namespaces).text

                argRelStateVar = None
                argRelStateNode = argumentNode.find("relatedStateVariable", namespaces=namespaces)
                if argRelStateNode is not None:
                    argRelStateVar = argRelStateNode.text

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

    
