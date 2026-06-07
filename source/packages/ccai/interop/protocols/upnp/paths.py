"""
    .. module:: paths
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module containing constants for different paths utilize by the code generator that are relative to the test framework.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
    
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


import os

from ccai.thisapp.appvardesc import AppVarDesc, VariableSource
from ccai.thisapp.appvaraccessor import AppVarAccessor
from ccai.thisapp.personavariables import PersonaVariables

from ccai.thisapp.wellknown import ThisApplicationSingleton


DIR_UPNP = os.path.dirname(__file__)


def get_home() -> str:
    rtnval = PersonaVariables.AM_PRESENCE_DIR
    return rtnval


class UpnpPathVariablesDesc:
    DIR_UPNP_EXTENSIONS = AppVarDesc(default=os.path.join(DIR_UPNP, "extensions"), source=VariableSource.NONE)

    DIR_UPNP_EXTENSIONS_STANDARD = AppVarDesc(default=os.path.join(DIR_UPNP, "extensions", "standard"), source=VariableSource.NONE)
    DIR_UPNP_EXTENSIONS_STANDARD_EMBEDDEDDEVICES = AppVarDesc(default=os.path.join(DIR_UPNP, "extensions", "standard", "embeddeddevices"), source=VariableSource.NONE)
    DIR_UPNP_EXTENSIONS_STANDARD_ROOTDEVICES = AppVarDesc(default=os.path.join(DIR_UPNP, "extensions", "standard", "rootdevices"), source=VariableSource.NONE)
    DIR_UPNP_EXTENSIONS_STANDARD_SERVICES = AppVarDesc(default=os.path.join(DIR_UPNP, "extensions", "standard", "services"), source=VariableSource.NONE)

    DIR_UPNP_GENERATOR = AppVarDesc(default=os.path.join(DIR_UPNP, "generator"), source=VariableSource.NONE)

    DIR_UPNP_GENERATOR_STANDARD = AppVarDesc(default=os.path.join(DIR_UPNP, "generator", "standard"), source=VariableSource.NONE)
    DIR_UPNP_GENERATOR_STANDARD_EMBEDDEDDEVICES = AppVarDesc(default=os.path.join(DIR_UPNP, "generator", "standard", "embeddeddevices"), source=VariableSource.NONE)
    DIR_UPNP_GENERATOR_STANDARD_ROOTDEVICES = AppVarDesc(default=os.path.join(DIR_UPNP, "generator", "standard", "rootdevices"), source=VariableSource.NONE)
    DIR_UPNP_GENERATOR_STANDARD_SERVICES = AppVarDesc(default=os.path.join(DIR_UPNP, "generator", "standard", "services"), source=VariableSource.NONE)

    DIR_UPNP_EXTENSIONS_INTEGRATION = AppVarDesc(default=lambda: os.path.join(get_home(), "upnp", "extensions", "integration"), source=VariableSource.NONE)
    DIR_UPNP_EXTENSIONS_INTEGRATION_EMBEDDEDDEVICES = AppVarDesc(default=lambda: os.path.join(get_home(), "upnp", "extensions", "integration", "embeddeddevices"), source=VariableSource.NONE)
    DIR_UPNP_EXTENSIONS_INTEGRATION_ROOTDEVICES = AppVarDesc(default=lambda: os.path.join(get_home(), "upnp", "extensions", "integration", "rootdevices"), source=VariableSource.NONE)
    DIR_UPNP_EXTENSIONS_INTEGRATION_SERVICES = AppVarDesc(default=lambda: os.path.join(get_home(), "upnp", "extensions", "integration", "services"), source=VariableSource.NONE)

    DIR_UPNP_SCAN_INTEGRATION = AppVarDesc(default=lambda: os.path.join(get_home(), "upnp", "scan", "integration"), source=VariableSource.NONE)
    DIR_UPNP_SCAN_INTEGRATION_EMBEDDEDDEVICES = AppVarDesc(default=lambda: os.path.join(get_home(), "upnp", "scan", "integration", "embeddeddevices"), source=VariableSource.NONE)
    DIR_UPNP_SCAN_INTEGRATION_ROOTDEVICES = AppVarDesc(default=lambda: os.path.join(get_home(), "upnp", "scan", "integration", "rootdevices"), source=VariableSource.NONE)
    DIR_UPNP_SCAN_INTEGRATION_SERVICES = AppVarDesc(default=lambda: os.path.join(get_home(), "upnp", "scan", "integration", "services"), source=VariableSource.NONE)


class UpnpPathVariables:
    DIR_UPNP_EXTENSIONS = AppVarAccessor(UpnpPathVariablesDesc.DIR_UPNP_EXTENSIONS)

    DIR_UPNP_EXTENSIONS_STANDARD = AppVarAccessor(UpnpPathVariablesDesc.DIR_UPNP_EXTENSIONS_STANDARD)
    DIR_UPNP_EXTENSIONS_STANDARD_EMBEDDEDDEVICES = AppVarAccessor(UpnpPathVariablesDesc.DIR_UPNP_EXTENSIONS_STANDARD_EMBEDDEDDEVICES)
    DIR_UPNP_EXTENSIONS_STANDARD_ROOTDEVICES = AppVarAccessor(UpnpPathVariablesDesc.DIR_UPNP_EXTENSIONS_STANDARD_ROOTDEVICES)
    DIR_UPNP_EXTENSIONS_STANDARD_SERVICES = AppVarAccessor(UpnpPathVariablesDesc.DIR_UPNP_EXTENSIONS_STANDARD_SERVICES)

    DIR_UPNP_GENERATOR = AppVarAccessor(UpnpPathVariablesDesc.DIR_UPNP_GENERATOR)

    DIR_UPNP_GENERATOR_STANDARD = AppVarAccessor(UpnpPathVariablesDesc.DIR_UPNP_GENERATOR_STANDARD)
    DIR_UPNP_GENERATOR_STANDARD_EMBEDDEDDEVICES = AppVarAccessor(UpnpPathVariablesDesc.DIR_UPNP_GENERATOR_STANDARD_EMBEDDEDDEVICES)
    DIR_UPNP_GENERATOR_STANDARD_ROOTDEVICES = AppVarAccessor(UpnpPathVariablesDesc.DIR_UPNP_GENERATOR_STANDARD_ROOTDEVICES)
    DIR_UPNP_GENERATOR_STANDARD_SERVICES = AppVarAccessor(UpnpPathVariablesDesc.DIR_UPNP_GENERATOR_STANDARD_SERVICES)

    DIR_UPNP_EXTENSIONS_INTEGRATION = AppVarAccessor(UpnpPathVariablesDesc.DIR_UPNP_EXTENSIONS_INTEGRATION)
    DIR_UPNP_EXTENSIONS_INTEGRATION_EMBEDDEDDEVICES = AppVarAccessor(UpnpPathVariablesDesc.DIR_UPNP_EXTENSIONS_INTEGRATION_EMBEDDEDDEVICES)
    DIR_UPNP_EXTENSIONS_INTEGRATION_ROOTDEVICES = AppVarAccessor(UpnpPathVariablesDesc.DIR_UPNP_EXTENSIONS_INTEGRATION_ROOTDEVICES)
    DIR_UPNP_EXTENSIONS_INTEGRATION_SERVICES = AppVarAccessor(UpnpPathVariablesDesc.DIR_UPNP_EXTENSIONS_INTEGRATION_SERVICES)

    DIR_UPNP_SCAN_INTEGRATION = AppVarAccessor(UpnpPathVariablesDesc.DIR_UPNP_SCAN_INTEGRATION)
    DIR_UPNP_SCAN_INTEGRATION_EMBEDDEDDEVICES = AppVarAccessor(UpnpPathVariablesDesc.DIR_UPNP_SCAN_INTEGRATION_EMBEDDEDDEVICES)
    DIR_UPNP_SCAN_INTEGRATION_ROOTDEVICES = AppVarAccessor(UpnpPathVariablesDesc.DIR_UPNP_SCAN_INTEGRATION_ROOTDEVICES)
    DIR_UPNP_SCAN_INTEGRATION_SERVICES = AppVarAccessor(UpnpPathVariablesDesc.DIR_UPNP_SCAN_INTEGRATION_SERVICES)


