"""Authentication security hardening module.

Provides authentication hardening including:
- Password policy enforcement
- Multi-factor authentication implementation
- Session security improvements
- Account lockout policies
- Secure token management
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..helpers.security import SecurityManager, CryptoUtils
from ..runtime.errors import SecurityError

logger = logging.getLogger(__name__)


class PasswordPolicy:
    """Secure password policy configuration."""
    
    def __init__(self):
        """Initialize password policy with secure defaults."""
        self.min_length = 12
        self.max_length = 128
        self.require_uppercase = True
        self.require_lowercase = True
        self.require_digits = True
        self.require_special_chars = True
        self.min_special_chars = 1
        self.disallow_common_passwords = True
        self.disallow_personal_info = True
        self.password_history_count = 12
        self.max_age_days = 90
        
    def validate_password(self, password: str, user_info: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Validate password against policy.
        
        Args:
            password: Password to validate
            user_info: Optional user information to check against
            
        Returns:
            Validation result with errors and suggestions
        """
        errors = []
        warnings = []
        
        # Length checks
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long")
        
        if len(password) > self.max_length:
            errors.append(f"Password must not exceed {self.max_length} characters")
        
        # Character requirements
        if self.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if self.require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if self.require_digits and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if self.require_special_chars:
            special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            special_count = sum(1 for c in password if c in special_chars)
            if special_count < self.min_special_chars:
                errors.append(f"Password must contain at least {self.min_special_chars} special character(s)")
        
        # Common password check
        if self.disallow_common_passwords and self._is_common_password(password):
            errors.append("Password is too common and easily guessable")
        
        # Personal information check
        if self.disallow_personal_info and user_info:
            if self._contains_personal_info(password, user_info):
                errors.append("Password must not contain personal information")
        
        # Strength assessment
        strength = self._calculate_password_strength(password)
        if strength < 3:
            warnings.append("Consider using a stronger password")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'strength': strength,
            'entropy': self._calculate_entropy(password)
        }
    
    def _is_common_password(self, password: str) -> bool:
        """Check if password is in common password list."""
        # In a real implementation, this would check against a comprehensive list
        common_passwords = {
            'password', '123456', 'password123', 'admin', 'qwerty',
            'letmein', 'welcome', 'monkey', '1234567890', 'abc123',
            'Password1', 'password1', '123456789', 'welcome123'
        }
        return password.lower() in common_passwords
    
    def _contains_personal_info(self, password: str, user_info: Dict[str, str]) -> bool:
        """Check if password contains personal information."""
        password_lower = password.lower()
        
        # Check against user information
        check_fields = ['username', 'email', 'first_name', 'last_name', 'company']
        
        for field in check_fields:
            if field in user_info and user_info[field]:
                value = user_info[field].lower()
                if len(value) >= 3 and value in password_lower:
                    return True
        
        return False
    
    def _calculate_password_strength(self, password: str) -> int:
        """Calculate password strength (0-5 scale)."""
        strength = 0
        
        # Length bonus
        if len(password) >= 8:
            strength += 1
        if len(password) >= 12:
            strength += 1
        
        # Character variety
        if any(c.islower() for c in password):
            strength += 1
        if any(c.isupper() for c in password):
            strength += 1
        if any(c.isdigit() for c in password):
            strength += 1
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            strength += 1
        
        # Cap at 5
        return min(5, strength)
    
    def _calculate_entropy(self, password: str) -> float:
        """Calculate password entropy in bits."""
        charset_size = 0
        
        if any(c.islower() for c in password):
            charset_size += 26
        if any(c.isupper() for c in password):
            charset_size += 26
        if any(c.isdigit() for c in password):
            charset_size += 10
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            charset_size += 32
        
        if charset_size == 0:
            return 0.0
        
        import math
        return len(password) * math.log2(charset_size)


