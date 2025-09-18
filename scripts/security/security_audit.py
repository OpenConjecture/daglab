#!/usr/bin/env python3
"""Security audit script for DagLab projects.

Provides command-line interface for running comprehensive security audits.

Usage:
    python security_audit.py [options]
    
Options:
    --project-path PATH     Path to project root (default: current directory)
    --config-path PATH      Path to audit configuration file
    --output-dir PATH       Directory for audit outputs
    --format FORMAT         Report format (json, html, pdf)
    --audit-type TYPE       Type of audit (comprehensive, vulnerability, config, code)
    --severity LEVEL        Minimum severity level (critical, high, medium, low, info)
    --verbose               Enable verbose logging
    --dry-run              Show what would be audited without running
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from daglab.security.audit.framework import SecurityAuditFramework, create_security_audit
from daglab.security.hardening.manager import SecurityHardeningManager
from daglab.runtime.logging import setup_logging


def main():
    """Main security audit script."""
    parser = argparse.ArgumentParser(
        description='Run comprehensive security audit for DagLab projects',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--project-path',
        type=Path,
        default=Path.cwd(),
        help='Path to project root (default: current directory)'
    )
    
    parser.add_argument(
        '--config-path',
        type=Path,
        help='Path to audit configuration file'
    )
    
    parser.add_argument(
        '--output-dir',
        type=Path,
        help='Directory for audit outputs (default: PROJECT_PATH/security_audit)'
    )
    
    parser.add_argument(
        '--format',
        choices=['json', 'html', 'pdf'],
        default='html',
        help='Report format (default: html)'
    )
    
    parser.add_argument(
        '--audit-type',
        choices=['comprehensive', 'vulnerability', 'configuration', 'code', 'risk'],
        default='comprehensive',
        help='Type of audit to run (default: comprehensive)'
    )
    
    parser.add_argument(
        '--severity',
        choices=['critical', 'high', 'medium', 'low', 'info'],
        default='medium',
        help='Minimum severity level to report (default: medium)'
    )
    
    parser.add_argument(
        '--apply-hardening',
        action='store_true',
        help='Apply security hardening after audit'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be audited without running'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level)
    
    logger = logging.getLogger(__name__)
    
    try:
        # Validate project path
        if not args.project_path.exists():
            logger.error(f"Project path does not exist: {args.project_path}")
            return 1
        
        if not args.project_path.is_dir():
            logger.error(f"Project path is not a directory: {args.project_path}")
            return 1
        
        project_name = args.project_path.name
        
        if args.dry_run:
            logger.info("DRY RUN MODE - No actual audit will be performed")
            logger.info(f"Would audit project: {project_name} at {args.project_path}")
            logger.info(f"Audit type: {args.audit_type}")
            logger.info(f"Output format: {args.format}")
            logger.info(f"Minimum severity: {args.severity}")
            if args.apply_hardening:
                logger.info("Would apply security hardening after audit")
            return 0
        
        logger.info(f"Starting security audit for {project_name}")
        logger.info(f"Project path: {args.project_path}")
        logger.info(f"Audit type: {args.audit_type}")
        
        # Initialize audit framework
        audit_framework = SecurityAuditFramework(
            project_path=args.project_path,
            config_path=args.config_path,
            output_dir=args.output_dir
        )
        
        # Run audit based on type
        if args.audit_type == 'comprehensive':
            logger.info("Running comprehensive security audit")
            audit_report = audit_framework.run_comprehensive_audit(project_name)
        else:
            logger.info(f"Running targeted {args.audit_type} audit")
            findings = audit_framework.run_targeted_audit(args.audit_type)
            
            # Create a minimal report for targeted audits
            audit_id = audit_framework.start_audit(project_name)
            audit_framework.current_audit.findings = findings
            audit_report = audit_framework.current_audit
        
        # Filter findings by severity
        severity_levels = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1, 'info': 0}
        min_severity_level = severity_levels[args.severity]
        
        filtered_findings = [
            f for f in audit_report.findings 
            if severity_levels.get(f.severity.value, 0) >= min_severity_level
        ]
        
        logger.info(f"Audit completed: {len(filtered_findings)} findings at {args.severity}+ severity")
        
        # Export report
        report_path = audit_framework.export_report(args.format)
        logger.info(f"Report exported to: {report_path}")
        
        # Print summary
        print("\n" + "="*60)
        print(f"SECURITY AUDIT SUMMARY - {project_name}")
        print("="*60)
        print(f"Total findings: {len(audit_report.findings)}")
        print(f"Findings at {args.severity}+ severity: {len(filtered_findings)}")
        
        if audit_report.risk_score is not None:
            print(f"Overall risk score: {audit_report.risk_score:.1f}/100")
        
        # Show severity breakdown
        severity_counts = {}
        for finding in filtered_findings:
            severity = finding.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        if severity_counts:
            print("\nFindings by severity:")
            for severity in ['critical', 'high', 'medium', 'low', 'info']:
                if severity in severity_counts:
                    print(f"  {severity.title()}: {severity_counts[severity]}")
        
        # Show top recommendations
        if audit_report.recommendations:
            print("\nTop recommendations:")
            for i, rec in enumerate(audit_report.recommendations[:3], 1):
                print(f"  {i}. {rec}")
        
        print(f"\nDetailed report: {report_path}")
        
        # Apply hardening if requested
        if args.apply_hardening:
            logger.info("Applying security hardening")
            hardening_manager = SecurityHardeningManager(args.project_path)
            hardening_results = hardening_manager.apply_comprehensive_hardening()
            
            successful_hardening = sum(1 for r in hardening_results if r.success)
            print(f"\nSecurity hardening: {successful_hardening}/{len(hardening_results)} successful")
        
        # Return exit code based on findings
        critical_count = severity_counts.get('critical', 0)
        high_count = severity_counts.get('high', 0)
        
        if critical_count > 0:
            logger.warning(f"Found {critical_count} critical security issues")
            return 2  # Critical issues found
        elif high_count > 0:
            logger.warning(f"Found {high_count} high severity security issues")
            return 1  # High severity issues found
        else:
            logger.info("No critical or high severity security issues found")
            return 0  # Success
        
    except KeyboardInterrupt:
        logger.info("Audit interrupted by user")
        return 130
    
    except Exception as e:
        logger.error(f"Security audit failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())