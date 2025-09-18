"""Process management utilities for daglab."""

import asyncio
import atexit
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
import psutil
from rich.console import Console

console = Console()


class ProcessState(Enum):
    """Process states."""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    RESTARTING = "restarting"


@dataclass
class ProcessInfo:
    """Information about a managed process."""
    name: str
    command: List[str]
    pid: Optional[int] = None
    state: ProcessState = ProcessState.STOPPED
    start_time: Optional[datetime] = None
    restart_count: int = 0
    last_health_check: Optional[datetime] = None
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    env: Optional[Dict[str, str]] = None
    cwd: Optional[str] = None
    stdout_file: Optional[Path] = None
    stderr_file: Optional[Path] = None
    health_check_fn: Optional[Callable[[], bool]] = None
    on_restart: Optional[Callable[[], None]] = None


class ProcessManager:
    """Manage subprocess lifecycles."""
    
    def __init__(self, log_dir: Optional[Path] = None):
        self.processes: Dict[str, ProcessInfo] = {}
        self.subprocesses: Dict[str, subprocess.Popen] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self.stop_event = threading.Event()
        self.log_dir = log_dir or Path.cwd() / ".daglab" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._setup_signal_handlers()
        atexit.register(self.shutdown_all)
        
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        if sys.platform != "win32":
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        console.print("\n[yellow]Received shutdown signal, stopping processes...[/yellow]")
        self.shutdown_all()
        sys.exit(0)
        
    def register(
        self,
        name: str,
        command: List[str],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        health_check_fn: Optional[Callable[[], bool]] = None,
        on_restart: Optional[Callable[[], None]] = None
    ) -> ProcessInfo:
        """Register a new process."""
        if name in self.processes:
            raise ValueError(f"Process '{name}' already registered")
            
        info = ProcessInfo(
            name=name,
            command=command,
            env=env or {},
            cwd=cwd,
            stdout_file=self.log_dir / f"{name}.stdout.log",
            stderr_file=self.log_dir / f"{name}.stderr.log",
            health_check_fn=health_check_fn,
            on_restart=on_restart
        )
        
        self.processes[name] = info
        return info
        
    def start(self, name: str) -> bool:
        """Start a registered process."""
        if name not in self.processes:
            raise ValueError(f"Process '{name}' not registered")
            
        info = self.processes[name]
        
        if info.state in (ProcessState.RUNNING, ProcessState.STARTING):
            return True
            
        info.state = ProcessState.STARTING
        
        try:
            # Prepare environment
            env = os.environ.copy()
            env.update(info.env or {})
            
            # Open log files
            stdout = open(info.stdout_file, "ab") if info.stdout_file else None
            stderr = open(info.stderr_file, "ab") if info.stderr_file else None
            
            # Start process
            proc = subprocess.Popen(
                info.command,
                env=env,
                cwd=info.cwd,
                stdout=stdout,
                stderr=stderr,
                preexec_fn=os.setsid if sys.platform != "win32" else None
            )
            
            self.subprocesses[name] = proc
            info.pid = proc.pid
            info.start_time = datetime.now()
            info.state = ProcessState.RUNNING
            
            # Start monitoring thread
            thread = threading.Thread(
                target=self._monitor_process,
                args=(name,),
                daemon=True
            )
            thread.start()
            self.threads[name] = thread
            
            return True
            
        except Exception as e:
            console.print(f"[red]Failed to start {name}: {e}[/red]")
            info.state = ProcessState.FAILED
            return False
            
    def stop(self, name: str, timeout: int = 10) -> bool:
        """Stop a running process."""
        if name not in self.processes:
            return False
            
        info = self.processes[name]
        proc = self.subprocesses.get(name)
        
        if not proc or info.state != ProcessState.RUNNING:
            return True
            
        info.state = ProcessState.STOPPING
        
        try:
            # Try graceful shutdown first
            if sys.platform == "win32":
                proc.terminate()
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Force kill if needed
                if sys.platform == "win32":
                    proc.kill()
                else:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                proc.wait()
                
            info.state = ProcessState.STOPPED
            info.pid = None
            
            if name in self.subprocesses:
                del self.subprocesses[name]
                
            return True
            
        except Exception as e:
            console.print(f"[red]Error stopping {name}: {e}[/red]")
            return False
            
    def restart(self, name: str) -> bool:
        """Restart a process."""
        info = self.processes.get(name)
        if not info:
            return False
            
        info.state = ProcessState.RESTARTING
        info.restart_count += 1
        
        # Call restart callback
        if info.on_restart:
            try:
                info.on_restart()
            except Exception as e:
                console.print(f"[yellow]Restart callback error: {e}[/yellow]")
        
        # Stop and start
        self.stop(name)
        time.sleep(1)  # Brief pause
        return self.start(name)
        
    def _monitor_process(self, name: str):
        """Monitor a process in a separate thread."""
        info = self.processes[name]
        proc = self.subprocesses.get(name)
        
        if not proc:
            return
            
        while not self.stop_event.is_set() and info.state == ProcessState.RUNNING:
            try:
                # Check if process is alive
                if proc.poll() is not None:
                    console.print(f"[yellow]Process {name} exited unexpectedly[/yellow]")
                    info.state = ProcessState.FAILED
                    
                    # Auto-restart if configured
                    if info.restart_count < 3:
                        time.sleep(2)
                        self.restart(name)
                    break
                    
                # Update resource usage
                try:
                    process = psutil.Process(proc.pid)
                    info.cpu_percent = process.cpu_percent(interval=0.1)
                    info.memory_mb = process.memory_info().rss / 1024 / 1024
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
                # Run health check
                if info.health_check_fn:
                    info.last_health_check = datetime.now()
                    if not info.health_check_fn():
                        console.print(f"[yellow]Health check failed for {name}[/yellow]")
                        if info.restart_count < 3:
                            self.restart(name)
                            
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                console.print(f"[red]Monitor error for {name}: {e}[/red]")
                time.sleep(5)
                
    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all processes."""
        status = {}
        for name, info in self.processes.items():
            status[name] = {
                "state": info.state.value,
                "pid": info.pid,
                "uptime": str(datetime.now() - info.start_time) if info.start_time else None,
                "restarts": info.restart_count,
                "cpu_percent": round(info.cpu_percent, 2),
                "memory_mb": round(info.memory_mb, 2)
            }
        return status
        
    def stream_logs(self, name: str, lines: int = 100) -> List[str]:
        """Get recent log lines from a process."""
        info = self.processes.get(name)
        if not info or not info.stdout_file:
            return []
            
        try:
            with open(info.stdout_file, "r") as f:
                all_lines = f.readlines()
                return all_lines[-lines:]
        except Exception:
            return []
            
    def wait_for_ready(self, name: str, timeout: int = 30) -> bool:
        """Wait for a process to be ready."""
        info = self.processes.get(name)
        if not info:
            return False
            
        start = time.time()
        while time.time() - start < timeout:
            if info.state == ProcessState.RUNNING:
                if info.health_check_fn:
                    if info.health_check_fn():
                        return True
                else:
                    return True
            elif info.state == ProcessState.FAILED:
                return False
            time.sleep(0.5)
            
        return False
        
    def shutdown_all(self):
        """Shutdown all managed processes."""
        self.stop_event.set()
        
        # Stop all processes
        for name in list(self.processes.keys()):
            self.stop(name)
            
        # Wait for threads
        for thread in self.threads.values():
            if thread.is_alive():
                thread.join(timeout=5)
                
        # Close log files
        for info in self.processes.values():
            if info.stdout_file and info.stdout_file.exists():
                try:
                    info.stdout_file.unlink()
                except Exception:
                    pass
            if info.stderr_file and info.stderr_file.exists():
                try:
                    info.stderr_file.unlink()
                except Exception:
                    pass