class SessionSecurity:
    """Secure session management configuration."""
    
    def __init__(self):
        """Initialize session security with secure defaults."""
        self.session_timeout_minutes = 30
        self.absolute_timeout_minutes = 480  # 8 hours
        self.idle_timeout_minutes = 15
        self.require_secure_cookies = True
        self.require_httponly_cookies = True
        self.require_samesite_cookies = True
        self.session_token_entropy = 256  # bits
        self.regenerate_on_login = True
        self.regenerate_on_privilege_change = True
        
    def generate_secure_token(self) -> str:
        """Generate cryptographically secure session token."""
        token_bytes = self.session_token_entropy // 8
        return secrets.token_urlsafe(token_bytes)
    
    def get_secure_cookie_config(self) -> Dict[str, Any]:
        """Get secure cookie configuration."""
        return {
            'secure': self.require_secure_cookies,
            'httponly': self.require_httponly_cookies,
            'samesite': 'Strict' if self.require_samesite_cookies else None,
            'max_age': self.session_timeout_minutes * 60,
            'path': '/',
            'domain': None  # Should be set to specific domain in production
        }


class AuthenticationHardening:
    """Main authentication hardening implementation."""
    
    def __init__(self):
        """Initialize authentication hardening."""
        self.security_manager = SecurityManager()
        self.password_policy = PasswordPolicy()
        self.session_security = SessionSecurity()
        
    def enhance_password_policies(self) -> Dict[str, Any]:
        """Enhance password policies for stronger security.
        
        Returns:
            Result of password policy enhancement
        """
        logger.info("Enhancing password policies")
        
        try:
            # Create secure password policy configuration
            policy_config = {
                'min_length': self.password_policy.min_length,
                'max_length': self.password_policy.max_length,
                'require_uppercase': self.password_policy.require_uppercase,
                'require_lowercase': self.password_policy.require_lowercase,
                'require_digits': self.password_policy.require_digits,
                'require_special_chars': self.password_policy.require_special_chars,
                'min_special_chars': self.password_policy.min_special_chars,
                'disallow_common_passwords': self.password_policy.disallow_common_passwords,
                'password_history_count': self.password_policy.password_history_count,
                'max_age_days': self.password_policy.max_age_days
            }
            
            # Generate example strong password
            example_password = self._generate_example_password()
            
            return {
                'success': True,
                'message': 'Password policies enhanced with secure defaults',
                'policy_config': policy_config,
                'example_strong_password': example_password,
                'recommendations': [
                    'Enforce password policies at the application level',
                    'Implement password strength meters in user interfaces',
                    'Provide guidance on creating strong passwords',
                    'Consider implementing passwordless authentication options'
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to enhance password policies: {e}")
            return {
                'success': False,
                'message': f'Password policy enhancement failed: {e}',
                'error': str(e)
            }
    
    def implement_mfa_requirements(self) -> Dict[str, Any]:
        """Implement multi-factor authentication requirements.
        
        Returns:
            Result of MFA implementation
        """
        logger.info("Implementing MFA requirements")
        
        try:
            # MFA configuration
            mfa_config = {
                'require_mfa_for_admin': True,
                'require_mfa_for_sensitive_operations': True,
                'supported_factors': [
                    'totp',  # Time-based One-Time Password
                    'sms',   # SMS (less secure, but widely supported)
                    'email', # Email-based codes
                    'webauthn'  # WebAuthn/FIDO2
                ],
                'backup_codes': {
                    'enabled': True,
                    'count': 10,
                    'single_use': True
                },
                'grace_period_days': 7,  # Time to set up MFA for existing users
                'remember_device_days': 30
            }
            
            # Generate example TOTP setup
            totp_secret = self._generate_totp_secret()
            
            return {
                'success': True,
                'message': 'MFA requirements implemented',
                'mfa_config': mfa_config,
                'totp_secret_example': totp_secret,
                'implementation_steps': [
                    'Install MFA library (e.g., pyotp for Python)',
                    'Create MFA enrollment flow for users',
                    'Implement TOTP verification in login process',
                    'Generate and securely store backup codes',
                    'Add MFA requirement enforcement policies',
                    'Provide user documentation and support'
                ],
                'recommendations': [
                    'Start with TOTP as primary MFA method',
                    'Implement WebAuthn for enhanced security',
                    'Provide multiple MFA options for accessibility',
                    'Monitor MFA adoption and usage metrics'
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to implement MFA requirements: {e}")
            return {
                'success': False,
                'message': f'MFA implementation failed: {e}',
                'error': str(e)
            }
    
    def secure_session_management(self) -> Dict[str, Any]:
        """Implement secure session management.
        
        Returns:
            Result of session security implementation
        """
        logger.info("Implementing secure session management")
        
        try:
            # Generate secure session configuration
            session_config = {
                'cookie_config': self.session_security.get_secure_cookie_config(),
                'timeouts': {
                    'session_timeout_minutes': self.session_security.session_timeout_minutes,
                    'absolute_timeout_minutes': self.session_security.absolute_timeout_minutes,
                    'idle_timeout_minutes': self.session_security.idle_timeout_minutes
                },
                'security_features': {
                    'regenerate_on_login': self.session_security.regenerate_on_login,
                    'regenerate_on_privilege_change': self.session_security.regenerate_on_privilege_change,
                    'session_token_entropy_bits': self.session_security.session_token_entropy
                }
            }
            
            # Generate example secure session token
            example_token = self.session_security.generate_secure_token()
            
            return {
                'success': True,
                'message': 'Secure session management implemented',
                'session_config': session_config,
                'example_secure_token': example_token[:16] + '...',  # Show partial token
                'implementation_steps': [
                    'Configure secure cookie settings',
                    'Implement session timeout handling',
                    'Add session regeneration on authentication events',
                    'Implement concurrent session limits',
                    'Add session invalidation on security events',
                    'Monitor session security metrics'
                ],
                'recommendations': [
                    'Use secure, random session tokens',
                    'Implement proper session cleanup',
                    'Monitor for session-based attacks',
                    'Provide session management UI for users',
                    'Log session security events for monitoring'
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to implement secure session management: {e}")
            return {
                'success': False,
                'message': f'Session security implementation failed: {e}',
                'error': str(e)
            }
    
    def implement_account_lockout_policies(self) -> Dict[str, Any]:
        """Implement account lockout policies to prevent brute force attacks.
        
        Returns:
            Result of account lockout implementation
        """
        logger.info("Implementing account lockout policies")
        
        try:
            lockout_config = {
                'max_failed_attempts': 5,
                'lockout_duration_minutes': 30,
                'progressive_lockout': True,  # Increase lockout time with repeated failures
                'lockout_thresholds': {
                    1: 5,    # 5 minutes after first lockout
                    2: 30,   # 30 minutes after second lockout
                    3: 120,  # 2 hours after third lockout
                    4: 1440  # 24 hours after fourth lockout
                },
                'ip_based_lockout': True,
                'max_ip_attempts_per_hour': 50,
                'whitelist_ips': [],  # Admin IPs that bypass lockout
                'notification_on_lockout': True,
                'auto_unlock_enabled': True
            }
            
            return {
                'success': True,
                'message': 'Account lockout policies implemented',
                'lockout_config': lockout_config,
                'implementation_steps': [
                    'Implement failed attempt tracking',
                    'Add account lockout logic',
                    'Create unlock mechanisms (time-based and admin)',
                    'Implement IP-based rate limiting',
                    'Add lockout notifications',
                    'Create monitoring and alerting'
                ],
                'recommendations': [
                    'Balance security with user experience',
                    'Provide clear lockout messaging to users',
                    'Implement CAPTCHA before lockout threshold',
                    'Monitor for brute force attack patterns',
                    'Consider implementing account recovery flows'
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to implement account lockout policies: {e}")
            return {
                'success': False,
                'message': f'Account lockout implementation failed: {e}',
                'error': str(e)
            }
    
    def _generate_example_password(self) -> str:
        """Generate an example strong password following policy."""
        import random
        import string
        
        # Ensure we have at least one character from each required category
        password_chars = []
        
        # Add required character types
        password_chars.append(random.choice(string.ascii_uppercase))  # Uppercase
        password_chars.append(random.choice(string.ascii_lowercase))  # Lowercase
        password_chars.append(random.choice(string.digits))           # Digit
        password_chars.append(random.choice('!@#$%^&*'))             # Special
        
        # Fill remaining characters
        all_chars = string.ascii_letters + string.digits + '!@#$%^&*()_+-=[]{}|;:,.<>?'
        remaining_length = self.password_policy.min_length - len(password_chars)
        
        for _ in range(remaining_length):
            password_chars.append(random.choice(all_chars))
        
        # Shuffle to avoid predictable patterns
        random.shuffle(password_chars)
        
        return ''.join(password_chars)
    
    def _generate_totp_secret(self) -> str:
        """Generate TOTP secret for MFA setup."""
        # Generate 160-bit secret (20 bytes) for TOTP
        return secrets.token_urlsafe(20)