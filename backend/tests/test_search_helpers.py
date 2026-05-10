"""Tests for search_helpers.py (normalize_umlauts, normalize_search_query, safe_regex_contains)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.search_helpers import (
    normalize_umlauts,
    normalize_search_query,
    safe_regex_contains,
)


class TestNormalizeUmlauts:

    def test_ae(self):
        assert normalize_umlauts("ä") == "ae"

    def test_oe(self):
        assert normalize_umlauts("ö") == "oe"

    def test_ue(self):
        assert normalize_umlauts("ü") == "ue"

    def test_eszett(self):
        assert normalize_umlauts("ß") == "ss"

    def test_uppercase_ae(self):
        assert normalize_umlauts("Ä") == "Ae"

    def test_uppercase_oe(self):
        assert normalize_umlauts("Ö") == "Oe"

    def test_uppercase_ue(self):
        assert normalize_umlauts("Ü") == "Ue"

    def test_mixed_text(self):
        result = normalize_umlauts("Überweisung für schöne Ärzte")
        assert "Ueberweisung" in result
        assert "schoene" in result
        assert "Aerzte" in result

    def test_no_umlauts(self):
        assert normalize_umlauts("Hello world") == "Hello world"

    def test_empty_string(self):
        assert normalize_umlauts("") == ""


class TestNormalizeSearchQuery:

    def test_trims_whitespace(self):
        assert normalize_search_query("  hello  ") == "hello"

    def test_collapses_spaces(self):
        assert normalize_search_query("hello   world") == "hello world"

    def test_normalizes_umlauts(self):
        assert normalize_search_query("ärztliche Überweisung") == "aerztliche Ueberweisung"

    def test_empty_query(self):
        assert normalize_search_query("") == ""

    def test_none_query(self):
        assert normalize_search_query(None) == ""

    def test_whitespace_only(self):
        assert normalize_search_query("   ") == ""


class TestSafeRegexContains:

    def test_simple_match(self):
        assert safe_regex_contains("Hello World", "world") is True

    def test_no_match(self):
        assert safe_regex_contains("Hello World", "foo") is False

    def test_regex_special_chars(self):
        assert safe_regex_contains("test (parens)", "(parens)") is True

    def test_regex_special_chars_dot(self):
        assert safe_regex_contains("file.txt", "file.txt") is True

    def test_regex_special_chars_brackets(self):
        assert safe_regex_contains("array[0]", "[0]") is True

    def test_empty_text(self):
        assert safe_regex_contains("", "hello") is False

    def test_empty_query(self):
        assert safe_regex_contains("hello", "") is False

    def test_case_insensitive(self):
        assert safe_regex_contains("HELLO", "hello") is True

    def test_partial_match(self):
        assert safe_regex_contains("find the needle here", "needle") is True
