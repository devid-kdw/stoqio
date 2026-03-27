"""Unit tests for shared validator helpers."""

import pytest

from app.utils.validators import QueryValidationError, parse_positive_int, parse_bool_query

def test_parse_positive_int_valid():
    assert parse_positive_int("5", field_name="page", default=1) == 5
    assert parse_positive_int(10, field_name="per_page", default=50) == 10

def test_parse_positive_int_zero():
    with pytest.raises(QueryValidationError, match="page must be greater than zero"):
        parse_positive_int("0", field_name="page", default=1)
    with pytest.raises(QueryValidationError, match="page must be greater than zero"):
        parse_positive_int(0, field_name="page", default=1)

def test_parse_positive_int_negative():
    with pytest.raises(QueryValidationError, match="page must be greater than zero"):
        parse_positive_int("-5", field_name="page", default=1)
    with pytest.raises(QueryValidationError, match="page must be greater than zero"):
        parse_positive_int(-5, field_name="page", default=1)

def test_parse_positive_int_non_numeric():
    with pytest.raises(QueryValidationError, match="page must be a valid integer"):
        parse_positive_int("abc", field_name="page", default=1)

def test_parse_positive_int_none_uses_default():
    assert parse_positive_int(None, field_name="page", default=42) == 42


def test_parse_bool_query_true():
    assert parse_bool_query("true", field_name="flag", default=False) is True
    assert parse_bool_query("1", field_name="flag", default=False) is True
    assert parse_bool_query("  TrUe  ", field_name="flag", default=False) is True

def test_parse_bool_query_false():
    assert parse_bool_query("false", field_name="flag", default=True) is False
    assert parse_bool_query("0", field_name="flag", default=True) is False
    assert parse_bool_query("  fAlSe  ", field_name="flag", default=True) is False

def test_parse_bool_query_none_uses_default():
    assert parse_bool_query(None, field_name="flag", default=True) is True
    assert parse_bool_query(None, field_name="flag", default=False) is False

def test_parse_bool_query_invalid():
    with pytest.raises(QueryValidationError, match="flag must be 'true' or 'false'"):
        parse_bool_query("yes", field_name="flag", default=True)
    with pytest.raises(QueryValidationError, match="flag must be 'true' or 'false'"):
        parse_bool_query("2", field_name="flag", default=True)
