"""Tests for state management helpers."""

import json
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, Mock
import pytest

from daglab.helpers.state import (
    StateManager,
    create_state_manager,
    quick_cache
)


class TestStateManager:
    """Test StateManager class."""
    
    @pytest.fixture
    def state_manager(self):
        """Create StateManager instance with temp database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_state.db"
            manager = StateManager(db_path, namespace="test")
            yield manager
    
    def test_set_and_get_basic(self, state_manager):
        """Test basic set and get operations."""
        # Set various types
        assert state_manager.set("string_key", "test_value")
        assert state_manager.set("int_key", 42)
        assert state_manager.set("float_key", 3.14)
        assert state_manager.set("bool_key", True)
        assert state_manager.set("list_key", [1, 2, 3])
        assert state_manager.set("dict_key", {"a": 1, "b": 2})
        
        # Get values
        assert state_manager.get("string_key") == "test_value"
        assert state_manager.get("int_key") == 42
        assert state_manager.get("float_key") == 3.14
        assert state_manager.get("bool_key") is True
        assert state_manager.get("list_key") == [1, 2, 3]
        assert state_manager.get("dict_key") == {"a": 1, "b": 2}
        
        # Get non-existent key
        assert state_manager.get("non_existent") is None
        assert state_manager.get("non_existent", "default") == "default"
    
    def test_set_with_ttl(self, state_manager):
        """Test setting values with TTL."""
        # Set with 1 second TTL
        assert state_manager.set("expiring_key", "value", ttl=1)
        
        # Value should exist immediately
        assert state_manager.get("expiring_key") == "value"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Value should be gone
        assert state_manager.get("expiring_key") is None
    
    def test_set_with_metadata(self, state_manager):
        """Test setting values with metadata."""
        metadata = {"created_by": "test_user", "version": 1}
        
        assert state_manager.set(
            "meta_key",
            "meta_value",
            metadata=metadata
        )
        
        # Metadata is stored but not returned with get
        assert state_manager.get("meta_key") == "meta_value"
    
    def test_set_with_encryption(self, state_manager):
        """Test setting encrypted values."""
        sensitive_data = {"password": "secret123", "api_key": "abc-123-def"}
        
        assert state_manager.set(
            "sensitive_key",
            sensitive_data,
            encrypt=True
        )
        
        # Should decrypt on retrieval
        retrieved = state_manager.get("sensitive_key")
        assert retrieved == sensitive_data
    
    def test_delete(self, state_manager):
        """Test deleting values."""
        state_manager.set("delete_me", "value")
        
        # Verify it exists
        assert state_manager.get("delete_me") == "value"
        
        # Delete it
        assert state_manager.delete("delete_me") is True
        
        # Verify it's gone
        assert state_manager.get("delete_me") is None
        
        # Delete non-existent key
        assert state_manager.delete("non_existent") is False
    
    def test_list_keys(self, state_manager):
        """Test listing keys."""
        # Set some keys
        state_manager.set("alpha", 1)
        state_manager.set("beta", 2)
        state_manager.set("gamma", 3)
        
        keys = state_manager.list_keys()
        assert sorted(keys) == ["alpha", "beta", "gamma"]
        
        # Test with pattern
        state_manager.set("test_1", 1)
        state_manager.set("test_2", 2)
        
        test_keys = state_manager.list_keys(pattern="test_%")
        assert sorted(test_keys) == ["test_1", "test_2"]
    
    def test_namespaces(self, state_manager):
        """Test namespace isolation."""
        # Set in default namespace
        state_manager.set("key1", "value1")
        
        # Set in different namespace
        state_manager.set("key1", "value2", namespace="other")
        
        # Values should be isolated
        assert state_manager.get("key1") == "value1"
        assert state_manager.get("key1", namespace="other") == "value2"
        
        # List keys should be isolated
        assert "key1" in state_manager.list_keys()
        assert "key1" in state_manager.list_keys(namespace="other")
        
        # Clear namespace
        count = state_manager.clear_namespace("other")
        assert count == 1
        assert state_manager.get("key1", namespace="other") is None
        assert state_manager.get("key1") == "value1"  # Default namespace unaffected
    
    def test_save_run(self, state_manager):
        """Test saving run information."""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=5)
        
        assert state_manager.save_run(
            run_id="run-123",
            job_name="test_job",
            status="SUCCESS",
            started_at=start_time,
            completed_at=end_time,
            run_config={"ops": {"my_op": {"config": {"value": 42}}}},
            tags={"env": "test"},
            metadata={"user": "test_user"}
        )
        
        # Get run history
        history = state_manager.get_run_history()
        assert len(history) == 1
        
        run = history[0]
        assert run["run_id"] == "run-123"
        assert run["job_name"] == "test_job"
        assert run["status"] == "SUCCESS"
        assert run["run_config"]["ops"]["my_op"]["config"]["value"] == 42
        assert run["tags"]["env"] == "test"
        assert run["metadata"]["user"] == "test_user"
    
    def test_get_run_history_filters(self, state_manager):
        """Test getting run history with filters."""
        # Save multiple runs
        base_time = datetime.now()
        
        for i in range(5):
            state_manager.save_run(
                run_id=f"run-{i}",
                job_name="job1" if i < 3 else "job2",
                status="SUCCESS" if i % 2 == 0 else "FAILURE",
                started_at=base_time - timedelta(hours=i)
            )
        
        # Test limit
        history = state_manager.get_run_history(limit=3)
        assert len(history) == 3
        
        # Test job name filter
        job1_history = state_manager.get_run_history(job_name="job1")
        assert len(job1_history) == 3
        assert all(run["job_name"] == "job1" for run in job1_history)
        
        # Test status filter
        success_history = state_manager.get_run_history(status_filter="SUCCESS")
        assert len(success_history) == 3
        assert all(run["status"] == "SUCCESS" for run in success_history)
        
        # Test combined filters
        filtered = state_manager.get_run_history(
            job_name="job1",
            status_filter="SUCCESS",
            limit=2
        )
        assert len(filtered) == 2
        assert all(run["job_name"] == "job1" and run["status"] == "SUCCESS" 
                  for run in filtered)
    
    def test_cache_result(self, state_manager):
        """Test caching computation results."""
        # Cache a result
        result = {"data": [1, 2, 3], "computed": True}
        
        assert state_manager.cache_result(
            "computation_key",
            result,
            ttl=3600,
            metadata={"algorithm": "test"}
        )
        
        # Retrieve cached result
        cached = state_manager.get_cached_result("computation_key")
        assert cached == result
        
        # Access count should increase
        state_manager.get_cached_result("computation_key")
        stats = state_manager.get_cache_stats()
        assert stats["total_entries"] >= 1
    
    def test_cache_expiration(self, state_manager):
        """Test cache expiration."""
        # Cache with short TTL
        state_manager.cache_result("expiring", "data", ttl=1)
        
        # Should exist immediately
        assert state_manager.get_cached_result("expiring") == "data"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be gone
        assert state_manager.get_cached_result("expiring") is None
    
    def test_get_cache_stats(self, state_manager):
        """Test getting cache statistics."""
        # Add some cached results
        state_manager.cache_result("cache1", "data1")
        state_manager.cache_result("cache2", "data2" * 1000)  # Larger data
        
        # Access cache1 multiple times
        for _ in range(5):
            state_manager.get_cached_result("cache1")
        
        stats = state_manager.get_cache_stats()
        
        assert stats["total_entries"] == 2
        assert stats["total_size_mb"] > 0
        assert stats["avg_access_count"] > 1
        assert stats["max_access_count"] >= 6  # 1 + 5 accesses
        
        # Check most accessed
        most_accessed = stats["most_accessed"]
        assert len(most_accessed) > 0
        assert most_accessed[0]["key"] == "cache1"
    
    def test_export_state(self, state_manager):
        """Test exporting state to file."""
        # Add some state
        state_manager.set("key1", "value1")
        state_manager.set("key2", {"nested": "value"})
        state_manager.cache_result("cached", "result")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            state_manager.export_state(f.name, include_cache=True)
            
            # Load and verify
            with open(f.name) as rf:
                data = json.load(rf)
            
            assert "timestamp" in data
            assert "state" in data
            assert len(data["state"]) == 2
            
            # Check cache was included
            assert "cache" in data
            assert len(data["cache"]) == 1
    
    def test_cleanup_expired(self, state_manager):
        """Test cleaning up expired entries."""
        # Add entries with different TTLs
        state_manager.set("permanent", "value")
        state_manager.set("expiring1", "value", ttl=1)
        state_manager.set("expiring2", "value", ttl=1)
        state_manager.cache_result("cache_perm", "result")
        state_manager.cache_result("cache_exp", "result", ttl=1)
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Clean up
        state_deleted, cache_deleted = state_manager.cleanup_expired()
        
        assert state_deleted == 2
        assert cache_deleted == 1
        
        # Verify permanent entries remain
        assert state_manager.get("permanent") == "value"
        assert state_manager.get_cached_result("cache_perm") == "result"
    
    def test_encryption_disabled(self):
        """Test StateManager with encryption disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_state.db"
            manager = StateManager(db_path, encrypt_sensitive=False)
            
            # Should work without encryption
            manager.set("key", "value", encrypt=True)  # encrypt flag ignored
            assert manager.get("key") == "value"


