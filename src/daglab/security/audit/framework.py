"""Comprehensive security audit framework for DagLab.

Provides systematic security assessment capabilities including:
- Vulnerability scanning
- Configuration analysis  
- Code security review
- Risk assessment
- Compliance validation
"""

import json
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..helpers.security import SecurityManager, FileOperationSecurity
from ..runtime.errors import SecurityError
from .vulnerability_assessor import VulnerabilityAssessor
from .config_analyzer import ConfigurationAnalyzer
from .code_analyzer import CodeSecurityAnalyzer
from .risk_assessor import RiskAssessor

logger = logging.getLogger(__name__)


class SeverityLevel(Enum):
    """Security finding severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(Enum):
    """Security finding categories."""
    VULNERABILITY = "vulnerability"
    CONFIGURATION = "configuration"
    CODE_SECURITY = "code_security"
    DEPENDENCY = "dependency"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_PROTECTION = "data_protection"
    NETWORK_SECURITY = "network_security"
    COMPLIANCE = "compliance"


@dataclass
class SecurityFinding:
    """Represents a security finding from audit."""
    id: str
    title: str
    description: str
    severity: SeverityLevel
    category: FindingCategory
    location: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    remediation: Optional[str] = None
    cve_id: Optional[str] = None
    cwe_id: Optional[str] = None
    cvss_score: Optional[float] = None
    affected_components: List[str] = field(default_factory=list)
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category.value,
            "location": self.location,
            "evidence": self.evidence,
            "remediation": self.remediation,
            "cve_id": self.cve_id,
            "cwe_id": self.cwe_id,
            "cvss_score": self.cvss_score,
            "affected_components": self.affected_components,
            "discovered_at": self.discovered_at.isoformat()
        }


@dataclass
class AuditReport:
    """Security audit report."""
    audit_id: str
    project_name: str
    audit_date: datetime
    auditor: str
    findings: List[SecurityFinding] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    compliance_status: Dict[str, bool] = field(default_factory=dict)
    risk_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "audit_id": self.audit_id,
            "project_name": self.project_name,
            "audit_date": self.audit_date.isoformat(),
            "auditor": self.auditor,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
            "recommendations": self.recommendations,
            "compliance_status": self.compliance_status,
            "risk_score": self.risk_score
        }
    
    def get_findings_by_severity(self, severity: SeverityLevel) -> List[SecurityFinding]:
        """Get findings by severity level."""
        return [f for f in self.findings if f.severity == severity]
    
    def get_findings_by_category(self, category: FindingCategory) -> List[SecurityFinding]:
        """Get findings by category."""
        return [f for f in self.findings if f.category == category]
    
    def get_critical_findings(self) -> List[SecurityFinding]:
        """Get critical severity findings."""
        return self.get_findings_by_severity(SeverityLevel.CRITICAL)
    
    def calculate_risk_score(self) -> float:
        """Calculate overall risk score based on findings."""
        if not self.findings:
            return 0.0
        
        severity_weights = {
            SeverityLevel.CRITICAL: 10.0,
            SeverityLevel.HIGH: 7.0,
            SeverityLevel.MEDIUM: 4.0,
            SeverityLevel.LOW: 2.0,
            SeverityLevel.INFO: 0.5
        }
        
        total_score = sum(
            severity_weights.get(finding.severity, 0.0) 
            for finding in self.findings
        )
        
        # Normalize to 0-100 scale
        max_possible = len(self.findings) * severity_weights[SeverityLevel.CRITICAL]
        if max_possible > 0:
            self.risk_score = min(100.0, (total_score / max_possible) * 100)
        else:
            self.risk_score = 0.0
            
        return self.risk_score


class SecurityAuditFramework:
    """Comprehensive security audit framework."""
    
    def __init__(
        self,
        project_path: Path,
        config_path: Optional[Path] = None,
        output_dir: Optional[Path] = None
    ):
        """Initialize security audit framework.
        
        Args:
            project_path: Path to project root
            config_path: Path to audit configuration
            output_dir: Directory for audit outputs
        """
        self.project_path = Path(project_path)
        self.config_path = config_path
        self.output_dir = output_dir or self.project_path / "security_audit"
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize security manager
        self.security_manager = SecurityManager(strict_mode=True)
        self.file_ops = FileOperationSecurity(base_path=self.project_path)
        
        # Initialize analyzers
        self.vulnerability_assessor = VulnerabilityAssessor()
        self.config_analyzer = ConfigurationAnalyzer()
        self.code_analyzer = CodeSecurityAnalyzer()
        self.risk_assessor = RiskAssessor()
        
        # Audit configuration
        self.config = self._load_audit_config()
        
        # Current audit context
        self.current_audit: Optional[AuditReport] = None
        
        logger.info(f"Security audit framework initialized for {project_path}")
    
    def _load_audit_config(self) -> Dict[str, Any]:
        """Load audit configuration."""
        default_config = {
            "scan_dependencies": True,
            "scan_code": True,
            "analyze_configs": True,
            "check_compliance": True,
            "excluded_paths": [
                ".git", "__pycache__", "node_modules", ".venv", "venv",
                "*.pyc", "*.pyo", "*.egg-info"
            ],
            "severity_threshold": "medium",
            "max_findings": 1000,
            "timeout_seconds": 3600
        }
        
        if self.config_path and self.config_path.exists():
            try:
                config_content = self.file_ops.safe_read(self.config_path)
                if self.config_path.suffix.lower() == '.json':
                    custom_config = json.loads(config_content)
                else:
                    # Assume YAML
                    import yaml
                    custom_config = yaml.safe_load(config_content)
                
                default_config.update(custom_config)
            except Exception as e:
                logger.warning(f"Failed to load audit config: {e}")
        
        return default_config
    
    def start_audit(
        self,
        project_name: str,
        auditor: str = "DagLab Security Framework"
    ) -> str:
        """Start a new security audit.
        
        Args:
            project_name: Name of the project being audited
            auditor: Name of the auditor
            
        Returns:
            Audit ID
        """
        audit_id = self._generate_audit_id()
        
        self.current_audit = AuditReport(
            audit_id=audit_id,
            project_name=project_name,
            audit_date=datetime.utcnow(),
            auditor=auditor
        )
        
        logger.info(f"Started security audit {audit_id} for {project_name}")
        return audit_id
    
    def run_comprehensive_audit(
        self,
        project_name: str,
        auditor: str = "DagLab Security Framework"
    ) -> AuditReport:
        """Run comprehensive security audit.
        
        Args:
            project_name: Name of the project
            auditor: Name of the auditor
            
        Returns:
            Complete audit report
        """
        # Start audit
        audit_id = self.start_audit(project_name, auditor)
        
        try:
            # Vulnerability assessment
            if self.config.get("scan_dependencies", True):
                vuln_findings = self.vulnerability_assessor.assess_dependencies(
                    self.project_path
                )
                self.current_audit.findings.extend(vuln_findings)
            
            # Configuration analysis
            if self.config.get("analyze_configs", True):
                config_findings = self.config_analyzer.analyze_configurations(
                    self.project_path
                )
                self.current_audit.findings.extend(config_findings)
            
            # Code security analysis
            if self.config.get("scan_code", True):
                code_findings = self.code_analyzer.analyze_code_security(
                    self.project_path,
                    excluded_paths=self.config.get("excluded_paths", [])
                )
                self.current_audit.findings.extend(code_findings)
            
            # Risk assessment
            risk_findings = self.risk_assessor.assess_risks(
                self.project_path,
                self.current_audit.findings
            )
            self.current_audit.findings.extend(risk_findings)
            
            # Generate summary and recommendations
            self._generate_audit_summary()
            self._generate_recommendations()
            
            # Calculate risk score
            self.current_audit.calculate_risk_score()
            
            # Save audit report
            self._save_audit_report()
            
            logger.info(
                f"Completed security audit {audit_id}: "
                f"{len(self.current_audit.findings)} findings, "
                f"risk score: {self.current_audit.risk_score:.1f}"
            )
            
            return self.current_audit
            
        except Exception as e:
            logger.error(f"Security audit failed: {e}")
            raise SecurityError(f"Security audit failed: {e}", cause=e)
    
    def run_targeted_audit(
        self,
        audit_type: str,
        target_path: Optional[Path] = None,
        **kwargs
    ) -> List[SecurityFinding]:
        """Run targeted security audit.
        
        Args:
            audit_type: Type of audit (vulnerability, configuration, code)
            target_path: Specific path to audit
            **kwargs: Additional audit parameters
            
        Returns:
            List of security findings
        """
        target = target_path or self.project_path
        findings = []
        
        if audit_type == "vulnerability":
            findings = self.vulnerability_assessor.assess_dependencies(target)
        elif audit_type == "configuration":
            findings = self.config_analyzer.analyze_configurations(target)
        elif audit_type == "code":
            findings = self.code_analyzer.analyze_code_security(
                target,
                excluded_paths=kwargs.get("excluded_paths", [])
            )
        else:
            raise ValueError(f"Unknown audit type: {audit_type}")
        
        logger.info(f"Completed {audit_type} audit: {len(findings)} findings")
        return findings
    
    def add_finding(
        self,
        title: str,
        description: str,
        severity: SeverityLevel,
        category: FindingCategory,
        location: str,
        **kwargs
    ) -> SecurityFinding:
        """Add a security finding to current audit.
        
        Args:
            title: Finding title
            description: Finding description
            severity: Severity level
            category: Finding category
            location: Location of the finding
            **kwargs: Additional finding properties
            
        Returns:
            Created security finding
        """
        if not self.current_audit:
            raise SecurityError("No active audit session")
        
        finding_id = self._generate_finding_id(title, location)
        
        finding = SecurityFinding(
            id=finding_id,
            title=title,
            description=description,
            severity=severity,
            category=category,
            location=location,
            **kwargs
        )
        
        self.current_audit.findings.append(finding)
        return finding
    
    def export_report(
        self,
        format_type: str = "json",
        output_path: Optional[Path] = None
    ) -> Path:
        """Export audit report in specified format.
        
        Args:
            format_type: Export format (json, html, pdf)
            output_path: Output file path
            
        Returns:
            Path to exported report
        """
        if not self.current_audit:
            raise SecurityError("No audit report to export")
        
        if not output_path:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"security_audit_{self.current_audit.audit_id}_{timestamp}.{format_type}"
            output_path = self.output_dir / filename
        
        if format_type == "json":
            self._export_json_report(output_path)
        elif format_type == "html":
            self._export_html_report(output_path)
        elif format_type == "pdf":
            self._export_pdf_report(output_path)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
        
        logger.info(f"Exported audit report to {output_path}")
        return output_path
    
    def _generate_audit_id(self) -> str:
        """Generate unique audit ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        project_hash = hashlib.md5(str(self.project_path).encode()).hexdigest()[:8]
        return f"audit_{timestamp}_{project_hash}"
    
    def _generate_finding_id(self, title: str, location: str) -> str:
        """Generate unique finding ID."""
        content = f"{title}_{location}_{datetime.utcnow().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _generate_audit_summary(self) -> None:
        """Generate audit summary."""
        if not self.current_audit:
            return
        
        findings = self.current_audit.findings
        
        # Count by severity
        severity_counts = {}
        for severity in SeverityLevel:
            severity_counts[severity.value] = len(
                self.current_audit.get_findings_by_severity(severity)
            )
        
        # Count by category
        category_counts = {}
        for category in FindingCategory:
            category_counts[category.value] = len(
                self.current_audit.get_findings_by_category(category)
            )
        
        # Top issues
        critical_findings = self.current_audit.get_critical_findings()
        high_findings = self.current_audit.get_findings_by_severity(SeverityLevel.HIGH)
        
        self.current_audit.summary = {
            "total_findings": len(findings),
            "severity_distribution": severity_counts,
            "category_distribution": category_counts,
            "critical_issues_count": len(critical_findings),
            "high_issues_count": len(high_findings),
            "scan_coverage": {
                "dependencies_scanned": self.config.get("scan_dependencies", False),
                "code_scanned": self.config.get("scan_code", False),
                "configs_analyzed": self.config.get("analyze_configs", False)
            }
        }
    
    def _generate_recommendations(self) -> None:
        """Generate security recommendations based on findings."""
        if not self.current_audit:
            return
        
        recommendations = []
        
        # Critical findings recommendations
        critical_findings = self.current_audit.get_critical_findings()
        if critical_findings:
            recommendations.append(
                f"URGENT: Address {len(critical_findings)} critical security findings immediately"
            )
        
        # Category-specific recommendations
        vuln_findings = self.current_audit.get_findings_by_category(
            FindingCategory.VULNERABILITY
        )
        if vuln_findings:
            recommendations.append(
                f"Update dependencies to resolve {len(vuln_findings)} vulnerability findings"
            )
        
        config_findings = self.current_audit.get_findings_by_category(
            FindingCategory.CONFIGURATION
        )
        if config_findings:
            recommendations.append(
                f"Review and harden {len(config_findings)} configuration issues"
            )
        
        code_findings = self.current_audit.get_findings_by_category(
            FindingCategory.CODE_SECURITY
        )
        if code_findings:
            recommendations.append(
                f"Implement secure coding practices to fix {len(code_findings)} code security issues"
            )
        
        # General recommendations
        if self.current_audit.risk_score and self.current_audit.risk_score > 70:
            recommendations.append(
                "Implement a comprehensive security improvement plan"
            )
        
        recommendations.extend([
            "Establish regular security audits and vulnerability assessments",
            "Implement automated security testing in CI/CD pipeline",
            "Provide security training for development team",
            "Establish incident response procedures"
        ])
        
        self.current_audit.recommendations = recommendations
    
    def _save_audit_report(self) -> None:
        """Save audit report to file."""
        if not self.current_audit:
            return
        
        report_path = self.output_dir / f"audit_{self.current_audit.audit_id}.json"
        
        try:
            report_data = self.current_audit.to_dict()
            self.file_ops.safe_write(
                report_path,
                json.dumps(report_data, indent=2),
                create_parents=True
            )
            logger.info(f"Saved audit report to {report_path}")
        except Exception as e:
            logger.error(f"Failed to save audit report: {e}")
    
    def _export_json_report(self, output_path: Path) -> None:
        """Export report as JSON."""
        report_data = self.current_audit.to_dict()
        self.file_ops.safe_write(
            output_path,
            json.dumps(report_data, indent=2),
            create_parents=True
        )
    
    def _export_html_report(self, output_path: Path) -> None:
        """Export report as HTML."""
        # HTML template for security report
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Security Audit Report - {project_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f4f4f4; padding: 20px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; }}
        .finding {{ 
            border: 1px solid #ddd; 
            margin: 10px 0; 
            padding: 15px; 
            border-radius: 5px;
        }}
        .critical {{ border-left: 5px solid #d32f2f; }}
        .high {{ border-left: 5px solid #f57c00; }}
        .medium {{ border-left: 5px solid #fbc02d; }}
        .low {{ border-left: 5px solid #388e3c; }}
        .info {{ border-left: 5px solid #1976d2; }}
        .severity {{ 
            display: inline-block; 
            padding: 2px 8px; 
            border-radius: 3px; 
            color: white; 
            font-size: 12px;
        }}
        .recommendations {{ background: #e8f5e8; padding: 15px; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Security Audit Report</h1>
        <p><strong>Project:</strong> {project_name}</p>
        <p><strong>Audit ID:</strong> {audit_id}</p>
        <p><strong>Date:</strong> {audit_date}</p>
        <p><strong>Auditor:</strong> {auditor}</p>
        <p><strong>Risk Score:</strong> {risk_score:.1f}/100</p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total Findings:</strong> {total_findings}</p>
        <p><strong>Critical:</strong> {critical_count} | 
           <strong>High:</strong> {high_count} | 
           <strong>Medium:</strong> {medium_count} | 
           <strong>Low:</strong> {low_count}</p>
    </div>
    
    <div class="recommendations">
        <h2>Recommendations</h2>
        <ul>
            {recommendations_html}
        </ul>
    </div>
    
    <div class="findings">
        <h2>Detailed Findings</h2>
        {findings_html}
    </div>
</body>
</html>
        """
        
        # Generate findings HTML
        findings_html = ""
        for finding in self.current_audit.findings:
            severity_class = finding.severity.value
            findings_html += f"""
        <div class="finding {severity_class}">
            <h3>{finding.title} 
                <span class="severity" style="background-color: {self._get_severity_color(finding.severity)}">
                    {finding.severity.value.upper()}
                </span>
            </h3>
            <p><strong>Location:</strong> {finding.location}</p>
            <p><strong>Category:</strong> {finding.category.value}</p>
            <p>{finding.description}</p>
            {f'<p><strong>Remediation:</strong> {finding.remediation}</p>' if finding.remediation else ''}
            {f'<p><strong>CVE:</strong> {finding.cve_id}</p>' if finding.cve_id else ''}
        </div>
            """
        
        # Generate recommendations HTML
        recommendations_html = "".join(
            f"<li>{rec}</li>" for rec in self.current_audit.recommendations
        )
        
        # Fill template
        html_content = html_template.format(
            project_name=self.current_audit.project_name,
            audit_id=self.current_audit.audit_id,
            audit_date=self.current_audit.audit_date.strftime("%Y-%m-%d %H:%M:%S UTC"),
            auditor=self.current_audit.auditor,
            risk_score=self.current_audit.risk_score or 0,
            total_findings=len(self.current_audit.findings),
            critical_count=len(self.current_audit.get_findings_by_severity(SeverityLevel.CRITICAL)),
            high_count=len(self.current_audit.get_findings_by_severity(SeverityLevel.HIGH)),
            medium_count=len(self.current_audit.get_findings_by_severity(SeverityLevel.MEDIUM)),
            low_count=len(self.current_audit.get_findings_by_severity(SeverityLevel.LOW)),
            recommendations_html=recommendations_html,
            findings_html=findings_html
        )
        
        self.file_ops.safe_write(output_path, html_content, create_parents=True)
    
    def _export_pdf_report(self, output_path: Path) -> None:
        """Export report as PDF."""
        # For PDF export, we'd use a library like reportlab or weasyprint
        # For now, create a text-based report
        
        text_content = f"""
SECURITY AUDIT REPORT
{'=' * 50}

Project: {self.current_audit.project_name}
Audit ID: {self.current_audit.audit_id}
Date: {self.current_audit.audit_date.strftime('%Y-%m-%d %H:%M:%S UTC')}
Auditor: {self.current_audit.auditor}
Risk Score: {self.current_audit.risk_score:.1f}/100

SUMMARY
{'-' * 20}
Total Findings: {len(self.current_audit.findings)}
Critical: {len(self.current_audit.get_findings_by_severity(SeverityLevel.CRITICAL))}
High: {len(self.current_audit.get_findings_by_severity(SeverityLevel.HIGH))}
Medium: {len(self.current_audit.get_findings_by_severity(SeverityLevel.MEDIUM))}
Low: {len(self.current_audit.get_findings_by_severity(SeverityLevel.LOW))}

RECOMMENDATIONS
{'-' * 20}
"""
        
        for i, rec in enumerate(self.current_audit.recommendations, 1):
            text_content += f"{i}. {rec}\n"
        
        text_content += f"\n\nDETAILED FINDINGS\n{'-' * 20}\n"
        
        for finding in self.current_audit.findings:
            text_content += f"""

[{finding.severity.value.upper()}] {finding.title}
Location: {finding.location}
Category: {finding.category.value}
Description: {finding.description}
"""
            if finding.remediation:
                text_content += f"Remediation: {finding.remediation}\n"
            if finding.cve_id:
                text_content += f"CVE: {finding.cve_id}\n"
            
            text_content += "-" * 40 + "\n"
        
        self.file_ops.safe_write(output_path, text_content, create_parents=True)
    
    def _get_severity_color(self, severity: SeverityLevel) -> str:
        """Get color for severity level."""
        colors = {
            SeverityLevel.CRITICAL: "#d32f2f",
            SeverityLevel.HIGH: "#f57c00",
            SeverityLevel.MEDIUM: "#fbc02d",
            SeverityLevel.LOW: "#388e3c",
            SeverityLevel.INFO: "#1976d2"
        }
        return colors.get(severity, "#666666")


def create_security_audit(
    project_path: Union[str, Path],
    project_name: str,
    config_path: Optional[Path] = None,
    output_dir: Optional[Path] = None
) -> AuditReport:
    """Convenience function to create a complete security audit.
    
    Args:
        project_path: Path to project root
        project_name: Name of the project
        config_path: Path to audit configuration
        output_dir: Directory for audit outputs
        
    Returns:
        Complete audit report
    """
    framework = SecurityAuditFramework(
        project_path=Path(project_path),
        config_path=config_path,
        output_dir=output_dir
    )
    
    return framework.run_comprehensive_audit(project_name)