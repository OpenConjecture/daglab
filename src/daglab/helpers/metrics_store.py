"""
Metrics storage system for DagLab performance monitoring.

Provides persistent storage and querying for performance metrics using SQLite.
"""

import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from enum import Enum

import pandas as pd
import numpy as np

from .performance import PerformanceMetrics


class AggregationType(Enum):
    """Metric aggregation types."""
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    SUM = "sum"
    COUNT = "count"
    P50 = "p50"
    P95 = "p95"
    P99 = "p99"
    STDDEV = "stddev"


class RetentionPolicy:
    """
    Data retention policy for metrics.
    
    Defines how long to keep metrics data at different resolutions.
    """
    
    def __init__(
        self,
        raw_retention_days: int = 7,
        hourly_retention_days: int = 30,
        daily_retention_days: int = 365
    ):
        """
        Initialize retention policy.
        
        Args:
            raw_retention_days: Days to keep raw metrics
            hourly_retention_days: Days to keep hourly aggregates
            daily_retention_days: Days to keep daily aggregates
        """
        self.raw_retention_days = raw_retention_days
        self.hourly_retention_days = hourly_retention_days
        self.daily_retention_days = daily_retention_days


class MetricsStore:
    """
    SQLite-based metrics storage with time-series capabilities.
    
    Provides efficient storage, aggregation, and querying of performance metrics.
    """
    
    def __init__(
        self,
        db_path: Union[str, Path] = "metrics.db",
        retention_policy: Optional[RetentionPolicy] = None
    ):
        """
        Initialize metrics store.
        
        Args:
            db_path: Path to SQLite database
            retention_policy: Data retention policy
        """
        self.db_path = Path(db_path)
        self.retention_policy = retention_policy or RetentionPolicy()
        
        # Create database and tables
        self._init_database()
        
    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            # Raw metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    operation TEXT NOT NULL,
                    duration REAL NOT NULL,
                    cpu_percent REAL NOT NULL,
                    memory_mb REAL NOT NULL,
                    memory_percent REAL NOT NULL,
                    memory_delta_mb REAL NOT NULL,
                    io_read_mb REAL NOT NULL,
                    io_write_mb REAL NOT NULL,
                    error_count INTEGER NOT NULL,
                    metadata TEXT,
                    tracker_name TEXT,
                    created_at REAL DEFAULT (julianday('now'))
                )
            """)
            
            # Indexes for efficient queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
                ON metrics(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_operation 
                ON metrics(operation)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_tracker 
                ON metrics(tracker_name)
            """)
            
            # Aggregated metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics_aggregated (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    operation TEXT NOT NULL,
                    aggregation_type TEXT NOT NULL,
                    aggregation_period TEXT NOT NULL,
                    duration_avg REAL,
                    duration_min REAL,
                    duration_max REAL,
                    duration_p50 REAL,
                    duration_p95 REAL,
                    duration_p99 REAL,
                    duration_stddev REAL,
                    cpu_avg REAL,
                    cpu_max REAL,
                    memory_avg REAL,
                    memory_max REAL,
                    io_read_sum REAL,
                    io_write_sum REAL,
                    error_sum INTEGER,
                    sample_count INTEGER,
                    created_at REAL DEFAULT (julianday('now'))
                )
            """)
            
            # Indexes for aggregated metrics
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agg_timestamp_operation 
                ON metrics_aggregated(timestamp, operation)
            """)
            
            # Alerts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    operation TEXT,
                    metric_name TEXT,
                    metric_value REAL,
                    threshold REAL,
                    message TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolved_at REAL,
                    created_at REAL DEFAULT (julianday('now'))
                )
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def store_metric(self, metric: PerformanceMetrics, tracker_name: str = "default"):
        """
        Store a performance metric.
        
        Args:
            metric: Performance metric to store
            tracker_name: Name of the tracker
        """
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO metrics (
                    timestamp, operation, duration, cpu_percent,
                    memory_mb, memory_percent, memory_delta_mb,
                    io_read_mb, io_write_mb, error_count,
                    metadata, tracker_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metric.start_time,
                metric.operation,
                metric.duration,
                metric.cpu_percent,
                metric.memory_mb,
                metric.memory_percent,
                metric.memory_delta_mb,
                metric.io_read_mb,
                metric.io_write_mb,
                len(metric.errors),
                json.dumps(metric.metadata),
                tracker_name
            ))
            conn.commit()
    
    def store_metrics_batch(self, metrics: List[PerformanceMetrics], 
                          tracker_name: str = "default"):
        """
        Store multiple metrics in batch.
        
        Args:
            metrics: List of metrics to store
            tracker_name: Name of the tracker
        """
        with self._get_connection() as conn:
            data = [
                (
                    m.start_time, m.operation, m.duration, m.cpu_percent,
                    m.memory_mb, m.memory_percent, m.memory_delta_mb,
                    m.io_read_mb, m.io_write_mb, len(m.errors),
                    json.dumps(m.metadata), tracker_name
                )
                for m in metrics
            ]
            
            conn.executemany("""
                INSERT INTO metrics (
                    timestamp, operation, duration, cpu_percent,
                    memory_mb, memory_percent, memory_delta_mb,
                    io_read_mb, io_write_mb, error_count,
                    metadata, tracker_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            conn.commit()
    
    def query_metrics(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        operation: Optional[str] = None,
        tracker_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Query metrics with filters.
        
        Args:
            start_time: Start timestamp
            end_time: End timestamp
            operation: Filter by operation name
            tracker_name: Filter by tracker name
            limit: Maximum number of results
            
        Returns:
            List of metrics
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM metrics WHERE 1=1"
            params = []
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)
            
            if operation:
                query += " AND operation = ?"
                params.append(operation)
            
            if tracker_name:
                query += " AND tracker_name = ?"
                params.append(tracker_name)
            
            query += " ORDER BY timestamp DESC"
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor = conn.execute(query, params)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def aggregate_metrics(
        self,
        start_time: float,
        end_time: float,
        aggregation_period: str = "hour",
        operations: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Aggregate metrics over time periods.
        
        Args:
            start_time: Start timestamp
            end_time: End timestamp
            aggregation_period: 'minute', 'hour', 'day'
            operations: Filter by operation names
            
        Returns:
            DataFrame with aggregated metrics
        """
        # Query raw metrics
        with self._get_connection() as conn:
            query = """
                SELECT * FROM metrics 
                WHERE timestamp >= ? AND timestamp <= ?
            """
            params = [start_time, end_time]
            
            if operations:
                placeholders = ','.join(['?' for _ in operations])
                query += f" AND operation IN ({placeholders})"
                params.extend(operations)
            
            df = pd.read_sql_query(query, conn, params=params)
        
        if df.empty:
            return pd.DataFrame()
        
        # Convert timestamp to datetime
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        
        # Set aggregation frequency
        freq_map = {
            'minute': 'T',
            'hour': 'H',
            'day': 'D'
        }
        freq = freq_map.get(aggregation_period, 'H')
        
        # Group and aggregate
        aggregated = df.groupby([
            pd.Grouper(key='datetime', freq=freq),
            'operation'
        ]).agg({
            'duration': ['mean', 'min', 'max', 'std', 'count'],
            'cpu_percent': ['mean', 'max'],
            'memory_mb': ['mean', 'max'],
            'io_read_mb': 'sum',
            'io_write_mb': 'sum',
            'error_count': 'sum'
        })
        
        # Add percentiles
        percentiles = df.groupby([
            pd.Grouper(key='datetime', freq=freq),
            'operation'
        ])['duration'].quantile([0.5, 0.95, 0.99]).unstack()
        
        percentiles.columns = ['duration_p50', 'duration_p95', 'duration_p99']
        
        # Combine results
        result = pd.concat([aggregated, percentiles], axis=1)
        result.columns = ['_'.join(col).strip() for col in result.columns]
        
        return result.reset_index()
    
    def calculate_percentiles(
        self,
        metric_name: str,
        operation: Optional[str] = None,
        percentiles: List[float] = [0.5, 0.95, 0.99],
        last_hours: Optional[int] = None
    ) -> Dict[float, float]:
        """
        Calculate percentiles for a metric.
        
        Args:
            metric_name: Metric to calculate ('duration', 'cpu_percent', etc.)
            operation: Filter by operation
            percentiles: List of percentiles to calculate
            last_hours: Limit to last N hours
            
        Returns:
            Dict mapping percentile to value
        """
        with self._get_connection() as conn:
            query = f"SELECT {metric_name} FROM metrics WHERE 1=1"
            params = []
            
            if operation:
                query += " AND operation = ?"
                params.append(operation)
            
            if last_hours:
                cutoff = time.time() - (last_hours * 3600)
                query += " AND timestamp > ?"
                params.append(cutoff)
            
            cursor = conn.execute(query, params)
            values = [row[0] for row in cursor.fetchall()]
        
        if not values:
            return {p: 0.0 for p in percentiles}
        
        return {
            p: float(np.percentile(values, p * 100))
            for p in percentiles
        }
    
    def apply_retention_policy(self):
        """Apply data retention policy to remove old data."""
        current_time = time.time()
        
        with self._get_connection() as conn:
            # Remove old raw metrics
            raw_cutoff = current_time - (self.retention_policy.raw_retention_days * 86400)
            conn.execute(
                "DELETE FROM metrics WHERE timestamp < ?",
                (raw_cutoff,)
            )
            
            # Remove old aggregated metrics
            hourly_cutoff = current_time - (self.retention_policy.hourly_retention_days * 86400)
            conn.execute(
                "DELETE FROM metrics_aggregated WHERE timestamp < ? AND aggregation_period = 'hour'",
                (hourly_cutoff,)
            )
            
            daily_cutoff = current_time - (self.retention_policy.daily_retention_days * 86400)
            conn.execute(
                "DELETE FROM metrics_aggregated WHERE timestamp < ? AND aggregation_period = 'day'",
                (daily_cutoff,)
            )
            
            conn.commit()
            
            # Vacuum to reclaim space
            conn.execute("VACUUM")
    
    def export_metrics(
        self,
        file_path: Union[str, Path],
        format: str = "csv",
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ):
        """
        Export metrics to file.
        
        Args:
            file_path: Output file path
            format: Export format ('csv', 'json', 'parquet')
            start_time: Start timestamp filter
            end_time: End timestamp filter
        """
        # Query metrics
        metrics = self.query_metrics(start_time=start_time, end_time=end_time)
        
        if not metrics:
            return
        
        path = Path(file_path)
        
        if format == "csv":
            df = pd.DataFrame(metrics)
            df.to_csv(path, index=False)
        
        elif format == "json":
            with open(path, "w") as f:
                json.dump(metrics, f, indent=2, default=str)
        
        elif format == "parquet":
            df = pd.DataFrame(metrics)
            df.to_parquet(path, index=False)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def import_metrics(
        self,
        file_path: Union[str, Path],
        format: str = "csv",
        tracker_name: str = "imported"
    ):
        """
        Import metrics from file.
        
        Args:
            file_path: Input file path
            format: Import format ('csv', 'json', 'parquet')
            tracker_name: Tracker name for imported metrics
        """
        path = Path(file_path)
        
        if format == "csv":
            df = pd.read_csv(path)
        elif format == "json":
            with open(path, "r") as f:
                data = json.load(f)
            df = pd.DataFrame(data)
        elif format == "parquet":
            df = pd.read_parquet(path)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # Convert to metrics and store
        with self._get_connection() as conn:
            for _, row in df.iterrows():
                conn.execute("""
                    INSERT INTO metrics (
                        timestamp, operation, duration, cpu_percent,
                        memory_mb, memory_percent, memory_delta_mb,
                        io_read_mb, io_write_mb, error_count,
                        metadata, tracker_name
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row.get('timestamp', time.time()),
                    row.get('operation', 'unknown'),
                    row.get('duration', 0),
                    row.get('cpu_percent', 0),
                    row.get('memory_mb', 0),
                    row.get('memory_percent', 0),
                    row.get('memory_delta_mb', 0),
                    row.get('io_read_mb', 0),
                    row.get('io_write_mb', 0),
                    row.get('error_count', 0),
                    json.dumps(row.get('metadata', {})),
                    tracker_name
                ))
            conn.commit()
    
    def get_statistics(
        self,
        operation: Optional[str] = None,
        last_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get statistical summary of metrics.
        
        Args:
            operation: Filter by operation
            last_hours: Limit to last N hours
            
        Returns:
            Statistical summary
        """
        with self._get_connection() as conn:
            query = """
                SELECT 
                    COUNT(*) as count,
                    AVG(duration) as avg_duration,
                    MIN(duration) as min_duration,
                    MAX(duration) as max_duration,
                    AVG(cpu_percent) as avg_cpu,
                    MAX(cpu_percent) as max_cpu,
                    AVG(memory_mb) as avg_memory,
                    MAX(memory_mb) as max_memory,
                    SUM(io_read_mb) as total_io_read,
                    SUM(io_write_mb) as total_io_write,
                    SUM(error_count) as total_errors
                FROM metrics WHERE 1=1
            """
            params = []
            
            if operation:
                query += " AND operation = ?"
                params.append(operation)
            
            if last_hours:
                cutoff = time.time() - (last_hours * 3600)
                query += " AND timestamp > ?"
                params.append(cutoff)
            
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            
            return {}
    
    def create_aggregates(self, period: str = "hour"):
        """
        Create aggregated metrics for faster queries.
        
        Args:
            period: Aggregation period ('hour', 'day')
        """
        # Determine time boundaries
        current_time = time.time()
        
        if period == "hour":
            interval = 3600
            cutoff = current_time - (7 * 86400)  # Last 7 days
        else:  # day
            interval = 86400
            cutoff = current_time - (30 * 86400)  # Last 30 days
        
        with self._get_connection() as conn:
            # Get distinct operations
            cursor = conn.execute(
                "SELECT DISTINCT operation FROM metrics WHERE timestamp > ?",
                (cutoff,)
            )
            operations = [row[0] for row in cursor.fetchall()]
            
            # Create aggregates for each operation
            for operation in operations:
                # Query metrics for aggregation
                query = """
                    SELECT 
                        CAST(timestamp / ? AS INTEGER) * ? as period_start,
                        AVG(duration) as duration_avg,
                        MIN(duration) as duration_min,
                        MAX(duration) as duration_max,
                        AVG(cpu_percent) as cpu_avg,
                        MAX(cpu_percent) as cpu_max,
                        AVG(memory_mb) as memory_avg,
                        MAX(memory_mb) as memory_max,
                        SUM(io_read_mb) as io_read_sum,
                        SUM(io_write_mb) as io_write_sum,
                        SUM(error_count) as error_sum,
                        COUNT(*) as sample_count
                    FROM metrics 
                    WHERE operation = ? AND timestamp > ?
                    GROUP BY period_start
                """
                
                cursor = conn.execute(query, (interval, interval, operation, cutoff))
                
                for row in cursor.fetchall():
                    # Check if aggregate already exists
                    existing = conn.execute(
                        """
                        SELECT id FROM metrics_aggregated 
                        WHERE timestamp = ? AND operation = ? AND aggregation_period = ?
                        """,
                        (row[0], operation, period)
                    ).fetchone()
                    
                    if not existing:
                        conn.execute("""
                            INSERT INTO metrics_aggregated (
                                timestamp, operation, aggregation_type, aggregation_period,
                                duration_avg, duration_min, duration_max,
                                cpu_avg, cpu_max, memory_avg, memory_max,
                                io_read_sum, io_write_sum, error_sum, sample_count
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            row[0], operation, 'standard', period,
                            row[1], row[2], row[3], row[4], row[5],
                            row[6], row[7], row[8], row[9], row[10], row[11]
                        ))
            
            conn.commit()


# Convenience functions
def create_metrics_store(db_path: str = "metrics.db") -> MetricsStore:
    """
    Create a metrics store with default configuration.
    
    Args:
        db_path: Database file path
        
    Returns:
        Configured MetricsStore instance
    """
    return MetricsStore(db_path)