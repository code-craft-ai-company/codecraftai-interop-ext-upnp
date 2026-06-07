"""
    .. module:: test_soap
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Test module for SOAP functionality.
    
    .. moduleauthor:: CodeCraftX <automation@mojo.com>
"""

from ccai import testbase

from ccai.interop.protocols.upnp.soap import remove_extraneous_xml_declarations


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