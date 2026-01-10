"""
    .. module:: test_soap_bugs
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Test module for specific SOAP bugs.

    .. moduleauthor:: AutomationX <automation@mojo.com>
"""

import sys
import os

from automojo import testbase

from automojo.interop.protocols.upnp.soap import SoapProcessor, remove_extraneous_xml_declarations

def test_soap_envelope_attrib_dict():
    """
    Test that create_request and create_response accept a dictionary for envelope_attrib.
    """
    processor = SoapProcessor()
    envelope_attrib = {'xmlns:foo': 'http://foo.com'}

    # Test create_request
    try:
        req = processor.create_request('Action', {}, envelope_attrib=envelope_attrib)
        testbase.assert_true('xmlns:foo="http://foo.com"' in req, "Request should contain the attribute")
    except Exception as e:
        raise AssertionError(f"create_request raised exception with dict envelope_attrib: {e}")

    # Test create_response
    try:
        resp = processor.create_response('Action', {}, envelope_attrib=envelope_attrib)
        testbase.assert_true('xmlns:foo="http://foo.com"' in resp, "Response should contain the attribute")
    except Exception as e:
        raise AssertionError(f"create_response raised exception with dict envelope_attrib: {e}")

def test_remove_extraneous_xml_declarations_fixes():
    """
    Test the fixes for remove_extraneous_xml_declarations.
    """
    # Case 1: Multiple declarations, one at start
    xml_multi = '<?xml version="1.0"?><root><?xml version="1.0"?><child/></root>'
    cleaned = remove_extraneous_xml_declarations(xml_multi)
    # Expect: One declaration at start, none elsewhere.
    testbase.assert_true(cleaned.startswith('<?xml'), "Should start with XML declaration")
    testbase.assert_equal(cleaned.count('<?xml'), 1, "Should have exactly one XML declaration")

    # Case 2: Leading whitespace
    xml_space = '   <?xml version="1.0"?><root/>'
    cleaned = remove_extraneous_xml_declarations(xml_space)
    # Expect: One declaration at start (stripped), content follows.
    testbase.assert_true(cleaned.startswith('<?xml'), "Should start with XML declaration (trimmed)")
    testbase.assert_true('<root/>' in cleaned, "Should contain root element")

    # Case 3: Case sensitivity
    xml_caps = '<?XML version="1.0"?><root/>'
    cleaned = remove_extraneous_xml_declarations(xml_caps)
    # Expect: One declaration at start (normalized case if matched by regex, or preserved if not normalized but regex is case insensitive for detection)
    # The current implementation extracts the match (preserving case) and prepends it.
    # So '<?XML ... ?>' should be preserved at start.
    testbase.assert_true(cleaned.lower().startswith('<?xml'), "Should start with XML declaration (case insensitive check)")
    testbase.assert_true('<root/>' in cleaned, "Should contain root element")
