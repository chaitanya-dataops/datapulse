"""
Conformance Validation Module for DataPulse
Format validation, pattern matching, and data type conformance
Aligned with Brightspeed Requirements Section 6
"""

import pandas as pd
import numpy as np
import re
from typing import Dict, List, Any, Optional, Callable, Pattern
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class ConformanceType(Enum):
    """Types of conformance checks"""
    REGEX_PATTERN = "regex"
    DATE_FORMAT = "date_format"
    ENUM_VALUES = "enum"
    NUMERIC_RANGE = "range"
    STRING_LENGTH = "length"
    DATA_TYPE = "type"
    CUSTOM = "custom"


class ConformanceLevel(Enum):
    """Conformance result levels"""
    FULL = "full"        # 100% conformant
    HIGH = "high"        # >95% conformant
    MEDIUM = "medium"    # 80-95% conformant
    LOW = "low"          # 50-80% conformant
    CRITICAL = "critical"  # <50% conformant


@dataclass
class ConformanceRule:
    """Defines a conformance validation rule"""
    name: str
    column: str
    conformance_type: ConformanceType
    description: str
    
    # Type-specific parameters
    pattern: Optional[str] = None  # Regex pattern
    date_format: Optional[str] = None  # strptime format
    allowed_values: Optional[List[Any]] = None  # Enum values
    min_value: Optional[float] = None  # Range min
    max_value: Optional[float] = None  # Range max
    min_length: Optional[int] = None  # String min length
    max_length: Optional[int] = None  # String max length
    expected_type: Optional[str] = None  # Expected data type
    custom_validator: Optional[Callable] = None  # Custom function
    
    # Thresholds
    min_conformance_pct: float = 95.0  # Minimum acceptable conformance
    
    def __post_init__(self):
        if self.pattern:
            self._compiled_pattern = re.compile(self.pattern)
        else:
            self._compiled_pattern = None


@dataclass
class ConformanceResult:
    """Result of a conformance check"""
    rule_name: str
    column: str
    check_time: str
    
    # Counts
    total_rows: int
    conformant_rows: int
    non_conformant_rows: int
    null_rows: int
    
    # Metrics
    conformance_pct: float
    conformance_level: ConformanceLevel
    passed: bool
    
    # Violations
    sample_violations: List[Any]
    violation_patterns: Dict[str, int]  # Common violation patterns
    
    # Recommendations
    issues: List[str]


# Pre-built patterns for common formats
COMMON_PATTERNS = {
    "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    "phone_us": r"^\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$",
    "phone_international": r"^\+\d{1,3}[-.\s]?\d{1,14}$",
    "ssn": r"^\d{3}-\d{2}-\d{4}$",
    "zip_us": r"^\d{5}(-\d{4})?$",
    "credit_card": r"^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$",
    "uuid": r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
    "ip_v4": r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$",
    "url": r"^https?://[^\s/$.?#].[^\s]*$",
    "iso_date": r"^\d{4}-\d{2}-\d{2}$",
    "iso_datetime": r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}",
    "alphanumeric": r"^[a-zA-Z0-9]+$",
    "alpha_only": r"^[a-zA-Z]+$",
    "numeric_string": r"^\d+$",
    "currency_usd": r"^\$?\d{1,3}(,\d{3})*(\.\d{2})?$"
}

# Common date formats
COMMON_DATE_FORMATS = {
    "iso": "%Y-%m-%d",
    "iso_datetime": "%Y-%m-%dT%H:%M:%S",
    "us_date": "%m/%d/%Y",
    "eu_date": "%d/%m/%Y",
    "us_datetime": "%m/%d/%Y %H:%M:%S",
    "compact": "%Y%m%d"
}


