"""Risk assessment and threat modeling module for DagLab security.

Provides comprehensive risk assessment including:
- Threat modeling and attack surface analysis
- Risk scoring and prioritization
- Business impact assessment
- Security control effectiveness evaluation
- Compliance risk assessment
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..helpers.security import SecurityManager
from ..runtime.errors import SecurityError
from .framework import SecurityFinding, SeverityLevel, FindingCategory

logger = logging.getLogger(__name__)


class ThreatCategory(Enum):
    """Categories of security threats."""
    CONFIDENTIALITY = "confidentiality"
    INTEGRITY = "integrity"
    AVAILABILITY = "availability"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NON_REPUDIATION = "non_repudiation"


class RiskLevel(Enum):
    """Risk levels for threat assessment."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEGLIGIBLE = "negligible"


@dataclass
class ThreatAgent:
    """Represents a threat agent/actor."""
    name: str
    description: str
    skill_level: str  # low, medium, high
    motivation: str   # low, medium, high
    opportunity: str  # low, medium, high
    resources: str    # low, medium, high
    
    def calculate_threat_level(self) -> float:
        """Calculate overall threat level (0-10 scale)."""
        levels = {'low': 1, 'medium': 5, 'high': 9}
        
        skill = levels.get(self.skill_level, 1)
        motivation = levels.get(self.motivation, 1)
        opportunity = levels.get(self.opportunity, 1)
        resources = levels.get(self.resources, 1)
        
        # Weighted average
        return (skill * 0.3 + motivation * 0.3 + opportunity * 0.2 + resources * 0.2)


@dataclass
class Asset:
    """Represents a system asset."""
    name: str
    description: str
    asset_type: str  # data, system, service, etc.
    confidentiality_value: str  # low, medium, high
    integrity_value: str        # low, medium, high
    availability_value: str     # low, medium, high
    
    def calculate_asset_value(self) -> float:
        """Calculate overall asset value (0-10 scale)."""
        levels = {'low': 1, 'medium': 5, 'high': 9}
        
        conf = levels.get(self.confidentiality_value, 1)
        integrity = levels.get(self.integrity_value, 1)
        avail = levels.get(self.availability_value, 1)
        
        return max(conf, integrity, avail)  # Highest value determines overall


@dataclass
class Vulnerability:
    """Represents a vulnerability in the system."""
    name: str
    description: str
    cve_id: Optional[str] = None
    cvss_score: Optional[float] = None
    exploitability: str = "medium"  # low, medium, high
    impact: str = "medium"          # low, medium, high
    
    def calculate_vulnerability_score(self) -> float:
        """Calculate vulnerability score (0-10 scale)."""
        if self.cvss_score:
            return self.cvss_score
        
        levels = {'low': 2, 'medium': 5, 'high': 8}
        exploit = levels.get(self.exploitability, 5)
        impact = levels.get(self.impact, 5)
        
        return (exploit + impact) / 2


@dataclass
class Threat:
    """Represents a specific threat."""
    name: str
    description: str
    category: ThreatCategory
    agent: ThreatAgent
    vulnerabilities: List[Vulnerability]
    affected_assets: List[Asset]
    likelihood: Optional[float] = None
    impact: Optional[float] = None
    risk_score: Optional[float] = None
    
    def calculate_likelihood(self) -> float:
        """Calculate threat likelihood based on agent and vulnerabilities."""
        if self.likelihood is not None:
            return self.likelihood
        
        agent_threat_level = self.agent.calculate_threat_level()
        
        if self.vulnerabilities:
            avg_vuln_score = sum(v.calculate_vulnerability_score() for v in self.vulnerabilities) / len(self.vulnerabilities)
            self.likelihood = (agent_threat_level + avg_vuln_score) / 2
        else:
            self.likelihood = agent_threat_level / 2  # Lower if no known vulnerabilities
        
        return min(10.0, self.likelihood)  # Cap at 10
    
    def calculate_impact(self) -> float:
        """Calculate threat impact based on affected assets."""
        if self.impact is not None:
            return self.impact
        
        if self.affected_assets:
            max_asset_value = max(asset.calculate_asset_value() for asset in self.affected_assets)
            self.impact = max_asset_value
        else:
            self.impact = 5.0  # Default medium impact
        
        return self.impact
    
    def calculate_risk_score(self) -> float:
        """Calculate overall risk score (likelihood × impact)."""
        likelihood = self.calculate_likelihood()
        impact = self.calculate_impact()
        
        self.risk_score = likelihood * impact
        return self.risk_score
    
    def get_risk_level(self) -> RiskLevel:
        """Get risk level based on risk score."""
        score = self.calculate_risk_score()
        
        if score >= 80:
            return RiskLevel.CRITICAL
        elif score >= 60:
            return RiskLevel.HIGH
        elif score >= 30:
            return RiskLevel.MEDIUM
        elif score >= 10:
            return RiskLevel.LOW
        else:
            return RiskLevel.NEGLIGIBLE


