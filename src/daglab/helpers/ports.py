"""Port management utilities for daglab."""

import socket
import random
from typing import List, Set, Optional, Tuple
from dataclasses import dataclass
from contextlib import closing


@dataclass
class PortRange:
    """Represents a range of ports."""
    start: int
    end: int
    
    def __contains__(self, port: int) -> bool:
        return self.start <= port <= self.end
    
    def __iter__(self):
        return iter(range(self.start, self.end + 1))


class PortManager:
    """Manage port allocation and availability."""
    
    # Default port ranges for different services
    DEFAULT_RANGES = {
        "dagster": PortRange(3000, 3099),
        "marimo": PortRange(2700, 2799),
        "api": PortRange(8000, 8099),
        "database": PortRange(5432, 5532),
        "custom": PortRange(9000, 9999)
    }
    
    def __init__(self):
        self.reserved_ports: Set[int] = set()
        self.allocations: dict[str, int] = {}
        
    def is_port_available(self, port: int, host: str = "localhost") -> bool:
        """Check if a port is available for binding."""
        if port in self.reserved_ports:
            return False
            
        # Try to bind to the port
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            try:
                sock.bind((host, port))
                return True
            except (OSError, socket.error):
                return False
                
    def find_available_port(
        self,
        preferred: Optional[int] = None,
        range_name: str = "custom",
        host: str = "localhost"
    ) -> Optional[int]:
        """Find an available port, preferring the given port if specified."""
        # Try preferred port first
        if preferred and self.is_port_available(preferred, host):
            return preferred
            
        # Get the appropriate range
        port_range = self.DEFAULT_RANGES.get(range_name, self.DEFAULT_RANGES["custom"])
        
        # Try random ports in the range
        ports = list(port_range)
        random.shuffle(ports)
        
        for port in ports:
            if self.is_port_available(port, host):
                return port
                
        return None
        
    def allocate_port(
        self,
        service_name: str,
        preferred: Optional[int] = None,
        range_name: Optional[str] = None
    ) -> int:
        """Allocate a port for a service."""
        # Check if already allocated
        if service_name in self.allocations:
            port = self.allocations[service_name]
            if self.is_port_available(port):
                return port
                
        # Determine range based on service name if not specified
        if not range_name:
            if "dagster" in service_name.lower():
                range_name = "dagster"
            elif "marimo" in service_name.lower():
                range_name = "marimo"
            elif "api" in service_name.lower():
                range_name = "api"
            else:
                range_name = "custom"
                
        # Find available port
        port = self.find_available_port(preferred, range_name)
        
        if not port:
            raise RuntimeError(f"No available ports in range '{range_name}'")
            
        # Reserve and allocate
        self.reserved_ports.add(port)
        self.allocations[service_name] = port
        
        return port
        
    def release_port(self, service_name: str) -> bool:
        """Release a port allocation."""
        if service_name not in self.allocations:
            return False
            
        port = self.allocations[service_name]
        self.reserved_ports.discard(port)
        del self.allocations[service_name]
        
        return True
        
    def release_all(self):
        """Release all port allocations."""
        self.reserved_ports.clear()
        self.allocations.clear()
        
    def get_allocation(self, service_name: str) -> Optional[int]:
        """Get the allocated port for a service."""
        return self.allocations.get(service_name)
        
    def get_all_allocations(self) -> dict[str, int]:
        """Get all current port allocations."""
        return self.allocations.copy()
        
    def scan_ports(
        self,
        start: int = 1024,
        end: int = 65535,
        host: str = "localhost"
    ) -> List[int]:
        """Scan for available ports in a range."""
        available = []
        
        for port in range(start, min(end + 1, 65536)):
            if self.is_port_available(port, host):
                available.append(port)
                
        return available
        
    def detect_conflicts(self, services: List[Tuple[str, int]]) -> List[str]:
        """Detect port conflicts among services."""
        conflicts = []
        seen_ports = {}
        
        for service, port in services:
            if port in seen_ports:
                conflicts.append(
                    f"Port {port} conflict: '{service}' and '{seen_ports[port]}'"
                )
            else:
                seen_ports[port] = service
                
            if not self.is_port_available(port):
                if service not in conflicts:
                    conflicts.append(f"Port {port} for '{service}' is already in use")
                    
        return conflicts
        
    def suggest_alternatives(self, port: int, count: int = 5) -> List[int]:
        """Suggest alternative ports near the given port."""
        alternatives = []
        
        # Try ports near the original
        for offset in range(1, 100):
            if len(alternatives) >= count:
                break
                
            # Try higher
            candidate = port + offset
            if candidate <= 65535 and self.is_port_available(candidate):
                alternatives.append(candidate)
                
            if len(alternatives) >= count:
                break
                
            # Try lower
            candidate = port - offset
            if candidate >= 1024 and self.is_port_available(candidate):
                alternatives.append(candidate)
                
        return alternatives[:count]
        
    def get_interface_addresses(self) -> List[str]:
        """Get all network interface addresses."""
        addresses = ["localhost", "127.0.0.1", "0.0.0.0"]
        
        try:
            # Get hostname
            hostname = socket.gethostname()
            addresses.append(hostname)
            
            # Get IP addresses
            for info in socket.getaddrinfo(hostname, None):
                addr = info[4][0]
                if addr not in addresses:
                    addresses.append(addr)
                    
        except Exception:
            pass
            
        return addresses