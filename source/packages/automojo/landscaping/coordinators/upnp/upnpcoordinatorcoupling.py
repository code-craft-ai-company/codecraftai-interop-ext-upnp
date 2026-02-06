"""
    .. module:: automationpodcoupling
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Contains a UpnpCoordinatorIntegration object to use for working with the nodes of a cluster

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import List, Tuple, TYPE_CHECKING

from automojo.errors.exceptions import SemanticError, ConfigurationError

from automojo.thisapp.wellknown import ThisApplicationSingleton
from automojo.thisapp.contextpaths import ContextPaths

from automojo.interop.protocols.upnp.model.upnpdevicehint import UpnpDeviceHint

from automojo.landscaping.coupling.coordinatorcoupling import CoordinatorCoupling

from automojo.landscaping.coordinators.upnp.upnpcoordinator import UpnpCoordinator


# Types imported only for type checking purposes
if TYPE_CHECKING:
    from automojo.landscaping.landscape import Landscape
    from automojo.landscaping.landscapedevice import LandscapeDevice

INTEGRATION_CLASS_NETWORK_UPNP = "network/upnp"

def is_upnp_device_config(device_info):
    """
        Determines if a device configuration represents a UPNP device.

        :param device_info: Device configuration dictionary.

        :returns: ``True`` if the device is configured as a UPNP device.
    """

    is_upnp_dev = False

    dev_type = device_info["deviceType"]
    if dev_type == INTEGRATION_CLASS_NETWORK_UPNP:
        is_upnp_dev = True

    return is_upnp_dev


class UpnpCoordinatorIntegration(CoordinatorCoupling):
    """
        The UpnpCoordinatorIntegration handle the requirement registration for the UPNP coordinator.
    """

    COORDINATOR_TYPE = UpnpCoordinator

    integration_root: str = "apod"
    integration_section: str = "devices"
    integration_leaf: str = "deviceType"
    integration_class: str = INTEGRATION_CLASS_NETWORK_UPNP

    lookup_upnp_device_config = {}
    lookup_upnp_device = {}


    def __init__(self, *args, **kwargs):
        """
            The default contructor for an :class:`UpnpCoordinatorIntegration`.
        """
        super(UpnpCoordinatorIntegration, self).__init__(*args, **kwargs)
        
        # Initialize device pool tracking dictionaries
        self.upnp_devices_pool = {}
        self.upnp_devices_inuse = {}
        
        return

    @classmethod
    def attach_to_environment(cls, landscape: "Landscape"):
        """
            This API is called so that the IntegrationCoupling can process configuration information.  The :class:`IntegrationCoupling`
            will verify that it has a valid environment and configuration to run in.

            :raises ConfigurationError: If UPnP device configuration is invalid.
        """

        cls.landscape = landscape
        cls.lookup_upnp_device_config = {}
        cls.lookup_upnp_device = {}
        layer_config = landscape.layer_configuration

        device_config_list = layer_config.get_device_configs()
        if len(device_config_list) > 0:
            for dev_config in device_config_list:
                if is_upnp_device_config(dev_config):
                    identifier = dev_config.get("hint", "")
                    if len(identifier) == 0:
                        identifier = dev_config.get("USN", "")
                        if len(identifier) == 0:
                            raise ConfigurationError("UPnP device configuration must provide either 'hint' or 'USN' identifier")

                    cls.lookup_upnp_device_config[identifier] = dev_config

            if len(cls.lookup_upnp_device_config) > 0:
                layer_integ = landscape.layer_integration
                layer_integ.register_integration_dependency(cls)
    
        return

    @classmethod
    def collect_resources(cls):
        """
            This API is called so the `IntegrationCoupling` can connect with a resource management
            system and gain access to the resources required for the automation run.

            :raises :class:`akit.exceptions.AKitResourceError`:
        """
        return

    @classmethod
    def create_coordinator(cls, landscape: "Landscape") -> object:
        """
            This API is called so that the landscape can create a coordinator for a given integration role.
        """
        cls.coordinator = UpnpCoordinator(landscape)
        return cls.coordinator

    @classmethod
    def declare_precedence(cls) -> int:
        """
            This API is called so that the IntegrationCoupling can declare an ordinal precedence that should be
            utilized for bringing up its integration state.
        """
        # We need to call the base class, it sets the 'logger' member
        precedence = super(UpnpCoordinatorIntegration, cls).declare_precedence()
        return precedence

    @classmethod
    def diagnostic(cls, label: str, level: int, diag_folder: str):
        """
            The API is called by the :class:`akit.sequencer.Sequencer` object when the automation sequencer is
            building out a diagnostic package at a diagnostic point in the automation sequence.  Example diagnostic
            points are:

            * pre-run
            * post-run

            Each diagnostic package has its own storage location so derived :class:`akit.scope.ScopeCoupling` objects
            can simply write to their specified output folder.

            :param label: The label associated with this diagnostic.
            :param level: The maximum diagnostic level to run dianostics for.
            :param diag_folder: The output folder path where the diagnostic information should be written.
        """

        return

    @classmethod
    def establish_connectivity(cls, allow_missing_devices: bool=False, upnp_recording: bool = False, allow_unknown_devices: bool = False) -> Tuple[List[str], dict]:
        """
            This API is called so the `IntegrationCoupling` can establish connectivity with any compute or storage
            resources.

            :returns: A tuple with a list of error messages for failed connections and dict of connectivity
            reports for devices devices based on the coordinator.
        """
        lscape = cls.landscape
        conn_errors: List[str] = []
        conn_results: dict = {}

        exclude_interfaces = ["lo"]

        this_app = ThisApplicationSingleton()
        context = this_app.context
        runtime_exclude_interfaces = context.lookup(ContextPaths.UPNP_EXCLUDE_INTERFACES)
        if runtime_exclude_interfaces is not None:
            exclude_interfaces = runtime_exclude_interfaces

        lscape = cls.landscape
        layer_integ = lscape.layer_integration
        
        # Create a list of device configs
        device_list: List["LandscapeDevice"] = layer_integ.get_devices()

        if len(device_list) > 0:
            
            for dev in device_list:
                dev_config = dev.device_config
                if is_upnp_device_config(dev_config):
                    identifier = dev_config.get("hint", "")
                    if len(identifier) == 0:
                        identifier = dev_config.get("USN", "")
                        if len(identifier) == 0:
                            raise ConfigurationError("UPnP device configuration must provide either 'hint' or 'USN' identifier")

                    cls.lookup_upnp_device[identifier] = dev

            
            if len(cls.lookup_upnp_device_config) == 0:
                raise SemanticError("we should not have been called if the upnp device config had 0 devices.") from None

            required_devices = None
            if not allow_missing_devices:
                required_devices = [UpnpDeviceHint(identifier) for identifier in cls.lookup_upnp_device_config.keys()]

            if cls.coordinator is None:
                raise SemanticError("UPnP coordinator not initialized.") from None

            found_devices, matching_devices, missing_devices = cls.coordinator.startup_scan(
                query_devices=cls.lookup_upnp_device_config,
                required_devices=required_devices,
                watchlist=None,
                exclude_interfaces=exclude_interfaces,
                upnp_recording=upnp_recording,
                allow_unknown_devices=allow_unknown_devices
            )

            conn_results = {
                "upnp": {
                    "found": found_devices,
                    "matching": matching_devices,
                    "missing": missing_devices
                }
            }

        return (conn_errors, conn_results)

    @classmethod
    def establish_presence(cls) -> Tuple[List[str], dict]:
        """
            This API is called so the `IntegrationCoupling` can establish presence with any compute or storage
            resources.

            :returns: A tuple with a list of error messages for failed connections and dict of connectivity
            reports for devices devices based on the coordinator.
        """
        presence_errors = []
        presence_results = {}
        
        if cls.coordinator is not None:
            cls.coordinator.establish_presence()
            
        return (presence_errors, presence_results)

    def checkout_upnp_device(self, usn):
        """
            Checkout a device from the device pool by USN.
        """
        codev = None

        if usn in self.upnp_devices_pool:
            codev = self.upnp_devices_pool.pop(usn)
            self.upnp_devices_inuse[usn] = codev

        return codev

    def checkin_upnp_device(self, codev):
        """
            Checkin a device to the device pool.
        """
        usn = codev.USN

        if usn in self.upnp_devices_inuse:
            # Remove the device from the in-use pool and put the original device back in the available pool
            self.upnp_devices_inuse.pop(usn)
            self.upnp_devices_pool[usn] = codev

        return

    