class ConformanceValidator:
    """Validate data conformance against rules"""
    
    def __init__(self):
        self.rules: Dict[str, ConformanceRule] = {}
        self.check_history: List[ConformanceResult] = []
    
    def register_rule(self, rule: ConformanceRule):
        """Register a conformance rule"""
        self.rules[rule.name] = rule
    
    def create_pattern_rule(
        self,
        name: str,
        column: str,
        pattern_name: str,
        min_conformance_pct: float = 95.0
    ) -> ConformanceRule:
        """Create a rule using a common pattern"""
        if pattern_name not in COMMON_PATTERNS:
            raise ValueError(f"Unknown pattern: {pattern_name}")
        
        return ConformanceRule(
            name=name,
            column=column,
            conformance_type=ConformanceType.REGEX_PATTERN,
            description=f"Validates {column} matches {pattern_name} pattern",
            pattern=COMMON_PATTERNS[pattern_name],
            min_conformance_pct=min_conformance_pct
        )
    
    def validate_pattern(
        self,
        series: pd.Series,
        pattern: Pattern
    ) -> pd.Series:
        """Check if values match a regex pattern"""
        def check(val):
            if pd.isna(val):
                return None
            return bool(pattern.match(str(val)))
        return series.apply(check)
    
    def validate_date_format(
        self,
        series: pd.Series,
        date_format: str
    ) -> pd.Series:
        """Check if values match a date format"""
        def check(val):
            if pd.isna(val):
                return None
            try:
                datetime.strptime(str(val), date_format)
                return True
            except ValueError:
                return False
        return series.apply(check)
    
    def validate_enum(
        self,
        series: pd.Series,
        allowed_values: List[Any]
    ) -> pd.Series:
        """Check if values are in allowed set"""
        allowed_set = set(allowed_values)
        def check(val):
            if pd.isna(val):
                return None
            return val in allowed_set
        return series.apply(check)
    
    def validate_range(
        self,
        series: pd.Series,
        min_val: Optional[float],
        max_val: Optional[float]
    ) -> pd.Series:
        """Check if numeric values are within range"""
        def check(val):
            if pd.isna(val):
                return None
            try:
                num = float(val)
                if min_val is not None and num < min_val:
                    return False
                if max_val is not None and num > max_val:
                    return False
                return True
            except (ValueError, TypeError):
                return False
        return series.apply(check)
    
    def validate_length(
        self,
        series: pd.Series,
        min_len: Optional[int],
        max_len: Optional[int]
    ) -> pd.Series:
        """Check if string length is within bounds"""
        def check(val):
            if pd.isna(val):
                return None
            length = len(str(val))
            if min_len is not None and length < min_len:
                return False
            if max_len is not None and length > max_len:
                return False
            return True
        return series.apply(check)
    
    def validate_type(
        self,
        series: pd.Series,
        expected_type: str
    ) -> pd.Series:
        """Check if values match expected type"""
        type_checks = {
            "int": lambda x: isinstance(x, (int, np.integer)) or (isinstance(x, float) and x.is_integer()),
            "float": lambda x: isinstance(x, (int, float, np.number)),
            "string": lambda x: isinstance(x, str),
            "bool": lambda x: isinstance(x, bool),
            "date": lambda x: isinstance(x, (datetime, pd.Timestamp))
        }
        
        check_func = type_checks.get(expected_type, lambda x: True)
        
        def check(val):
            if pd.isna(val):
                return None
            return check_func(val)
        return series.apply(check)
    
    def check_conformance(
        self,
        df: pd.DataFrame,
        rule_name: str
    ) -> ConformanceResult:
        """Run a conformance check against a dataframe"""
        
        if rule_name not in self.rules:
            raise ValueError(f"Rule '{rule_name}' not registered")
        
        rule = self.rules[rule_name]
        
        if rule.column not in df.columns:
            raise ValueError(f"Column '{rule.column}' not found in dataframe")
        
        series = df[rule.column]
        
        # Run appropriate validator
        if rule.conformance_type == ConformanceType.REGEX_PATTERN:
            results = self.validate_pattern(series, rule._compiled_pattern)
        elif rule.conformance_type == ConformanceType.DATE_FORMAT:
            results = self.validate_date_format(series, rule.date_format)
        elif rule.conformance_type == ConformanceType.ENUM_VALUES:
            results = self.validate_enum(series, rule.allowed_values)
        elif rule.conformance_type == ConformanceType.NUMERIC_RANGE:
            results = self.validate_range(series, rule.min_value, rule.max_value)
        elif rule.conformance_type == ConformanceType.STRING_LENGTH:
            results = self.validate_length(series, rule.min_length, rule.max_length)
        elif rule.conformance_type == ConformanceType.DATA_TYPE:
            results = self.validate_type(series, rule.expected_type)
        elif rule.conformance_type == ConformanceType.CUSTOM and rule.custom_validator:
            results = series.apply(rule.custom_validator)
        else:
            raise ValueError(f"Invalid conformance type: {rule.conformance_type}")
        
        # Calculate metrics
        total_rows = len(series)
        null_rows = results.isna().sum()
        non_null_results = results.dropna()
        conformant_rows = non_null_results.sum()
        non_conformant_rows = len(non_null_results) - conformant_rows
        
        conformance_pct = (conformant_rows / (total_rows - null_rows) * 100) if (total_rows - null_rows) > 0 else 100.0
        
        # Determine conformance level
        if conformance_pct >= 100:
            level = ConformanceLevel.FULL
        elif conformance_pct >= 95:
            level = ConformanceLevel.HIGH
        elif conformance_pct >= 80:
            level = ConformanceLevel.MEDIUM
        elif conformance_pct >= 50:
            level = ConformanceLevel.LOW
        else:
            level = ConformanceLevel.CRITICAL
        
        # Get sample violations
        violation_mask = results == False
        sample_violations = series[violation_mask].head(10).tolist()
        
        # Analyze violation patterns
        violation_patterns = {}
        violations = series[violation_mask]
        if len(violations) > 0:
            # Try to categorize violations
            for val in violations.head(100):
                if pd.isna(val):
                    continue
                val_str = str(val)
                # Simplified pattern detection
                if re.match(r"^\d+$", val_str):
                    pattern = "numeric_only"
                elif re.match(r"^[a-zA-Z]+$", val_str):
                    pattern = "alpha_only"
                elif len(val_str) < 3:
                    pattern = "too_short"
                elif len(val_str) > 100:
                    pattern = "too_long"
                else:
                    pattern = "format_mismatch"
                violation_patterns[pattern] = violation_patterns.get(pattern, 0) + 1
        
        # Generate issues
        issues = []
        if conformance_pct < rule.min_conformance_pct:
            issues.append(f"Conformance {conformance_pct:.1f}% below threshold {rule.min_conformance_pct}%")
        if null_rows > total_rows * 0.1:
            issues.append(f"High null rate: {null_rows / total_rows * 100:.1f}%")
        if violation_patterns:
            top_pattern = max(violation_patterns.items(), key=lambda x: x[1])
            issues.append(f"Most common violation: {top_pattern[0]} ({top_pattern[1]} occurrences)")
        
        result = ConformanceResult(
            rule_name=rule_name,
            column=rule.column,
            check_time=datetime.now().isoformat(),
            total_rows=total_rows,
            conformant_rows=int(conformant_rows),
            non_conformant_rows=int(non_conformant_rows),
            null_rows=int(null_rows),
            conformance_pct=round(conformance_pct, 2),
            conformance_level=level,
            passed=conformance_pct >= rule.min_conformance_pct,
            sample_violations=sample_violations,
            violation_patterns=violation_patterns,
            issues=issues
        )
        
        self.check_history.append(result)
        return result
    
    def check_all_rules(self, df: pd.DataFrame) -> List[ConformanceResult]:
        """Run all registered rules against a dataframe"""
        results = []
        for rule_name, rule in self.rules.items():
            if rule.column in df.columns:
                try:
                    result = self.check_conformance(df, rule_name)
                    results.append(result)
                except Exception as e:
                    # Log error but continue
                    pass
        return results
    
    def get_conformance_summary(self) -> Dict[str, Any]:
        """Get summary of recent conformance checks"""
        
        recent_checks = {}
        for check in reversed(self.check_history):
            if check.rule_name not in recent_checks:
                recent_checks[check.rule_name] = check
        
        by_level = {level.value: 0 for level in ConformanceLevel}
        for check in recent_checks.values():
            by_level[check.conformance_level.value] += 1
        
        passed_count = sum(1 for c in recent_checks.values() if c.passed)
        
        return {
            "total_rules": len(self.rules),
            "rules_checked": len(recent_checks),
            "passed": passed_count,
            "failed": len(recent_checks) - passed_count,
            "by_level": by_level,
            "avg_conformance": round(
                sum(c.conformance_pct for c in recent_checks.values()) / len(recent_checks)
                if recent_checks else 100, 2
            )
        }


