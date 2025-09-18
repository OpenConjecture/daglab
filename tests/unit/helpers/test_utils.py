"""Tests for utility helper functions."""

import re
from datetime import datetime
from unittest.mock import patch, Mock
import pytest
import pandas as pd
from dagster import AssetKey

from daglab.helpers.utils import (
    parse_asset_selection,
    expand_pattern,
    generate_dagster_url,
    format_error,
    pretty_print_error,
    validate_data,
    create_asset_tree,
    create_run_table,
    format_run_config,
    validate_dataframe,
    safe_divide,
    truncate_string,
    humanize_bytes,
    humanize_duration
)


class TestAssetSelection:
    """Test asset selection parsing."""
    
    def test_parse_single_asset(self):
        """Test parsing single asset."""
        keys = parse_asset_selection("my_asset", ["my_asset", "other_asset"])
        assert len(keys) == 1
        assert keys[0] == AssetKey(["my_asset"])
    
    def test_parse_multiple_assets(self):
        """Test parsing comma-separated assets."""
        keys = parse_asset_selection(
            "asset1,asset2,asset3",
            ["asset1", "asset2", "asset3", "asset4"]
        )
        assert len(keys) == 3
        assert AssetKey(["asset1"]) in keys
        assert AssetKey(["asset2"]) in keys
        assert AssetKey(["asset3"]) in keys
    
    def test_parse_wildcard_assets(self):
        """Test parsing with wildcards."""
        available = ["model_a", "model_b", "model_c", "data_x", "data_y"]
        
        # Prefix wildcard
        keys = parse_asset_selection("model_*", available)
        assert len(keys) == 3
        assert all(k.path[0].startswith("model_") for k in keys)
        
        # Suffix wildcard
        keys = parse_asset_selection("*_x", available)
        assert len(keys) == 1
        assert keys[0] == AssetKey(["data_x"])
    
    def test_parse_with_exclusions(self):
        """Test parsing with exclusions."""
        available = ["asset1", "asset2", "test_asset", "test_data"]
        
        keys = parse_asset_selection("* -test_*", available)
        assert len(keys) == 2
        assert AssetKey(["asset1"]) in keys
        assert AssetKey(["asset2"]) in keys
    
    def test_parse_nested_assets(self):
        """Test parsing nested asset keys."""
        available = ["models/silver/customers", "models/gold/revenue"]
        
        keys = parse_asset_selection("models/silver/customers", available)
        assert len(keys) == 1
        assert keys[0] == AssetKey(["models", "silver", "customers"])
    
    def test_parse_list_input(self):
        """Test parsing list input."""
        keys = parse_asset_selection(
            ["asset1", "asset2"],
            ["asset1", "asset2", "asset3"]
        )
        assert len(keys) == 2
    
    def test_parse_without_validation(self):
        """Test parsing without available assets list."""
        # Should work for non-wildcard selections
        keys = parse_asset_selection("asset1,asset2")
        assert len(keys) == 2
        
        # Should raise for wildcards
        with pytest.raises(ValueError, match="Cannot expand wildcard"):
            parse_asset_selection("asset*")


class TestPatternExpansion:
    """Test pattern expansion."""
    
    def test_expand_exact_match(self):
        """Test exact pattern matching."""
        candidates = ["asset1", "asset2", "asset3"]
        matches = expand_pattern("asset2", candidates)
        assert matches == {"asset2"}
    
    def test_expand_prefix_wildcard(self):
        """Test prefix wildcard matching."""
        candidates = ["test_a", "test_b", "prod_a", "prod_b"]
        matches = expand_pattern("test_*", candidates)
        assert matches == {"test_a", "test_b"}
    
    def test_expand_suffix_wildcard(self):
        """Test suffix wildcard matching."""
        candidates = ["a_test", "b_test", "a_prod", "b_prod"]
        matches = expand_pattern("*_test", candidates)
        assert matches == {"a_test", "b_test"}
    
    def test_expand_middle_wildcard(self):
        """Test wildcard in the middle."""
        candidates = ["model_silver_customers", "model_gold_customers", "data_silver_orders"]
        matches = expand_pattern("model_*_customers", candidates)
        assert matches == {"model_silver_customers", "model_gold_customers"}
    
    def test_expand_multiple_wildcards(self):
        """Test multiple wildcards."""
        candidates = ["a_b_c", "x_y_z", "a_y_c", "x_b_z"]
        matches = expand_pattern("a_*_c", candidates)
        assert matches == {"a_b_c", "a_y_c"}


