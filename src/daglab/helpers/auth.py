"""Authentication configuration and management for Dagster GraphQL client."""
import base64
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Protocol
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AuthType(Enum):
    """Supported authentication types."""
    NONE = "none"
    BEARER = "bearer"
    BASIC = "basic"
    CUSTOM = "custom"


class TokenProvider(Protocol):
    """Protocol for token providers."""
    
    def get_token(self) -> str:
        """Get the current authentication token."""
        ...
    
    def refresh_token(self) -> Optional[str]:
        """Refresh the authentication token if needed."""
        ...


@dataclass
class TokenCache:
    """Simple token cache with expiration."""
    token: str
    expires_at: Optional[float] = None
    
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        return time.time() >= self.expires_at
    
    def is_valid(self) -> bool:
        """Check if token is valid."""
        return bool(self.token) and not self.is_expired()


class AuthProvider(ABC):
    """Base class for authentication providers."""
    
    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        pass
    
    @abstractmethod
    def refresh(self) -> None:
        """Refresh authentication if needed."""
        pass


class NoAuthProvider(AuthProvider):
    """No authentication provider."""
    
    def get_headers(self) -> Dict[str, str]:
        return {}
    
    def refresh(self) -> None:
        pass


class BearerAuthProvider(AuthProvider):
    """Bearer token authentication provider."""
    
    def __init__(
        self,
        token: Optional[str] = None,
        token_provider: Optional[TokenProvider] = None,
        header_name: str = "Authorization",
        prefix: str = "Bearer",
    ):
        self.token = token
        self.token_provider = token_provider
        self.header_name = header_name
        self.prefix = prefix
        self._cache: Optional[TokenCache] = None
        
        if not self.token and not self.token_provider:
            raise ValueError("Either token or token_provider must be provided")
    
    def get_headers(self) -> Dict[str, str]:
        """Get bearer token headers."""
        token = self._get_current_token()
        if not token:
            return {}
        
        return {
            self.header_name: f"{self.prefix} {token}".strip()
        }
    
    def refresh(self) -> None:
        """Refresh token if provider supports it."""
        if self.token_provider and hasattr(self.token_provider, 'refresh_token'):
            new_token = self.token_provider.refresh_token()
            if new_token:
                self._cache = TokenCache(token=new_token)
    
    def _get_current_token(self) -> Optional[str]:
        """Get current valid token."""
        if self.token_provider:
            if self._cache and self._cache.is_valid():
                return self._cache.token
            
            token = self.token_provider.get_token()
            self._cache = TokenCache(token=token)
            return token
        
        return self.token


class BasicAuthProvider(AuthProvider):
    """Basic authentication provider."""
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
    
    def get_headers(self) -> Dict[str, str]:
        """Get basic auth headers."""
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {
            "Authorization": f"Basic {encoded}"
        }
    
    def refresh(self) -> None:
        """Basic auth doesn't need refresh."""
        pass


class CustomAuthProvider(AuthProvider):
    """Custom header authentication provider."""
    
    def __init__(self, headers: Dict[str, str]):
        self.headers = headers
    
    def get_headers(self) -> Dict[str, str]:
        """Get custom headers."""
        return self.headers.copy()
    
    def refresh(self) -> None:
        """Custom headers don't need refresh."""
        pass