class TestHelperFunctions:
    """Test standalone helper functions."""
    
    def test_create_state_manager(self):
        """Test create_state_manager helper."""
        manager = create_state_manager("custom_namespace")
        assert isinstance(manager, StateManager)
        assert manager.namespace == "custom_namespace"
    
    def test_quick_cache_decorator(self):
        """Test quick_cache decorator."""
        call_count = 0
        
        @quick_cache(ttl=60)
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x ** y
        
        # First call - should compute
        result1 = expensive_function(2, 10)
        assert result1 == 1024
        assert call_count == 1
        
        # Second call with same args - should use cache
        result2 = expensive_function(2, 10)
        assert result2 == 1024
        assert call_count == 1  # Not incremented
        
        # Different args - should compute
        result3 = expensive_function(3, 5)
        assert result3 == 243
        assert call_count == 2
    
    def test_quick_cache_with_kwargs(self):
        """Test quick_cache with keyword arguments."""
        call_count = 0
        
        @quick_cache(ttl=60)
        def function_with_kwargs(a, b=10, c=20):
            nonlocal call_count
            call_count += 1
            return a + b + c
        
        # Different ways of calling should have different cache keys
        result1 = function_with_kwargs(5)
        assert call_count == 1
        
        result2 = function_with_kwargs(5, b=10)
        assert call_count == 1  # Same as default
        
        result3 = function_with_kwargs(5, b=15)
        assert call_count == 2  # Different b value
        
        result4 = function_with_kwargs(5, c=25)
        assert call_count == 3  # Different c value