class TestURLGeneration:
    """Test Dagster URL generation."""
    
    def test_generate_basic_url(self):
        """Test basic URL generation."""
        url = generate_dagster_url(path="/instance/runs/abc123")
        assert url == "http://localhost:3000/instance/runs/abc123"
    
    def test_generate_url_with_params(self):
        """Test URL with query parameters."""
        url = generate_dagster_url(
            path="/instance/assets",
            prefix="models",
            status="MATERIALIZED"
        )
        assert "prefix=models" in url
        assert "status=MATERIALIZED" in url
        assert url.startswith("http://localhost:3000/instance/assets?")
    
    def test_generate_url_custom_base(self):
        """Test URL with custom base."""
        url = generate_dagster_url(
            base_url="https://dagster.example.com",
            path="/graphql"
        )
        assert url == "https://dagster.example.com/graphql"
    
    def test_generate_url_filter_none_params(self):
        """Test filtering None parameters."""
        url = generate_dagster_url(
            path="/test",
            param1="value1",
            param2=None,
            param3="value3"
        )
        assert "param1=value1" in url
        assert "param2" not in url
        assert "param3=value3" in url


class TestErrorFormatting:
    """Test error formatting functions."""
    
    def test_format_error_basic(self):
        """Test basic error formatting."""
        try:
            raise ValueError("Test error message")
        except ValueError as e:
            formatted = format_error(e, include_traceback=False)
        
        assert "ValueError: Test error message" in formatted
        assert "Traceback" not in formatted
    
    def test_format_error_with_traceback(self):
        """Test error formatting with traceback."""
        try:
            raise RuntimeError("Test error")
        except RuntimeError as e:
            formatted = format_error(e, include_traceback=True)
        
        assert "RuntimeError: Test error" in formatted
        assert "Traceback" in formatted
        assert "test_format_error_with_traceback" in formatted
    
    def test_format_error_with_context(self):
        """Test error formatting with context."""
        try:
            raise KeyError("missing_key")
        except KeyError as e:
            formatted = format_error(
                e,
                context={
                    "operation": "data_processing",
                    "step": 3,
                    "input_size": 1000
                }
            )
        
        assert "KeyError: 'missing_key'" in formatted
        assert "Context:" in formatted
        assert "operation: data_processing" in formatted
        assert "step: 3" in formatted
    
    @patch('daglab.helpers.utils.console')
    def test_pretty_print_error(self, mock_console):
        """Test pretty printing errors."""
        try:
            x = 1 / 0
        except ZeroDivisionError as e:
            pretty_print_error(
                e,
                title="Division Error",
                context={"numerator": 1, "denominator": 0}
            )
        
        # Verify console.print was called
        assert mock_console.print.called
        call_args = [str(arg) for call in mock_console.print.call_args_list for arg in call[0]]
        assert any("Division Error" in arg for arg in call_args)
        assert any("ZeroDivisionError" in arg for arg in call_args)


