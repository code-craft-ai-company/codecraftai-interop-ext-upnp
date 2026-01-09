"""
    .. module:: upnpserviceproxy
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module containing the :class:`UpnpServiceProxy` class which is the base class
    all services proxied.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
    
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import Optional, Union, TYPE_CHECKING

from automojo.xmodules.xlogging.enhancedloggers import getEnhancedLogger
import os
import threading
import time
import traceback
import weakref

from xml.etree.ElementTree import Element as XmlElement

from datetime import datetime, timedelta

import requests

from automojo.errors.xtraceback import format_exc_lines
from automojo.waiting.waitmodel import TimeoutContext

from automojo.thisapp.contextpaths import ContextPaths
from automojo.thisapp.wellknown import ThisApplicationSingleton

from automojo.interop.aspects import ActionPattern
from automojo.xmodules.eventing.eventedvariablesink import EventedVariableSink
from automojo.xmodules.eventing.eventedvariable import EventedVariable
from automojo.xmodules.xlogging.monitoredscope import MonitoredScope

from automojo.interop.protocols.upnp.aspects import AspectsUPnP, DEFAULT_UPNP_ASPECTS, DEFAULT_UPNP_CALL_ASPECTS
from automojo.interop.protocols.upnp.soap import SoapProcessor, SOAP_TIMEOUT
from automojo.interop.protocols.upnp.upnperrors import UpnpError
from automojo.interop.protocols.upnp.model.services.upnpdefaultvar import UpnpDefaultVar

from automojo.interop.protocols.upnp.model.description.basic1devicedesc import Basic1DeviceDesc
from automojo.interop.protocols.upnp.model.description.serviceevidence import ServiceEvidence


logger = getEnhancedLogger()

if TYPE_CHECKING:
    from automojo.interop.protocols.upnp.model.devices.upnpdevicebase import UpnpDeviceBase


class UpnpServiceProxy(EventedVariableSink):
    """
        The :class:`UpnpServiceProxy` object provides that base data and functional methods for providing
        inter-operability with a devices Service.  It provides methods for making calls on actions and
        access to methods for making subscriptions.
    """

    SERVICE_ID = None
    SERVICE_TYPE = None

    SERVICE_DEFAULT_VARIABLES = {}

    SERVICE_EVENT_VARIABLES = {}

    def __init__(self):
        """
            Initialize the proxy for interacting with a UPnP service.
        """
        self._service_lock = threading.RLock()

        self._device_ref = None
        self._service_description = None

        self._soap_processor = SoapProcessor()

        self._host = None
        self._baseURL = None

        self._controlURL = None
        self._eventSubURL = None
        self._SCPDURL = None

        self._serviceType = None
        self._serviceId = None

        self._validate_parameter_values = True

        self._default_variables = {}
        self._create_default_variables_from_list()

        self._subscription_id: Optional[str] = None
        self._subscription_expiration: Optional[datetime] = None

        # Initialize the evented variable sink
        super().__init__(self.SERVICE_EVENT_VARIABLES, state_lock=self._service_lock, sink_prefix=self.SERVICE_TYPE, auto_subscribe=True)

        self._logged_events = None
        if self.SERVICE_TYPE is not None:
            this_app = ThisApplicationSingleton()
            ctx = this_app.ctx
            logged_events_by_service = ctx.lookup(ContextPaths.UPNP_LOGGED_EVENTS)
            if logged_events_by_service is not None and self.SERVICE_TYPE in logged_events_by_service:
                self._logged_events = logged_events_by_service[self.SERVICE_TYPE]
        return

    @property
    def baseUrl(self) -> str:
        """
            Returns the base URL for working with a service.
        """
        return self._baseURL

    @property
    def subscription_id(self) -> Optional[str]:
        """
            Returns the active subscription identifier for this service, if any.
        """
        return self._subscription_id

    @property
    def subscription_expiration(self) -> Optional[datetime]:
        """
            Returns the expiration timestamp for the active subscription, if any.
        """
        return self._subscription_expiration

    @property
    def controlURL(self) -> str:
        """
            Returns the control URL that is used making calls on actions on a device service.
        """
        return self._controlURL

    @property
    def device(self) -> Optional["UpnpDeviceBase"]:
        """
            Returns a reference to the parent device of this service, or None if the device
            has been garbage collected.
        """
        return self._device_ref() if self._device_ref is not None else None

    @property
    def eventSubURL(self) -> str:
        """
            Returns the URL that is used to subscribe to events.
        """
        return self._eventSubURL

    @property
    def host(self) -> str:
        """
            The host associated with the parent device.
        """
        return self._host

    @property
    def SCPDURL(self) -> str:
        """
            The URL called to retrieve the service description document.
        """
        return self._SCPDURL

    @property
    def serviceId(self) -> str:
        """
            Returns the service ID
        """
        return self._serviceId

    @property
    def serviceType(self) -> str:
        """
            Returns the service Type ID.
        """
        return self._serviceType

    def call_action(self, action_name: str, arguments: Optional[dict] = None, auth: Optional[dict] = None, headers: Optional[dict] = None, aspects: AspectsUPnP=DEFAULT_UPNP_CALL_ASPECTS):
        """
            Method utilize to make direct calls on a service for action APIs that are not published in a service description.
            
            :param action_name: The action name to make a call on.
            :param arguments: The arguments to pass to the action.
            :param auth: The authentication parameter to use when making a request on the remote action.
            :param headers: The headers to use when making the request on the remote action.
            
            :returns: Returns a dictionary which contains the returned response data.
        """
        rtnval = None

        completion_toctx = TimeoutContext(aspects.completion_timeout, aspects.completion_interval)
        monitor_delay = timedelta(seconds=aspects.monitor_delay)

        retry_logging_interval = aspects.retry_logging_interval
        allowed_error_codes = aspects.allowed_error_codes
        must_connect = aspects.must_connect

        this_thr = threading.current_thread()
        monmsg= "Thread failed to exit monitored scope. thid={} thname={} action_name={}".format(this_thr.ident, this_thr.name, action_name)

        if aspects.action_pattern == ActionPattern.SINGLE_CALL:
            with MonitoredScope("CALL_ACTION-SINGLE_CALL", monmsg, completion_toctx, notify_delay=monitor_delay) as _:
                rtnval = self._proxy_call_action(action_name, arguments=arguments, auth=auth, headers=headers, aspects=aspects)
        
        elif aspects.action_pattern == ActionPattern.SINGLE_CONNECTED_CALL:
            completion_toctx.mark_begin()
            retry_counter = 0
            max_retries = 1000  # Safety limit to prevent infinite loops

            while True:

                with MonitoredScope("CALL_ACTION-SINGLE_CONNECTED_CALL", monmsg, completion_toctx, notify_delay=monitor_delay) as _:
                    try:
                        rtnval = self._proxy_call_action(action_name, arguments=arguments, auth=auth, headers=headers, aspects=aspects)
                        break
                    except UpnpError as upnp_err:
                        # If we got a UpnpError, then the call to the device succeeded from a connectivity perspective.
                        # We log the error and raise an exception immediately (no retries for UPnP protocol errors).
                        err_code = upnp_err.errorCode
                        err_description = upnp_err.errorDescription
                        err_extra = upnp_err.extra
                        if retry_counter % retry_logging_interval == 0:
                            dbg_msg_lines = [
                                "UpnpError: calling '{}' args={} attempt={} errCode={} errDescription={}".format(
                                    action_name, arguments, retry_counter + 1, err_code, err_description),
                                "EXTRA: {}".format(err_extra)
                            ]
                            dbg_msg = os.linesep.join(dbg_msg_lines)
                            logger.debug(dbg_msg)
                        raise
                    except Exception as xcpt:
                        # Connection or other non-UPnP errors - these should be retried
                        err_msg_lines = [
                            "Exception raised by _proxy_call_action."
                        ]
                        err_msg_lines.extend(format_exc_lines())
                        err_msg = os.linesep.join(err_msg_lines)
                        logger.error(err_msg)

                # Safety check to prevent infinite loops
                if retry_counter >= max_retries:
                    logger.error("Maximum retry limit (%d) exceeded for action '%s', aborting", max_retries, action_name)
                    raise RuntimeError(f"Maximum retry limit ({max_retries}) exceeded for action '{action_name}'")

                # Only reach here for non-UPnP exceptions that should be retried
                if completion_toctx.final_attempt:
                    what_for="a single UPNP action call to transact"
                    details = [
                        "ACTION: %s" % action_name
                    ]
                    toerr = completion_toctx.create_timeout(what_for=what_for, detail=details)
                    raise toerr

                elif not completion_toctx.should_continue():
                    completion_toctx.mark_final_attempt()

                time.sleep(completion_toctx.interval)

                retry_counter += 1

        elif aspects.action_pattern == ActionPattern.DO_UNTIL_SUCCESS:
            completion_toctx.mark_begin()
            retry_counter = 0

            while True:

                with MonitoredScope("CALL_ACTION-DO_UNTIL_SUCCESS", monmsg, completion_toctx, notify_delay=monitor_delay) as _:
                    try:
                        rtnval = self._proxy_call_action(action_name, arguments=arguments, auth=auth, headers=headers, aspects=aspects)
                        break
                    except UpnpError as upnp_err:
                        # If we got a UpnpError, then the call to the device succeeded from a connectivity perspective.
                        # If there is an entry for the error in the allowed_upnp_errors, then we just log the error
                        # and allow a retry.
                        err_code = upnp_err.errorCode
                        err_description = upnp_err.errorDescription
                        err_extra = upnp_err.extra
                        if retry_counter % retry_logging_interval == 0:
                            dbg_msg_lines = [
                                "UpnpError: calling '{}' args={} attempt={} errCode={} errDescription={}".format(
                                    action_name, arguments, retry_counter + 1, err_code, err_description),
                                "EXTRA: {}".format(err_extra)
                            ]
                            dbg_msg = os.linesep.join(dbg_msg_lines)
                            logger.debug(dbg_msg)

                        # If we were given a list of allowed error codes and the error code is
                        # not in the list of allowed error codes, re-raise the UpnpError
                        if allowed_error_codes is not None and len(allowed_error_codes) > 0:
                            if err_code not in allowed_error_codes:
                                raise

                    except Exception as xcpt:
                        # Un-Successful calls, always allow a retry for the ActionPattern.DO_UNTIL_SUCCESS pattern.
                        err_msg_lines = [
                            "Exception raised by _proxy_call_action."
                        ]
                        err_msg_lines.extend(format_exc_lines())
                        err_msg = os.linesep.join(err_msg_lines)
                        logger.error(err_msg)

                        # If the must, connect flag was passed with ActionPattern.DO_UNTIL_SUCCESS then
                        # re-raise the exception after logging it.
                        if must_connect:
                            raise

                if completion_toctx.final_attempt:
                    what_for="UPNP action call success"
                    details = [
                        "ACTION: %s" % action_name
                    ]
                    toerr = completion_toctx.create_timeout(what_for=what_for, detail=details)
                    raise toerr

                elif not completion_toctx.should_continue():
                    completion_toctx.mark_final_attempt()

                time.sleep(completion_toctx.interval)

                retry_counter += 1

        elif aspects.action_pattern == ActionPattern.DO_WHILE_SUCCESS:
            completion_toctx.mark_begin()
            retry_counter = 0

            while True:

                with MonitoredScope("CALL_ACTION-DO_WHILE_SUCCESS", monmsg, completion_toctx, notify_delay=monitor_delay) as _:
                    try:
                        rtnval = self._proxy_call_action(action_name, arguments=arguments, auth=auth, headers=headers, aspects=aspects)
                    except UpnpError as upnp_err:
                        # If we got a UpnpError, then the call to the device succeeded from a connectivity perspective.
                        # If there is an entry for the error in the allowed_upnp_errors, then we just log the error
                        # and allow a retry.
                        err_code = upnp_err.errorCode
                        err_description = upnp_err.errorDescription
                        err_extra = upnp_err.extra
                        if retry_counter % retry_logging_interval == 0:
                            dbg_msg_lines = [
                                "UpnpError: calling '{}' args={} attempt={} errCode={} errDescription={}".format(
                                    action_name, arguments, retry_counter + 1, err_code, err_description),
                                "EXTRA: {}".format(err_extra)
                            ]
                            dbg_msg = os.linesep.join(dbg_msg_lines)
                            logger.debug(dbg_msg)
                        break
                    except Exception as xcpt:
                        if not must_connect:
                            break

                if completion_toctx.final_attempt:
                    what_for="UPNP action call failure"
                    details = [
                        "ACTION: %s" % action_name
                    ]
                    toerr = completion_toctx.create_timeout(what_for=what_for, detail=details)
                    raise toerr

                elif not completion_toctx.should_continue():
                    completion_toctx.mark_final_attempt()

                retry_counter += 1
                time.sleep(completion_toctx.interval)

        elif aspects.action_pattern == ActionPattern.DO_UNTIL_CONNECTION_FAILURE:
            completion_toctx.mark_begin()
            retry_counter = 0

            while True:

                with MonitoredScope("CALL_ACTION-DO_UNTIL_CONNECTION_FAILURE", monmsg, completion_toctx, notify_delay=monitor_delay) as _:
                    try:
                        rtnval = self._proxy_call_action(action_name, arguments=arguments, auth=auth, headers=headers, aspects=aspects)
                    except UpnpError as upnp_err:
                        # We only log UPNP errors
                        err_code = upnp_err.errorCode
                        err_description = upnp_err.errorDescription
                        err_extra = upnp_err.extra
                        if retry_counter % retry_logging_interval == 0:
                            dbg_msg_lines = [
                                "UpnpError: calling '{}' args={} attempt={} errCode={} errDescription={}".format(
                                    action_name, arguments, retry_counter + 1, err_code, err_description),
                                "EXTRA: {}".format(err_extra)
                            ]
                            dbg_msg = os.linesep.join(dbg_msg_lines)
                            logger.debug(dbg_msg)
                    except Exception as xcpt:
                        break

                if completion_toctx.final_attempt:
                    what_for="UPNP connection failure"
                    details = [
                        "ACTION: %s" % action_name
                    ]
                    toerr = completion_toctx.create_timeout(what_for=what_for, detail=details)
                    raise toerr

                elif not completion_toctx.should_continue():
                    completion_toctx.mark_final_attempt()

                time.sleep(completion_toctx.interval)

                retry_counter += 1

        else:
            errmsg = "UpnpServiceProxy: Unknown ActionPattern encountered. action_pattern={}".format(aspects.action_pattern)
            raise RuntimeError(errmsg) from None

        return rtnval

    def get_extension_key(self) -> str:
        """
            Returns the extension key for this service proxy.  The extension key is used to identify
            the service proxy in the context of the UPnP extension protocol.
        """
        ekey = self._service_description.get_extension_key()
        return ekey


    def invalidate_subscription(self):
        """
            Called in order to invalidate any active subscriptions.
        """
        
        for _ in self.yield_state_lock():
            self._subscription_id = None
            self._subscription_expiration = None

            for varkey in self._evented_variables:
                varobj = self._evented_variables[varkey]
                varobj.invalidate_subscription()

        return

    def lookup_default_variable(self, varname: str) -> Union[UpnpDefaultVar, None]:
        """
            Looks up the specified default variable.
            
            :param varname: The event name to find the :class:`UpnpDefaultVar` for.
        """
        varobj = None

        varkey = "{}/{}".format(self.SERVICE_TYPE, varname)

        for _ in self.yield_state_lock():
            if varkey in self._default_variables:
                varobj = self._default_variables[varkey]

        return varobj

    def renew_subscription(self):
        """
            Called in order to renew the subscription to the
        """
        sub_id, sub_expires = self.device.subscribe_to_events(self, renew=True)

        if sub_id is not None:
            self._update_subscription_details(sub_id, sub_expires)
        else:
            self._clear_subscription()

        return

    def trigger_auto_subscribe_from_variable(self, varkey: str):
        """
            Called in order to renew the subscription to the
            
            :param varkey: The key for the variable that is triggering the auto-subscription process.
        """
        logger.debug("UpnpServiceProxy subscription renewal for {} triggered from variable {}".format(
            self.SERVICE_ID, varkey
        ))
        self.renew_subscription()
        return

    def _clear_subscription(self):
        """
            Reset subscription tracking information.
        """

        for _ in self.yield_state_lock():
            self._subscription_id = None
            self._subscription_expiration = None
        
        return

    def _update_subscription_details(self, sub_id: Optional[str], sub_expires: Optional[datetime]) -> None:
        """
            Updates the stored subscription information and refreshes the expiration for all event variables.

            :param sub_id: The subscription identifier returned by the event sink.
            :param sub_expires: The expiration timestamp associated with the subscription.
        """

        for _ in self.yield_state_lock():
            self._subscription_id = sub_id
            self._subscription_expiration = sub_expires

            for varobj in self._evented_variables.values():
                varobj._expires = sub_expires

        return

    def _create_default_variable(self, event_name: str, data_type: Optional[str] = None, default: Optional[str] = None, allowed_list: Optional[list] = None, evented: bool=True):
        """
            Creates a default variable and stores a reference to it in the variables table.
            
            :param event_name: The name of the event variable to create.
            :param data_type: The type of the event variable to create.
            :param default: The default value to set the new event variable to.
        """

        variable_key = "{}/{}".format(self.SERVICE_TYPE, event_name)

        service_ref = weakref.ref(self)
        event_var = EventedVariable(variable_key, event_name, service_ref, data_type=data_type, default=default, allowed_list=allowed_list, evented=evented)
        self._default_variables[variable_key] = event_var

        return

    def _create_default_variables_from_list(self):
        """
            Called by the constructor to create the defalut variables listed in the SERVICE_DEFAULT_VARIABLES list on creation
            of the service proxy instance.  We pre-create the event variables because they can have default values and
            we want to maintain consistent reference for the variables for the the life of the service instance.
        """
        for event_name in self.SERVICE_DEFAULT_VARIABLES:
            event_info = self.SERVICE_DEFAULT_VARIABLES[event_name]
            self._create_default_variable(event_name, **event_info)
        return

    def _proxy_link_service_to_device(self, device_ref: weakref.ReferenceType, service_description: ServiceEvidence):
        """
            Called to link a :class:`UpnpServiceProxy` instance to a :class:`UpnpDevice` instance.  The link to the parent
            device allows device users to find the service instance and to link the service proxy with the host it interacts
            with.  It is also utilized by the service proxy to setup event subscription callback routing in order to be
            able to route updates to the :class:`EventedVariable` variables managed by this service proxy.
            
            :param device_ref: A weak reference to the parent device that owns this device.
            :param service_description: The service description for this service.
        """

        device: "UpnpDeviceBase" = device_ref()

        self._device_ref = device_ref
        self._service_description = service_description

        self._host = device.host
        self._baseURL = device.URLBase

        self._controlURL = service_description.controlURL
        self._eventSubURL = service_description.eventSubURL
        self._SCPDURL = service_description.SCPDURL
        self._serviceId = service_description.serviceId
        self._serviceType = service_description.serviceType

        return

    def _proxy_set_call_parameters(self, host: str, baseURL: str, controlURL: str, eventSubURL: str, serviceId: Optional[str] = None, serviceType: Optional[str] = None):
        """
            Sets the call parameters that are used by the service for making calls on a remote service.
            
            :param host: The host of the remote service.
            :param baseURL: The base URL of the host and remote service.
            :param controlURL: The URL use to make calls on service actions.
            :param eventSubURL: The URL to use for creating service event variable subscriptions.
            :param serviceId: The service ID of the service.
            :param serviceType: The service Type ID of the service.
        """
        self._host = host

        if serviceId is None:
            serviceId = self.SERVICE_ID

        if serviceType is None:
            serviceType = self.SERVICE_TYPE

        self._baseURL = baseURL

        self._controlURL = controlURL
        self._eventSubURL = eventSubURL
        self._serviceId = serviceId
        self._serviceType = serviceType
        return

    def _proxy_call_action(self, action_name: str, arguments: Optional[dict] = None, auth: Optional[dict] = None, headers: Optional[dict] = None, aspects: AspectsUPnP=DEFAULT_UPNP_ASPECTS) -> dict:
        """
            Helper method utilize by derived service proxies to make calls on remote service actions.
            
            :param action_name: The action name to make a call on.
            :param arguments: The arguments to pass to the action.
            :param auth: The authentication parameter to use when making a request on the remote action.
            :param headers: The headers to use when making the request on the remote action.
            
            :returns: Returns a dictionary which contains the returned response data.
        """
        # pylint: disable=dangerous-default-value
        
        # Handle None default arguments
        if arguments is None:
            arguments = {}
        if headers is None:
            headers = {}

        call_url = self.controlURL
        if self._baseURL is not None:
            # Properly construct URL by ensuring single separator
            base_url = self._baseURL.rstrip('/')
            control_url = call_url.lstrip('/')
            call_url = f"{base_url}/{control_url}"

        call_body = self._soap_processor.create_request(action_name, arguments, typed=self.serviceType)

        call_headers = {
            'SOAPAction': '"%s#%s"' % (self.serviceType, action_name),
            'Host': self._host,
            'Content-Type': 'text/xml'
        }
        call_headers.update(headers)

        resp: requests.Response = None
        resp_content = None
        status_code = None
        try:
            resp = requests.post(
                call_url,
                call_body,
                headers=call_headers,
                timeout=SOAP_TIMEOUT,
                auth=auth
            )
            resp.raise_for_status()
            # Extract all needed data before closing the response
            resp_content = resp.content.strip()
            status_code = resp.status_code
        except requests.exceptions.HTTPError:
            if resp is not None:
                # Extract status code before any potential response closure
                status_code = resp.status_code
                # If the body of the error response contains XML then it should be a UPnP error,
                # extract the UPnP error information and raise a UpnpError
                content_type = resp.headers.get("content-type", "").lower()
                if content_type.find('text/xml') != -1:
                    # This is a UPnP error response in XML format, parse it
                    try:
                        errorCode, errorDescription = self._soap_processor.parse_response_error_for_upnp(action_name, resp.content, resp.status_code, typed=self.serviceType)
                        raise UpnpError(errorCode, errorDescription, "host=%s action=%s args=%s" % (self._host, action_name, repr(arguments)))
                    except Exception:
                        # If we can't parse the UPnP error, fall back to re-raising the original HTTP error
                        raise
                else:
                    # Not a UPnP XML error, re-raise the original HTTP error
                    raise
        except requests.exceptions.RequestException as req_ex:
            # Handle network-related errors (timeouts, connection errors, etc.)
            logger.error("Network error during UPnP action call: host=%s action=%s error=%s", 
                        self._host, action_name, str(req_ex))
            raise
        except Exception as ex:
            # Handle any other unexpected errors with proper logging
            logger.error("Unexpected error during UPnP action call: host=%s action=%s error=%s", 
                        self._host, action_name, str(ex))
            logger.debug("Full traceback for UPnP action error:", exc_info=True)
            raise
        finally:
            # Ensure the response is properly closed to free up the connection
            if resp is not None:
                resp.close()

        resp_dict = None

        if status_code >= 200 and status_code < 300: # pylint: disable=chained-comparison
            resp_dict = self._soap_processor.parse_response(action_name, resp_content, typed=self.serviceType)
        else:
            errorCode, errorDescription = self._soap_processor.parse_response_error_for_upnp(action_name, resp_content, status_code, typed=self.serviceType)
            raise UpnpError(errorCode, errorDescription, "host=%s action=%s args=%s" % (self._host, action_name, repr(arguments)))

        return resp_dict

    def _update_event_variables(self, sender_ip: str, usn_dev: str, propertyNodeList: XmlElement):
        """
            Helper method called during the processing of a subscription callback in order
            to update all of the event variables for this service instance.
            
            :param propertyNodeList: An XML :class:`Element` object that contains a list
            of child elements for each event variable.
        """

        for _ in self.yield_state_lock():
            
            propNodeOuter : XmlElement
            propNode : XmlElement

            for propNodeOuter in propertyNodeList:
                # Get the first node of the outer property node
                if len(propNodeOuter) == 0:
                    # Skip empty property nodes
                    continue
                propNode = propNodeOuter[0]

                event_name = propNode.tag
                event_value = propNode.text
                if event_value is None:
                    event_value = ""

                if self._logged_events is not None and event_name in self._logged_events:
                        infomsg = "UPNP event update for {}/{}/{} from {}{}    VALUE: {}".format(
                            usn_dev, self.SERVICE_TYPE, event_name, sender_ip, os.linesep, event_value)
                        logger.debug(infomsg)

                try:
                    self.update_event_variable(event_name, event_value, sink_locked=True)
                except KeyError:
                    logger.debug("UpnpServiceProxy: Received value for unknown event host=%s event=%s value=%r" % (sender_ip, event_name, event_value))

        return
