"""Configuration security analyzer for DagLab.

Analyzes configuration files for security issues including:
- Hardcoded secrets and credentials
- Insecure configuration settings
- Missing security configurations
- Exposed sensitive information
- Weak cryptographic settings
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Pattern
from dataclasses import dataclass
import yaml

from ..helpers.security import SecurityManager, FileOperationSecurity
from ..runtime.errors import SecurityError
from .framework import SecurityFinding, SeverityLevel, FindingCategory

logger = logging.getLogger(__name__)


@dataclass
class ConfigSecurityRule:
    """Configuration security rule definition."""
    name: str
    description: str
    pattern: Pattern[str]
    severity: SeverityLevel
    category: FindingCategory
    remediation: str
    file_types: List[str]
    

class ConfigurationAnalyzer:
    """Analyzes configuration files for security issues."""
    
    def __init__(self):
        """Initialize configuration analyzer."""
        self.security_manager = SecurityManager()
        self.file_ops = FileOperationSecurity()
        
        # Initialize security rules
        self.security_rules = self._load_security_rules()
        
        # File types to analyze
        self.config_extensions = {
            '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
            '.env', '.properties', '.xml', '.config'
        }
        
    def analyze_configurations(self, project_path: Path) -> List[SecurityFinding]:
        """Analyze all configuration files in project.
        
        Args:
            project_path: Path to project root
            
        Returns:
            List of configuration security findings
        """
        findings = []
        
        logger.info(f"Starting configuration security analysis for {project_path}")
        
        # Find all configuration files
        config_files = self._find_config_files(project_path)
        
        for config_file in config_files:
            try:
                file_findings = self._analyze_config_file(config_file)
                findings.extend(file_findings)
            except Exception as e:
                logger.error(f"Failed to analyze {config_file}: {e}")
                
                # Add error as finding
                error_finding = SecurityFinding(
                    id=f"config_analysis_error_{config_file.name}",
                    title=f"Configuration Analysis Error: {config_file.name}",
                    description=f"Failed to analyze configuration file: {str(e)}",
                    severity=SeverityLevel.LOW,
                    category=FindingCategory.CONFIGURATION,
                    location=str(config_file),
                    evidence={"error": str(e)}
                )
                findings.append(error_finding)
        
        logger.info(f"Configuration analysis completed: {len(findings)} findings")
        return findings
    
    def _find_config_files(self, project_path: Path) -> List[Path]:
        """Find all configuration files in project."""
        config_files = []
        
        # Common configuration file patterns
        config_patterns = [
            "*.json", "*.yaml", "*.yml", "*.toml", "*.ini", "*.cfg", "*.conf",
            "*.env", "*.properties", "*.xml", "*.config",
            ".env*", "config.*", "settings.*", "dagster.*", "docker-compose.*"
        ]
        
        for pattern in config_patterns:
            config_files.extend(project_path.glob(pattern))
            config_files.extend(project_path.glob(f"**/{pattern}"))
        
        # Remove duplicates and filter valid files
        unique_files = []
        seen = set()
        
        for file_path in config_files:
            if file_path.is_file() and str(file_path) not in seen:
                # Skip certain directories
                skip_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}
                if not any(skip_dir in file_path.parts for skip_dir in skip_dirs):
                    unique_files.append(file_path)
                    seen.add(str(file_path))
        
        return unique_files
    
    def _analyze_config_file(self, config_file: Path) -> List[SecurityFinding]:
        """Analyze a single configuration file."""
        findings = []
        
        try:
            # Read file content
            content = self.file_ops.safe_read(config_file)
            
            # Apply security rules
            for rule in self.security_rules:
                if self._file_matches_rule(config_file, rule):
                    rule_findings = self._apply_rule(config_file, content, rule)
                    findings.extend(rule_findings)
            
            # Perform structured analysis if possible
            if config_file.suffix.lower() in ['.json', '.yaml', '.yml']:
                structured_findings = self._analyze_structured_config(
                    config_file, content
                )
                findings.extend(structured_findings)
            
            # Check for environment-specific issues
            env_findings = self._check_environment_config(config_file, content)
            findings.extend(env_findings)
            
        except Exception as e:
            logger.error(f"Failed to read config file {config_file}: {e}")
        
        return findings
    
    def _file_matches_rule(self, file_path: Path, rule: ConfigSecurityRule) -> bool:
        """Check if file matches rule criteria."""
        file_ext = file_path.suffix.lower()
        return file_ext in rule.file_types or '*' in rule.file_types
    
    def _apply_rule(self, file_path: Path, content: str, rule: ConfigSecurityRule) -> List[SecurityFinding]:
        """Apply security rule to file content."""
        findings = []
        
        # Search for pattern matches
        matches = rule.pattern.finditer(content)
        
        for match in matches:
            # Get line number
            line_num = content[:match.start()].count('\n') + 1
            
            # Extract matched content (mask sensitive parts)
            matched_text = match.group(0)
            if len(matched_text) > 100:
                matched_text = matched_text[:100] + "..."
            
            # Create finding
            finding = SecurityFinding(
                id=f"config_{rule.name}_{file_path.name}_{line_num}",
                title=f"Configuration Security Issue: {rule.name}",
                description=f"{rule.description}\n\nFound in {file_path.name} at line {line_num}",
                severity=rule.severity,
                category=rule.category,
                location=f"{file_path}:{line_num}",
                evidence={
                    "rule_name": rule.name,
                    "line_number": line_num,
                    "matched_pattern": matched_text,
                    "file_type": file_path.suffix
                },
                remediation=rule.remediation
            )
            
            findings.append(finding)
        
        return findings
    
    def _analyze_structured_config(self, file_path: Path, content: str) -> List[SecurityFinding]:
        """Analyze structured configuration files (JSON/YAML)."""
        findings = []
        
        try:
            # Parse configuration
            if file_path.suffix.lower() == '.json':
                config_data = json.loads(content)
            else:  # YAML
                config_data = yaml.safe_load(content)
            
            if not isinstance(config_data, dict):
                return findings
            
            # Check for specific configuration issues
            findings.extend(self._check_dagster_config(file_path, config_data))
            findings.extend(self._check_database_config(file_path, config_data))
            findings.extend(self._check_auth_config(file_path, config_data))
            findings.extend(self._check_logging_config(file_path, config_data))
            
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            logger.warning(f"Failed to parse structured config {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error analyzing structured config {file_path}: {e}")
        
        return findings
    
    def _check_dagster_config(self, file_path: Path, config: Dict[str, Any]) -> List[SecurityFinding]:
        """Check Dagster-specific configuration security."""
        findings = []
        
        # Check for development mode in production
        if 'dagster' in config:
            dagster_config = config['dagster']
            
            if dagster_config.get('debug', False):
                findings.append(SecurityFinding(
                    id=f"dagster_debug_{file_path.name}",
                    title="Dagster Debug Mode Enabled",
                    description="Debug mode is enabled which may expose sensitive information",
                    severity=SeverityLevel.MEDIUM,
                    category=FindingCategory.CONFIGURATION,
                    location=str(file_path),
                    remediation="Disable debug mode in production environments"
                ))
            
            # Check for insecure run launcher
            run_launcher = dagster_config.get('run_launcher', {})
            if run_launcher.get('module') == 'dagster.core.launcher.sync_in_memory_run_launcher':
                findings.append(SecurityFinding(
                    id=f"dagster_insecure_launcher_{file_path.name}",
                    title="Insecure Dagster Run Launcher",
                    description="Using in-memory run launcher which is not suitable for production",
                    severity=SeverityLevel.MEDIUM,
                    category=FindingCategory.CONFIGURATION,
                    location=str(file_path),
                    remediation="Use a production-ready run launcher like K8sRunLauncher or DockerRunLauncher"
                ))
        
        return findings
    
    def _check_database_config(self, file_path: Path, config: Dict[str, Any]) -> List[SecurityFinding]:
        """Check database configuration security."""
        findings = []
        
        # Look for database configurations
        db_keys = ['database', 'db', 'storage', 'postgres', 'mysql', 'sqlite']
        
        for key in db_keys:
            if key in config:
                db_config = config[key]
                if isinstance(db_config, dict):
                    
                    # Check for hardcoded passwords
                    if 'password' in db_config and db_config['password']:
                        findings.append(SecurityFinding(
                            id=f"db_hardcoded_password_{file_path.name}",
                            title="Hardcoded Database Password",
                            description="Database password is hardcoded in configuration file",
                            severity=SeverityLevel.HIGH,
                            category=FindingCategory.DATA_PROTECTION,
                            location=str(file_path),
                            remediation="Use environment variables or secure secret management for database passwords"
                        ))
                    
                    # Check for weak SSL settings
                    if db_config.get('sslmode') == 'disable':
                        findings.append(SecurityFinding(
                            id=f"db_ssl_disabled_{file_path.name}",
                            title="Database SSL Disabled",
                            description="SSL/TLS encryption is disabled for database connection",
                            severity=SeverityLevel.HIGH,
                            category=FindingCategory.NETWORK_SECURITY,
                            location=str(file_path),
                            remediation="Enable SSL/TLS encryption for database connections"
                        ))
        
        return findings
    
    def _check_auth_config(self, file_path: Path, config: Dict[str, Any]) -> List[SecurityFinding]:
        """Check authentication configuration security."""
        findings = []
        
        # Look for authentication configurations
        auth_keys = ['auth', 'authentication', 'security', 'jwt', 'oauth']
        
        for key in auth_keys:
            if key in config:
                auth_config = config[key]
                if isinstance(auth_config, dict):
                    
                    # Check for weak JWT secrets
                    jwt_secret = auth_config.get('jwt_secret') or auth_config.get('secret_key')
                    if jwt_secret and len(str(jwt_secret)) < 32:
                        findings.append(SecurityFinding(
                            id=f"weak_jwt_secret_{file_path.name}",
                            title="Weak JWT Secret",
                            description="JWT secret key is too short and may be easily brute-forced",
                            severity=SeverityLevel.HIGH,
                            category=FindingCategory.AUTHENTICATION,
                            location=str(file_path),
                            remediation="Use a strong, randomly generated secret key of at least 32 characters"
                        ))
                    
                    # Check for disabled authentication
                    if auth_config.get('enabled', True) is False:
                        findings.append(SecurityFinding(
                            id=f"auth_disabled_{file_path.name}",
                            title="Authentication Disabled",
                            description="Authentication is explicitly disabled",
                            severity=SeverityLevel.CRITICAL,
                            category=FindingCategory.AUTHENTICATION,
                            location=str(file_path),
                            remediation="Enable authentication for production environments"
                        ))
        
        return findings
    
    def _check_logging_config(self, file_path: Path, config: Dict[str, Any]) -> List[SecurityFinding]:
        """Check logging configuration security."""
        findings = []
        
        # Look for logging configurations
        log_keys = ['logging', 'log', 'logger']
        
        for key in log_keys:
            if key in config:
                log_config = config[key]
                if isinstance(log_config, dict):
                    
                    # Check for debug logging in production
                    level = log_config.get('level', '').upper()
                    if level == 'DEBUG':
                        findings.append(SecurityFinding(
                            id=f"debug_logging_{file_path.name}",
                            title="Debug Logging Enabled",
                            description="Debug logging level may expose sensitive information",
                            severity=SeverityLevel.MEDIUM,
                            category=FindingCategory.DATA_PROTECTION,
                            location=str(file_path),
                            remediation="Use INFO or WARNING log level in production"
                        ))
                    
                    # Check for log file permissions
                    log_file = log_config.get('filename') or log_config.get('file')
                    if log_file and not str(log_file).startswith('/var/log/'):
                        findings.append(SecurityFinding(
                            id=f"insecure_log_location_{file_path.name}",
                            title="Insecure Log File Location",
                            description="Log files are not stored in a secure location",
                            severity=SeverityLevel.LOW,
                            category=FindingCategory.CONFIGURATION,
                            location=str(file_path),
                            remediation="Store log files in /var/log/ or other secure location"
                        ))
        
        return findings
    
    def _check_environment_config(self, file_path: Path, content: str) -> List[SecurityFinding]:
        """Check for environment-specific configuration issues."""
        findings = []
        
        # Check for development/test configurations in production
        dev_indicators = [
            'localhost', '127.0.0.1', 'dev', 'development', 'test', 'testing',
            'debug=true', 'DEBUG=True', 'example.com'
        ]
        
        for indicator in dev_indicators:
            if indicator.lower() in content.lower():
                findings.append(SecurityFinding(
                    id=f"dev_config_{file_path.name}_{indicator}",
                    title="Development Configuration Detected",
                    description=f"Configuration contains development/test indicator: {indicator}",
                    severity=SeverityLevel.MEDIUM,
                    category=FindingCategory.CONFIGURATION,
                    location=str(file_path),
                    evidence={"indicator": indicator},
                    remediation="Ensure production configurations don't contain development settings"
                ))
                break  # Only report once per file
        
        return findings
    
    def _load_security_rules(self) -> List[ConfigSecurityRule]:
        """Load configuration security rules."""
        rules = [
            # Hardcoded secrets
            ConfigSecurityRule(
                name="hardcoded_api_key",
                description="Hardcoded API key found in configuration",
                pattern=re.compile(r'(api[_-]?key|apikey)\s*[=:]\s*["\']?[a-zA-Z0-9]{20,}["\']?', re.IGNORECASE),
                severity=SeverityLevel.HIGH,
                category=FindingCategory.DATA_PROTECTION,
                remediation="Use environment variables or secure secret management for API keys",
                file_types=['*']
            ),
            
            ConfigSecurityRule(
                name="hardcoded_password",
                description="Hardcoded password found in configuration",
                pattern=re.compile(r'password\s*[=:]\s*["\']?[^\s"\',;]{8,}["\']?', re.IGNORECASE),
                severity=SeverityLevel.HIGH,
                category=FindingCategory.AUTHENTICATION,
                remediation="Use environment variables or secure secret management for passwords",
                file_types=['*']
            ),
            
            ConfigSecurityRule(
                name="hardcoded_token",
                description="Hardcoded token found in configuration",
                pattern=re.compile(r'(token|bearer|jwt)\s*[=:]\s*["\']?[a-zA-Z0-9+/]{30,}[="\']?', re.IGNORECASE),
                severity=SeverityLevel.HIGH,
                category=FindingCategory.AUTHENTICATION,
                remediation="Use environment variables or secure secret management for tokens",
                file_types=['*']
            ),
            
            # Database connections
            ConfigSecurityRule(
                name="database_url_with_password",
                description="Database URL with embedded password",
                pattern=re.compile(r'(postgresql|mysql|mongodb)://[^:]+:[^@]+@', re.IGNORECASE),
                severity=SeverityLevel.HIGH,
                category=FindingCategory.DATA_PROTECTION,
                remediation="Use connection strings without embedded passwords",
                file_types=['*']
            ),
            
            # AWS credentials
            ConfigSecurityRule(
                name="aws_access_key",
                description="AWS access key found in configuration",
                pattern=re.compile(r'AKIA[0-9A-Z]{16}'),
                severity=SeverityLevel.CRITICAL,
                category=FindingCategory.DATA_PROTECTION,
                remediation="Use IAM roles or AWS credentials file instead of hardcoded keys",
                file_types=['*']
            ),
            
            ConfigSecurityRule(
                name="aws_secret_key",
                description="AWS secret key found in configuration",
                pattern=re.compile(r'aws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*["\']?[a-zA-Z0-9+/]{40}["\']?', re.IGNORECASE),
                severity=SeverityLevel.CRITICAL,
                category=FindingCategory.DATA_PROTECTION,
                remediation="Use IAM roles or AWS credentials file instead of hardcoded keys",
                file_types=['*']
            ),
            
            # Private keys
            ConfigSecurityRule(
                name="private_key",
                description="Private key found in configuration",
                pattern=re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
                severity=SeverityLevel.CRITICAL,
                category=FindingCategory.DATA_PROTECTION,
                remediation="Store private keys in secure key management systems",
                file_types=['*']
            ),
            
            # Insecure protocols
            ConfigSecurityRule(
                name="http_url",
                description="Insecure HTTP URL found (should use HTTPS)",
                pattern=re.compile(r'http://(?!localhost|127\.0\.0\.1)[^\s"\'>]+', re.IGNORECASE),
                severity=SeverityLevel.MEDIUM,
                category=FindingCategory.NETWORK_SECURITY,
                remediation="Use HTTPS instead of HTTP for external URLs",
                file_types=['*']
            ),
            
            # Debug settings
            ConfigSecurityRule(
                name="debug_enabled",
                description="Debug mode enabled in configuration",
                pattern=re.compile(r'debug\s*[=:]\s*(true|1|yes|on)', re.IGNORECASE),
                severity=SeverityLevel.MEDIUM,
                category=FindingCategory.CONFIGURATION,
                remediation="Disable debug mode in production environments",
                file_types=['*']
            ),
            
            # Weak encryption
            ConfigSecurityRule(
                name="weak_cipher",
                description="Weak cipher or encryption algorithm",
                pattern=re.compile(r'(des|3des|md5|sha1|rc4)(?!\w)', re.IGNORECASE),
                severity=SeverityLevel.HIGH,
                category=FindingCategory.DATA_PROTECTION,
                remediation="Use strong encryption algorithms like AES-256, SHA-256, or better",
                file_types=['*']
            )
        ]
        
        return rules