"""
    .. module:: soap
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Contains classes and constants for working with SOAP message processing.
    
    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
    
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from typing import Optional

import enum
import os
import re
import warnings

from xml.etree.ElementTree import Element, SubElement, ParseError
from xml.etree.ElementTree import tostring as xml_tostring
from xml.etree.ElementTree import register_namespace

from defusedxml.ElementTree import fromstring as xml_fromstring_secure


def xml_fromstring(data):
    """
        Securely parse XML, blocking XXE and entity-expansion (billion-laughs /
        quadratic-blowup) attacks via ``defusedxml``.

        SOAP responses and fault bodies are parsed from device-controlled data,
        so they must not be handed to the raw stdlib parser (which, while it
        blocks external entities by default, remains vulnerable to entity-
        expansion denial of service).

        :param data: XML data to parse (bytes or string).

        :returns: The parsed XML Element.
        :raises: ParseError / EntitiesForbidden / DTDForbidden on malicious input.
    """
    element = xml_fromstring_secure(data)
    return element

from ccai.xmodules.xconvert import safe_as_str

from ccai.errors.exceptions import ProtocolError

from ccai.interop.protocols.upnp.upnperrors import UPNP_ERROR_TEST_LOOKUP

NS_SOAP_ENV = "http://schemas.xmlsoap.org/soap/envelope/"
NS_SOAP_ENC = "http://schemas.xmlsoap.org/soap/encoding/"
NS_XSI = "http://www.w3.org/1999/XMLSchema-instance"
NS_XSD = "http://www.w3.org/1999/XMLSchema"

NS_UPNP_CONTROL = "urn:schemas-upnp-org:control-1-0"
NS_UPNP_EVENT = "urn:schemas-upnp-org:event-1-0"

URI_SOAP_ENCODING = "http://schemas.xmlsoap.org/soap/encoding/"

XML_DOCUMENT_DECLARATION = '<?xml version="1.0" encoding="utf-8"?>'

SOAP_TIMEOUT = 60

PYTHON_TO_SOAP_TYPE_MAP = {
    bytes: 'xsd:string',
    str: 'xsd:string',
    int: 'xsd:int',
    float: 'xsd:float',
    bool: 'xsd:boolean'
}

class SOAPError(ProtocolError):
    """
        Error that is raised when a Soap error occurs.
    """


class SOAPProtocolError(ProtocolError):
    """
        Error that is raised when a Soap protocol error occurs.
    """

def find_declared_encoding_style(*elements: Optional[Element]) -> Optional[str]:
    """
        Finds the SOAP ``encodingStyle`` that is in effect for the innermost of the elements.  The elements are
        passed from the innermost to the outermost (for example the response element, the Body and the
        Envelope) and the first one that declares an ``encodingStyle`` wins, which is how the scope of the
        SOAP 1.1 ``encodingStyle`` attribute works.  An attribute without the SOAP envelope namespace is
        accepted as well for non-compliant devices.

        :param elements: The elements to search, from the innermost to the outermost.  ``None`` entries are
                         skipped.

        :returns: The declared ``encodingStyle`` value or ``None`` when none of the elements declares one.
    """
    declared = None

    for element in elements:
        if element is None:
            continue

        declared = element.get(f"{{{NS_SOAP_ENV}}}encodingStyle")
        if declared is None:
            declared = element.get("encodingStyle")

        if declared is not None:
            break

    return declared


def verify_encoding_style(action_name: str, expected_encoding: Optional[str], declared_encoding: Optional[str]):
    """
        Verifies that a SOAP message was serialized with the encoding the processor decodes.  The check is
        lenient for devices that do not declare an ``encodingStyle`` (or declare the zero-length URI, which
        makes no claim) and strict when a device declares encoding rules that do not include the expected
        one, because the message cannot then be decoded with the expected rules.  The ``encodingStyle`` value
        is a space separated list of URIs; the URIs are compared without a trailing '/'.

        :param action_name: The name of the action the message belongs to, for the error message.
        :param expected_encoding: The SOAP encoding URI the processor decodes, ``None`` or empty to skip the check.
        :param declared_encoding: The ``encodingStyle`` declared by the message, ``None`` when it declares none.

        :raises: SOAPProtocolError when the message declares encoding rules that do not include the expected one.
    """

    if expected_encoding is None or len(expected_encoding) == 0:
        return

    if declared_encoding is None:
        return

    declared_uris = declared_encoding.split()
    if len(declared_uris) == 0:
        return

    expected_uri = expected_encoding.rstrip("/")

    matched = False
    for declared_uri in declared_uris:
        if declared_uri.rstrip("/") == expected_uri:
            matched = True
            break

    if not matched:
        errmsg_lines = [
            f"The SOAP message for action '{action_name}' declares an encodingStyle that does not include the expected SOAP encoding.",
            f"EXPECTED: {expected_encoding}",
            f"DECLARED: {declared_encoding}",
            "Pass the 'encoding' the device uses to the SoapProcessor or to the parse method.",
        ]
        errmsg = os.linesep.join(errmsg_lines)
        raise SOAPProtocolError(errmsg)

    return


def warn_envelope_attrib_ignored_for_parsing(method_name: str):
    """
        Warns that the ``envelope_attrib`` parameter of a parse method is deprecated.  The envelope attributes
        (namespace prefix declarations and the envelope ``encodingStyle``) only describe how an envelope is
        built by :meth:`SoapProcessor.create_request` and :meth:`SoapProcessor.create_response`.  A parser
        cannot check them against a response: prefixes are chosen freely by the sender and ElementTree resolves
        and drops the ``xmlns`` declarations while parsing.  The expected ``encodingStyle`` is checked through
        the ``encoding`` parameter instead.

        :param method_name: The name of the parse method that was passed ``envelope_attrib``.
    """
    msg_lines = [
        f"The 'envelope_attrib' parameter of SoapProcessor.{method_name} is deprecated and ignored.",
        "It only applies to building envelopes (create_request/create_response); use 'encoding' to check the",
        "encodingStyle of a response.",
    ]
    msg = " ".join(msg_lines)
    warnings.warn(msg, DeprecationWarning, stacklevel=3)
    return


def remove_extraneous_xml_declarations(xml_str):
    """
        Special method for correcting XML content that has an extra XML declaration.
    """
    if isinstance(xml_str, bytes):
        xml_str = xml_str.decode('utf-8', errors='replace')

    xml_declaration = ''

    # Look for a valid XML declaration at the start of the string (allowing for whitespace)
    # We use regex to be case-insensitive and robust
    match = re.match(r'\s*<\?xml.*?\?>', xml_str, flags=re.I | re.DOTALL)
    if match:
        xml_declaration = match.group(0).strip()

    # Remove all XML declarations from the content
    xml_str = re.sub(r'<\?xml.*?\?>', '', xml_str, flags=re.I | re.DOTALL)

    return xml_declaration + xml_str

class SoapProcessor:
    """
        The Soap processor object stores encoding and decoding settings for processing the Soap messages
        senti to and from a UPNP device.
    """
    def __init__(self, encoding=URI_SOAP_ENCODING, envelope_attrib=None, typed=None):
        """
            :param encoding: URI string describing the SOAP encoding.
            :param envelope_attrib: Optional attributes to apply to the envelope element.
            :param typed: Optional namespace used for typed parameters.
        """

        self._encoding = encoding
        self._envelope_attrib = envelope_attrib
        self._typed = typed
        return

    def create_request(self, action_name: str, arguments: dict, encoding=None, envelope_attrib=None, typed=None):
        """
            Creates a Soap request for a call on the specified action and with the specified arguments.
        """
        register_namespace('', None)

        if encoding is None:
            encoding = self._encoding
        if envelope_attrib is None:
            envelope_attrib = self._envelope_attrib
        if typed is None:
            typed = self._typed

        envelope = Element("s:Envelope")
        if envelope_attrib:
            envelope.attrib.update(envelope_attrib)
        else:
            envelope.attrib.update({'xmlns:s': NS_SOAP_ENV})
            envelope.attrib.update({'s:encodingStyle': encoding})
            # Ensure xmlns:xsd is present if we are going to use xsd: prefix
            envelope.attrib.update({'xmlns:xsd': NS_XSD})
            envelope.attrib.update({'xmlns:xsi': NS_XSI})

        body = SubElement(envelope, "s:Body")

        if typed:
            methElement = SubElement(body, "u:" + action_name)
            methElement.attrib.update({'xmlns:u': typed})
        else:
            methElement = SubElement(body, action_name)

        if arguments:
            for arg_name, arg_val in arguments.items():
                if isinstance(arg_val, enum.Enum):
                    arg_val = arg_val.value

                py_type = type(arg_val)
                
                # Handle None values explicitly
                if arg_val is None:
                    soap_type = 'xsd:string'
                    arg_val = ""
                else:
                    # Get SOAP type with fallback to string for unsupported types
                    soap_type = PYTHON_TO_SOAP_TYPE_MAP.get(py_type, 'xsd:string')

                if soap_type == 'xsd:string':
                    # Convert unsupported types to string representation
                    if py_type not in PYTHON_TO_SOAP_TYPE_MAP:
                        arg_val = str(arg_val)
                    elif isinstance(arg_val, bytes):
                        arg_val = arg_val.decode('utf-8')
                    # else: arg_val is already a string, no conversion needed
                elif soap_type == 'xsd:int' or soap_type == 'xsd:float':
                    arg_val = str(arg_val)
                elif soap_type == 'xsd:boolean':
                    arg_val = "1" if arg_val else "0"

                argElement = SubElement(methElement, arg_name)
                if typed and soap_type:
                    # FIX: Don't use QName in set() for attribute value as ElementTree doesn't serialize it with prefix automatically in all versions/configurations
                    # Instead, simply set the string value with the prefix.
                    # We want xsi:type="xsd:string" (or whatever prefix points to NS_XSD)
                    if ":" in soap_type:
                        argElement.set("xsi:type", soap_type) # Assuming xmlns:xsi is bound
                    else:
                        argElement.set("xsi:type", "xsd:" + soap_type)

                argElement.text = arg_val
        else:
            methElement.text = ""

        envelope_content = xml_tostring(envelope, short_empty_elements=False)
        content = XML_DOCUMENT_DECLARATION + safe_as_str(envelope_content)

        return content

    def create_response(self, action_name: str, arguments: dict, encoding=None, envelope_attrib=None, typed=None):
        """
            Creates a Soap response to the action with the specified arguments.
        """
        register_namespace('', None)

        if encoding is None:
            encoding = self._encoding
        if envelope_attrib is None:
            envelope_attrib = self._envelope_attrib
        if typed is None:
            typed = self._typed

        envelope = Element("s:Envelope")
        if envelope_attrib:
            envelope.attrib.update(envelope_attrib)
        else:
            envelope.attrib.update({'xmlns:s': NS_SOAP_ENV})
            envelope.attrib.update({'s:encodingStyle': encoding})
            # Ensure xmlns:xsd is present if we are going to use xsd: prefix
            envelope.attrib.update({'xmlns:xsd': NS_XSD})
            envelope.attrib.update({'xmlns:xsi': NS_XSI})

        body = SubElement(envelope, "s:Body")

        action_name_tag_name = action_name + "Response"
        methElement = SubElement(body, action_name_tag_name)
        if encoding:
            methElement.set(f"{{{NS_SOAP_ENV}}}encodingStyle", encoding)

        if arguments:
            for arg_name, arg_val in arguments.items():
                # Handle None values explicitly
                if arg_val is None:
                    soap_type = 'xsd:string'
                    arg_val = ""
                else:
                    py_type = type(arg_val)
                    # Get SOAP type with fallback to string for unsupported types
                    soap_type = PYTHON_TO_SOAP_TYPE_MAP.get(py_type, 'xsd:string')

                if soap_type == 'xsd:string':
                    # Convert unsupported types to string representation
                    if arg_val is not None and type(arg_val) not in PYTHON_TO_SOAP_TYPE_MAP:
                        arg_val = str(arg_val)
                    elif isinstance(arg_val, bytes):
                        arg_val = arg_val.decode('utf-8')
                    # else: arg_val is already a string, no conversion needed
                elif soap_type == 'xsd:int' or soap_type == 'xsd:float':
                    arg_val = str(arg_val)
                elif soap_type == 'xsd:boolean':
                    arg_val = "1" if arg_val else "0"

                argElement = SubElement(methElement, arg_name)
                if typed and soap_type:
                    # FIX: Don't use QName in set() for attribute value as ElementTree doesn't serialize it with prefix automatically in all versions/configurations
                    # Instead, simply set the string value with the prefix.
                    # We want xsi:type="xsd:string" (or whatever prefix points to NS_XSD)
                    if ":" in soap_type:
                        argElement.set("xsi:type", soap_type) # Assuming xmlns:xsi is bound
                    else:
                        argElement.set("xsi:type", "xsd:" + soap_type)

                argElement.text = arg_val
        else:
            methElement.text = ""

        envelope_content = xml_tostring(envelope, short_empty_elements=False)
        content = XML_DOCUMENT_DECLARATION + "\n" + safe_as_str(envelope_content)

        return content

    def parse_response(self, action_name, content, encoding=None, envelope_attrib=None, typed=None):
        """
            Parses a response from the server with the given action name and content.

            :param action_name: The name of the action the response belongs to.
            :param content: The XML content of the response.
            :param encoding: The SOAP encoding URI the response is decoded with, defaults to the processor's
                             encoding.  A response that declares an ``encodingStyle`` which does not include it
                             is rejected; a response that declares none is accepted.
            :param envelope_attrib: Deprecated and ignored, the envelope attributes only apply to building
                                    envelopes.  Passing it emits a :class:`DeprecationWarning`.
            :param typed: The service type namespace of the response element, defaults to the processor's.

            :returns: A dictionary of the response arguments.
            :raises: SOAPProtocolError
        """
        register_namespace('', None)

        if envelope_attrib is not None:
            warn_envelope_attrib_ignored_for_parsing("parse_response")

        if encoding is None:
            encoding = self._encoding
        if typed is None:
            typed = self._typed

        try:
            docNode = xml_fromstring(content)
        except ParseError:
            # Try removing any extra XML declarations in case there are more than one.
            # This sometimes happens when a device sends its own XML config files.
            content = remove_extraneous_xml_declarations(content)
            docNode = xml_fromstring(content)
        except ValueError:
            # This can occur when requests returns a str (unicode) but there's also an XML
            # declaration, which lxml doesn't like.
            docNode = xml_fromstring(content.encode('utf8'))

        resp_body = None
        if typed:
            resp_body = docNode.find(".//{%s}%sResponse" % (typed, action_name))
        else:
            resp_body = docNode.find(".//%sResponse" % (action_name,))

        if resp_body is None:
            msg = ('Returned XML did not include an element which matches namespace %r and tag name'
                   ' \'%sResponse\'.' % (typed, action_name))
            try:
                xml_debug = xml_tostring(docNode, short_empty_elements=False).decode('utf-8')
            except UnicodeDecodeError:
                xml_debug = xml_tostring(docNode, short_empty_elements=False).decode('utf-8', errors='replace')
            print(msg + '\n' + xml_debug)
            raise SOAPProtocolError(msg)

        body_node = docNode.find("{%s}Body" % (NS_SOAP_ENV,))
        declared_encoding = find_declared_encoding_style(resp_body, body_node, docNode)
        verify_encoding_style(action_name, encoding, declared_encoding)

        # Sometimes devices return XML strings as their argument values without escaping them with
        # CDATA. This checks to see if the argument has been parsed as XML and un-parses it if so.
        resp_dict = {}
        for arg in resp_body:
            children = list(arg)
            if children:
                # FIX: xml_tostring returns bytes, so join needs to handle decoding or we need to decode bytes
                resp_dict[arg.tag] = "\n".join(safe_as_str(xml_tostring(x)) for x in children)
            else:
                if arg.text is None:
                    resp_dict[arg.tag] = ""
                else:
                    resp_dict[arg.tag] = arg.text

        return resp_dict

    def parse_response_error_for_upnp(self, action_name, content, status_code, extra=None, encoding=None, envelope_attrib=None, typed=None):
        """
            Parse response error for a upnp response.

            :param action_name: The name of the action the error response belongs to.
            :param content: The XML content of the error response.
            :param status_code: The HTTP status code of the error response.
            :param extra: Optional extra text added to the error when the response cannot be processed.
            :param encoding: The SOAP encoding URI the response is decoded with, defaults to the processor's
                             encoding.  A response that declares an ``encodingStyle`` which does not include it
                             is rejected; a response that declares none is accepted.
            :param envelope_attrib: Deprecated and ignored, the envelope attributes only apply to building
                                    envelopes.  Passing it emits a :class:`DeprecationWarning`.
            :param typed: The service type namespace, used to find a Fault placed in it by non-compliant devices.

            :returns: A tuple of the UPnP error code and error description.
            :raises: SOAPProtocolError
        """
        register_namespace('', None)

        if envelope_attrib is not None:
            warn_envelope_attrib_ignored_for_parsing("parse_response_error_for_upnp")

        if encoding is None:
            encoding = self._encoding
        if typed is None:
            typed = self._typed

        try:
            docNode = xml_fromstring(content)
        except ParseError:
            # Try removing any extra XML declarations in case there are more than one.
            # This sometimes happens when a device sends its own XML config files.
            content = remove_extraneous_xml_declarations(content)
            docNode = xml_fromstring(content)
        except ValueError:
            # This can occur when requests returns a str (unicode) but there's also an XML
            # declaration, which lxml doesn't like.
            docNode = xml_fromstring(content.encode('utf8'))

        resp_body = None
        # Try multiple approaches to find the Fault element to handle non-compliant devices
        
        # First, try the correct SOAP envelope namespace
        resp_body = docNode.find(".//{%s}Fault" % (NS_SOAP_ENV,))
        
        # If not found, try without namespace (for non-compliant devices)
        if resp_body is None:
            resp_body = docNode.find(".//Fault")
        
        # If still not found and typed is provided, try with the service namespace 
        # (some devices might incorrectly use this)
        if resp_body is None and typed:
            resp_body = docNode.find(".//{%s}Fault" % (typed,))

        if resp_body is None:
            msg = ('Returned XML did not include a SOAP Fault element. Tried SOAP envelope namespace (%r), '
                   'no namespace, and service namespace (%r).' % (NS_SOAP_ENV, typed))
            try:
                xml_debug = xml_tostring(docNode, short_empty_elements=False).decode('utf-8')
            except UnicodeDecodeError:
                xml_debug = xml_tostring(docNode, short_empty_elements=False).decode('utf-8', errors='replace')
            print(msg + '\n' + xml_debug)
            raise SOAPProtocolError(msg)

        body_node = docNode.find("{%s}Body" % (NS_SOAP_ENV,))
        declared_encoding = find_declared_encoding_style(resp_body, body_node, docNode)
        verify_encoding_style(action_name, encoding, declared_encoding)

        # Lets try to extract the XML response error information
        try:
            faultCodeNode = resp_body.find(".//faultcode")
            if faultCodeNode is None or faultCodeNode.text is None:
                raise SOAPProtocolError("SOAP Fault missing required 'faultcode' element or empty content")
            
            faultStringNode = resp_body.find(".//faultstring")
            if faultStringNode is None or faultStringNode.text is None:
                raise SOAPProtocolError("SOAP Fault missing required 'faultstring' element or empty content")
            
            detail = resp_body.find(".//detail")
            if detail is None:
                raise SOAPProtocolError("SOAP Fault missing required 'detail' element")
                
            # Try multiple approaches to find UPnPError for non-compliant devices
            upnpErrorNode = detail.find(".//{%s}UPnPError" % NS_UPNP_CONTROL)
            if upnpErrorNode is None:
                # Try without namespace for non-compliant devices
                upnpErrorNode = detail.find(".//UPnPError")
            if upnpErrorNode is None:
                raise SOAPProtocolError("SOAP Fault detail missing required 'UPnPError' element")
                
            # Try multiple approaches to find errorCode for non-compliant devices
            errorCodeNode = upnpErrorNode.find(".//{%s}errorCode" % NS_UPNP_CONTROL)
            if errorCodeNode is None:
                errorCodeNode = upnpErrorNode.find(".//errorCode")
            if errorCodeNode is None or errorCodeNode.text is None:
                raise SOAPProtocolError("UPnPError missing required 'errorCode' element")
            try:
                errorCode = int(errorCodeNode.text)
            except ValueError:
                raise SOAPProtocolError(f"UPnPError has invalid 'errorCode' value: '{errorCodeNode.text}'")
            
            # Try multiple approaches to find errorDescription for non-compliant devices
            errorDescriptionNode = upnpErrorNode.find(".//{%s}errorDescription" % NS_UPNP_CONTROL)
            if errorDescriptionNode is None:
                errorDescriptionNode = upnpErrorNode.find(".//errorDescription")
            
            # Use provided errorDescription if available, otherwise use lookup table fallback
            if errorDescriptionNode is not None and errorDescriptionNode.text is not None:
                errorDescription = errorDescriptionNode.text
            else:
                errorDescription = UPNP_ERROR_TEST_LOOKUP.get(errorCode, "Unknown error.")

        except SOAPProtocolError:
            # Re-raise SOAP protocol errors as-is
            raise
        except Exception as xcpt:
            errmsg = "Unable to process xml response: status=%r\n%s" % (status_code, content)
            if extra is not None:
                errmsg += "EXTRA:\n%s" % extra
            raise SOAPProtocolError(errmsg) from xcpt

        return errorCode, errorDescription