def generate_mock_conformance_data() -> pd.DataFrame:
    """Generate mock data with various format violations"""
    np.random.seed(42)
    n = 1000
    
    # Email - some invalid
    emails = [f"user{i}@example.com" for i in range(n)]
    for i in np.random.choice(n, 50):
        emails[i] = f"invalid_email_{i}"  # Missing @
    
    # Phone - mixed formats
    phones = [f"+1-555-{np.random.randint(100, 999):03d}-{np.random.randint(1000, 9999):04d}" for _ in range(n)]
    for i in np.random.choice(n, 30):
        phones[i] = f"{np.random.randint(10000000, 99999999)}"  # Wrong format
    
    # Status - enum violations
    statuses = np.random.choice(["active", "inactive", "pending"], n, p=[0.7, 0.2, 0.1])
    for i in np.random.choice(n, 20):
        statuses[i] = "unknown"  # Invalid value
    
    # Amount - range violations
    amounts = np.random.uniform(10, 500, n)
    for i in np.random.choice(n, 25):
        amounts[i] = np.random.uniform(-100, -1)  # Negative values
    
    # Date - format violations
    dates = [(datetime.now() - timedelta(days=np.random.randint(0, 365))).strftime("%Y-%m-%d") for _ in range(n)]
    for i in np.random.choice(n, 40):
        dates[i] = f"{np.random.randint(1, 12)}/{np.random.randint(1, 28)}/{np.random.randint(2020, 2025)}"  # US format
    
    return pd.DataFrame({
        "email": emails,
        "phone": phones,
        "status": statuses,
        "amount": amounts,
        "date": dates,
        "id": [f"ID-{i:05d}" for i in range(n)]
    })