@dataclass
class ThreatModel:
    """Complete threat model for a system."""
    name: str
    description: str
    scope: str
    assets: List[Asset] = field(default_factory=list)
    threat_agents: List[ThreatAgent] = field(default_factory=list)
    threats: List[Threat] = field(default_factory=list)
    created_date: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def get_high_risk_threats(self) -> List[Threat]:
        """Get threats with high or critical risk levels."""
        return [t for t in self.threats if t.get_risk_level() in [RiskLevel.HIGH, RiskLevel.CRITICAL]]
    
    def calculate_overall_risk_score(self) -> float:
        """Calculate overall system risk score."""
        if not self.threats:
            return 0.0
        
        # Use weighted average based on threat impact
        total_weighted_score = sum(t.calculate_risk_score() * t.calculate_impact() for t in self.threats)
        total_weight = sum(t.calculate_impact() for t in self.threats)
        
        if total_weight > 0:
            return total_weighted_score / total_weight
        else:
            return 0.0


class RiskAssessor:
    """Risk assessment and threat modeling coordinator."""
    
    def __init__(self):
        """Initialize risk assessor."""
        self.security_manager = SecurityManager()
        
        # Default threat agents
        self.default_threat_agents = self._create_default_threat_agents()
        
        # Common asset types
        self.common_assets = self._create_common_assets()
    
    def assess_risks(self, project_path: Path, existing_findings: List[SecurityFinding]) -> List[SecurityFinding]:
        """Assess risks based on project analysis and existing findings.
        
        Args:
            project_path: Path to project root
            existing_findings: Security findings from other analyzers
            
        Returns:
            List of risk assessment findings
        """
        logger.info(f"Starting risk assessment for {project_path}")
        
        findings = []
        
        try:
            # Create threat model
            threat_model = self._create_threat_model(project_path, existing_findings)
            
            # Generate risk findings
            risk_findings = self._generate_risk_findings(threat_model)
            findings.extend(risk_findings)
            
            # Save threat model
            self._save_threat_model(project_path, threat_model)
            
            # Generate compliance risk findings
            compliance_findings = self._assess_compliance_risks(project_path, existing_findings)
            findings.extend(compliance_findings)
            
        except Exception as e:
            logger.error(f"Risk assessment failed: {e}")
            raise SecurityError(f"Risk assessment failed: {e}", cause=e)
        
        logger.info(f"Risk assessment completed: {len(findings)} findings")
        return findings
    
    def _create_threat_model(self, project_path: Path, findings: List[SecurityFinding]) -> ThreatModel:
        """Create threat model based on project and findings."""
        threat_model = ThreatModel(
            name=f"Threat Model - {project_path.name}",
            description=f"Threat model for DagLab project at {project_path}",
            scope="DagLab application and supporting infrastructure"
        )
        
        # Add common assets
        threat_model.assets = self.common_assets.copy()
        
        # Add threat agents
        threat_model.threat_agents = self.default_threat_agents.copy()
        
        # Create threats based on findings
        threats = self._create_threats_from_findings(findings, threat_model)
        threat_model.threats = threats
        
        return threat_model
    
    def _create_threats_from_findings(self, findings: List[SecurityFinding], threat_model: ThreatModel) -> List[Threat]:
        """Create threat objects from security findings."""
        threats = []
        
        # Group findings by category
        finding_groups = {}
        for finding in findings:
            category = finding.category
            if category not in finding_groups:
                finding_groups[category] = []
            finding_groups[category].append(finding)
        
        # Create threats for each category
        for category, category_findings in finding_groups.items():
            if category == FindingCategory.VULNERABILITY:
                threat = self._create_vulnerability_threat(category_findings, threat_model)
                threats.append(threat)
            elif category == FindingCategory.AUTHENTICATION:
                threat = self._create_auth_threat(category_findings, threat_model)
                threats.append(threat)
            elif category == FindingCategory.DATA_PROTECTION:
                threat = self._create_data_threat(category_findings, threat_model)
                threats.append(threat)
            elif category == FindingCategory.CONFIGURATION:
                threat = self._create_config_threat(category_findings, threat_model)
                threats.append(threat)
        
        return threats
    
    def _create_vulnerability_threat(self, findings: List[SecurityFinding], threat_model: ThreatModel) -> Threat:
        """Create threat from vulnerability findings."""
        vulnerabilities = []
        
        for finding in findings:
            vuln = Vulnerability(
                name=finding.title,
                description=finding.description,
                cve_id=finding.cve_id,
                cvss_score=finding.cvss_score,
                exploitability="high" if finding.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH] else "medium",
                impact="high" if finding.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH] else "medium"
            )
            vulnerabilities.append(vuln)
        
        # Select appropriate threat agent (external attacker for vulnerabilities)
        external_attacker = next((a for a in threat_model.threat_agents if "external" in a.name.lower()), threat_model.threat_agents[0])
        
        threat = Threat(
            name="Exploitation of Known Vulnerabilities",
            description="Threat of attackers exploiting known vulnerabilities in dependencies or code",
            category=ThreatCategory.CONFIDENTIALITY,
            agent=external_attacker,
            vulnerabilities=vulnerabilities,
            affected_assets=[a for a in threat_model.assets if a.asset_type in ["application", "data"]]
        )
        
        return threat
    
    def _create_auth_threat(self, findings: List[SecurityFinding], threat_model: ThreatModel) -> Threat:
        """Create threat from authentication findings."""
        # Create vulnerability from auth findings
        auth_vulns = []
        for finding in findings:
            vuln = Vulnerability(
                name=finding.title,
                description=finding.description,
                exploitability="medium",
                impact="high"
            )
            auth_vulns.append(vuln)
        
        # Select appropriate threat agent
        internal_attacker = next((a for a in threat_model.threat_agents if "internal" in a.name.lower()), threat_model.threat_agents[0])
        
        threat = Threat(
            name="Authentication Bypass or Compromise",
            description="Threat of unauthorized access due to weak or missing authentication controls",
            category=ThreatCategory.AUTHENTICATION,
            agent=internal_attacker,
            vulnerabilities=auth_vulns,
            affected_assets=[a for a in threat_model.assets if a.asset_type in ["application", "data", "user_accounts"]]
        )
        
        return threat
    
    def _create_data_threat(self, findings: List[SecurityFinding], threat_model: ThreatModel) -> Threat:
        """Create threat from data protection findings."""
        data_vulns = []
        for finding in findings:
            vuln = Vulnerability(
                name=finding.title,
                description=finding.description,
                exploitability="medium",
                impact="high"
            )
            data_vulns.append(vuln)
        
        external_attacker = next((a for a in threat_model.threat_agents if "external" in a.name.lower()), threat_model.threat_agents[0])
        
        threat = Threat(
            name="Data Exposure or Theft",
            description="Threat of sensitive data being exposed or stolen due to inadequate protection",
            category=ThreatCategory.CONFIDENTIALITY,
            agent=external_attacker,
            vulnerabilities=data_vulns,
            affected_assets=[a for a in threat_model.assets if a.asset_type == "data"]
        )
        
        return threat
    
    def _create_config_threat(self, findings: List[SecurityFinding], threat_model: ThreatModel) -> Threat:
        """Create threat from configuration findings."""
        config_vulns = []
        for finding in findings:
            vuln = Vulnerability(
                name=finding.title,
                description=finding.description,
                exploitability="low",
                impact="medium"
            )
            config_vulns.append(vuln)
        
        internal_attacker = next((a for a in threat_model.threat_agents if "internal" in a.name.lower()), threat_model.threat_agents[0])
        
        threat = Threat(
            name="System Compromise via Misconfiguration",
            description="Threat of system compromise due to insecure configurations",
            category=ThreatCategory.INTEGRITY,
            agent=internal_attacker,
            vulnerabilities=config_vulns,
            affected_assets=[a for a in threat_model.assets if a.asset_type in ["application", "infrastructure"]]
        )
        
        return threat
    
    def _generate_risk_findings(self, threat_model: ThreatModel) -> List[SecurityFinding]:
        """Generate security findings from threat model."""
        findings = []
        
        # Overall risk assessment
        overall_risk = threat_model.calculate_overall_risk_score()
        
        findings.append(SecurityFinding(
            id="overall_risk_assessment",
            title="Overall Security Risk Assessment",
            description=f"Overall security risk score: {overall_risk:.1f}/100",
            severity=self._map_risk_to_severity(overall_risk),
            category=FindingCategory.COMPLIANCE,
            location="System-wide",
            evidence={
                "risk_score": overall_risk,
                "threat_count": len(threat_model.threats),
                "high_risk_threats": len(threat_model.get_high_risk_threats())
            },
            remediation="Address high-priority threats and implement comprehensive security controls"
        ))
        
        # Individual threat findings
        for threat in threat_model.threats:
            threat_risk = threat.calculate_risk_score()
            risk_level = threat.get_risk_level()
            
            if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                findings.append(SecurityFinding(
                    id=f"threat_{threat.name.lower().replace(' ', '_')}",
                    title=f"High Risk Threat: {threat.name}",
                    description=f"{threat.description}\n\nRisk Level: {risk_level.value}\nRisk Score: {threat_risk:.1f}/100",
                    severity=SeverityLevel.HIGH if risk_level == RiskLevel.HIGH else SeverityLevel.CRITICAL,
                    category=FindingCategory.COMPLIANCE,
                    location="System-wide",
                    evidence={
                        "threat_category": threat.category.value,
                        "likelihood": threat.calculate_likelihood(),
                        "impact": threat.calculate_impact(),
                        "risk_score": threat_risk,
                        "affected_assets": [a.name for a in threat.affected_assets],
                        "vulnerabilities": [v.name for v in threat.vulnerabilities]
                    },
                    remediation="Implement threat-specific mitigation controls and monitor for indicators of compromise"
                ))
        
        return findings
    
    def _assess_compliance_risks(self, project_path: Path, findings: List[SecurityFinding]) -> List[SecurityFinding]:
        """Assess compliance-related risks."""
        compliance_findings = []
        
        # Check for GDPR compliance risks
        gdpr_risks = self._assess_gdpr_risks(findings)
        compliance_findings.extend(gdpr_risks)
        
        # Check for SOX compliance risks
        sox_risks = self._assess_sox_risks(findings)
        compliance_findings.extend(sox_risks)
        
        # Check for PCI DSS risks (if applicable)
        pci_risks = self._assess_pci_risks(findings)
        compliance_findings.extend(pci_risks)
        
        return compliance_findings
    
    def _assess_gdpr_risks(self, findings: List[SecurityFinding]) -> List[SecurityFinding]:
        """Assess GDPR compliance risks."""
        gdpr_findings = []
        
        # Check for data protection issues
        data_protection_findings = [f for f in findings if f.category == FindingCategory.DATA_PROTECTION]
        
        if data_protection_findings:
            gdpr_findings.append(SecurityFinding(
                id="gdpr_data_protection_risk",
                title="GDPR Data Protection Risk",
                description=f"Found {len(data_protection_findings)} data protection issues that may violate GDPR requirements",
                severity=SeverityLevel.HIGH,
                category=FindingCategory.COMPLIANCE,
                location="System-wide",
                evidence={
                    "regulation": "GDPR",
                    "data_protection_issues": len(data_protection_findings),
                    "potential_violations": [f.title for f in data_protection_findings[:5]]  # First 5
                },
                remediation="Implement data protection controls and ensure GDPR compliance"
            ))
        
        return gdpr_findings
    
    def _assess_sox_risks(self, findings: List[SecurityFinding]) -> List[SecurityFinding]:
        """Assess Sarbanes-Oxley compliance risks."""
        sox_findings = []
        
        # Check for configuration and access control issues
        config_findings = [f for f in findings if f.category == FindingCategory.CONFIGURATION]
        auth_findings = [f for f in findings if f.category == FindingCategory.AUTHENTICATION]
        
        total_control_issues = len(config_findings) + len(auth_findings)
        
        if total_control_issues > 5:  # Threshold for SOX concern
            sox_findings.append(SecurityFinding(
                id="sox_internal_controls_risk",
                title="SOX Internal Controls Risk",
                description=f"Found {total_control_issues} configuration and access control issues that may impact SOX compliance",
                severity=SeverityLevel.MEDIUM,
                category=FindingCategory.COMPLIANCE,
                location="System-wide",
                evidence={
                    "regulation": "SOX",
                    "control_issues": total_control_issues,
                    "configuration_issues": len(config_findings),
                    "authentication_issues": len(auth_findings)
                },
                remediation="Strengthen internal controls and implement proper access management"
            ))
        
        return sox_findings
    
    def _assess_pci_risks(self, findings: List[SecurityFinding]) -> List[SecurityFinding]:
        """Assess PCI DSS compliance risks."""
        pci_findings = []
        
        # Check for network security and encryption issues
        network_findings = [f for f in findings if f.category == FindingCategory.NETWORK_SECURITY]
        data_findings = [f for f in findings if f.category == FindingCategory.DATA_PROTECTION]
        
        if network_findings or data_findings:
            pci_findings.append(SecurityFinding(
                id="pci_dss_risk",
                title="PCI DSS Compliance Risk",
                description=f"Found security issues that may impact PCI DSS compliance if payment data is processed",
                severity=SeverityLevel.MEDIUM,
                category=FindingCategory.COMPLIANCE,
                location="System-wide",
                evidence={
                    "regulation": "PCI DSS",
                    "network_security_issues": len(network_findings),
                    "data_protection_issues": len(data_findings)
                },
                remediation="Ensure PCI DSS compliance if processing payment card data"
            ))
        
        return pci_findings
    
    def _save_threat_model(self, project_path: Path, threat_model: ThreatModel) -> None:
        """Save threat model to file."""
        try:
            output_dir = project_path / "security_audit"
            output_dir.mkdir(exist_ok=True)
            
            threat_model_path = output_dir / "threat_model.json"
            
            # Convert to JSON-serializable format
            threat_model_data = {
                "name": threat_model.name,
                "description": threat_model.description,
                "scope": threat_model.scope,
                "created_date": threat_model.created_date.isoformat(),
                "last_updated": threat_model.last_updated.isoformat(),
                "overall_risk_score": threat_model.calculate_overall_risk_score(),
                "assets": [
                    {
                        "name": asset.name,
                        "description": asset.description,
                        "type": asset.asset_type,
                        "confidentiality": asset.confidentiality_value,
                        "integrity": asset.integrity_value,
                        "availability": asset.availability_value,
                        "value": asset.calculate_asset_value()
                    }
                    for asset in threat_model.assets
                ],
                "threat_agents": [
                    {
                        "name": agent.name,
                        "description": agent.description,
                        "skill_level": agent.skill_level,
                        "motivation": agent.motivation,
                        "opportunity": agent.opportunity,
                        "resources": agent.resources,
                        "threat_level": agent.calculate_threat_level()
                    }
                    for agent in threat_model.threat_agents
                ],
                "threats": [
                    {
                        "name": threat.name,
                        "description": threat.description,
                        "category": threat.category.value,
                        "agent": threat.agent.name,
                        "likelihood": threat.calculate_likelihood(),
                        "impact": threat.calculate_impact(),
                        "risk_score": threat.calculate_risk_score(),
                        "risk_level": threat.get_risk_level().value,
                        "vulnerabilities": [
                            {
                                "name": vuln.name,
                                "description": vuln.description,
                                "cve_id": vuln.cve_id,
                                "cvss_score": vuln.cvss_score,
                                "score": vuln.calculate_vulnerability_score()
                            }
                            for vuln in threat.vulnerabilities
                        ],
                        "affected_assets": [asset.name for asset in threat.affected_assets]
                    }
                    for threat in threat_model.threats
                ]
            }
            
            with open(threat_model_path, 'w') as f:
                json.dump(threat_model_data, f, indent=2)
            
            logger.info(f"Saved threat model to {threat_model_path}")
            
        except Exception as e:
            logger.error(f"Failed to save threat model: {e}")
    
    def _map_risk_to_severity(self, risk_score: float) -> SeverityLevel:
        """Map risk score to severity level."""
        if risk_score >= 80:
            return SeverityLevel.CRITICAL
        elif risk_score >= 60:
            return SeverityLevel.HIGH
        elif risk_score >= 30:
            return SeverityLevel.MEDIUM
        elif risk_score >= 10:
            return SeverityLevel.LOW
        else:
            return SeverityLevel.INFO
    
    def _create_default_threat_agents(self) -> List[ThreatAgent]:
        """Create default threat agents for risk assessment."""
        return [
            ThreatAgent(
                name="External Attacker",
                description="External malicious actor with internet access",
                skill_level="medium",
                motivation="high",
                opportunity="medium",
                resources="medium"
            ),
            ThreatAgent(
                name="Internal Attacker",
                description="Malicious insider with system access",
                skill_level="medium",
                motivation="medium",
                opportunity="high",
                resources="medium"
            ),
            ThreatAgent(
                name="Script Kiddie",
                description="Low-skill attacker using automated tools",
                skill_level="low",
                motivation="medium",
                opportunity="medium",
                resources="low"
            ),
            ThreatAgent(
                name="Advanced Persistent Threat",
                description="Sophisticated, well-resourced attacker",
                skill_level="high",
                motivation="high",
                opportunity="low",
                resources="high"
            ),
            ThreatAgent(
                name="Unintentional Insider",
                description="Employee making security mistakes",
                skill_level="low",
                motivation="low",
                opportunity="high",
                resources="low"
            )
        ]
    
    def _create_common_assets(self) -> List[Asset]:
        """Create common assets for DagLab applications."""
        return [
            Asset(
                name="DagLab Application",
                description="Main DagLab application and web interface",
                asset_type="application",
                confidentiality_value="medium",
                integrity_value="high",
                availability_value="high"
            ),
            Asset(
                name="User Data",
                description="User account information and personal data",
                asset_type="data",
                confidentiality_value="high",
                integrity_value="high",
                availability_value="medium"
            ),
            Asset(
                name="Configuration Data",
                description="Application configuration and settings",
                asset_type="data",
                confidentiality_value="medium",
                integrity_value="high",
                availability_value="high"
            ),
            Asset(
                name="Database",
                description="Backend database system",
                asset_type="infrastructure",
                confidentiality_value="high",
                integrity_value="high",
                availability_value="high"
            ),
            Asset(
                name="API Endpoints",
                description="REST API and GraphQL endpoints",
                asset_type="service",
                confidentiality_value="medium",
                integrity_value="high",
                availability_value="high"
            ),
            Asset(
                name="User Accounts",
                description="User authentication and authorization system",
                asset_type="user_accounts",
                confidentiality_value="high",
                integrity_value="high",
                availability_value="medium"
            )
        ]