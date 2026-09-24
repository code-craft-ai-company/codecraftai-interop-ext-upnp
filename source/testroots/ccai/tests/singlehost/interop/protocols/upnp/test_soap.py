"""
    .. module:: test_soap
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Test module for SOAP functionality.
    
    .. moduleauthor:: CodeCraftX <automation@mojo.com>
"""

import warnings

from ccai import testbase

from ccai.interop.protocols.upnp.soap import (
    NS_SOAP_ENV,
    SOAPProtocolError,
    SoapProcessor,
    URI_SOAP_ENCODING,
    remove_extraneous_xml_declarations,
)


SERVICE_TYPE = "urn:schemas-upnp-org:service:RenderingControl:1"
OTHER_ENCODING = "http://example.com/other-encoding"


def create_action_response(envelope_encoding_attr: str = f' s:encodingStyle="{URI_SOAP_ENCODING}"',
                           response_encoding_attr: str = "") -> bytes:
    """
        Creates the bytes of a 'GetVolume' action response.

        :param envelope_encoding_attr: The encodingStyle attribute text placed on the Envelope.
        :param response_encoding_attr: The encodingStyle attribute text placed on the response element.

        :returns: The response content.
    """
    content = (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<s:Envelope xmlns:s="{NS_SOAP_ENV}"{envelope_encoding_attr}>'
        '<s:Body>'
        f'<u:GetVolumeResponse xmlns:u="{SERVICE_TYPE}"{response_encoding_attr}>'
        '<CurrentVolume>42</CurrentVolume>'
        '</u:GetVolumeResponse>'
        '</s:Body>'
        '</s:Envelope>'
    )
    content_bytes = content.encode("utf-8")
    return content_bytes


def create_fault_response(envelope_encoding_attr: str = f' s:encodingStyle="{URI_SOAP_ENCODING}"') -> bytes:
    """
        Creates the bytes of a UPnP fault response for error code 402.

        :param envelope_encoding_attr: The encodingStyle attribute text placed on the Envelope.

        :returns: The response content.
    """
    content = (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<s:Envelope xmlns:s="{NS_SOAP_ENV}"{envelope_encoding_attr}>'
        '<s:Body>'
        '<s:Fault>'
        '<faultcode>s:Client</faultcode>'
        '<faultstring>UPnPError</faultstring>'
        '<detail>'
        '<UPnPError xmlns="urn:schemas-upnp-org:control-1-0">'
        '<errorCode>402</errorCode>'
        '<errorDescription>Invalid Args</errorDescription>'
        '</UPnPError>'
        '</detail>'
        '</s:Fault>'
        '</s:Body>'
        '</s:Envelope>'
    )
    content_bytes = content.encode("utf-8")
    return content_bytes


def test_remove_extraneous_xml_declarations_normal_case():
    """
        Test that normal XML with proper declaration is handled correctly.
    """
    xml_input = '<?xml version="1.0" encoding="UTF-8"?><root><element>content</element></root>'
    expected = '<?xml version="1.0" encoding="UTF-8"?><root><element>content</element></root>'
    
    result = remove_extraneous_xml_declarations(xml_input)
    testbase.assert_equal(result, expected)
    return


def test_remove_extraneous_xml_declarations_multiple_declarations():
    """
        Test that multiple XML declarations are properly cleaned up.
    """
    xml_input = '<?xml version="1.0"?><?xml version="1.0" encoding="UTF-8"?><root><element>content</element></root>'
    expected = '<?xml version="1.0"?><root><element>content</element></root>'
    
    result = remove_extraneous_xml_declarations(xml_input)
    testbase.assert_equal(result, expected)
    return


def test_remove_extraneous_xml_declarations_no_declaration():
    """
        Test that XML without declaration is handled correctly.
    """
    xml_input = '<root><element>content</element></root>'
    expected = '<root><element>content</element></root>'
    
    result = remove_extraneous_xml_declarations(xml_input)
    testbase.assert_equal(result, expected)
    return


def test_remove_extraneous_xml_declarations_malformed_declaration():
    """
        Test that malformed XML declaration (missing closing ?>) is handled gracefully.
        This tests the bug fix for unsafe string splitting.
    """
    xml_input = '<?xml version="1.0" encoding="UTF-8"<root><element>content</element></root>'
    # When malformed, the regex still removes any <?xml...?> patterns, leaving just the content
    expected = '<?xml version="1.0" encoding="UTF-8"<root><element>content</element></root>'
    
    result = remove_extraneous_xml_declarations(xml_input)
    testbase.assert_equal(result, expected)
    return