@dataclass
class AuthConfig:
    """Authentication configuration with support for multiple auth types."""
    
    auth_type: AuthType = AuthType.NONE
    provider: Optional[AuthProvider] = None
    
    # Environment variable names
    token_env_var: str = "DAGSTER_TOKEN"
    username_env_var: str = "DAGSTER_USERNAME"
    password_env_var: str = "DAGSTER_PASSWORD"
    
    # Additional options
    validate_ssl: bool = True
    additional_headers: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_env(cls, auth_type: Optional[AuthType] = None) -> "AuthConfig":
        """Create auth config from environment variables.
        
        Tries to detect auth type if not specified:
        1. If DAGSTER_TOKEN is set, uses bearer auth
        2. If DAGSTER_USERNAME and DAGSTER_PASSWORD are set, uses basic auth
        3. Otherwise, no auth
        """
        # Try to detect auth type if not specified
        if auth_type is None:
            if os.getenv("DAGSTER_TOKEN"):
                auth_type = AuthType.BEARER
            elif os.getenv("DAGSTER_USERNAME") and os.getenv("DAGSTER_PASSWORD"):
                auth_type = AuthType.BASIC
            else:
                auth_type = AuthType.NONE
        
        # Create appropriate provider
        provider: Optional[AuthProvider] = None
        
        if auth_type == AuthType.BEARER:
            token = os.getenv("DAGSTER_TOKEN")
            if token:
                provider = BearerAuthProvider(token=token)
            else:
                logger.warning("Bearer auth requested but DAGSTER_TOKEN not found")
                auth_type = AuthType.NONE
        
        elif auth_type == AuthType.BASIC:
            username = os.getenv("DAGSTER_USERNAME")
            password = os.getenv("DAGSTER_PASSWORD")
            if username and password:
                provider = BasicAuthProvider(username=username, password=password)
            else:
                logger.warning("Basic auth requested but credentials not found")
                auth_type = AuthType.NONE
        
        elif auth_type == AuthType.NONE:
            provider = NoAuthProvider()
        
        return cls(auth_type=auth_type, provider=provider)
    
    @classmethod
    def bearer(cls, token: str) -> "AuthConfig":
        """Create bearer token auth config."""
        return cls(
            auth_type=AuthType.BEARER,
            provider=BearerAuthProvider(token=token)
        )
    
    @classmethod
    def basic(cls, username: str, password: str) -> "AuthConfig":
        """Create basic auth config."""
        return cls(
            auth_type=AuthType.BASIC,
            provider=BasicAuthProvider(username=username, password=password)
        )
    
    @classmethod
    def custom(cls, headers: Dict[str, str]) -> "AuthConfig":
        """Create custom header auth config."""
        return cls(
            auth_type=AuthType.CUSTOM,
            provider=CustomAuthProvider(headers=headers)
        )
    
    def get_headers(self) -> Dict[str, str]:
        """Get all authentication headers including additional ones."""
        headers = {}
        
        if self.provider:
            headers.update(self.provider.get_headers())
        
        # Add any additional headers
        headers.update(self.additional_headers)
        
        # Never log authentication headers
        safe_headers = {k: v for k, v in headers.items() if k.lower() != "authorization"}
        logger.debug(f"Request headers (auth hidden): {safe_headers}")
        
        return headers
    
    def refresh(self) -> None:
        """Refresh authentication if supported."""
        if self.provider:
            self.provider.refresh()


class TokenManager:
    """Manages token lifecycle with caching and refresh."""
    
    def __init__(
        self,
        token_provider: TokenProvider,
        cache_ttl: float = 3600.0,  # 1 hour default
        refresh_threshold: float = 300.0,  # 5 minutes before expiry
    ):
        self.token_provider = token_provider
        self.cache_ttl = cache_ttl
        self.refresh_threshold = refresh_threshold
        self._cache: Optional[TokenCache] = None
    
    def get_token(self) -> str:
        """Get current token, refreshing if needed."""
        # Check cache
        if self._cache and self._cache.is_valid():
            # Check if we should proactively refresh
            if self._should_refresh():
                self._refresh_token()
            
            if self._cache and self._cache.is_valid():
                return self._cache.token
        
        # Get new token
        token = self.token_provider.get_token()
        self._cache = TokenCache(
            token=token,
            expires_at=time.time() + self.cache_ttl
        )
        return token
    
    def _should_refresh(self) -> bool:
        """Check if token should be refreshed proactively."""
        if not self._cache or not self._cache.expires_at:
            return False
        
        time_until_expiry = self._cache.expires_at - time.time()
        return time_until_expiry <= self.refresh_threshold
    
    def _refresh_token(self) -> None:
        """Attempt to refresh the token."""
        try:
            if hasattr(self.token_provider, 'refresh_token'):
                new_token = self.token_provider.refresh_token()
                if new_token:
                    self._cache = TokenCache(
                        token=new_token,
                        expires_at=time.time() + self.cache_ttl
                    )
                    logger.info("Token refreshed successfully")
        except Exception as e:
            logger.warning(f"Failed to refresh token: {e}")
    
    def clear_cache(self) -> None:
        """Clear the token cache."""
        self._cache = None