"""
Custom SQL Rules Engine for DataPulse
Define and execute custom data quality rules
100% local processing
"""

import pandas as pd
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import re


@dataclass
class RuleResult:
    """Result of a rule execution"""
    rule_name: str
    passed: bool
    message: str
    severity: str  # critical, high, medium, low
    rows_checked: int
    rows_failed: int
    failure_rate: float
    details: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0


@dataclass
class DataQualityRule:
    """Definition of a data quality rule"""
    name: str
    description: str
    rule_type: str  # null_check, range_check, regex_check, custom_sql, comparison
    severity: str  # critical, high, medium, low
    column: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class SQLRulesEngine:
    """Execute custom data quality rules"""
    
    def __init__(self):
        self.rules: List[DataQualityRule] = []
        self.results: List[RuleResult] = []
    
    def add_rule(self, rule: DataQualityRule) -> None:
        """Add a rule to the engine"""
        self.rules.append(rule)
    
    def clear_rules(self) -> None:
        """Clear all rules"""
        self.rules = []
        self.results = []
    
    def execute_null_check(self, df: pd.DataFrame, rule: DataQualityRule) -> RuleResult:
        """Check for null values in a column"""
        column = rule.column
        max_null_pct = rule.parameters.get("max_null_pct", 0)
        
        if column not in df.columns:
            return RuleResult(
                rule_name=rule.name,
                passed=False,
                message=f"Column '{column}' not found",
                severity=rule.severity,
                rows_checked=0,
                rows_failed=0,
                failure_rate=0
            )
        
        total = len(df)
        nulls = df[column].isna().sum()
        null_pct = (nulls / total * 100) if total > 0 else 0
        
        passed = null_pct <= max_null_pct
        
        return RuleResult(
            rule_name=rule.name,
            passed=passed,
            message=f"Null rate: {null_pct:.2f}% (max allowed: {max_null_pct}%)",
            severity=rule.severity,
            rows_checked=total,
            rows_failed=nulls,
            failure_rate=null_pct,
            details={"null_count": nulls, "null_pct": null_pct}
        )
    
    def execute_range_check(self, df: pd.DataFrame, rule: DataQualityRule) -> RuleResult:
        """Check if values are within a specified range"""
        column = rule.column
        min_val = rule.parameters.get("min_value")
        max_val = rule.parameters.get("max_value")
        
        if column not in df.columns:
            return RuleResult(
                rule_name=rule.name,
                passed=False,
                message=f"Column '{column}' not found",
                severity=rule.severity,
                rows_checked=0,
                rows_failed=0,
                failure_rate=0
            )
        
        total = len(df)
        failures = 0
        
        if min_val is not None:
            failures += (df[column] < min_val).sum()
        if max_val is not None:
            failures += (df[column] > max_val).sum()
        
        failure_pct = (failures / total * 100) if total > 0 else 0
        passed = failures == 0
        
        return RuleResult(
            rule_name=rule.name,
            passed=passed,
            message=f"Range check: {failures} values out of range [{min_val}, {max_val}]",
            severity=rule.severity,
            rows_checked=total,
            rows_failed=failures,
            failure_rate=failure_pct,
            details={"min": min_val, "max": max_val, "out_of_range": failures}
        )
    
    def execute_regex_check(self, df: pd.DataFrame, rule: DataQualityRule) -> RuleResult:
        """Check if values match a regex pattern"""
        column = rule.column
        pattern = rule.parameters.get("pattern", ".*")
        
        if column not in df.columns:
            return RuleResult(
                rule_name=rule.name,
                passed=False,
                message=f"Column '{column}' not found",
                severity=rule.severity,
                rows_checked=0,
                rows_failed=0,
                failure_rate=0
            )
        
        total = len(df)
        try:
            regex = re.compile(pattern)
            matches = df[column].astype(str).str.match(pattern, na=False)
            failures = (~matches).sum()
        except re.error as e:
            return RuleResult(
                rule_name=rule.name,
                passed=False,
                message=f"Invalid regex pattern: {e}",
                severity=rule.severity,
                rows_checked=0,
                rows_failed=0,
                failure_rate=0
            )
        
        failure_pct = (failures / total * 100) if total > 0 else 0
        passed = failures == 0
        
        return RuleResult(
            rule_name=rule.name,
            passed=passed,
            message=f"Pattern match: {total - failures}/{total} rows match pattern",
            severity=rule.severity,
            rows_checked=total,
            rows_failed=failures,
            failure_rate=failure_pct,
            details={"pattern": pattern, "non_matching": failures}
        )
    
    def execute_uniqueness_check(self, df: pd.DataFrame, rule: DataQualityRule) -> RuleResult:
        """Check for duplicate values"""
        column = rule.column
        
        if column not in df.columns:
            return RuleResult(
                rule_name=rule.name,
                passed=False,
                message=f"Column '{column}' not found",
                severity=rule.severity,
                rows_checked=0,
                rows_failed=0,
                failure_rate=0
            )
        
        total = len(df)
        duplicates = df[column].duplicated().sum()
        dup_pct = (duplicates / total * 100) if total > 0 else 0
        
        passed = duplicates == 0
        
        return RuleResult(
            rule_name=rule.name,
            passed=passed,
            message=f"Uniqueness: {duplicates} duplicate values found ({dup_pct:.2f}%)",
            severity=rule.severity,
            rows_checked=total,
            rows_failed=duplicates,
            failure_rate=dup_pct,
            details={"duplicate_count": duplicates}
        )
    
    def execute_custom_condition(self, df: pd.DataFrame, rule: DataQualityRule) -> RuleResult:
        """Execute a custom pandas condition"""
        condition = rule.parameters.get("condition", "True")
        
        total = len(df)
        try:
            # Safely evaluate the condition
            # Note: In production, use a safer expression parser
            result = df.eval(condition)
            failures = (~result).sum() if hasattr(result, 'sum') else (0 if result else total)
        except Exception as e:
            return RuleResult(
                rule_name=rule.name,
                passed=False,
                message=f"Error evaluating condition: {e}",
                severity=rule.severity,
                rows_checked=0,
                rows_failed=0,
                failure_rate=0
            )
        
        failure_pct = (failures / total * 100) if total > 0 else 0
        passed = failures == 0
        
        return RuleResult(
            rule_name=rule.name,
            passed=passed,
            message=f"Custom check: {total - failures}/{total} rows pass condition",
            severity=rule.severity,
            rows_checked=total,
            rows_failed=failures,
            failure_rate=failure_pct,
            details={"condition": condition}
        )
    
    def execute_rule(self, df: pd.DataFrame, rule: DataQualityRule) -> RuleResult:
        """Execute a single rule"""
        start_time = datetime.now()
        
        executors = {
            "null_check": self.execute_null_check,
            "range_check": self.execute_range_check,
            "regex_check": self.execute_regex_check,
            "uniqueness_check": self.execute_uniqueness_check,
            "custom_condition": self.execute_custom_condition
        }
        
        executor = executors.get(rule.rule_type)
        if not executor:
            return RuleResult(
                rule_name=rule.name,
                passed=False,
                message=f"Unknown rule type: {rule.rule_type}",
                severity=rule.severity,
                rows_checked=0,
                rows_failed=0,
                failure_rate=0
            )
        
        result = executor(df, rule)
        result.execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return result
    
    def execute_all_rules(self, df: pd.DataFrame) -> List[RuleResult]:
        """Execute all enabled rules"""
        self.results = []
        
        for rule in self.rules:
            if rule.enabled:
                result = self.execute_rule(df, rule)
                self.results.append(result)
        
        return self.results
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of rule execution results"""
        if not self.results:
            return {"total": 0, "passed": 0, "failed": 0, "pass_rate": 0}
        
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        severity_breakdown = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for r in self.results:
            if not r.passed:
                severity_breakdown[r.severity] += 1
        
        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / len(self.results) * 100) if self.results else 0,
            "severity_breakdown": severity_breakdown
        }


def get_predefined_rules() -> List[DataQualityRule]:
    """Get a list of common predefined rules"""
    return [
        DataQualityRule(
            name="ID Not Null",
            description="ID column should never be null",
            rule_type="null_check",
            severity="critical",
            column="id",
            parameters={"max_null_pct": 0}
        ),
        DataQualityRule(
            name="Email Format",
            description="Email should match standard format",
            rule_type="regex_check",
            severity="high",
            column="email",
            parameters={"pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"}
        ),
        DataQualityRule(
            name="Amount Positive",
            description="Amount should be positive",
            rule_type="range_check",
            severity="high",
            column="amount",
            parameters={"min_value": 0}
        ),
        DataQualityRule(
            name="User ID Unique",
            description="User ID should be unique",
            rule_type="uniqueness_check",
            severity="critical",
            column="user_id"
        ),
        DataQualityRule(
            name="Status Valid",
            description="Status should be one of allowed values",
            rule_type="custom_condition",
            severity="medium",
            parameters={"condition": "status.isin(['active', 'inactive', 'pending'])"}
        )
    ]


def generate_rule_from_template(template: str, column: str, **params) -> DataQualityRule:
    """Generate a rule from a template"""
    templates = {
        "not_null": DataQualityRule(
            name=f"{column} Not Null",
            description=f"{column} should not contain null values",
            rule_type="null_check",
            severity="high",
            column=column,
            parameters={"max_null_pct": params.get("max_null_pct", 0)}
        ),
        "positive": DataQualityRule(
            name=f"{column} Positive",
            description=f"{column} should be positive",
            rule_type="range_check",
            severity="medium",
            column=column,
            parameters={"min_value": 0}
        ),
        "unique": DataQualityRule(
            name=f"{column} Unique",
            description=f"{column} should have unique values",
            rule_type="uniqueness_check",
            severity="high",
            column=column
        ),
        "range": DataQualityRule(
            name=f"{column} Range",
            description=f"{column} should be within range",
            rule_type="range_check",
            severity="medium",
            column=column,
            parameters={"min_value": params.get("min"), "max_value": params.get("max")}
        )
    }
    
    return templates.get(template, templates["not_null"])
