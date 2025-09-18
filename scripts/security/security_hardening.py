#!/usr/bin/env python3
"""Security hardening script for DagLab projects.

Provides command-line interface for applying security hardening measures.

Usage:
    python security_hardening.py [options]
    
Options:
    --project-path PATH     Path to project root (default: current directory)
    --component COMPONENT   Specific component to harden (auth, input, config, network)
    --dry-run              Show what would be hardened without applying changes
    --verbose               Enable verbose logging
    --force                Force hardening even with warnings
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from daglab.security.hardening.manager import SecurityHardeningManager
from daglab.runtime.logging import setup_logging


def main():
    """Main security hardening script."""
    parser = argparse.ArgumentParser(
        description='Apply security hardening to DagLab projects',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--project-path',
        type=Path,
        default=Path.cwd(),
        help='Path to project root (default: current directory)'
    )
    
    parser.add_argument(
        '--component',
        choices=['auth', 'input', 'config', 'network', 'all'],
        default='all',
        help='Specific component to harden (default: all)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be hardened without applying changes'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force hardening even with warnings'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show current hardening status'
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
        
        # Initialize hardening manager
        hardening_manager = SecurityHardeningManager(args.project_path)
        
        # Show status if requested
        if args.status:
            status = hardening_manager.get_hardening_status()
            print("\n" + "="*50)
            print("SECURITY HARDENING STATUS")
            print("="*50)
            print(f"Status: {status['status']}")
            print(f"Message: {status['message']}")
            if status.get('total_operations'):
                print(f"Operations: {status['successful_operations']}/{status['total_operations']} successful")
                print(f"Success rate: {status['success_rate']:.1f}%")
            if status.get('last_updated'):
                print(f"Last updated: {status['last_updated']}")
            return 0
        
        if args.dry_run:
            logger.info("DRY RUN MODE - No actual hardening will be applied")
            logger.info(f"Would harden project: {args.project_path.name} at {args.project_path}")
            if args.component == 'all':
                logger.info("Would apply comprehensive hardening to all components")
            else:
                logger.info(f"Would apply hardening to {args.component} component")
            return 0
        
        project_name = args.project_path.name
        logger.info(f"Starting security hardening for {project_name}")
        logger.info(f"Project path: {args.project_path}")
        logger.info(f"Component: {args.component}")
        
        # Apply hardening
        if args.component == 'all':
            logger.info("Applying comprehensive security hardening")
            results = hardening_manager.apply_comprehensive_hardening()
        else:
            logger.info(f"Applying {args.component} hardening")
            results = hardening_manager.apply_targeted_hardening(args.component)
        
        # Analyze results
        successful_count = sum(1 for r in results if r.success)
        failed_count = len(results) - successful_count
        
        logger.info(f"Hardening completed: {successful_count}/{len(results)} successful")
        
        # Print summary
        print("\n" + "="*60)
        print(f"SECURITY HARDENING SUMMARY - {project_name}")
        print("="*60)
        print(f"Total operations: {len(results)}")
        print(f"Successful: {successful_count}")
        print(f"Failed: {failed_count}")
        print(f"Success rate: {(successful_count/len(results)*100):.1f}%")
        
        # Show results by component
        component_results = {}
        for result in results:
            if result.component not in component_results:
                component_results[result.component] = {'success': 0, 'failed': 0}
            
            if result.success:
                component_results[result.component]['success'] += 1
            else:
                component_results[result.component]['failed'] += 1
        
        if component_results:
            print("\nResults by component:")
            for component, counts in component_results.items():
                total = counts['success'] + counts['failed']
                rate = (counts['success'] / total * 100) if total > 0 else 0
                print(f"  {component}: {counts['success']}/{total} ({rate:.1f}%)")
        
        # Show failed operations if any
        failed_results = [r for r in results if not r.success]
        if failed_results and not args.force:
            print("\nFailed operations:")
            for result in failed_results[:5]:  # Show first 5
                print(f"  - {result.message}")
            
            if len(failed_results) > 5:
                print(f"  ... and {len(failed_results) - 5} more")
        
        # Show recommendations from hardening manager
        status = hardening_manager.get_hardening_status()
        if status.get('status') != 'completed':
            print("\nRecommendations:")
            print("  - Review failed operations and address underlying issues")
            print("  - Run security audit to identify remaining vulnerabilities")
            print("  - Consider manual security review for critical components")
            print("  - Implement monitoring for security-related events")
        
        # Return appropriate exit code
        if failed_count == 0:
            logger.info("All hardening operations completed successfully")
            return 0
        elif successful_count > failed_count:
            logger.warning(f"Some hardening operations failed ({failed_count}/{len(results)})")
            return 1
        else:
            logger.error(f"Most hardening operations failed ({failed_count}/{len(results)})")
            return 2
        
    except KeyboardInterrupt:
        logger.info("Hardening interrupted by user")
        return 130
    
    except Exception as e:
        logger.error(f"Security hardening failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())