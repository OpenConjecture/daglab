"""
State management for DagLab notebooks.

This module provides utilities for persisting state across notebook cells,
managing run history, and caching results.
"""

import json
import pickle
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from cryptography.fernet import Fernet


class StateManager:
    """
    Manages persistent state across notebook cells and sessions.
    
    Uses SQLite for storage with support for TTL, namespacing,
    and encryption for sensitive data.
    """
    
    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        namespace: str = "default",
        encrypt_sensitive: bool = True
    ):
        """
        Initialize state manager.
        
        Args:
            db_path: Path to SQLite database (defaults to .daglab/state.db)
            namespace: Default namespace for state storage
            encrypt_sensitive: Whether to encrypt sensitive data
        """
        if db_path is None:
            db_path = Path.home() / ".daglab" / "state.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.namespace = namespace
        self.encrypt_sensitive = encrypt_sensitive
        
        # Initialize encryption
        if encrypt_sensitive:
            self._init_encryption()
        
        # Initialize database
        self._init_db()
    
    def _init_encryption(self):
        """Initialize encryption for sensitive data."""
        key_path = self.db_path.parent / ".state_key"
        
        if key_path.exists():
            self.cipher = Fernet(key_path.read_bytes())
        else:
            key = Fernet.generate_key()
            key_path.write_bytes(key)
            key_path.chmod(0o600)  # Restrict access
            self.cipher = Fernet(key)
    
    def _init_db(self):
        """Initialize SQLite database."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value BLOB NOT NULL,
                    value_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    metadata TEXT,
                    is_encrypted BOOLEAN DEFAULT FALSE,
                    UNIQUE(namespace, key)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_state_namespace_key 
                ON state(namespace, key)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_state_expires 
                ON state(expires_at)
            """)
            
            # Run history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS run_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    job_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    run_config TEXT,
                    tags TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_run_history_job 
                ON run_history(job_name, started_at DESC)
            """)
            
            # Results cache table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS results_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT NOT NULL UNIQUE,
                    result BLOB NOT NULL,
                    result_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_key 
                ON results_cache(cache_key)
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(
            self.db_path,
            isolation_level=None,  # Autocommit mode
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        encrypt: bool = False
    ) -> bool:
        """
        Store a value in state.
        
        Args:
            key: State key
            value: Value to store
            ttl: Time to live in seconds
            namespace: Namespace (uses default if None)
            metadata: Additional metadata
            encrypt: Whether to encrypt this value
            
        Returns:
            True if successful
        """
        namespace = namespace or self.namespace
        
        # Serialize value
        value_type = type(value).__name__
        try:
            if isinstance(value, (str, int, float, bool)):
                serialized = json.dumps(value).encode()
            else:
                serialized = pickle.dumps(value)
        except Exception as e:
            raise ValueError(f"Cannot serialize value: {e}")
        
        # Encrypt if requested
        is_encrypted = encrypt and self.encrypt_sensitive
        if is_encrypted:
            serialized = self.cipher.encrypt(serialized)
        
        # Calculate expiration
        expires_at = None
        if ttl:
            expires_at = datetime.now() + timedelta(seconds=ttl)
        
        # Store in database
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO state 
                    (namespace, key, value, value_type, expires_at, metadata, is_encrypted)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    namespace,
                    key,
                    serialized,
                    value_type,
                    expires_at,
                    json.dumps(metadata) if metadata else None,
                    is_encrypted
                ))
            return True
        except Exception as e:
            print(f"Failed to store state: {e}")
            return False
    
    def get(
        self,
        key: str,
        default: Any = None,
        namespace: Optional[str] = None
    ) -> Any:
        """
        Retrieve a value from state.
        
        Args:
            key: State key
            default: Default value if not found
            namespace: Namespace (uses default if None)
            
        Returns:
            Stored value or default
        """
        namespace = namespace or self.namespace
        
        with self._get_connection() as conn:
            # Clean expired entries
            conn.execute("""
                DELETE FROM state 
                WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP
            """)
            
            # Retrieve value
            row = conn.execute("""
                SELECT value, value_type, is_encrypted 
                FROM state 
                WHERE namespace = ? AND key = ?
            """, (namespace, key)).fetchone()
            
            if not row:
                return default
            
            # Decrypt if needed
            value_data = row["value"]
            if row["is_encrypted"] and self.encrypt_sensitive:
                value_data = self.cipher.decrypt(value_data)
            
            # Deserialize
            value_type = row["value_type"]
            try:
                if value_type in ["str", "int", "float", "bool"]:
                    return json.loads(value_data.decode())
                else:
                    return pickle.loads(value_data)
            except Exception as e:
                print(f"Failed to deserialize value: {e}")
                return default
    
    def delete(
        self,
        key: str,
        namespace: Optional[str] = None
    ) -> bool:
        """
        Delete a value from state.
        
        Args:
            key: State key
            namespace: Namespace (uses default if None)
            
        Returns:
            True if deleted
        """
        namespace = namespace or self.namespace
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM state 
                WHERE namespace = ? AND key = ?
            """, (namespace, key))
            
            return cursor.rowcount > 0
    
    def list_keys(
        self,
        pattern: Optional[str] = None,
        namespace: Optional[str] = None
    ) -> List[str]:
        """
        List all keys in namespace.
        
        Args:
            pattern: Optional pattern to filter keys (SQL LIKE syntax)
            namespace: Namespace (uses default if None)
            
        Returns:
            List of keys
        """
        namespace = namespace or self.namespace
        
        with self._get_connection() as conn:
            if pattern:
                rows = conn.execute("""
                    SELECT key FROM state 
                    WHERE namespace = ? AND key LIKE ?
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                    ORDER BY key
                """, (namespace, pattern)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT key FROM state 
                    WHERE namespace = ?
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                    ORDER BY key
                """, (namespace,)).fetchall()
            
            return [row["key"] for row in rows]
    
    def clear_namespace(self, namespace: Optional[str] = None) -> int:
        """
        Clear all values in a namespace.
        
        Args:
            namespace: Namespace to clear (uses default if None)
            
        Returns:
            Number of entries deleted
        """
        namespace = namespace or self.namespace
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM state 
                WHERE namespace = ?
            """, (namespace,))
            
            return cursor.rowcount
    
    def save_run(
        self,
        run_id: str,
        job_name: str,
        status: str,
        started_at: datetime,
        completed_at: Optional[datetime] = None,
        run_config: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save run information to history.
        
        Args:
            run_id: Dagster run ID
            job_name: Job name
            status: Run status
            started_at: Start timestamp
            completed_at: Completion timestamp
            run_config: Run configuration
            tags: Run tags
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO run_history 
                    (run_id, job_name, status, started_at, completed_at, 
                     run_config, tags, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id,
                    job_name,
                    status,
                    started_at,
                    completed_at,
                    json.dumps(run_config) if run_config else None,
                    json.dumps(tags) if tags else None,
                    json.dumps(metadata) if metadata else None
                ))
            return True
        except Exception as e:
            print(f"Failed to save run: {e}")
            return False
    
    def get_run_history(
        self,
        job_name: Optional[str] = None,
        limit: int = 10,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get run history.
        
        Args:
            job_name: Filter by job name
            limit: Maximum number of runs to return
            status_filter: Filter by status
            
        Returns:
            List of run records
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM run_history WHERE 1=1"
            params = []
            
            if job_name:
                query += " AND job_name = ?"
                params.append(job_name)
            
            if status_filter:
                query += " AND status = ?"
                params.append(status_filter)
            
            query += " ORDER BY started_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            
            return [
                {
                    "run_id": row["run_id"],
                    "job_name": row["job_name"],
                    "status": row["status"],
                    "started_at": row["started_at"],
                    "completed_at": row["completed_at"],
                    "run_config": json.loads(row["run_config"]) if row["run_config"] else None,
                    "tags": json.loads(row["tags"]) if row["tags"] else None,
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None
                }
                for row in rows
            ]
    
    def cache_result(
        self,
        cache_key: str,
        result: Any,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Cache a computation result.
        
        Args:
            cache_key: Cache key
            result: Result to cache
            ttl: Time to live in seconds
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        # Serialize result
        result_type = type(result).__name__
        try:
            serialized = pickle.dumps(result)
        except Exception as e:
            raise ValueError(f"Cannot serialize result: {e}")
        
        # Calculate expiration
        expires_at = None
        if ttl:
            expires_at = datetime.now() + timedelta(seconds=ttl)
        
        # Store in cache
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO results_cache 
                    (cache_key, result, result_type, expires_at, metadata, 
                     access_count, last_accessed)
                    VALUES (?, ?, ?, ?, ?, 
                            COALESCE((SELECT access_count FROM results_cache WHERE cache_key = ?), 0) + 1,
                            CURRENT_TIMESTAMP)
                """, (
                    cache_key,
                    serialized,
                    result_type,
                    expires_at,
                    json.dumps(metadata) if metadata else None,
                    cache_key
                ))
            return True
        except Exception as e:
            print(f"Failed to cache result: {e}")
            return False
    
    def get_cached_result(
        self,
        cache_key: str,
        default: Any = None
    ) -> Any:
        """
        Retrieve cached result.
        
        Args:
            cache_key: Cache key
            default: Default value if not found
            
        Returns:
            Cached result or default
        """
        with self._get_connection() as conn:
            # Clean expired entries
            conn.execute("""
                DELETE FROM results_cache 
                WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP
            """)
            
            # Retrieve result
            row = conn.execute("""
                SELECT result, result_type 
                FROM results_cache 
                WHERE cache_key = ?
            """, (cache_key,)).fetchone()
            
            if not row:
                return default
            
            # Update access stats
            conn.execute("""
                UPDATE results_cache 
                SET access_count = access_count + 1,
                    last_accessed = CURRENT_TIMESTAMP
                WHERE cache_key = ?
            """, (cache_key,))
            
            # Deserialize
            try:
                return pickle.loads(row["result"])
            except Exception as e:
                print(f"Failed to deserialize cached result: {e}")
                return default
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache statistics
        """
        with self._get_connection() as conn:
            # Overall stats
            stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_entries,
                    SUM(LENGTH(result)) as total_size,
                    AVG(access_count) as avg_access_count,
                    MAX(access_count) as max_access_count
                FROM results_cache
                WHERE expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP
            """).fetchone()
            
            # Most accessed
            most_accessed = conn.execute("""
                SELECT cache_key, access_count 
                FROM results_cache
                WHERE expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP
                ORDER BY access_count DESC
                LIMIT 5
            """).fetchall()
            
            return {
                "total_entries": stats["total_entries"] or 0,
                "total_size_mb": (stats["total_size"] or 0) / 1024 / 1024,
                "avg_access_count": float(stats["avg_access_count"] or 0),
                "max_access_count": stats["max_access_count"] or 0,
                "most_accessed": [
                    {"key": row["cache_key"], "count": row["access_count"]}
                    for row in most_accessed
                ]
            }
    
    def export_state(
        self,
        file_path: Union[str, Path],
        namespace: Optional[str] = None,
        include_cache: bool = False
    ):
        """
        Export state to file.
        
        Args:
            file_path: Export file path
            namespace: Namespace to export (all if None)
            include_cache: Whether to include cache entries
        """
        namespace = namespace or self.namespace
        
        with self._get_connection() as conn:
            # Export state
            if namespace:
                state_rows = conn.execute("""
                    SELECT * FROM state 
                    WHERE namespace = ?
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                """, (namespace,)).fetchall()
            else:
                state_rows = conn.execute("""
                    SELECT * FROM state 
                    WHERE expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP
                """).fetchall()
            
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "state": [dict(row) for row in state_rows]
            }
            
            # Include cache if requested
            if include_cache:
                cache_rows = conn.execute("""
                    SELECT cache_key, result_type, created_at, expires_at, 
                           access_count, metadata
                    FROM results_cache
                    WHERE expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP
                """).fetchall()
                
                export_data["cache"] = [dict(row) for row in cache_rows]
            
            # Save to file
            path = Path(file_path)
            with open(path, "w") as f:
                json.dump(export_data, f, indent=2, default=str)
    
    def cleanup_expired(self) -> Tuple[int, int]:
        """
        Clean up expired entries.
        
        Returns:
            Tuple of (state_deleted, cache_deleted)
        """
        with self._get_connection() as conn:
            state_cursor = conn.execute("""
                DELETE FROM state 
                WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP
            """)
            
            cache_cursor = conn.execute("""
                DELETE FROM results_cache 
                WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP
            """)
            
            return state_cursor.rowcount, cache_cursor.rowcount
    
    def get_state_version(self) -> int:
        """Get current state schema version."""
        with self._get_connection() as conn:
            # Check if version table exists
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='schema_version'
            """)
            
            if not cursor.fetchone():
                # Create version table
                conn.execute("""
                    CREATE TABLE schema_version (
                        version INTEGER PRIMARY KEY,
                        migrated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("INSERT INTO schema_version (version) VALUES (1)")
                return 1
            
            # Get current version
            row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
            return row[0] if row else 1
    
    def migrate_state(self, target_version: int) -> bool:
        """Migrate state to target schema version."""
        current_version = self.get_state_version()
        
        if current_version >= target_version:
            return True
        
        migrations = {
            2: self._migrate_to_v2,
            3: self._migrate_to_v3,
        }
        
        with self._get_connection() as conn:
            for version in range(current_version + 1, target_version + 1):
                if version in migrations:
                    try:
                        migrations[version](conn)
                        conn.execute(
                            "INSERT INTO schema_version (version) VALUES (?)",
                            (version,)
                        )
                        conn.commit()
                    except Exception as e:
                        print(f"Migration to v{version} failed: {e}")
                        return False
        
        return True
    
    def _migrate_to_v2(self, conn):
        """Migration to schema version 2."""
        # Add access tracking to state table
        conn.execute("""
            ALTER TABLE state 
            ADD COLUMN access_count INTEGER DEFAULT 0
        """)
        conn.execute("""
            ALTER TABLE state 
            ADD COLUMN last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """)
    
    def _migrate_to_v3(self, conn):
        """Migration to schema version 3."""
        # Add state compression
        conn.execute("""
            ALTER TABLE state 
            ADD COLUMN is_compressed BOOLEAN DEFAULT FALSE
        """)
        conn.execute("""
            ALTER TABLE results_cache 
            ADD COLUMN is_compressed BOOLEAN DEFAULT FALSE
        """)
    
    def verify_integrity(self) -> Dict[str, Any]:
        """Verify state database integrity."""
        issues = []
        
        with self._get_connection() as conn:
            # Check integrity
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if result[0] != "ok":
                issues.append(f"Database integrity check failed: {result[0]}")
            
            # Check for orphaned entries
            orphaned = conn.execute("""
                SELECT COUNT(*) FROM state 
                WHERE namespace NOT IN (
                    SELECT DISTINCT namespace FROM state 
                    WHERE key = '__namespace_meta__'
                )
            """).fetchone()[0]
            
            if orphaned > 0:
                issues.append(f"Found {orphaned} orphaned state entries")
            
            # Check encryption key
            if self.encrypt_sensitive:
                try:
                    test_data = b"test"
                    encrypted = self.cipher.encrypt(test_data)
                    decrypted = self.cipher.decrypt(encrypted)
                    if decrypted != test_data:
                        issues.append("Encryption key verification failed")
                except:
                    issues.append("Encryption system is not functional")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "version": self.get_state_version(),
        }
    
    def recover_corrupted_state(self) -> Dict[str, Any]:
        """Attempt to recover from corrupted state."""
        recovery_stats = {
            "recovered": 0,
            "lost": 0,
            "actions": [],
        }
        
        backup_path = self.db_path.with_suffix('.backup')
        
        try:
            # Create backup
            import shutil
            shutil.copy2(self.db_path, backup_path)
            recovery_stats["actions"].append(f"Created backup at {backup_path}")
            
            with self._get_connection() as conn:
                # Try to recover each table
                tables = ["state", "run_history", "results_cache"]
                
                for table in tables:
                    try:
                        # Dump and recreate table
                        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                        recovery_stats["recovered"] += len(rows)
                        
                        # Store schema
                        schema = conn.execute(
                            f"SELECT sql FROM sqlite_master WHERE name='{table}'"
                        ).fetchone()[0]
                        
                        # Drop and recreate
                        conn.execute(f"DROP TABLE {table}")
                        conn.execute(schema)
                        
                        # Reinsert data
                        if rows:
                            placeholders = ",".join(["?" for _ in rows[0]])
                            conn.executemany(
                                f"INSERT INTO {table} VALUES ({placeholders})",
                                rows
                            )
                        
                        recovery_stats["actions"].append(
                            f"Recovered {len(rows)} entries from {table}"
                        )
                    except Exception as e:
                        recovery_stats["lost"] += 1
                        recovery_stats["actions"].append(
                            f"Failed to recover {table}: {e}"
                        )
                
                # Vacuum database
                conn.execute("VACUUM")
                recovery_stats["actions"].append("Database vacuumed")
                
        except Exception as e:
            recovery_stats["actions"].append(f"Recovery failed: {e}")
            recovery_stats["success"] = False
        else:
            recovery_stats["success"] = True
        
        return recovery_stats
    
    def create_rollback_point(self, name: str) -> str:
        """Create a rollback point for state."""
        rollback_id = f"rollback_{name}_{int(time.time())}"
        rollback_path = self.db_path.parent / "rollbacks" / f"{rollback_id}.db"
        rollback_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy current state
        import shutil
        shutil.copy2(self.db_path, rollback_path)
        
        # Record rollback metadata
        self.set(
            "__rollback_meta__",
            {
                "id": rollback_id,
                "name": name,
                "created_at": datetime.now().isoformat(),
                "path": str(rollback_path),
            },
            namespace="__system__"
        )
        
        return rollback_id
    
    def rollback_to(self, rollback_id: str) -> bool:
        """Rollback state to a previous point."""
        # Get rollback metadata
        meta = self.get("__rollback_meta__", namespace="__system__")
        if not meta or meta.get("id") != rollback_id:
            print(f"Rollback point {rollback_id} not found")
            return False
        
        rollback_path = Path(meta["path"])
        if not rollback_path.exists():
            print(f"Rollback file not found: {rollback_path}")
            return False
        
        try:
            # Create backup of current state
            backup_path = self.db_path.with_suffix('.pre_rollback')
            import shutil
            shutil.copy2(self.db_path, backup_path)
            
            # Restore from rollback
            shutil.copy2(rollback_path, self.db_path)
            
            return True
        except Exception as e:
            print(f"Rollback failed: {e}")
            return False
    
    def compress_state(self, older_than_days: int = 30) -> Dict[str, int]:
        """Compress old state entries to save space."""
        import zlib
        import base64
        
        stats = {"compressed": 0, "saved_bytes": 0}
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        
        with self._get_connection() as conn:
            # Find entries to compress
            rows = conn.execute("""
                SELECT id, value, value_type 
                FROM state 
                WHERE created_at < ? 
                AND is_compressed = FALSE
                AND LENGTH(value) > 1000
            """, (cutoff_date,)).fetchall()
            
            for row in rows:
                try:
                    original_size = len(row["value"])
                    compressed = zlib.compress(row["value"], level=9)
                    compressed_b64 = base64.b64encode(compressed)
                    compressed_size = len(compressed_b64)
                    
                    if compressed_size < original_size * 0.8:  # Only if 20% savings
                        conn.execute("""
                            UPDATE state 
                            SET value = ?, is_compressed = TRUE 
                            WHERE id = ?
                        """, (compressed_b64, row["id"]))
                        
                        stats["compressed"] += 1
                        stats["saved_bytes"] += original_size - compressed_size
                except:
                    pass
            
            # Same for cache
            cache_rows = conn.execute("""
                SELECT id, result 
                FROM results_cache 
                WHERE created_at < ? 
                AND is_compressed = FALSE
                AND LENGTH(result) > 1000
            """, (cutoff_date,)).fetchall()
            
            for row in cache_rows:
                try:
                    original_size = len(row["result"])
                    compressed = zlib.compress(row["result"], level=9)
                    compressed_b64 = base64.b64encode(compressed)
                    compressed_size = len(compressed_b64)
                    
                    if compressed_size < original_size * 0.8:
                        conn.execute("""
                            UPDATE results_cache 
                            SET result = ?, is_compressed = TRUE 
                            WHERE id = ?
                        """, (compressed_b64, row["id"]))
                        
                        stats["compressed"] += 1
                        stats["saved_bytes"] += original_size - compressed_size
                except:
                    pass
        
        return stats
    
    def debug_state(self, key: str, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Get debug information about a state entry."""
        namespace = namespace or self.namespace
        
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM state 
                WHERE namespace = ? AND key = ?
            """, (namespace, key)).fetchone()
            
            if not row:
                return {"exists": False}
            
            debug_info = dict(row)
            debug_info["exists"] = True
            debug_info["value_size"] = len(row["value"])
            debug_info["is_expired"] = (
                row["expires_at"] is not None and 
                datetime.fromisoformat(row["expires_at"]) < datetime.now()
            )
            
            # Try to peek at value type
            try:
                if row["value_type"] in ["str", "int", "float", "bool"]:
                    debug_info["preview"] = str(json.loads(row["value"].decode()))[:100]
                else:
                    debug_info["preview"] = "<binary data>"
            except:
                debug_info["preview"] = "<unable to preview>"
            
            return debug_info


# Convenience functions
def create_state_manager(namespace: str = "default") -> StateManager:
    """Create a state manager instance."""
    return StateManager(namespace=namespace)


def quick_cache(ttl: int = 3600):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds
        
    Example:
        @quick_cache(ttl=3600)
        def expensive_computation(x, y):
            return x ** y
    """
    def decorator(func):
        manager = StateManager()
        
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"func:{func.__name__}:{args}:{sorted(kwargs.items())}"
            
            # Check cache
            result = manager.get_cached_result(cache_key)
            if result is not None:
                return result
            
            # Compute and cache
            result = func(*args, **kwargs)
            manager.cache_result(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    
    return decorator