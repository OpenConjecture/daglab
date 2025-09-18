"""
Performance monitoring dashboard for DagLab.

Provides real-time and historical performance monitoring via a web interface.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from .performance import PerformanceTracker, MetricsCollector


class DashboardConfig(BaseModel):
    """Dashboard configuration."""
    host: str = "127.0.0.1"
    port: int = 8765
    refresh_interval: float = 1.0
    max_history_points: int = 100
    alert_thresholds: Dict[str, float] = {
        "cpu_percent": 80.0,
        "memory_percent": 85.0,
        "duration_seconds": 10.0,
        "error_rate": 0.1
    }


class Alert(BaseModel):
    """Performance alert."""
    id: str
    timestamp: float
    level: str  # info, warning, error, critical
    metric: str
    value: float
    threshold: float
    message: str


class DashboardServer:
    """
    Real-time performance monitoring dashboard server.
    
    Provides WebSocket-based real-time updates and HTTP endpoints for
    historical data and configuration.
    """
    
    def __init__(self, config: Optional[DashboardConfig] = None):
        """
        Initialize dashboard server.
        
        Args:
            config: Dashboard configuration
        """
        self.config = config or DashboardConfig()
        self.app = FastAPI(title="DagLab Performance Dashboard")
        self.metrics_collector = MetricsCollector()
        self.active_connections: Set[WebSocket] = set()
        self.alerts: List[Alert] = []
        self.history: Dict[str, List[Dict[str, Any]]] = {
            "cpu": [],
            "memory": [],
            "operations": [],
            "errors": []
        }
        
        # Setup routes
        self._setup_routes()
        
        # Background tasks
        self._monitor_task = None
        
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/")
        async def dashboard():
            """Serve dashboard HTML."""
            return HTMLResponse(self._get_dashboard_html())
        
        @self.app.get("/api/status")
        async def get_status():
            """Get current system status."""
            return JSONResponse({
                "status": "running",
                "timestamp": time.time(),
                "trackers": list(self.metrics_collector.trackers.keys()),
                "alerts": len(self.alerts),
                "connections": len(self.active_connections)
            })
        
        @self.app.get("/api/metrics")
        async def get_metrics(last_seconds: Optional[int] = None):
            """Get aggregated metrics."""
            metrics = self.metrics_collector.get_aggregated_metrics()
            
            if last_seconds:
                # Filter history to last N seconds
                cutoff = time.time() - last_seconds
                filtered_history = {}
                for key, values in self.history.items():
                    filtered_history[key] = [
                        v for v in values
                        if v.get("timestamp", 0) > cutoff
                    ]
                metrics["history"] = filtered_history
            
            return JSONResponse(metrics)
        
        @self.app.get("/api/alerts")
        async def get_alerts(active_only: bool = True):
            """Get alerts."""
            if active_only:
                # Return only recent alerts (last 5 minutes)
                cutoff = time.time() - 300
                active_alerts = [
                    alert.dict() for alert in self.alerts
                    if alert.timestamp > cutoff
                ]
                return JSONResponse({"alerts": active_alerts})
            
            return JSONResponse({
                "alerts": [alert.dict() for alert in self.alerts]
            })
        
        @self.app.post("/api/alerts/clear")
        async def clear_alerts():
            """Clear all alerts."""
            self.alerts.clear()
            return JSONResponse({"message": "Alerts cleared"})
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates."""
            await websocket.accept()
            self.active_connections.add(websocket)
            
            try:
                while True:
                    # Send updates periodically
                    await asyncio.sleep(self.config.refresh_interval)
                    
                    # Collect current metrics
                    metrics = self._collect_current_metrics()
                    
                    # Check for alerts
                    self._check_alerts(metrics)
                    
                    # Send to client
                    await websocket.send_json({
                        "type": "metrics",
                        "data": metrics,
                        "timestamp": time.time()
                    })
                    
                    # Send any new alerts
                    if self.alerts:
                        recent_alerts = [
                            alert.dict() for alert in self.alerts[-5:]
                        ]
                        await websocket.send_json({
                            "type": "alerts",
                            "data": recent_alerts
                        })
                        
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
            except Exception as e:
                self.active_connections.remove(websocket)
                raise e
        
        @self.app.get("/api/export")
        async def export_dashboard(format: str = "html"):
            """Export dashboard as static file."""
            if format == "html":
                return HTMLResponse(self._export_static_html())
            elif format == "json":
                return JSONResponse(self._export_json_data())
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
    
    def register_tracker(self, tracker: PerformanceTracker):
        """
        Register a performance tracker.
        
        Args:
            tracker: PerformanceTracker instance
        """
        self.metrics_collector.register_tracker(tracker)
    
    async def start(self):
        """Start dashboard server."""
        # Start metrics collection
        self.metrics_collector.start_collection(self.config.refresh_interval)
        
        # Start monitoring task
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        
        # Run server
        config = uvicorn.Config(
            app=self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    async def stop(self):
        """Stop dashboard server."""
        # Stop monitoring
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        # Stop metrics collection
        self.metrics_collector.stop_collection()
        
        # Close WebSocket connections
        for connection in list(self.active_connections):
            await connection.close()
    
    def _collect_current_metrics(self) -> Dict[str, Any]:
        """Collect current performance metrics."""
        # Get system metrics
        system_metrics = self.metrics_collector.collect_system_metrics()
        
        # Get tracker metrics
        tracker_metrics = {}
        for name, tracker in self.metrics_collector.trackers.items():
            # Get recent operations
            recent_ops = []
            if tracker.metrics:
                # Last 10 operations
                for metric in tracker.metrics[-10:]:
                    recent_ops.append({
                        "operation": metric.operation,
                        "duration": metric.duration,
                        "cpu": metric.cpu_percent,
                        "memory": metric.memory_mb,
                        "errors": len(metric.errors),
                        "timestamp": metric.start_time
                    })
            
            tracker_metrics[name] = {
                "summary": tracker.get_summary(),
                "recent_operations": recent_ops
            }
        
        return {
            "system": system_metrics,
            "trackers": tracker_metrics
        }
    
    def _check_alerts(self, metrics: Dict[str, Any]):
        """Check metrics against alert thresholds."""
        timestamp = time.time()
        
        # Check system metrics
        if "system" in metrics:
            system = metrics["system"]
            
            # CPU alert
            cpu_percent = system.get("cpu", {}).get("percent", 0)
            if cpu_percent > self.config.alert_thresholds["cpu_percent"]:
                self._add_alert(
                    level="warning" if cpu_percent < 90 else "critical",
                    metric="cpu_percent",
                    value=cpu_percent,
                    threshold=self.config.alert_thresholds["cpu_percent"],
                    message=f"High CPU usage: {cpu_percent:.1f}%"
                )
            
            # Memory alert
            mem_percent = system.get("memory", {}).get("percent", 0)
            if mem_percent > self.config.alert_thresholds["memory_percent"]:
                self._add_alert(
                    level="warning" if mem_percent < 95 else "critical",
                    metric="memory_percent",
                    value=mem_percent,
                    threshold=self.config.alert_thresholds["memory_percent"],
                    message=f"High memory usage: {mem_percent:.1f}%"
                )
        
        # Check operation metrics
        for tracker_name, tracker_data in metrics.get("trackers", {}).items():
            recent_ops = tracker_data.get("recent_operations", [])
            
            for op in recent_ops:
                # Duration alert
                if op["duration"] > self.config.alert_thresholds["duration_seconds"]:
                    self._add_alert(
                        level="warning",
                        metric="duration",
                        value=op["duration"],
                        threshold=self.config.alert_thresholds["duration_seconds"],
                        message=f"Slow operation '{op['operation']}': {op['duration']:.2f}s"
                    )
                
                # Error rate alert
                if op["errors"] > 0:
                    self._add_alert(
                        level="error",
                        metric="errors",
                        value=op["errors"],
                        threshold=0,
                        message=f"Errors in operation '{op['operation']}': {op['errors']} errors"
                    )
    
    def _add_alert(self, level: str, metric: str, value: float,
                   threshold: float, message: str):
        """Add a new alert."""
        alert = Alert(
            id=str(uuid4()),
            timestamp=time.time(),
            level=level,
            metric=metric,
            value=value,
            threshold=threshold,
            message=message
        )
        
        self.alerts.append(alert)
        
        # Keep only last 1000 alerts
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while True:
            try:
                # Collect metrics
                metrics = self._collect_current_metrics()
                
                # Update history
                timestamp = time.time()
                
                if "system" in metrics:
                    self.history["cpu"].append({
                        "timestamp": timestamp,
                        "value": metrics["system"].get("cpu", {}).get("percent", 0)
                    })
                    self.history["memory"].append({
                        "timestamp": timestamp,
                        "value": metrics["system"].get("memory", {}).get("percent", 0)
                    })
                
                # Trim history
                max_points = self.config.max_history_points
                for key in self.history:
                    if len(self.history[key]) > max_points:
                        self.history[key] = self.history[key][-max_points:]
                
                # Sleep
                await asyncio.sleep(self.config.refresh_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
    
    def _get_dashboard_html(self) -> str:
        """Get dashboard HTML."""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>DagLab Performance Dashboard</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: #f5f5f5;
        }
        
        .header {
            background: #2196F3;
            color: white;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1rem;
            padding: 1rem;
        }
        
        .card {
            background: white;
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 0.5rem 0;
        }
        
        .metric-value {
            font-size: 1.5rem;
            font-weight: bold;
        }
        
        .alert {
            padding: 0.5rem;
            margin: 0.5rem 0;
            border-radius: 4px;
        }
        
        .alert-warning { background: #fff3cd; color: #856404; }
        .alert-error { background: #f8d7da; color: #721c24; }
        .alert-critical { background: #721c24; color: white; }
        
        .chart {
            width: 100%;
            height: 200px;
            margin-top: 1rem;
        }
        
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 0.5rem;
        }
        
        .status-ok { background: #4caf50; }
        .status-warning { background: #ff9800; }
        .status-error { background: #f44336; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="header">
        <h1>DagLab Performance Dashboard</h1>
        <p>Real-time performance monitoring</p>
    </div>
    
    <div class="container">
        <div class="card">
            <h2>System Status</h2>
            <div class="metric">
                <span>CPU Usage</span>
                <span class="metric-value" id="cpu-usage">0%</span>
            </div>
            <div class="metric">
                <span>Memory Usage</span>
                <span class="metric-value" id="memory-usage">0%</span>
            </div>
            <div class="metric">
                <span>Active Operations</span>
                <span class="metric-value" id="active-ops">0</span>
            </div>
            <canvas id="cpu-chart" class="chart"></canvas>
        </div>
        
        <div class="card">
            <h2>Recent Operations</h2>
            <div id="operations-list">
                <p>No operations yet...</p>
            </div>
        </div>
        
        <div class="card">
            <h2>Alerts</h2>
            <div id="alerts-list">
                <p>No alerts</p>
            </div>
        </div>
        
        <div class="card">
            <h2>Performance Trends</h2>
            <canvas id="memory-chart" class="chart"></canvas>
        </div>
    </div>
    
    <script>
        // WebSocket connection
        const ws = new WebSocket(`ws://${window.location.host}/ws`);
        
        // Charts
        const cpuChart = new Chart(document.getElementById('cpu-chart'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU %',
                    data: [],
                    borderColor: '#2196F3',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
        
        const memoryChart = new Chart(document.getElementById('memory-chart'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Memory %',
                    data: [],
                    borderColor: '#4caf50',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
        
        // WebSocket handlers
        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            
            if (message.type === 'metrics') {
                updateMetrics(message.data);
            } else if (message.type === 'alerts') {
                updateAlerts(message.data);
            }
        };
        
        function updateMetrics(data) {
            // Update system metrics
            if (data.system) {
                const cpuPercent = data.system.cpu.percent.toFixed(1);
                const memPercent = data.system.memory.percent.toFixed(1);
                
                document.getElementById('cpu-usage').textContent = cpuPercent + '%';
                document.getElementById('memory-usage').textContent = memPercent + '%';
                
                // Update charts
                const time = new Date().toLocaleTimeString();
                
                cpuChart.data.labels.push(time);
                cpuChart.data.datasets[0].data.push(cpuPercent);
                if (cpuChart.data.labels.length > 30) {
                    cpuChart.data.labels.shift();
                    cpuChart.data.datasets[0].data.shift();
                }
                cpuChart.update();
                
                memoryChart.data.labels.push(time);
                memoryChart.data.datasets[0].data.push(memPercent);
                if (memoryChart.data.labels.length > 30) {
                    memoryChart.data.labels.shift();
                    memoryChart.data.datasets[0].data.shift();
                }
                memoryChart.update();
            }
            
            // Update operations
            if (data.trackers) {
                updateOperations(data.trackers);
            }
        }
        
        function updateOperations(trackers) {
            const container = document.getElementById('operations-list');
            container.innerHTML = '';
            
            let totalOps = 0;
            
            for (const [name, tracker] of Object.entries(trackers)) {
                if (tracker.recent_operations && tracker.recent_operations.length > 0) {
                    const ops = tracker.recent_operations;
                    totalOps += ops.length;
                    
                    ops.slice(-5).forEach(op => {
                        const div = document.createElement('div');
                        div.className = 'metric';
                        div.innerHTML = `
                            <span>${op.operation}</span>
                            <span>${op.duration.toFixed(2)}s</span>
                        `;
                        container.appendChild(div);
                    });
                }
            }
            
            document.getElementById('active-ops').textContent = totalOps;
            
            if (totalOps === 0) {
                container.innerHTML = '<p>No operations yet...</p>';
            }
        }
        
        function updateAlerts(alerts) {
            const container = document.getElementById('alerts-list');
            container.innerHTML = '';
            
            if (alerts.length === 0) {
                container.innerHTML = '<p>No alerts</p>';
                return;
            }
            
            alerts.forEach(alert => {
                const div = document.createElement('div');
                div.className = `alert alert-${alert.level}`;
                div.textContent = alert.message;
                container.appendChild(div);
            });
        }
        
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        ws.onclose = () => {
            console.log('WebSocket connection closed');
        };
    </script>
</body>
</html>
        """
    
    def _export_static_html(self) -> str:
        """Export dashboard as static HTML with embedded data."""
        # Collect current metrics
        metrics = self.metrics_collector.get_aggregated_metrics()
        
        # Generate static HTML with embedded data
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>DagLab Performance Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        
        .header {{
            background: #2196F3;
            color: white;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 2rem;
        }}
        
        .section {{
            background: white;
            padding: 1.5rem;
            margin-bottom: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }}
        
        th, td {{
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        
        th {{
            background: #f5f5f5;
            font-weight: 600;
        }}
        
        .metric-value {{
            font-size: 1.25rem;
            font-weight: bold;
            color: #2196F3;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>DagLab Performance Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="section">
        <h2>Summary</h2>
        <p>Total Operations: <span class="metric-value">{metrics.get('total_operations', 0)}</span></p>
        <p>Active Trackers: <span class="metric-value">{metrics.get('total_trackers', 0)}</span></p>
    </div>
    
    <div class="section">
        <h2>Operation Statistics</h2>
        <table>
            <tr>
                <th>Operation</th>
                <th>Count</th>
                <th>Avg Duration (s)</th>
                <th>Avg CPU (%)</th>
                <th>Avg Memory (MB)</th>
            </tr>
"""
        
        # Add operation statistics
        for op, stats in metrics.get("operation_types", {}).items():
            html += f"""
            <tr>
                <td>{op}</td>
                <td>{stats['count']}</td>
                <td>{stats['avg_duration']:.3f}</td>
                <td>{stats['avg_cpu']:.1f}</td>
                <td>{stats['avg_memory']:.1f}</td>
            </tr>
"""
        
        html += """
        </table>
    </div>
</body>
</html>
        """
        
        return html
    
    def _export_json_data(self) -> Dict[str, Any]:
        """Export dashboard data as JSON."""
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": self.metrics_collector.get_aggregated_metrics(),
            "alerts": [alert.dict() for alert in self.alerts],
            "history": self.history
        }


# Convenience function to start dashboard
def start_dashboard(host: str = "127.0.0.1", port: int = 8765,
                   trackers: Optional[List[PerformanceTracker]] = None):
    """
    Start performance dashboard server.
    
    Args:
        host: Server host
        port: Server port
        trackers: List of trackers to register
        
    Example:
        tracker = PerformanceTracker()
        start_dashboard(trackers=[tracker])
    """
    dashboard = DashboardServer(DashboardConfig(host=host, port=port))
    
    if trackers:
        for tracker in trackers:
            dashboard.register_tracker(tracker)
    
    asyncio.run(dashboard.start())