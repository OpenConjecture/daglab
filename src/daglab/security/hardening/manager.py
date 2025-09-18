"""Security hardening manager for coordinating security improvements.

Provides centralized security hardening including:
- Automated security control implementation
- Configuration hardening
- Security policy enforcement
- Continuous security monitoring
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from ..helpers.security import SecurityManager
from ..runtime.errors import SecurityError
from .auth_hardening import AuthenticationHardening
from .input_hardening import InputValidationHardening
from .config_hardening import ConfigurationHardening
from .network_hardening import NetworkSecurityHardening

logger = logging.getLogger(__name__)


@dataclass
class HardeningResult:
    """Result of security hardening operation."""
    component: str
    success: bool
    message: str
    details: Dict[str, Any]
    timestamp: datetime


class SecurityHardeningManager:
    """Manages security hardening across all components."""
    
    def __init__(self, project_path: Path):
        """Initialize security hardening manager.
        
        Args:
            project_path: Path to project root
        """
        self.project_path = Path(project_path)
        self.security_manager = SecurityManager()
        
        # Initialize hardening components
        self.auth_hardening = AuthenticationHardening()
        self.input_hardening = InputValidationHardening()
        self.config_hardening = ConfigurationHardening()
        self.network_hardening = NetworkSecurityHardening()
        
        # Hardening results
        self.results: List[HardeningResult] = []
        
        logger.info(f"Security hardening manager initialized for {project_path}")
    
    def apply_comprehensive_hardening(self) -> List[HardeningResult]:
        """Apply comprehensive security hardening.
        
        Returns:
            List of hardening results
        """
        logger.info("Starting comprehensive security hardening")
        
        # Clear previous results
        self.results = []
        
        try:
            # Apply authentication hardening
            auth_results = self._apply_authentication_hardening()
            self.results.extend(auth_results)
            
            # Apply input validation hardening
            input_results = self._apply_input_hardening()
            self.results.extend(input_results)
            
            # Apply configuration hardening
            config_results = self._apply_configuration_hardening()
            self.results.extend(config_results)
            
            # Apply network security hardening
            network_results = self._apply_network_hardening()
            self.results.extend(network_results)
            
            # Generate hardening report
            self._generate_hardening_report()
            
        except Exception as e:
            logger.error(f"Security hardening failed: {e}")
            raise SecurityError(f"Security hardening failed: {e}", cause=e)
        
        successful_count = sum(1 for r in self.results if r.success)
        logger.info(f"Security hardening completed: {successful_count}/{len(self.results)} successful")
        
        return self.results
    
    def apply_targeted_hardening(self, component: str) -> List[HardeningResult]:
        """Apply hardening to specific component.
        
        Args:
            component: Component to harden (auth, input, config, network)
            
        Returns:
            List of hardening results
        """
        results = []
        
        if component == "auth":
            results = self._apply_authentication_hardening()
        elif component == "input":
            results = self._apply_input_hardening()
        elif component == "config":
            results = self._apply_configuration_hardening()
        elif component == "network":
            results = self._apply_network_hardening()
        else:
            raise ValueError(f"Unknown hardening component: {component}")
        
        self.results.extend(results)
        return results
    
    def _apply_authentication_hardening(self) -> List[HardeningResult]:
        """Apply authentication hardening."""
        logger.info("Applying authentication hardening")
        results = []
        
        try:
            # Enhance password policies
            result = self.auth_hardening.enhance_password_policies()
            results.append(HardeningResult(
                component="authentication",
                success=result.get('success', False),
                message=result.get('message', 'Password policy enhancement'),
                details=result,
                timestamp=datetime.utcnow()
            ))
            
            # Implement MFA requirements
            result = self.auth_hardening.implement_mfa_requirements()
            results.append(HardeningResult(
                component="authentication",
                success=result.get('success', False),
                message=result.get('message', 'MFA implementation'),
                details=result,
                timestamp=datetime.utcnow()
            ))
            
            # Secure session management
            result = self.auth_hardening.secure_session_management()
            results.append(HardeningResult(
                component="authentication",
                success=result.get('success', False),
                message=result.get('message', 'Session security hardening'),
                details=result,
                timestamp=datetime.utcnow()
            ))
            
        except Exception as e:
            logger.error(f"Authentication hardening failed: {e}")
            results.append(HardeningResult(
                component="authentication",
                success=False,
                message=f"Authentication hardening failed: {e}",
                details={'error': str(e)},
                timestamp=datetime.utcnow()
            ))
        
        return results
    
    def _apply_input_hardening(self) -> List[HardeningResult]:
        """Apply input validation hardening."""
        logger.info("Applying input validation hardening")
        results = []
        
        try:
            # Enhance input sanitization
            result = self.input_hardening.enhance_input_sanitization(self.project_path)
            results.append(HardeningResult(
                component="input_validation",
                success=result.get('success', False),
                message=result.get('message', 'Input sanitization enhancement'),
                details=result,
                timestamp=datetime.utcnow()
            ))
            
            # Implement rate limiting
            result = self.input_hardening.implement_rate_limiting()
            results.append(HardeningResult(
                component="input_validation",
                success=result.get('success', False),
                message=result.get('message', 'Rate limiting implementation'),
                details=result,
                timestamp=datetime.utcnow()
            ))
            
            # Add CSRF protection
            result = self.input_hardening.add_csrf_protection()
            results.append(HardeningResult(
                component="input_validation",
                success=result.get('success', False),
                message=result.get('message', 'CSRF protection implementation'),
                details=result,
                timestamp=datetime.utcnow()
            ))
            
        except Exception as e:
            logger.error(f"Input validation hardening failed: {e}")
            results.append(HardeningResult(
                component="input_validation",
                success=False,
                message=f"Input validation hardening failed: {e}",
                details={'error': str(e)},
                timestamp=datetime.utcnow()
            ))
        
        return results
    
    def _apply_configuration_hardening(self) -> List[HardeningResult]:
        """Apply configuration hardening."""
        logger.info("Applying configuration hardening")
        results = []
        
        try:
            # Secure default configurations
            result = self.config_hardening.secure_default_configurations(self.project_path)
            results.append(HardeningResult(
                component="configuration",
                success=result.get('success', False),
                message=result.get('message', 'Default configuration hardening'),
                details=result,
                timestamp=datetime.utcnow()
            ))
            
            # Implement secrets management
            result = self.config_hardening.implement_secrets_management(self.project_path)
            results.append(HardeningResult(
                component="configuration",
                success=result.get('success', False),
                message=result.get('message', 'Secrets management implementation'),
                details=result,
                timestamp=datetime.utcnow()
            ))
            
            # Secure file permissions
            result = self.config_hardening.secure_file_permissions(self.project_path)
            results.append(HardeningResult(
                component="configuration",
                success=result.get('success', False),
                message=result.get('message', 'File permissions hardening'),
                details=result,
                timestamp=datetime.utcnow()
            ))
            
        except Exception as e:
            logger.error(f"Configuration hardening failed: {e}")
            results.append(HardeningResult(
                component="configuration",
                success=False,
                message=f"Configuration hardening failed: {e}",
                details={'error': str(e)},
                timestamp=datetime.utcnow()
            ))
        
        return results
    
    def _apply_network_hardening(self) -> List[HardeningResult]:
        """Apply network security hardening."""
        logger.info("Applying network security hardening")
        results = []
        
        try:
            # Enforce HTTPS/TLS
            result = self.network_hardening.enforce_https_tls()
            results.append(HardeningResult(
                component="network_security",
                success=result.get('success', False),
                message=result.get('message', 'HTTPS/TLS enforcement'),
                details=result,
                timestamp=datetime.utcnow()
            ))
            
            # Implement security headers
            result = self.network_hardening.implement_security_headers()
            results.append(HardeningResult(
                component="network_security",
                success=result.get('success', False),
                message=result.get('message', 'Security headers implementation'),
                details=result,
                timestamp=datetime.utcnow()
            ))
            
            # Configure CORS properly
            result = self.network_hardening.configure_cors_security()
            results.append(HardeningResult(
                component="network_security",
                success=result.get('success', False),
                message=result.get('message', 'CORS security configuration'),
                details=result,
                timestamp=datetime.utcnow()
            ))
            
        except Exception as e:
            logger.error(f"Network security hardening failed: {e}")
            results.append(HardeningResult(
                component="network_security",
                success=False,
                message=f"Network security hardening failed: {e}",
                details={'error': str(e)},
                timestamp=datetime.utcnow()
            ))
        
        return results
    
    def _generate_hardening_report(self) -> None:
        """Generate comprehensive hardening report."""
        try:
            output_dir = self.project_path / "security_audit"
            output_dir.mkdir(exist_ok=True)
            
            report_path = output_dir / "hardening_report.json"
            
            # Aggregate results by component
            component_results = {}
            for result in self.results:
                if result.component not in component_results:
                    component_results[result.component] = []
                component_results[result.component].append({
                    'success': result.success,
                    'message': result.message,
                    'details': result.details,
                    'timestamp': result.timestamp.isoformat()
                })
            
            # Calculate summary statistics
            total_operations = len(self.results)
            successful_operations = sum(1 for r in self.results if r.success)
            success_rate = (successful_operations / total_operations * 100) if total_operations > 0 else 0
            
            report_data = {
                'report_info': {
                    'generated_at': datetime.utcnow().isoformat(),
                    'project_path': str(self.project_path),
                    'total_operations': total_operations,
                    'successful_operations': successful_operations,
                    'success_rate': success_rate
                },
                'summary': {
                    'authentication': len([r for r in self.results if r.component == 'authentication']),
                    'input_validation': len([r for r in self.results if r.component == 'input_validation']),
                    'configuration': len([r for r in self.results if r.component == 'configuration']),
                    'network_security': len([r for r in self.results if r.component == 'network_security'])
                },
                'results_by_component': component_results,
                'recommendations': self._generate_hardening_recommendations()
            }
            
            import json
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            logger.info(f"Hardening report saved to {report_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate hardening report: {e}")
    
    def _generate_hardening_recommendations(self) -> List[str]:
        """Generate recommendations based on hardening results."""
        recommendations = []
        
        # Check for failed operations
        failed_results = [r for r in self.results if not r.success]
        
        if failed_results:
            recommendations.append(
                f"Review and address {len(failed_results)} failed hardening operations"
            )
        
        # Component-specific recommendations
        auth_failures = [r for r in failed_results if r.component == 'authentication']
        if auth_failures:
            recommendations.append(
                "Prioritize authentication security improvements for critical security impact"
            )
        
        input_failures = [r for r in failed_results if r.component == 'input_validation']
        if input_failures:
            recommendations.append(
                "Implement comprehensive input validation to prevent injection attacks"
            )
        
        # General recommendations
        recommendations.extend([
            "Regularly review and update security configurations",
            "Monitor security logs for indicators of compromise",
            "Conduct periodic security assessments",
            "Provide security training for development team",
            "Implement automated security testing in CI/CD pipeline"
        ])
        
        return recommendations
    
    def get_hardening_status(self) -> Dict[str, Any]:
        """Get current hardening status.
        
        Returns:
            Dictionary with hardening status information
        """
        if not self.results:
            return {
                'status': 'not_started',
                'message': 'No hardening operations have been performed'
            }
        
        total_operations = len(self.results)
        successful_operations = sum(1 for r in self.results if r.success)
        success_rate = (successful_operations / total_operations * 100) if total_operations > 0 else 0
        
        # Determine overall status
        if success_rate == 100:
            status = 'completed'
            message = 'All hardening operations completed successfully'
        elif success_rate >= 80:
            status = 'mostly_complete'
            message = f'Most hardening operations successful ({success_rate:.1f}%)'
        elif success_rate >= 50:
            status = 'partial'
            message = f'Some hardening operations successful ({success_rate:.1f}%)'
        else:
            status = 'failed'
            message = f'Many hardening operations failed ({success_rate:.1f}% success)'
        
        return {
            'status': status,
            'message': message,
            'total_operations': total_operations,
            'successful_operations': successful_operations,
            'success_rate': success_rate,
            'last_updated': max(r.timestamp for r in self.results).isoformat() if self.results else None
        }