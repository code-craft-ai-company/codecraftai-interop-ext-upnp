
"""
    .. module:: aspects
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: aspects module.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""


__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import List, Optional

import logging

from automojo.interop.aspects import (
    Aspects,
    ActionPattern,
    LoggingPattern,
    DEFAULT_COMPLETION_TIMEOUT,
    DEFAULT_COMPLETION_INTERVAL,
    DEFAULT_INACTIVITY_TIMEOUT,
    DEFAULT_INACTIVITY_INTERVAL,
    DEFAULT_MONITOR_DELAY,
    DEFAULT_LOGGING_PATTERN,
    DEFAULT_RETRY_LOGGING_INTERVAL,
    DEFAULT_ALLOWED_ERROR_CODES,
    DEFAULT_MUST_CONNECT
)


UPNP_CALL_COMPLETION_TIMEOUT = 30
UPNP_CALL_COMPLETION_INTERVAL = 5

UPNP_CALL_INACTIVITY_TIMEOUT = 30
UPNP_CALL_INACTIVITY_INTERVAL = 1

class AspectsUPnP:
    """
        Default aspects configuration for UPnP protocol operations.
    """
    def __init__(self, action_pattern: ActionPattern = ActionPattern.SINGLE_CONNECTED_CALL,
                       completion_timeout: float = DEFAULT_COMPLETION_TIMEOUT,
                       completion_interval: float = DEFAULT_COMPLETION_INTERVAL,
                       inactivity_timeout: float = DEFAULT_INACTIVITY_TIMEOUT,
                       inactivity_interval: float = DEFAULT_INACTIVITY_INTERVAL,
                       monitor_delay: float = DEFAULT_MONITOR_DELAY,
                       logging_pattern: LoggingPattern = DEFAULT_LOGGING_PATTERN,
                       retry_logging_interval: int = DEFAULT_RETRY_LOGGING_INTERVAL,
                       allowed_error_codes: Optional[List[int]] = None,
                       must_connect: bool = DEFAULT_MUST_CONNECT,
                       logger: Optional[logging.Logger]=None):
        """
            Construct an :class:`AspectsUPnP` instance with sensible defaults.

            :param action_pattern: The :class:`ActionPattern` used for operations.
            :param completion_timeout: Timeout for operation completion.
            :param completion_interval: Interval between completion checks.
            :param inactivity_timeout: Timeout for inactivity.
            :param inactivity_interval: Interval between inactivity checks.
            :param monitor_delay: Delay before monitoring begins.
            :param logging_pattern: Pattern controlling logging behavior.
            :param retry_logging_interval: Interval between retry log messages.
            :param allowed_error_codes: Error codes that should not abort retries.
            :param must_connect: ``True`` if connection failures should raise.
            :param logger: Optional logger for diagnostics.
        """
        self.action_pattern=action_pattern
        self.completion_timeout=completion_timeout
        self.completion_interval=completion_interval
        self.inactivity_timeout=inactivity_timeout
        self.inactivity_interval=inactivity_interval
        self.monitor_delay=monitor_delay
        self.logging_pattern=logging_pattern
        self.retry_logging_interval=retry_logging_interval
        self.allowed_error_codes=allowed_error_codes if allowed_error_codes is not None else DEFAULT_ALLOWED_ERROR_CODES
        self.must_connect=must_connect
        self.logger=logger
        return

DEFAULT_UPNP_ASPECTS = AspectsUPnP()

DEFAULT_UPNP_CALL_ASPECTS = AspectsUPnP(
    completion_timeout=UPNP_CALL_COMPLETION_TIMEOUT,
    completion_interval=UPNP_CALL_COMPLETION_INTERVAL,
    inactivity_timeout=UPNP_CALL_INACTIVITY_TIMEOUT,
    inactivity_interval=UPNP_CALL_INACTIVITY_INTERVAL)

