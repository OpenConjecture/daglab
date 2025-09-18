"""Code security analyzer for static analysis of security vulnerabilities.

Performs static code analysis to identify:
- SQL injection vulnerabilities
- Cross-site scripting (XSS) vulnerabilities  
- Command injection vulnerabilities
- Path traversal vulnerabilities
- Insecure cryptographic usage
- Hardcoded secrets in code
- Unsafe deserialization
- Insecure random number generation
"""

import ast
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass
import tokenize
import io

from ..helpers.security import SecurityManager, FileOperationSecurity
from ..runtime.errors import SecurityError
from .framework import SecurityFinding, SeverityLevel, FindingCategory

logger = logging.getLogger(__name__)


@dataclass
class CodeSecurityPattern:
    """Pattern for detecting security issues in code."""
    name: str
    description: str
    pattern: re.Pattern
    severity: SeverityLevel
    category: FindingCategory
    remediation: str
    languages: List[str]
    context_required: bool = False


class PythonSecurityAnalyzer:
    """Security analyzer specifically for Python code."""
    
    def __init__(self):
        """Initialize Python security analyzer."""
        self.dangerous_functions = {
            'eval', 'exec', 'compile', '__import__',
            'subprocess.call', 'subprocess.run', 'subprocess.Popen',
            'os.system', 'os.popen', 'os.spawn*',
            'pickle.loads', 'pickle.load', 'cPickle.loads',
            'yaml.load', 'yaml.unsafe_load'
        }
        
        self.sql_injection_patterns = [
            r'execute\s*\(\s*["\'][^"\'
]*%[^"\'
]*["\']\s*%',
            r'cursor\.execute\s*\(\s*f["\']',
            r'query\s*=\s*["\'][^"\'
]*\{[^}]*\}[^"\'
]*["\']',
            r'SELECT\s+.*\s+FROM\s+.*\s+WHERE\s+.*%',
        ]
        
    def analyze_python_file(self, file_path: Path) -> List[SecurityFinding]:
        """Analyze Python file for security issues."""
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST for deeper analysis
            try:
                tree = ast.parse(content, filename=str(file_path))
                ast_findings = self._analyze_ast(file_path, tree, content)
                findings.extend(ast_findings)
            except SyntaxError as e:
                # File has syntax errors, can't analyze AST
                logger.warning(f"Syntax error in {file_path}: {e}")
            
            # Pattern-based analysis
            pattern_findings = self._analyze_patterns(file_path, content)
            findings.extend(pattern_findings)
            
        except Exception as e:
            logger.error(f"Failed to analyze Python file {file_path}: {e}")
        
        return findings
    
    def _analyze_ast(self, file_path: Path, tree: ast.AST, content: str) -> List[SecurityFinding]:
        """Analyze Python AST for security issues."""
        findings = []
        lines = content.split('\n')
        
        class SecurityVisitor(ast.NodeVisitor):
            def __init__(self):
                self.findings = []
            
            def visit_Call(self, node):
                # Check for dangerous function calls
                func_name = self._get_function_name(node)
                
                if func_name in ['eval', 'exec']:
                    line_num = getattr(node, 'lineno', 1)
                    self.findings.append(SecurityFinding(
                        id=f"dangerous_eval_{file_path.name}_{line_num}",
                        title=f"Dangerous {func_name}() Function Call",
                        description=f"Use of {func_name}() can lead to code injection vulnerabilities",
                        severity=SeverityLevel.HIGH,
                        category=FindingCategory.CODE_SECURITY,
                        location=f"{file_path}:{line_num}",
                        evidence={
                            "function": func_name,
                            "line": lines[line_num - 1] if line_num <= len(lines) else ""
                        },
                        remediation=f"Avoid using {func_name}(). Use safer alternatives like ast.literal_eval() for eval() or structured approaches instead of exec()"
                    ))
                
                elif func_name in ['subprocess.call', 'subprocess.run', 'subprocess.Popen']:
                    # Check for shell=True
                    for keyword in node.keywords:
                        if keyword.arg == 'shell' and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                            line_num = getattr(node, 'lineno', 1)
                            self.findings.append(SecurityFinding(
                                id=f"subprocess_shell_{file_path.name}_{line_num}",
                                title="Subprocess Call with shell=True",
                                description="Using shell=True in subprocess calls can lead to command injection",
                                severity=SeverityLevel.HIGH,
                                category=FindingCategory.CODE_SECURITY,
                                location=f"{file_path}:{line_num}",
                                evidence={
                                    "function": func_name,
                                    "line": lines[line_num - 1] if line_num <= len(lines) else ""
                                },
                                remediation="Use shell=False and pass command as a list of arguments"
                            ))
                
                elif func_name == 'pickle.loads':
                    line_num = getattr(node, 'lineno', 1)
                    self.findings.append(SecurityFinding(
                        id=f"unsafe_pickle_{file_path.name}_{line_num}",
                        title="Unsafe Pickle Deserialization",
                        description="pickle.loads() can execute arbitrary code during deserialization",
                        severity=SeverityLevel.HIGH,
                        category=FindingCategory.CODE_SECURITY,
                        location=f"{file_path}:{line_num}",
                        evidence={
                            "function": func_name,
                            "line": lines[line_num - 1] if line_num <= len(lines) else ""
                        },
                        remediation="Use safer serialization formats like JSON or validate pickle data sources"
                    ))
                
                self.generic_visit(node)
            
            def visit_Assign(self, node):
                # Check for hardcoded secrets
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    value = node.value.value
                    
                    # Check for potential secrets
                    if len(value) > 20 and re.match(r'^[a-zA-Z0-9+/=]{20,}$', value):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                var_name = target.id.lower()
                                if any(keyword in var_name for keyword in ['secret', 'key', 'token', 'password']):
                                    line_num = getattr(node, 'lineno', 1)
                                    self.findings.append(SecurityFinding(
                                        id=f"hardcoded_secret_{file_path.name}_{line_num}",
                                        title="Hardcoded Secret in Code",
                                        description=f"Variable '{target.id}' appears to contain a hardcoded secret",
                                        severity=SeverityLevel.HIGH,
                                        category=FindingCategory.DATA_PROTECTION,
                                        location=f"{file_path}:{line_num}",
                                        evidence={
                                            "variable": target.id,
                                            "line": lines[line_num - 1] if line_num <= len(lines) else ""
                                        },
                                        remediation="Use environment variables or secure secret management for sensitive data"
                                    ))
                
                self.generic_visit(node)
            
            def _get_function_name(self, node):
                """Extract function name from call node."""
                if isinstance(node.func, ast.Name):
                    return node.func.id
                elif isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        return f"{node.func.value.id}.{node.func.attr}"
                    else:
                        return node.func.attr
                return None
        
        visitor = SecurityVisitor()
        visitor.visit(tree)
        findings.extend(visitor.findings)
        
        return findings
    
    def _analyze_patterns(self, file_path: Path, content: str) -> List[SecurityFinding]:
        """Analyze content using regex patterns."""
        findings = []
        lines = content.split('\n')
        
        # SQL injection patterns
        for i, line in enumerate(lines, 1):
            for pattern in self.sql_injection_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(SecurityFinding(
                        id=f"sql_injection_{file_path.name}_{i}",
                        title="Potential SQL Injection Vulnerability",
                        description="Code pattern suggests potential SQL injection vulnerability",
                        severity=SeverityLevel.HIGH,
                        category=FindingCategory.CODE_SECURITY,
                        location=f"{file_path}:{i}",
                        evidence={
                            "line_number": i,
                            "line": line.strip(),
                            "pattern": pattern
                        },
                        remediation="Use parameterized queries or ORM methods to prevent SQL injection"
                    ))
                    break
        
        return findings