class TestDataValidation:
    """Test data validation functions."""
    
    def test_validate_data_simple_types(self):
        """Test validation of simple types."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "score": {"type": "number"},
                "active": {"type": "boolean"}
            },
            "required": ["name", "age"]
        }
        
        # Valid data
        data = {"name": "John", "age": 30, "score": 95.5, "active": True}
        is_valid, errors = validate_data(data, schema)
        assert is_valid
        assert errors == []
        
        # Missing required field
        data = {"name": "John", "score": 95.5}
        is_valid, errors = validate_data(data, schema)
        assert not is_valid
        assert any("Missing required field 'age'" in e for e in errors)
        
        # Wrong type
        data = {"name": "John", "age": "thirty"}
        is_valid, errors = validate_data(data, schema)
        assert not is_valid
        assert any("Expected type 'integer'" in e for e in errors)
    
    def test_validate_data_enums(self):
        """Test validation with enum values."""
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "inactive", "pending"]}
            }
        }
        
        # Valid enum
        is_valid, errors = validate_data({"status": "active"}, schema)
        assert is_valid
        
        # Invalid enum
        is_valid, errors = validate_data({"status": "unknown"}, schema)
        assert not is_valid
        assert any("not in allowed values" in e for e in errors)
    
    def test_validate_data_patterns(self):
        """Test validation with regex patterns."""
        schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$"}
            }
        }
        
        # Valid pattern
        is_valid, errors = validate_data({"email": "test@example.com"}, schema)
        assert is_valid
        
        # Invalid pattern
        is_valid, errors = validate_data({"email": "not-an-email"}, schema)
        assert not is_valid
        assert any("doesn't match pattern" in e for e in errors)
    
    def test_validate_data_numeric_constraints(self):
        """Test validation with numeric constraints."""
        schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "minimum": 0, "maximum": 150},
                "score": {"type": "number", "minimum": 0, "maximum": 100}
            }
        }
        
        # Valid ranges
        is_valid, errors = validate_data({"age": 25, "score": 85.5}, schema)
        assert is_valid
        
        # Below minimum
        is_valid, errors = validate_data({"age": -5}, schema)
        assert not is_valid
        assert any("less than minimum" in e for e in errors)
        
        # Above maximum
        is_valid, errors = validate_data({"score": 105}, schema)
        assert not is_valid
        assert any("greater than maximum" in e for e in errors)
    
    def test_validate_data_arrays(self):
        """Test validation of arrays."""
        schema = {
            "type": "array",
            "items": {"type": "integer"}
        }
        
        # Valid array
        is_valid, errors = validate_data([1, 2, 3], schema)
        assert is_valid
        
        # Invalid item type
        is_valid, errors = validate_data([1, "two", 3], schema)
        assert not is_valid
        assert any("[1]" in e and "Expected type 'integer'" in e for e in errors)


class TestDataFrameValidation:
    """Test DataFrame validation."""
    
    def test_validate_dataframe_basic(self):
        """Test basic DataFrame validation."""
        df = pd.DataFrame({
            "name": ["Alice", "Bob"],
            "age": [25, 30],
            "score": [95.5, 88.0]
        })
        
        is_valid, errors = validate_dataframe(df)
        assert is_valid
        assert errors == []
    
    def test_validate_dataframe_required_columns(self):
        """Test DataFrame with required columns."""
        df = pd.DataFrame({
            "name": ["Alice"],
            "age": [25]
        })
        
        # Has required columns
        is_valid, errors = validate_dataframe(df, required_columns=["name", "age"])
        assert is_valid
        
        # Missing required column
        is_valid, errors = validate_dataframe(df, required_columns=["name", "age", "email"])
        assert not is_valid
        assert any("Missing required columns" in e for e in errors)
    
    def test_validate_dataframe_column_types(self):
        """Test DataFrame column type validation."""
        df = pd.DataFrame({
            "name": ["Alice", "Bob"],
            "age": [25, 30],
            "active": [True, False]
        })
        
        # Correct types
        is_valid, errors = validate_dataframe(
            df,
            column_types={"name": str, "age": int, "active": bool}
        )
        assert is_valid
        
        # Wrong type
        is_valid, errors = validate_dataframe(df, column_types={"age": str})
        assert not is_valid
        assert any("expected str" in e for e in errors)
    
    def test_validate_dataframe_row_constraints(self):
        """Test DataFrame row count constraints."""
        df = pd.DataFrame({"a": [1, 2, 3]})
        
        # Within constraints
        is_valid, errors = validate_dataframe(df, min_rows=2, max_rows=5)
        assert is_valid
        
        # Too few rows
        is_valid, errors = validate_dataframe(df, min_rows=5)
        assert not is_valid
        assert any("minimum required is 5" in e for e in errors)
        
        # Too many rows
        is_valid, errors = validate_dataframe(df, max_rows=2)
        assert not is_valid
        assert any("maximum allowed is 2" in e for e in errors)
    
    def test_validate_dataframe_empty(self):
        """Test empty DataFrame validation."""
        df = pd.DataFrame()
        
        # Empty allowed
        is_valid, errors = validate_dataframe(df, min_rows=0)
        assert is_valid
        
        # Empty not allowed
        is_valid, errors = validate_dataframe(df, min_rows=1)
        assert not is_valid
        assert any("DataFrame is empty" in e for e in errors)
    
    def test_validate_dataframe_not_dataframe(self):
        """Test validation of non-DataFrame input."""
        is_valid, errors = validate_dataframe([1, 2, 3])
        assert not is_valid
        assert any("Expected pandas DataFrame" in e for e in errors)


class TestUtilityFunctions:
    """Test miscellaneous utility functions."""
    
    def test_safe_divide(self):
        """Test safe division."""
        assert safe_divide(10, 2) == 5
        assert safe_divide(10, 0) == 0
        assert safe_divide(10, 0, default=-1) == -1
        assert safe_divide(7, 2) == 3.5
    
    def test_truncate_string(self):
        """Test string truncation."""
        assert truncate_string("short", max_length=10) == "short"
        assert truncate_string("this is a long string", max_length=10) == "this is..."
        assert truncate_string("custom suffix", max_length=10, suffix="[..]") == "custom[..]"
    
    def test_humanize_bytes(self):
        """Test bytes formatting."""
        assert humanize_bytes(0) == "0.00 B"
        assert humanize_bytes(1023) == "1023.00 B"
        assert humanize_bytes(1024) == "1.00 KB"
        assert humanize_bytes(1024 * 1024) == "1.00 MB"
        assert humanize_bytes(1024 * 1024 * 1024) == "1.00 GB"
        assert humanize_bytes(1536 * 1024) == "1.50 MB"
        assert humanize_bytes(1234567890, decimal_places=1) == "1.1 GB"
    
    def test_humanize_duration(self):
        """Test duration formatting."""
        assert humanize_duration(0) == "0s"
        assert humanize_duration(45) == "45s"
        assert humanize_duration(90) == "1m 30s"
        assert humanize_duration(3661) == "1h 1m 1s"
        assert humanize_duration(90061) == "1d 1h 1m 1s"
        
        # Test precision
        assert humanize_duration(3661, precision="minutes") == "1h 1m"
        assert humanize_duration(3661, precision="hours") == "1h"
        
        # Test negative duration
        assert humanize_duration(-10) == "Invalid duration"