def test_remove_extraneous_xml_declarations_empty_string():
    """
        Test that empty string is handled correctly.
    """
    xml_input = ''
    expected = ''
    
    result = remove_extraneous_xml_declarations(xml_input)
    testbase.assert_equal(result, expected)
    return


def test_remove_extraneous_xml_declarations_only_declaration():
    """
        Test that string with only XML declaration is handled correctly.
    """
    xml_input = '<?xml version="1.0" encoding="UTF-8"?>'
    expected = '<?xml version="1.0" encoding="UTF-8"?>'
    
    result = remove_extraneous_xml_declarations(xml_input)
    testbase.assert_equal(result, expected)
    return


def test_remove_extraneous_xml_declarations_malformed_only_declaration():
    """
        Test that string with only malformed XML declaration is handled correctly.
    """
    xml_input = '<?xml version="1.0" encoding="UTF-8"'
    # When malformed, no split occurs, so original string is preserved
    expected = '<?xml version="1.0" encoding="UTF-8"'
    
    result = remove_extraneous_xml_declarations(xml_input)
    testbase.assert_equal(result, expected)
    return

def test_parse_response_accepts_the_expected_encoding_style():
    """
        A response that declares the SOAP encoding the processor decodes is parsed.
    """
    processor = SoapProcessor()
    content = create_action_response()

    resp_dict = processor.parse_response("GetVolume", content, typed=SERVICE_TYPE)

    testbase.assert_equal(resp_dict, {"CurrentVolume": "42"})
    return


def test_parse_response_accepts_a_response_without_an_encoding_style():
    """
        Devices that do not declare an encodingStyle (or declare the zero-length URI, which makes no claim)
        are still accepted.
    """
    processor = SoapProcessor()

    for envelope_attr in ["", ' s:encodingStyle=""']:
        content = create_action_response(envelope_encoding_attr=envelope_attr)
        resp_dict = processor.parse_response("GetVolume", content, typed=SERVICE_TYPE)
        testbase.assert_equal(resp_dict, {"CurrentVolume": "42"})

    return


def test_parse_response_accepts_an_encoding_style_list_without_trailing_slash():
    """
        The encodingStyle is a space separated list of URIs, and the URIs are compared without a trailing '/'.
    """
    processor = SoapProcessor()
    declared = f"{OTHER_ENCODING} {URI_SOAP_ENCODING.rstrip('/')}"
    content = create_action_response(envelope_encoding_attr=f' s:encodingStyle="{declared}"')

    resp_dict = processor.parse_response("GetVolume", content, typed=SERVICE_TYPE)

    testbase.assert_equal(resp_dict, {"CurrentVolume": "42"})
    return


def test_parse_response_rejects_a_mismatched_encoding_style():
    """
        A response that declares encoding rules which do not include the processor's encoding cannot be
        decoded with that encoding and raises a SOAPProtocolError naming both encodings.
    """
    processor = SoapProcessor()
    content = create_action_response(envelope_encoding_attr=f' s:encodingStyle="{OTHER_ENCODING}"')

    raised = None
    try:
        processor.parse_response("GetVolume", content, typed=SERVICE_TYPE)
    except SOAPProtocolError as xcpt:
        raised = xcpt

    testbase.assert_true(raised is not None, "SOAPProtocolError raised for the mismatched encodingStyle")
    message = str(raised)
    testbase.assert_true(f"EXPECTED: {URI_SOAP_ENCODING}" in message, "the error names the expected encoding")
    testbase.assert_true(f"DECLARED: {OTHER_ENCODING}" in message, "the error names the declared encoding")
    testbase.assert_true("GetVolume" in message, "the error names the action")
    return


def test_parse_response_decodes_with_the_encoding_parameter():
    """
        The 'encoding' parameter selects the encoding the response is decoded with, for a call and for the
        processor default.
    """
    content = create_action_response(envelope_encoding_attr=f' s:encodingStyle="{OTHER_ENCODING}"')

    processor = SoapProcessor()
    resp_dict = processor.parse_response("GetVolume", content, encoding=OTHER_ENCODING, typed=SERVICE_TYPE)
    testbase.assert_equal(resp_dict, {"CurrentVolume": "42"})

    other_processor = SoapProcessor(encoding=OTHER_ENCODING)
    resp_dict = other_processor.parse_response("GetVolume", content, typed=SERVICE_TYPE)
    testbase.assert_equal(resp_dict, {"CurrentVolume": "42"})
    return


