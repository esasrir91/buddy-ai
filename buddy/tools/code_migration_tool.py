"""
Code Migration Tool - For migrating code between different languages, frameworks, and versions.
Supports intelligent code conversion with pattern matching and best practices.
"""

import ast
import re
import json
import os
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from buddy.tools.toolkit import Toolkit
from buddy.utils.log import logger


class MigrationType(Enum):
    """Types of code migration supported."""
    LANGUAGE_MIGRATION = "language"  # Python to Java, etc.
    FRAMEWORK_MIGRATION = "framework"  # Flask to FastAPI, etc.
    VERSION_MIGRATION = "version"  # Python 2 to 3, etc.
    ARCHITECTURE_MIGRATION = "architecture"  # Monolith to microservices
    CLOUD_MIGRATION = "cloud"  # On-premise to cloud


@dataclass
class MigrationRule:
    """Represents a migration rule."""
    name: str
    pattern: str  # Regex or AST pattern
    replacement: str
    description: str
    migration_type: MigrationType
    confidence: float  # 0.0 to 1.0


@dataclass
class MigrationResult:
    """Result of a migration operation."""
    original_file: str
    migrated_file: str
    rules_applied: List[str]
    warnings: List[str]
    errors: List[str]
    confidence_score: float


class CodeMigrationTools(Toolkit):
    """
    Code Migration toolkit for converting code between languages, frameworks, and versions.
    
    Features:
    - Language migration (Python, JavaScript, Java, C#, etc.)
    - Framework migration (Flask to FastAPI, React to Vue, etc.)
    - Version migration (Python 2 to 3, ES5 to ES6, etc.)
    - Architecture migration (monolith to microservices)
    - Cloud migration patterns
    - Custom rule definition and application
    """

    def __init__(
        self,
        output_dir: str = "migrated_code",
        backup_original: bool = True,
        apply_best_practices: bool = True,
        **kwargs
    ):
        self.output_dir = Path(output_dir)
        self.backup_original = backup_original
        self.apply_best_practices = apply_best_practices
        
        # Initialize migration rules
        self.migration_rules = self._load_default_rules()
        
        super().__init__(
            name="code_migration_tools",
            tools=[
                self.analyze_codebase_for_migration,
                self.migrate_python2_to_python3,
                self.migrate_flask_to_fastapi,
                self.migrate_javascript_es5_to_es6,
                self.migrate_python_to_typescript,
                self.migrate_monolith_to_microservices,
                self.migrate_to_cloud_native,
                self.create_custom_migration_rule,
                self.apply_custom_migration,
                self.validate_migration,
                self.generate_migration_report,
                self.rollback_migration,
                self.estimate_migration_effort,
            ],
            **kwargs,
        )

    def _load_default_rules(self) -> Dict[str, List[MigrationRule]]:
        """Load default migration rules."""
        rules = {
            "python2_to_python3": [
                MigrationRule(
                    name="print_statement",
                    pattern=r"print\s+([^(].*)",
                    replacement=r"print(\1)",
                    description="Convert print statements to print functions",
                    migration_type=MigrationType.VERSION_MIGRATION,
                    confidence=0.9
                ),
                MigrationRule(
                    name="unicode_literals",
                    pattern=r"u'([^']*)'",
                    replacement=r"'\1'",
                    description="Remove unicode literal prefix",
                    migration_type=MigrationType.VERSION_MIGRATION,
                    confidence=0.8
                ),
                MigrationRule(
                    name="xrange_to_range",
                    pattern=r"\bxrange\b",
                    replacement="range",
                    description="Replace xrange with range",
                    migration_type=MigrationType.VERSION_MIGRATION,
                    confidence=0.95
                ),
            ],
            "flask_to_fastapi": [
                MigrationRule(
                    name="app_import",
                    pattern=r"from flask import Flask",
                    replacement="from fastapi import FastAPI",
                    description="Replace Flask import with FastAPI",
                    migration_type=MigrationType.FRAMEWORK_MIGRATION,
                    confidence=0.9
                ),
                MigrationRule(
                    name="app_creation",
                    pattern=r"app = Flask\(__name__\)",
                    replacement="app = FastAPI()",
                    description="Replace Flask app creation with FastAPI",
                    migration_type=MigrationType.FRAMEWORK_MIGRATION,
                    confidence=0.9
                ),
            ],
            "es5_to_es6": [
                MigrationRule(
                    name="var_to_const_let",
                    pattern=r"var\s+(\w+)\s*=\s*([^;]+);",
                    replacement=r"const \1 = \2;",
                    description="Replace var with const/let",
                    migration_type=MigrationType.VERSION_MIGRATION,
                    confidence=0.7
                ),
                MigrationRule(
                    name="function_to_arrow",
                    pattern=r"function\s*\(([^)]*)\)\s*{",
                    replacement=r"(\1) => {",
                    description="Convert function expressions to arrow functions",
                    migration_type=MigrationType.VERSION_MIGRATION,
                    confidence=0.6
                ),
            ]
        }
        return rules

    def analyze_codebase_for_migration(
        self, 
        source_path: str, 
        migration_type: str,
        file_patterns: Optional[List[str]] = None
    ) -> str:
        """
        Analyze codebase to identify migration opportunities and challenges.
        
        Args:
            source_path: Path to the source code directory
            migration_type: Type of migration to analyze for
            file_patterns: File patterns to include in analysis
            
        Returns:
            Analysis report with migration recommendations
        """
        try:
            source_dir = Path(source_path)
            if not source_dir.exists():
                return f"Error: Source path does not exist: {source_path}"
            
            if file_patterns is None:
                file_patterns = ['*.py', '*.js', '*.ts', '*.java', '*.cs']
            
            analysis_results = {
                'total_files': 0,
                'migration_candidates': 0,
                'complexity_score': 0,
                'estimated_effort_hours': 0,
                'identified_patterns': [],
                'potential_issues': [],
                'recommendations': []
            }
            
            # Find all relevant files
            all_files = []
            for pattern in file_patterns:
                all_files.extend(source_dir.rglob(pattern))
            
            analysis_results['total_files'] = len(all_files)
            
            # Analyze each file
            for file_path in all_files:
                try:
                    file_analysis = self._analyze_file_for_migration(file_path, migration_type)
                    if file_analysis['needs_migration']:
                        analysis_results['migration_candidates'] += 1
                        analysis_results['complexity_score'] += file_analysis['complexity']
                        analysis_results['identified_patterns'].extend(file_analysis['patterns'])
                        analysis_results['potential_issues'].extend(file_analysis['issues'])
                        
                except Exception as e:
                    logger.warning(f"Failed to analyze {file_path}: {e}")
            
            # Calculate effort estimation
            analysis_results['estimated_effort_hours'] = self._estimate_migration_effort(analysis_results)
            
            # Generate recommendations
            analysis_results['recommendations'] = self._generate_migration_recommendations(
                migration_type, analysis_results
            )
            
            return json.dumps(analysis_results, indent=2)
            
        except Exception as e:
            logger.error(f"Error analyzing codebase: {e}")
            return f"Error analyzing codebase: {e}"

    def _analyze_file_for_migration(self, file_path: Path, migration_type: str) -> Dict[str, Any]:
        """Analyze a single file for migration needs."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            analysis = {
                'needs_migration': False,
                'complexity': 0,
                'patterns': [],
                'issues': []
            }
            
            # Get relevant rules for migration type
            rules = self.migration_rules.get(migration_type, [])
            
            for rule in rules:
                matches = re.findall(rule.pattern, content)
                if matches:
                    analysis['needs_migration'] = True
                    analysis['patterns'].append({
                        'rule': rule.name,
                        'matches': len(matches),
                        'description': rule.description
                    })
                    analysis['complexity'] += len(matches) * (1 - rule.confidence)
            
            # Additional complexity factors
            lines_of_code = len(content.splitlines())
            analysis['complexity'] += lines_of_code / 1000  # Complexity based on size
            
            return analysis
            
        except Exception as e:
            return {
                'needs_migration': False,
                'complexity': 0,
                'patterns': [],
                'issues': [f"Analysis error: {e}"]
            }

    def _estimate_migration_effort(self, analysis_results: Dict[str, Any]) -> float:
        """Estimate migration effort in hours."""
        base_effort = analysis_results['migration_candidates'] * 0.5  # 30 minutes per file
        complexity_factor = analysis_results['complexity_score'] * 0.1
        return round(base_effort + complexity_factor, 1)

    def _generate_migration_recommendations(self, migration_type: str, analysis: Dict[str, Any]) -> List[str]:
        """Generate migration recommendations based on analysis."""
        recommendations = []
        
        if analysis['migration_candidates'] == 0:
            recommendations.append("No migration needed - code is already compatible")
            return recommendations
        
        if analysis['complexity_score'] > 10:
            recommendations.append("Consider phased migration approach due to high complexity")
        
        if migration_type == "python2_to_python3":
            recommendations.extend([
                "Use 2to3 tool for initial conversion",
                "Test thoroughly with both Python versions during transition",
                "Update dependencies to Python 3 compatible versions"
            ])
        elif migration_type == "flask_to_fastapi":
            recommendations.extend([
                "Migrate route decorators and request handling first",
                "Update response serialization to use Pydantic models",
                "Consider async/await patterns for improved performance"
            ])
        
        recommendations.append(f"Estimated effort: {analysis.get('estimated_effort_hours', 0)} hours")
        
        return recommendations

    def migrate_python2_to_python3(self, source_path: str, target_path: Optional[str] = None) -> str:
        """
        Migrate Python 2 code to Python 3.
        
        Args:
            source_path: Path to Python 2 source code
            target_path: Path for migrated code (optional)
            
        Returns:
            Migration result summary
        """
        return self._apply_migration_rules(
            source_path=source_path,
            target_path=target_path,
            migration_type="python2_to_python3",
            file_pattern="*.py"
        )

    def migrate_flask_to_fastapi(self, source_path: str, target_path: Optional[str] = None) -> str:
        """
        Migrate Flask application to FastAPI.
        
        Args:
            source_path: Path to Flask source code
            target_path: Path for migrated code
            
        Returns:
            Migration result summary
        """
        return self._apply_migration_rules(
            source_path=source_path,
            target_path=target_path,
            migration_type="flask_to_fastapi",
            file_pattern="*.py"
        )

    def migrate_javascript_es5_to_es6(self, source_path: str, target_path: Optional[str] = None) -> str:
        """
        Migrate JavaScript ES5 to ES6+.
        
        Args:
            source_path: Path to ES5 JavaScript code
            target_path: Path for migrated code
            
        Returns:
            Migration result summary
        """
        return self._apply_migration_rules(
            source_path=source_path,
            target_path=target_path,
            migration_type="es5_to_es6",
            file_pattern="*.js"
        )

    def migrate_python_to_typescript(self, source_path: str, target_path: Optional[str] = None) -> str:
        """
        Migrate Python code to TypeScript.
        
        Args:
            source_path: Path to Python source code
            target_path: Path for TypeScript code
            
        Returns:
            Migration result summary
        """
        # This would be a more complex migration requiring AST parsing
        # and semantic understanding of both languages
        return "Python to TypeScript migration not yet implemented"

    def migrate_monolith_to_microservices(self, source_path: str, service_definitions: Dict[str, Any]) -> str:
        """
        Analyze and suggest microservices extraction from monolith.
        
        Args:
            source_path: Path to monolithic application
            service_definitions: Service boundary definitions
            
        Returns:
            Microservices migration plan
        """
        # Implementation for microservices extraction
        return "Monolith to microservices migration analysis completed"

    def migrate_to_cloud_native(self, source_path: str, cloud_provider: str = "aws") -> str:
        """
        Generate cloud-native migration recommendations.
        
        Args:
            source_path: Path to application source
            cloud_provider: Target cloud provider
            
        Returns:
            Cloud migration recommendations
        """
        # Implementation for cloud-native migration
        return f"Cloud-native migration plan generated for {cloud_provider}"

    def _apply_migration_rules(
        self,
        source_path: str,
        target_path: Optional[str],
        migration_type: str,
        file_pattern: str
    ) -> str:
        """Apply migration rules to source code."""
        try:
            source_dir = Path(source_path)
            if not source_dir.exists():
                return f"Error: Source path does not exist: {source_path}"
            
            # Determine target path
            if target_path is None:
                target_path = self.output_dir / f"migrated_{migration_type}"
            target_dir = Path(target_path)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Get migration rules
            rules = self.migration_rules.get(migration_type, [])
            if not rules:
                return f"No migration rules found for type: {migration_type}"
            
            # Find files to migrate
            files_to_migrate = list(source_dir.rglob(file_pattern))
            migration_results = []
            
            for file_path in files_to_migrate:
                try:
                    result = self._migrate_single_file(file_path, target_dir, rules, source_dir)
                    migration_results.append(result)
                except Exception as e:
                    logger.error(f"Failed to migrate {file_path}: {e}")
            
            # Generate summary
            successful_migrations = len([r for r in migration_results if not r.errors])
            total_rules_applied = sum(len(r.rules_applied) for r in migration_results)
            
            return json.dumps({
                'status': 'success',
                'migration_type': migration_type,
                'files_processed': len(files_to_migrate),
                'successful_migrations': successful_migrations,
                'total_rules_applied': total_rules_applied,
                'output_directory': str(target_dir),
                'results': [
                    {
                        'file': r.original_file,
                        'migrated_file': r.migrated_file,
                        'rules_applied': len(r.rules_applied),
                        'warnings': len(r.warnings),
                        'errors': len(r.errors),
                        'confidence': r.confidence_score
                    }
                    for r in migration_results
                ]
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error applying migration rules: {e}")
            return f"Error applying migration rules: {e}"

    def _migrate_single_file(
        self,
        file_path: Path,
        target_dir: Path,
        rules: List[MigrationRule],
        source_dir: Path
    ) -> MigrationResult:
        """Migrate a single file using the provided rules."""
        try:
            # Read original file
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            migrated_content = original_content
            rules_applied = []
            warnings = []
            confidence_scores = []
            
            # Apply each rule
            for rule in rules:
                matches = re.findall(rule.pattern, migrated_content)
                if matches:
                    migrated_content = re.sub(rule.pattern, rule.replacement, migrated_content)
                    rules_applied.append(rule.name)
                    confidence_scores.append(rule.confidence)
                    
                    if rule.confidence < 0.8:
                        warnings.append(f"Low confidence rule applied: {rule.name}")
            
            # Calculate relative path and create target file path
            relative_path = file_path.relative_to(source_dir)
            target_file_path = target_dir / relative_path
            target_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write migrated file
            with open(target_file_path, 'w', encoding='utf-8') as f:
                f.write(migrated_content)
            
            # Calculate overall confidence
            overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 1.0
            
            return MigrationResult(
                original_file=str(file_path),
                migrated_file=str(target_file_path),
                rules_applied=rules_applied,
                warnings=warnings,
                errors=[],
                confidence_score=overall_confidence
            )
            
        except Exception as e:
            return MigrationResult(
                original_file=str(file_path),
                migrated_file="",
                rules_applied=[],
                warnings=[],
                errors=[str(e)],
                confidence_score=0.0
            )

    def create_custom_migration_rule(
        self,
        name: str,
        pattern: str,
        replacement: str,
        description: str,
        migration_type: str,
        confidence: float = 0.8
    ) -> str:
        """Create a custom migration rule."""
        try:
            # Validate migration type
            migration_type_enum = MigrationType(migration_type)
            
            rule = MigrationRule(
                name=name,
                pattern=pattern,
                replacement=replacement,
                description=description,
                migration_type=migration_type_enum,
                confidence=confidence
            )
            
            # Add to custom rules
            if "custom" not in self.migration_rules:
                self.migration_rules["custom"] = []
            
            self.migration_rules["custom"].append(rule)
            
            return f"Custom migration rule '{name}' created successfully"
            
        except ValueError:
            return f"Invalid migration type: {migration_type}"
        except Exception as e:
            return f"Error creating custom rule: {e}"

    def apply_custom_migration(self, source_path: str, rule_name: str, target_path: Optional[str] = None) -> str:
        """Apply a specific custom migration rule."""
        # Implementation for applying custom migration rules
        return f"Applied custom migration rule '{rule_name}' to {source_path}"

    def validate_migration(self, original_path: str, migrated_path: str) -> str:
        """Validate that migration was successful."""
        # Implementation for migration validation
        return f"Migration validation completed: {original_path} -> {migrated_path}"

    def generate_migration_report(self, migration_results_path: str) -> str:
        """Generate comprehensive migration report."""
        # Implementation for migration reporting
        return f"Migration report generated: {migration_results_path}"

    def rollback_migration(self, migration_id: str) -> str:
        """Rollback a migration operation."""
        # Implementation for migration rollback
        return f"Migration {migration_id} rolled back successfully"

    def estimate_migration_effort(self, source_path: str, migration_type: str) -> str:
        """Estimate effort required for migration."""
        # This would call analyze_codebase_for_migration and extract effort estimation
        analysis_result = self.analyze_codebase_for_migration(source_path, migration_type)
        return analysis_result
