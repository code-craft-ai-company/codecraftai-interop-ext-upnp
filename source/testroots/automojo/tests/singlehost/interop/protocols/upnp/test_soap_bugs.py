"""
    .. module:: test_soap_bugs
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Test module for SOAP functionality bugs.

    .. moduleauthor:: AutomationX <automation@mojo.com>
"""

import sys
from automojo import testbase
from automojo.interop.protocols.upnp.soap import SoapProcessor, xml_fromstring

def test_parse_response_bug():
    """
    Test fix for TypeError in parse_response when handling child elements.
    """
    processor = SoapProcessor()

    content = """<?xml version="1.0"?>
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
        <s:Body>
            <u:ActionResponse xmlns:u="urn:schemas-upnp-org:service:Service:1">
                <Result>
                    <Item>Value1</Item>
                    <Item>Value2</Item>
                </Result>
            </u:ActionResponse>
        </s:Body>
    </s:Envelope>
    """

    try:
        # This should not raise TypeError
        resp = processor.parse_response("Action", content, typed="urn:schemas-upnp-org:service:Service:1")

        # Verification
        testbase.assert_equal("Result" in resp, True)
        testbase.assert_equal("Value1" in resp["Result"], True)
        testbase.assert_equal("Value2" in resp["Result"], True)
        print("test_parse_response_bug PASSED")
    except Exception as e:
        print(f"test_parse_response_bug FAILED: {e}")
        raise

def test_xml_parser_bug():
    """
    Test fix for AttributeError in xml_fromstring.
    """
    data = "<root>test</root>"
    try:
        # This should not raise AttributeError
        elem = xml_fromstring(data)
        testbase.assert_equal(elem.tag, "root")
        testbase.assert_equal(elem.text, "test")
        print("test_xml_parser_bug PASSED")
    except Exception as e:
        print(f"test_xml_parser_bug FAILED: {e}")
        raise

def test_missing_xsd_namespace_bug():
    """
    Test fix for missing xmlns:xsd definition.
    """
    processor = SoapProcessor()

    try:
        # Enable typed response to trigger xsi:type usage
        content = processor.create_response(
            action_name="TestAction",
            arguments={"Arg1": "Value1"},
            typed="urn:schemas-upnp-org:service:Service:1"
        )

        # Check if xmlns:xsd is present
        has_xsd = 'xmlns:xsd="http://www.w3.org/1999/XMLSchema"' in content or "xmlns:xsd" in content
        if not has_xsd:
            print(f"Generated Content: {content}")

        testbase.assert_equal(has_xsd, True)
        print("test_missing_xsd_namespace_bug PASSED")
    except Exception as e:
        print(f"test_missing_xsd_namespace_bug FAILED: {e}")
        raise

if __name__ == "__main__":
    try:
        test_parse_response_bug()
        test_xml_parser_bug()
        test_missing_xsd_namespace_bug()
    except Exception:
        sys.exit(1)