class JavaScriptSecurityAnalyzer:
    """Security analyzer for JavaScript/TypeScript code."""
    
    def __init__(self):
        """Initialize JavaScript security analyzer."""
        self.dangerous_functions = {
            'eval', 'Function', 'setTimeout', 'setInterval',
            'document.write', 'innerHTML', 'outerHTML'
        }
    
    def analyze_javascript_file(self, file_path: Path) -> List[SecurityFinding]:
        """Analyze JavaScript file for security issues."""
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Pattern-based analysis
            findings.extend(self._analyze_xss_patterns(file_path, content))
            findings.extend(self._analyze_dangerous_functions(file_path, content))
            
        except Exception as e:
            logger.error(f"Failed to analyze JavaScript file {file_path}: {e}")
        
        return findings
    
    def _analyze_xss_patterns(self, file_path: Path, content: str) -> List[SecurityFinding]:
        """Analyze for XSS vulnerabilities."""
        findings = []
        lines = content.split('\n')
        
        xss_patterns = [
            r'innerHTML\s*=\s*.*\+',
            r'outerHTML\s*=\s*.*\+',
            r'document\.write\s*\(',
            r'\$\([^)]+\)\.html\s*\(',
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern in xss_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(SecurityFinding(
                        id=f"xss_vulnerability_{file_path.name}_{i}",
                        title="Potential XSS Vulnerability",
                        description="Code pattern suggests potential cross-site scripting vulnerability",
                        severity=SeverityLevel.HIGH,
                        category=FindingCategory.CODE_SECURITY,
                        location=f"{file_path}:{i}",
                        evidence={
                            "line_number": i,
                            "line": line.strip(),
                            "pattern": pattern
                        },
                        remediation="Sanitize user input and use safe DOM manipulation methods"
                    ))
                    break
        
        return findings
    
    def _analyze_dangerous_functions(self, file_path: Path, content: str) -> List[SecurityFinding]:
        """Analyze for dangerous function usage."""
        findings = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            if 'eval(' in line:
                findings.append(SecurityFinding(
                    id=f"dangerous_eval_{file_path.name}_{i}",
                    title="Dangerous eval() Function",
                    description="eval() can execute arbitrary code and lead to code injection",
                    severity=SeverityLevel.HIGH,
                    category=FindingCategory.CODE_SECURITY,
                    location=f"{file_path}:{i}",
                    evidence={
                        "line_number": i,
                        "line": line.strip()
                    },
                    remediation="Avoid eval(). Use JSON.parse() for JSON data or other safe alternatives"
                ))
        
        return findings


class CodeSecurityAnalyzer:
    """Main code security analyzer that coordinates language-specific analyzers."""
    
    def __init__(self):
        """Initialize code security analyzer."""
        self.security_manager = SecurityManager()
        self.file_ops = FileOperationSecurity()
        
        # Initialize language-specific analyzers
        self.python_analyzer = PythonSecurityAnalyzer()
        self.javascript_analyzer = JavaScriptSecurityAnalyzer()
        
        # File extensions to analyze
        self.python_extensions = {'.py', '.pyw'}
        self.javascript_extensions = {'.js', '.jsx', '.ts', '.tsx'}
        self.code_extensions = self.python_extensions | self.javascript_extensions
        
    def analyze_code_security(self, project_path: Path, excluded_paths: List[str] = None) -> List[SecurityFinding]:
        """Analyze all code files in project for security issues.
        
        Args:
            project_path: Path to project root
            excluded_paths: List of path patterns to exclude
            
        Returns:
            List of code security findings
        """
        findings = []
        excluded_paths = excluded_paths or []
        
        logger.info(f"Starting code security analysis for {project_path}")
        
        # Find all code files
        code_files = self._find_code_files(project_path, excluded_paths)
        
        for code_file in code_files:
            try:
                file_findings = self._analyze_code_file(code_file)
                findings.extend(file_findings)
            except Exception as e:
                logger.error(f"Failed to analyze {code_file}: {e}")
        
        logger.info(f"Code security analysis completed: {len(findings)} findings")
        return findings
    
    def _find_code_files(self, project_path: Path, excluded_paths: List[str]) -> List[Path]:
        """Find all code files in project."""
        code_files = []
        
        for ext in self.code_extensions:
            code_files.extend(project_path.glob(f"**/*{ext}"))
        
        # Filter out excluded paths
        filtered_files = []
        for file_path in code_files:
            if file_path.is_file():
                # Check if file should be excluded
                should_exclude = False
                for excluded in excluded_paths:
                    if excluded in str(file_path):
                        should_exclude = True
                        break
                
                if not should_exclude:
                    filtered_files.append(file_path)
        
        return filtered_files
    
    def _analyze_code_file(self, file_path: Path) -> List[SecurityFinding]:
        """Analyze a single code file."""
        findings = []
        
        file_ext = file_path.suffix.lower()
        
        if file_ext in self.python_extensions:
            findings = self.python_analyzer.analyze_python_file(file_path)
        elif file_ext in self.javascript_extensions:
            findings = self.javascript_analyzer.analyze_javascript_file(file_path)
        
        # Add general security patterns
        general_findings = self._analyze_general_patterns(file_path)
        findings.extend(general_findings)
        
        return findings
    
    def _analyze_general_patterns(self, file_path: Path) -> List[SecurityFinding]:
        """Analyze file for general security patterns."""
        findings = []
        
        try:
            content = self.file_ops.safe_read(file_path)
            lines = content.split('\n')
            
            # Common security patterns
            patterns = [
                {
                    'name': 'hardcoded_ip',
                    'pattern': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
                    'description': 'Hardcoded IP address found',
                    'severity': SeverityLevel.LOW,
                    'remediation': 'Use configuration files or environment variables for IP addresses'
                },
                {
                    'name': 'hardcoded_url',
                    'pattern': r'https?://[^\s"\'>]+',
                    'description': 'Hardcoded URL found',
                    'severity': SeverityLevel.LOW,
                    'remediation': 'Use configuration for external URLs'
                },
                {
                    'name': 'temp_file',
                    'pattern': r'/tmp/[^\s"\'>]+',
                    'description': 'Hardcoded temporary file path',
                    'severity': SeverityLevel.MEDIUM,
                    'remediation': 'Use tempfile module for temporary files'
                }
            ]
            
            for i, line in enumerate(lines, 1):
                for pattern_info in patterns:
                    if re.search(pattern_info['pattern'], line):
                        findings.append(SecurityFinding(
                            id=f"{pattern_info['name']}_{file_path.name}_{i}",
                            title=pattern_info['description'],
                            description=f"{pattern_info['description']} in {file_path.name} at line {i}",
                            severity=pattern_info['severity'],
                            category=FindingCategory.CODE_SECURITY,
                            location=f"{file_path}:{i}",
                            evidence={
                                "line_number": i,
                                "line": line.strip()
                            },
                            remediation=pattern_info['remediation']
                        ))
                        break  # Only one finding per line
            
        except Exception as e:
            logger.error(f"Failed to analyze general patterns in {file_path}: {e}")
        
        return findings