def generate_mock_conformance_results() -> List[Dict]:
    """Generate mock conformance results for demo"""
    return [
        {
            "rule": "email_format",
            "column": "customer_email",
            "conformance_pct": 95.2,
            "level": "high",
            "violations": 48,
            "sample_violations": ["invalid_email_1", "missingat.com"],
            "status": "passed"
        },
        {
            "rule": "phone_format",
            "column": "contact_phone",
            "conformance_pct": 97.1,
            "level": "high",
            "violations": 29,
            "sample_violations": ["12345678", "555-1234"],
            "status": "passed"
        },
        {
            "rule": "status_enum",
            "column": "account_status",
            "conformance_pct": 98.0,
            "level": "high",
            "violations": 20,
            "sample_violations": ["unknown", "deleted"],
            "status": "passed"
        },
        {
            "rule": "amount_range",
            "column": "transaction_amount",
            "conformance_pct": 75.5,
            "level": "low",
            "violations": 245,
            "sample_violations": [-50.25, -15.00, 10001.50],
            "status": "failed"
        },
        {
            "rule": "date_iso",
            "column": "created_date",
            "conformance_pct": 96.0,
            "level": "high",
            "violations": 40,
            "sample_violations": ["1/15/2025", "12-25-2024"],
            "status": "passed"
        }
    ]