def test_parse_response_uses_the_innermost_encoding_style():
    """
        An encodingStyle on the response element overrides the one on the Envelope, following the scope of
        the SOAP encodingStyle attribute.
    """
    processor = SoapProcessor()
    content = create_action_response(
        envelope_encoding_attr=f' s:encodingStyle="{OTHER_ENCODING}"',
        response_encoding_attr=f' s:encodingStyle="{URI_SOAP_ENCODING}"',
    )

    resp_dict = processor.parse_response("GetVolume", content, typed=SERVICE_TYPE)

    testbase.assert_equal(resp_dict, {"CurrentVolume": "42"})
    return


def test_parse_response_reads_a_created_response():
    """
        A response built by create_response is parsed back with the same processor.
    """
    processor = SoapProcessor()
    content = processor.create_response("GetVolume", {"CurrentVolume": 42})

    resp_dict = processor.parse_response("GetVolume", content)

    testbase.assert_equal(resp_dict, {"CurrentVolume": "42"})
    return


def test_parse_response_error_for_upnp_checks_the_encoding_style():
    """
        A fault response with the expected encoding (or none) returns the UPnP error, and a fault response
        that declares other encoding rules raises a SOAPProtocolError unless that encoding is passed.
    """
    processor = SoapProcessor()

    error_code, error_description = processor.parse_response_error_for_upnp("GetVolume", create_fault_response(), 500)
    testbase.assert_equal((error_code, error_description), (402, "Invalid Args"))

    error_code, error_description = processor.parse_response_error_for_upnp(
        "GetVolume", create_fault_response(envelope_encoding_attr=""), 500)
    testbase.assert_equal((error_code, error_description), (402, "Invalid Args"))

    mismatched = create_fault_response(envelope_encoding_attr=f' s:encodingStyle="{OTHER_ENCODING}"')

    raised = None
    try:
        processor.parse_response_error_for_upnp("GetVolume", mismatched, 500)
    except SOAPProtocolError as xcpt:
        raised = xcpt
    testbase.assert_true(raised is not None, "SOAPProtocolError raised for the mismatched encodingStyle")

    error_code, error_description = processor.parse_response_error_for_upnp(
        "GetVolume", mismatched, 500, encoding=OTHER_ENCODING)
    testbase.assert_equal((error_code, error_description), (402, "Invalid Args"))
    return


def test_parse_methods_deprecate_envelope_attrib():
    """
        Passing 'envelope_attrib' to a parse method is still accepted but emits a DeprecationWarning, because
        envelope attributes only apply to building envelopes; the parse result is unchanged.
    """
    processor = SoapProcessor()
    envelope_attrib = {"xmlns:s": NS_SOAP_ENV, "s:encodingStyle": URI_SOAP_ENCODING}

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        resp_dict = processor.parse_response("GetVolume", create_action_response(), envelope_attrib=envelope_attrib,
                                             typed=SERVICE_TYPE)
        error_info = processor.parse_response_error_for_upnp("GetVolume", create_fault_response(), 500,
                                                             envelope_attrib=envelope_attrib)

    testbase.assert_equal(resp_dict, {"CurrentVolume": "42"})
    testbase.assert_equal(error_info, (402, "Invalid Args"))

    deprecations = [warn for warn in caught if issubclass(warn.category, DeprecationWarning)]
    testbase.assert_equal(len(deprecations), 2)
    testbase.assert_true("parse_response" in str(deprecations[0].message), "the warning names parse_response")
    testbase.assert_true("parse_response_error_for_upnp" in str(deprecations[1].message),
                         "the warning names parse_response_error_for_upnp")
    testbase.assert_true(deprecations[0].filename.endswith("test_soap.py"), "the warning points at the caller")
    return


def test_parse_methods_do_not_warn_without_envelope_attrib():
    """
        A processor created with envelope attributes, used without passing 'envelope_attrib' to the parse
        methods, parses without a deprecation warning.
    """
    processor = SoapProcessor(envelope_attrib={"xmlns:s": NS_SOAP_ENV})

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        processor.parse_response("GetVolume", create_action_response(), typed=SERVICE_TYPE)

    deprecations = [warn for warn in caught if issubclass(warn.category, DeprecationWarning)]
    testbase.assert_equal(len(deprecations), 0)
    return
