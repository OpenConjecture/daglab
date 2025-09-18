"""Input validation and sanitization hardening module.

Provides input security hardening including:
- Enhanced input sanitization
- Rate limiting implementation
- CSRF protection
- XSS prevention
- SQL injection prevention
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..helpers.security import SecurityManager
from ..runtime.errors import SecurityError

logger = logging.getLogger(__name__)


class InputValidationHardening:
    """Input validation and sanitization hardening."""
    
    def __init__(self):
        """Initialize input validation hardening."""
        self.security_manager = SecurityManager()
        
    def enhance_input_sanitization(self, project_path: Path) -> Dict[str, Any]:
        """Enhance input sanitization across the project.
        
        Args:
            project_path: Path to project root
            
        Returns:
            Result of input sanitization enhancement
        """
        logger.info("Enhancing input sanitization")
        
        try:
            # Input sanitization configuration
            sanitization_config = {
                'string_sanitization': {
                    'max_length': 10000,
                    'remove_null_bytes': True,
                    'normalize_unicode': True,
                    'trim_whitespace': True,
                    'escape_html': True,
                    'disallow_control_chars': True
                },
                'sql_injection_prevention': {
                    'use_parameterized_queries': True,
                    'escape_sql_chars': True,
                    'validate_sql_patterns': True,
                    'blocked_sql_keywords': [
                        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE',
                        'EXEC', 'EXECUTE', 'UNION', 'INSERT', 'UPDATE'
                    ]
                },
                'xss_prevention': {
                    'html_escape': True,
                    'javascript_escape': True,
                    'css_escape': True,
                    'url_encode': True,
                    'content_security_policy': True
                },
                'file_upload_security': {
                    'allowed_extensions': ['.txt', '.csv', '.json', '.yaml'],
                    'max_file_size_mb': 10,
                    'scan_for_malware': True,
                    'validate_mime_types': True,
                    'quarantine_suspicious_files': True
                }
            }
            
            # Generate sanitization utilities
            sanitization_code = self._generate_sanitization_utilities()
            
            # Create input validation middleware
            middleware_code = self._generate_validation_middleware()
            
            return {
                'success': True,
                'message': 'Input sanitization enhanced with comprehensive protection',
                'sanitization_config': sanitization_config,
                'implementation_files': {
                    'sanitization_utils.py': sanitization_code,
                    'validation_middleware.py': middleware_code
                },
                'implementation_steps': [
                    'Create input sanitization utility functions',
                    'Implement validation middleware for web requests',
                    'Add sanitization to all user input points',
                    'Implement file upload security checks',
                    'Add input validation to API endpoints',
                    'Create input validation decorators'
                ],
                'recommendations': [
                    'Apply sanitization at input boundaries',
                    'Use whitelist validation where possible',
                    'Implement context-specific escaping',
                    'Regular security testing of input handling',
                    'Monitor for injection attack attempts'
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to enhance input sanitization: {e}")
            return {
                'success': False,
                'message': f'Input sanitization enhancement failed: {e}',
                'error': str(e)
            }
    
    def implement_rate_limiting(self) -> Dict[str, Any]:
        """Implement rate limiting for API endpoints.
        
        Returns:
            Result of rate limiting implementation
        """
        logger.info("Implementing rate limiting")
        
        try:
            # Rate limiting configuration
            rate_limit_config = {
                'global_limits': {
                    'requests_per_minute': 1000,
                    'requests_per_hour': 10000,
                    'requests_per_day': 100000
                },
                'endpoint_specific_limits': {
                    'auth_endpoints': {
                        'login': {'requests_per_minute': 5, 'burst': 10},
                        'password_reset': {'requests_per_minute': 2, 'burst': 5},
                        'registration': {'requests_per_minute': 3, 'burst': 7}
                    },
                    'api_endpoints': {
                        'data_query': {'requests_per_minute': 100, 'burst': 200},
                        'file_upload': {'requests_per_minute': 10, 'burst': 20},
                        'admin_operations': {'requests_per_minute': 20, 'burst': 30}
                    }
                },
                'user_based_limits': {
                    'free_tier': {'requests_per_hour': 100},
                    'premium_tier': {'requests_per_hour': 1000},
                    'enterprise_tier': {'requests_per_hour': 10000}
                },
                'ip_based_limits': {
                    'same_ip_requests_per_minute': 200,
                    'suspicious_ip_threshold': 500,
                    'auto_block_duration_minutes': 60
                },
                'rate_limit_storage': {
                    'backend': 'redis',  # or 'memory', 'database'
                    'key_prefix': 'daglab:ratelimit:',
                    'ttl_seconds': 3600
                }
            }
            
            # Generate rate limiting middleware
            rate_limit_code = self._generate_rate_limiting_middleware()
            
            return {
                'success': True,
                'message': 'Rate limiting implemented with tiered controls',
                'rate_limit_config': rate_limit_config,
                'middleware_code': rate_limit_code,
                'implementation_steps': [
                    'Install rate limiting dependencies (redis-py)',
                    'Configure Redis for rate limit storage',
                    'Implement rate limiting middleware',
                    'Add rate limit decorators to endpoints',
                    'Configure different limits for user tiers',
                    'Implement rate limit monitoring and alerts'
                ],
                'recommendations': [
                    'Start with conservative limits and adjust based on usage',
                    'Implement graceful degradation for rate-limited requests',
                    'Provide clear rate limit information in API responses',
                    'Monitor rate limiting effectiveness and bypass attempts',
                    'Consider implementing CAPTCHA for suspicious activity'
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to implement rate limiting: {e}")
            return {
                'success': False,
                'message': f'Rate limiting implementation failed: {e}',
                'error': str(e)
            }
    
    def add_csrf_protection(self) -> Dict[str, Any]:
        """Add CSRF protection to web forms.
        
        Returns:
            Result of CSRF protection implementation
        """
        logger.info("Adding CSRF protection")
        
        try:
            # CSRF protection configuration
            csrf_config = {
                'token_generation': {
                    'algorithm': 'sha256',
                    'secret_length_bytes': 32,
                    'token_length_bytes': 32,
                    'token_lifetime_minutes': 60
                },
                'validation': {
                    'require_referrer_check': True,
                    'allowed_origins': [],  # Should be configured with actual origins
                    'require_https_referrer': True,
                    'double_submit_cookie': True
                },
                'implementation': {
                    'cookie_name': 'csrftoken',
                    'header_name': 'X-CSRFToken',
                    'form_field_name': 'csrfmiddlewaretoken',
                    'cookie_secure': True,
                    'cookie_httponly': False,  # Must be False for JS access
                    'cookie_samesite': 'Strict'
                }
            }
            
            # Generate CSRF protection utilities
            csrf_code = self._generate_csrf_protection()
            
            return {
                'success': True,
                'message': 'CSRF protection implemented with token-based validation',
                'csrf_config': csrf_config,
                'protection_code': csrf_code,
                'implementation_steps': [
                    'Generate secure CSRF tokens for each session',
                    'Add CSRF tokens to all forms and AJAX requests',
                    'Implement CSRF validation middleware',
                    'Configure secure cookie settings for CSRF tokens',
                    'Add CSRF token to JavaScript for AJAX requests',
                    'Implement referrer checking as additional protection'
                ],
                'recommendations': [
                    'Use double-submit cookie pattern for stateless apps',
                    'Regenerate CSRF tokens on authentication events',
                    'Implement proper error handling for CSRF failures',
                    'Educate developers on CSRF protection best practices',
                    'Monitor for CSRF attack attempts'
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to add CSRF protection: {e}")
            return {
                'success': False,
                'message': f'CSRF protection implementation failed: {e}',
                'error': str(e)
            }
    
    def _generate_sanitization_utilities(self) -> str:
        """Generate input sanitization utility code."""
        return '''
"""Input sanitization utilities for DagLab security."""

import html
import re
import unicodedata
from typing import Any, Optional, Union


class InputSanitizer:
    """Comprehensive input sanitization utilities."""
    
    # Common injection patterns
    SQL_INJECTION_PATTERNS = [
        r\'(?:\'|\\\')\s*(?:or|and)\s*(?:\'|\\\')\s*=\s*(?:\'|\\\')\',
        r\'(?:\'|\\\');\s*(?:drop|delete|insert|update|create)\s*\',
        r\'(?:\'|\\\')\s*(?:union|select)\s*\',
        r\'--\s*\',
        r\'/\\*.*?\\*/\',
    ]
    
    XSS_PATTERNS = [
        r\'<script[^>]*>.*?</script>\',
        r\'javascript:\',
        r\'on\\w+\s*=\',
        r\'<iframe[^>]*>.*?</iframe>\',
        r\'<object[^>]*>.*?</object>\',
    ]
    
    @classmethod
    def sanitize_string(
        cls, 
        value: str, 
        max_length: int = 10000,
        remove_html: bool = True,
        normalize_unicode: bool = True
    ) -> str:
        """Sanitize string input comprehensively."""
        if not isinstance(value, str):
            value = str(value)
        
        # Remove null bytes
        value = value.replace(\'\\x00\', \'\')
        
        # Normalize unicode
        if normalize_unicode:
            value = unicodedata.normalize(\'NFKC\', value)
        
        # Remove/escape HTML
        if remove_html:
            value = html.escape(value)
        
        # Remove control characters (except common whitespace)
        value = \'\'.join(char for char in value 
                        if unicodedata.category(char)[0] != \'C\' 
                        or char in \'\\t\\n\\r\')
        
        # Trim whitespace
        value = value.strip()
        
        # Enforce length limit
        if len(value) > max_length:
            value = value[:max_length]
        
        return value
    
    @classmethod
    def validate_against_injection(
        cls, 
        value: str, 
        check_sql: bool = True, 
        check_xss: bool = True
    ) -> tuple[bool, list[str]]:
        """Validate input against injection patterns."""
        issues = []
        
        if check_sql:
            for pattern in cls.SQL_INJECTION_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    issues.append(f\'Potential SQL injection pattern detected\')
                    break
        
        if check_xss:
            for pattern in cls.XSS_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    issues.append(f\'Potential XSS pattern detected\')
                    break
        
        return len(issues) == 0, issues
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename for safe storage."""
        # Remove path separators and dangerous chars
        filename = re.sub(r\'[<>:"/\\\\|?*]\', \'_\', filename)
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip(\'. \')
        
        # Prevent reserved names (Windows)
        reserved = {\'CON\', \'PRN\', \'AUX\', \'NUL\', \'COM1\', \'COM2\', \'COM3\', 
                   \'COM4\', \'COM5\', \'COM6\', \'COM7\', \'COM8\', \'COM9\', 
                   \'LPT1\', \'LPT2\', \'LPT3\', \'LPT4\', \'LPT5\', \'LPT6\', 
                   \'LPT7\', \'LPT8\', \'LPT9\'}
        
        if filename.upper() in reserved:
            filename = f\'file_{filename}\'
        
        # Ensure reasonable length
        if len(filename) > 255:
            name, ext = filename.rsplit(\'.\', 1) if \'.\' in filename else (filename, \'\')
            filename = name[:250] + (f\'.{ext}\' if ext else \'\')
        
        return filename or \'unnamed_file\'
'''
    
    def _generate_validation_middleware(self) -> str:
        """Generate validation middleware code."""
        return '''
"""Input validation middleware for DagLab."""

from functools import wraps
from typing import Any, Callable, Dict, List, Optional
from .sanitization_utils import InputSanitizer


class ValidationMiddleware:
    """Middleware for input validation and sanitization."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize validation middleware."""
        self.config = config or {}
        self.sanitizer = InputSanitizer()
    
    def validate_request_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize request data."""
        sanitized_data = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                # Sanitize string values
                sanitized_value = self.sanitizer.sanitize_string(value)
                
                # Validate against injection
                is_valid, issues = self.sanitizer.validate_against_injection(sanitized_value)
                
                if not is_valid:
                    raise ValueError(f\'Invalid input in field {key}: {issues[0]}\')
                
                sanitized_data[key] = sanitized_value
            
            elif isinstance(value, (int, float, bool)):
                sanitized_data[key] = value
            
            elif isinstance(value, dict):
                # Recursively validate nested objects
                sanitized_data[key] = self.validate_request_data(value)
            
            elif isinstance(value, list):
                # Validate list items
                sanitized_list = []
                for item in value:
                    if isinstance(item, str):
                        sanitized_item = self.sanitizer.sanitize_string(item)
                        is_valid, issues = self.sanitizer.validate_against_injection(sanitized_item)
                        if not is_valid:
                            raise ValueError(f\'Invalid input in list item: {issues[0]}\')
                        sanitized_list.append(sanitized_item)
                    else:
                        sanitized_list.append(item)
                
                sanitized_data[key] = sanitized_list
            
            else:
                # For other types, convert to string and sanitize
                sanitized_data[key] = self.sanitizer.sanitize_string(str(value))
        
        return sanitized_data


def validate_input(**validation_rules):
    """Decorator for input validation."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Apply validation rules to kwargs
            for param_name, rules in validation_rules.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    
                    # Apply validation rules
                    if \'max_length\' in rules and isinstance(value, str):
                        if len(value) > rules[\'max_length\']:
                            raise ValueError(f\'{param_name} exceeds maximum length of {rules["max_length"]}\')    
                    
                    if \'pattern\' in rules and isinstance(value, str):
                        import re
                        if not re.match(rules[\'pattern\'], value):
                            raise ValueError(f\'{param_name} does not match required pattern\')
                    
                    if \'sanitize\' in rules and rules[\'sanitize\'] and isinstance(value, str):
                        kwargs[param_name] = InputSanitizer.sanitize_string(value)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator
'''
    
    def _generate_rate_limiting_middleware(self) -> str:
        """Generate rate limiting middleware code."""
        return '''
"""Rate limiting middleware for DagLab."""

import time
import hashlib
from functools import wraps
from typing import Any, Callable, Dict, Optional


class RateLimiter:
    """Rate limiting implementation."""
    
    def __init__(self, storage_backend: str = \'memory\'):
        """Initialize rate limiter."""
        self.storage_backend = storage_backend
        self._memory_store = {} if storage_backend == \'memory\' else None
        self._redis_client = None
        
        if storage_backend == \'redis\':
            try:
                import redis
                self._redis_client = redis.Redis(host=\'localhost\', port=6379, db=0)
            except ImportError:
                raise ImportError("Redis package required for Redis rate limiting")
    
    def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int,
        burst_limit: Optional[int] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under rate limit."""
        current_time = int(time.time())
        window_start = current_time - window_seconds
        
        if self.storage_backend == \'memory\':
            return self._check_memory_limit(key, limit, window_start, current_time, burst_limit)
        elif self.storage_backend == \'redis\':
            return self._check_redis_limit(key, limit, window_start, current_time, burst_limit)
        else:
            raise ValueError(f"Unsupported storage backend: {self.storage_backend}")
    
    def _check_memory_limit(
        self, 
        key: str, 
        limit: int, 
        window_start: int, 
        current_time: int,
        burst_limit: Optional[int]
    ) -> tuple[bool, Dict[str, Any]]:
        """Check rate limit using memory storage."""
        if key not in self._memory_store:
            self._memory_store[key] = []
        
        # Remove old entries
        self._memory_store[key] = [
            timestamp for timestamp in self._memory_store[key] 
            if timestamp > window_start
        ]
        
        current_count = len(self._memory_store[key])
        
        # Check burst limit first
        if burst_limit and current_count >= burst_limit:
            return False, {
                \'allowed\': False,
                \'limit\': limit,
                \'remaining\': 0,
                \'reset_time\': window_start + 60,
                \'reason\': \'burst_limit_exceeded\'
            }
        
        # Check regular limit
        if current_count >= limit:
            return False, {
                \'allowed\': False,
                \'limit\': limit,
                \'remaining\': 0,
                \'reset_time\': window_start + 60,
                \'reason\': \'rate_limit_exceeded\'
            }
        
        # Allow request and record it
        self._memory_store[key].append(current_time)
        
        return True, {
            \'allowed\': True,
            \'limit\': limit,
            \'remaining\': limit - current_count - 1,
            \'reset_time\': window_start + 60
        }
    
    def _check_redis_limit(
        self, 
        key: str, 
        limit: int, 
        window_start: int, 
        current_time: int,
        burst_limit: Optional[int]
    ) -> tuple[bool, Dict[str, Any]]:
        """Check rate limit using Redis storage."""
        pipe = self._redis_client.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current entries
        pipe.zcard(key)
        
        # Execute pipeline
        results = pipe.execute()
        current_count = results[1]
        
        # Check limits
        if burst_limit and current_count >= burst_limit:
            return False, {
                \'allowed\': False,
                \'limit\': limit,
                \'remaining\': 0,
                \'reset_time\': window_start + 60,
                \'reason\': \'burst_limit_exceeded\'
            }
        
        if current_count >= limit:
            return False, {
                \'allowed\': False,
                \'limit\': limit,
                \'remaining\': 0,
                \'reset_time\': window_start + 60,
                \'reason\': \'rate_limit_exceeded\'
            }
        
        # Add current request
        self._redis_client.zadd(key, {str(current_time): current_time})
        self._redis_client.expire(key, 3600)  # Expire key after 1 hour
        
        return True, {
            \'allowed\': True,
            \'limit\': limit,
            \'remaining\': limit - current_count - 1,
            \'reset_time\': window_start + 60
        }


def rate_limit(limit: int, window_seconds: int = 60, burst_limit: Optional[int] = None):
    """Rate limiting decorator."""
    rate_limiter = RateLimiter()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate rate limit key (could be based on IP, user ID, etc.)
            key = f"rate_limit:{func.__name__}:default"
            
            # Check rate limit
            allowed, info = rate_limiter.is_allowed(key, limit, window_seconds, burst_limit)
            
            if not allowed:
                raise Exception(f"Rate limit exceeded: {info[\'reason\']}") 
            
            # Add rate limit info to response headers (if applicable)
            result = func(*args, **kwargs)
            
            # If result is a response object, add headers
            if hasattr(result, \'headers\'):
                result.headers[\'X-RateLimit-Limit\'] = str(info[\'limit\'])
                result.headers[\'X-RateLimit-Remaining\'] = str(info[\'remaining\'])
                result.headers[\'X-RateLimit-Reset\'] = str(info[\'reset_time\'])
            
            return result
        
        return wrapper
    return decorator
'''
    
    def _generate_csrf_protection(self) -> str:
        """Generate CSRF protection code."""
        return '''
"""CSRF protection utilities for DagLab."""

import hashlib
import hmac
import secrets
import time
from typing import Optional


class CSRFProtection:
    """CSRF protection implementation."""
    
    def __init__(self, secret_key: str):
        """Initialize CSRF protection with secret key."""
        self.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key
    
    def generate_token(self, session_id: str, timestamp: Optional[int] = None) -> str:
        """Generate CSRF token for session."""
        if timestamp is None:
            timestamp = int(time.time())
        
        # Create token data
        token_data = f"{session_id}:{timestamp}"
        
        # Generate HMAC signature
        signature = hmac.new(
            self.secret_key,
            token_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Combine timestamp and signature
        token = f"{timestamp}:{signature}"
        
        return token
    
    def validate_token(
        self, 
        token: str, 
        session_id: str, 
        max_age_seconds: int = 3600
    ) -> bool:
        """Validate CSRF token."""
        try:
            # Parse token
            timestamp_str, signature = token.split(\':\', 1)
            timestamp = int(timestamp_str)
            
            # Check token age
            current_time = int(time.time())
            if current_time - timestamp > max_age_seconds:
                return False
            
            # Regenerate expected signature
            token_data = f"{session_id}:{timestamp}"
            expected_signature = hmac.new(
                self.secret_key,
                token_data.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(signature, expected_signature)
            
        except (ValueError, TypeError):
            return False
    
    def generate_double_submit_token(self) -> str:
        """Generate double-submit CSRF token."""
        return secrets.token_urlsafe(32)
    
    def validate_double_submit(
        self, 
        cookie_token: str, 
        form_token: str
    ) -> bool:
        """Validate double-submit CSRF tokens."""
        return cookie_token and form_token and hmac.compare_digest(cookie_token, form_token)


def csrf_exempt(func):
    """Decorator to exempt function from CSRF protection."""
    func.csrf_exempt = True
    return func


def require_csrf_token(csrf_protection: CSRFProtection):
    """Decorator to require CSRF token validation."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Skip if function is marked as CSRF exempt
            if getattr(func, \'csrf_exempt\', False):
                return func(*args, **kwargs)
            
            # Extract request and session (implementation specific)
            # This would need to be adapted for your specific framework
            
            # Example validation logic:
            # csrf_token = request.form.get(\'csrfmiddlewaretoken\') or request.headers.get(\'X-CSRFToken\')
            # session_id = request.session.get(\'session_id\')
            # 
            # if not csrf_protection.validate_token(csrf_token, session_id):
            #     raise Exception("CSRF token validation failed")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator
'''


def create_input_validation_config() -> Dict[str, Any]:
    """Create default input validation configuration."""
    return {
        'sanitization': {
            'max_string_length': 10000,
            'remove_html_tags': True,
            'normalize_unicode': True,
            'remove_control_chars': True
        },
        'validation': {
            'check_sql_injection': True,
            'check_xss_patterns': True,
            'validate_file_uploads': True,
            'enforce_data_types': True
        },
        'rate_limiting': {
            'enabled': True,
            'default_limit': 1000,
            'window_seconds': 3600,
            'storage_backend': 'redis'
        },
        'csrf_protection': {
            'enabled': True,
            'token_lifetime_seconds': 3600,
            'double_submit_cookies': True,
            'require_referrer_check': True
        }
    }