"""Browser integration utilities for daglab."""

import os
import sys
import time
import webbrowser
import subprocess
import platform
from typing import Optional, List, Dict, Any
from pathlib import Path
from rich.console import Console

console = Console()


class BrowserManager:
    """Manage browser operations across platforms."""
    
    # Common browser names and their executable paths
    BROWSER_COMMANDS = {
        "chrome": {
            "darwin": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"],
            "win32": ["chrome.exe", "chrome"],
            "linux": ["google-chrome", "chrome", "chromium"]
        },
        "firefox": {
            "darwin": ["/Applications/Firefox.app/Contents/MacOS/firefox"],
            "win32": ["firefox.exe", "firefox"],
            "linux": ["firefox"]
        },
        "safari": {
            "darwin": ["/Applications/Safari.app/Contents/MacOS/Safari"],
            "win32": [],
            "linux": []
        },
        "edge": {
            "darwin": ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"],
            "win32": ["msedge.exe", "edge.exe"],
            "linux": ["microsoft-edge", "edge"]
        }
    }
    
    def __init__(self, preferred_browser: Optional[str] = None):
        self.preferred_browser = preferred_browser
        self.platform = sys.platform
        self.opened_tabs: Dict[str, List[str]] = {}
        
    def detect_browsers(self) -> List[str]:
        """Detect available browsers on the system."""
        available = []
        
        for browser, commands in self.BROWSER_COMMANDS.items():
            platform_commands = commands.get(self.platform, [])
            
            for cmd in platform_commands:
                if self._is_executable(cmd):
                    available.append(browser)
                    break
                    
        return available
        
    def _is_executable(self, command: str) -> bool:
        """Check if a command is executable."""
        # Check if it's an absolute path
        if os.path.isabs(command):
            return os.path.isfile(command) and os.access(command, os.X_OK)
            
        # Check in PATH
        for path in os.environ.get("PATH", "").split(os.pathsep):
            exe_path = os.path.join(path, command)
            if os.path.isfile(exe_path) and os.access(exe_path, os.X_OK):
                return True
                
        return False
        
    def open_url(
        self,
        url: str,
        new_tab: bool = True,
        browser: Optional[str] = None,
        wait: bool = False
    ) -> bool:
        """Open a URL in the browser."""
        browser = browser or self.preferred_browser
        
        try:
            if browser:
                # Try to use specific browser
                controller = self._get_browser_controller(browser)
                if controller:
                    if new_tab:
                        controller.open_new_tab(url)
                    else:
                        controller.open(url)
                else:
                    # Fallback to system default
                    webbrowser.open_new_tab(url) if new_tab else webbrowser.open(url)
            else:
                # Use system default
                webbrowser.open_new_tab(url) if new_tab else webbrowser.open(url)
                
            # Track opened tabs
            session = self.opened_tabs.setdefault("default", [])
            session.append(url)
            
            if wait:
                time.sleep(2)  # Give browser time to open
                
            return True
            
        except Exception as e:
            console.print(f"[yellow]Failed to open browser: {e}[/yellow]")
            console.print(f"[cyan]Please open manually: {url}[/cyan]")
            return False
            
    def _get_browser_controller(self, browser: str) -> Optional[Any]:
        """Get browser controller for specific browser."""
        browser = browser.lower()
        
        if browser == "chrome":
            return webbrowser.get("chrome") if webbrowser.get("chrome") else None
        elif browser == "firefox":
            return webbrowser.get("firefox") if webbrowser.get("firefox") else None
        elif browser == "safari" and self.platform == "darwin":
            return webbrowser.get("safari") if webbrowser.get("safari") else None
            
        return None
        
    def open_multiple(
        self,
        urls: List[str],
        delay: float = 1.0,
        browser: Optional[str] = None
    ) -> int:
        """Open multiple URLs with a delay between each."""
        opened = 0
        
        for i, url in enumerate(urls):
            if i > 0:
                time.sleep(delay)
                
            if self.open_url(url, new_tab=True, browser=browser):
                opened += 1
                
        return opened
        
    def open_dev_tools(self, url: str, browser: Optional[str] = None) -> bool:
        """Open URL with developer tools (Chrome/Firefox only)."""
        browser = browser or self.preferred_browser or "chrome"
        
        if browser.lower() not in ["chrome", "firefox"]:
            console.print("[yellow]Dev tools only supported in Chrome/Firefox[/yellow]")
            return self.open_url(url, browser=browser)
            
        try:
            if browser.lower() == "chrome":
                commands = self.BROWSER_COMMANDS["chrome"][self.platform]
                for cmd in commands:
                    if self._is_executable(cmd):
                        subprocess.Popen([cmd, "--new-window", "--auto-open-devtools-for-tabs", url])
                        return True
                        
            elif browser.lower() == "firefox":
                commands = self.BROWSER_COMMANDS["firefox"][self.platform]
                for cmd in commands:
                    if self._is_executable(cmd):
                        subprocess.Popen([cmd, "-new-window", "-devtools", url])
                        return True
                        
        except Exception as e:
            console.print(f"[yellow]Failed to open with dev tools: {e}[/yellow]")
            
        # Fallback to regular open
        return self.open_url(url, browser=browser)
        
    def is_browser_available(self, browser: str) -> bool:
        """Check if a specific browser is available."""
        return browser.lower() in [b.lower() for b in self.detect_browsers()]
        
    def get_default_browser(self) -> Optional[str]:
        """Try to determine the system's default browser."""
        try:
            # Try to get from webbrowser module
            default = webbrowser.get()
            
            if hasattr(default, "name"):
                return default.name
                
            # Platform-specific detection
            if self.platform == "darwin":
                result = subprocess.run(
                    ["defaults", "read", "com.apple.LaunchServices", 
                     "LSHandlers", "|", "grep", "-B", "1", "-A", "1", "https"],
                    capture_output=True,
                    text=True,
                    shell=True
                )
                if "chrome" in result.stdout.lower():
                    return "chrome"
                elif "firefox" in result.stdout.lower():
                    return "firefox"
                elif "safari" in result.stdout.lower():
                    return "safari"
                    
            elif self.platform == "win32":
                # Check Windows registry
                import winreg
                try:
                    with winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice"
                    ) as key:
                        prog_id = winreg.QueryValueEx(key, "ProgId")[0]
                        if "chrome" in prog_id.lower():
                            return "chrome"
                        elif "firefox" in prog_id.lower():
                            return "firefox"
                        elif "edge" in prog_id.lower():
                            return "edge"
                except Exception:
                    pass
                    
        except Exception:
            pass
            
        # Fallback: return first available
        available = self.detect_browsers()
        return available[0] if available else None
        
    def create_app_url(self, base_url: str, params: Dict[str, Any]) -> str:
        """Create URL with query parameters."""
        from urllib.parse import urlencode
        
        if not params:
            return base_url
            
        query = urlencode(params)
        separator = "&" if "?" in base_url else "?"
        
        return f"{base_url}{separator}{query}"
        
    def wait_for_close(self, timeout: Optional[int] = None):
        """Wait for user to close browser (interactive mode)."""
        try:
            if timeout:
                console.print(f"\n[dim]Browser opened. Waiting {timeout}s or press Ctrl+C to continue...[/dim]")
                time.sleep(timeout)
            else:
                console.print("\n[dim]Browser opened. Press Ctrl+C when done...[/dim]")
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[green]Continuing...[/green]")
            
    def get_session_urls(self, session: str = "default") -> List[str]:
        """Get all URLs opened in a session."""
        return self.opened_tabs.get(session, [])