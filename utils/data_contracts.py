"""
Data Contracts Module for DataPulse
Define and enforce data quality SLAs using YAML contracts
100% local processing - no external services
"""

import yaml
import pandas as pd
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class ContractStatus(Enum):
    PASSING = "passing"
    WARNING = "warning"
    FAILING = "failing"
    NOT_EVALUATED = "not_evaluated"


@dataclass
class SLACheck:
    """Result of an SLA check"""
    name: str
    sla_type: str
    expected: Any
    actual: Any
    passed: bool
    message: str
    severity: str  # critical, high, medium, low


@dataclass
class ContractValidation:
    """Full validation result for a data contract"""
    contract_name: str
    table_name: str
    status: ContractStatus
    sla_checks: List[SLACheck]
    passed_count: int
    failed_count: int
    warning_count: int
    overall_score: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class DataContract:
    """
    Data Contract definition and validation
    
    Example YAML structure:
    ```yaml
    contract:
      name: orders_contract
      version: 1.0
      owner: data-team@company.com
      
    dataset:
      name: orders
      schema: analytics
      
    slas:
      freshness:
        max_hours: 24
        severity: critical
        
      completeness:
        min_row_count: 1000
        max_null_pct:
          order_id: 0
          customer_id: 5
          amount: 10
        severity: high
        
      schema:
        required_columns:
          - order_id
          - customer_id
          - amount
          - created_at
        column_types:
          order_id: int
          amount: float
        severity: critical
        
      quality:
        unique_columns:
          - order_id
        range_checks:
          amount:
            min: 0
            max: 100000
        regex_checks:
          email: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
        severity: medium
        
    alerts:
      slack_webhook: https://hooks.slack.com/...
      email: data-alerts@company.com
      on_failure: true
      on_warning: false
    ```
    """
    
    def __init__(self, contract_yaml: str):
        self.config = yaml.safe_load(contract_yaml)
        self.name = self.config.get("contract", {}).get("name", "unnamed")
        self.version = self.config.get("contract", {}).get("version", "1.0")
        self.owner = self.config.get("contract", {}).get("owner", "unknown")
        self.dataset = self.config.get("dataset", {})
        self.slas = self.config.get("slas", {})
        self.alerts = self.config.get("alerts", {})
    
    def validate_freshness(self, last_updated: datetime) -> SLACheck:
        """Check data freshness SLA"""
        freshness_config = self.slas.get("freshness", {})
        max_hours = freshness_config.get("max_hours", 24)
        severity = freshness_config.get("severity", "high")
        
        hours_old = (datetime.now() - last_updated).total_seconds() / 3600
        passed = hours_old <= max_hours
        
        return SLACheck(
            name="Freshness",
            sla_type="freshness",
            expected=f"<= {max_hours} hours",
            actual=f"{hours_old:.1f} hours",
            passed=passed,
            message=f"Data is {hours_old:.1f} hours old (max: {max_hours}h)",
            severity=severity
        )
    
    def validate_completeness(self, df: pd.DataFrame) -> List[SLACheck]:
        """Check completeness SLAs"""
        checks = []
        completeness_config = self.slas.get("completeness", {})
        severity = completeness_config.get("severity", "high")
        
        # Row count check
        min_rows = completeness_config.get("min_row_count")
        if min_rows is not None:
            actual_rows = len(df)
            passed = actual_rows >= min_rows
            checks.append(SLACheck(
                name="Min Row Count",
                sla_type="completeness",
                expected=f">= {min_rows:,}",
                actual=f"{actual_rows:,}",
                passed=passed,
                message=f"Row count: {actual_rows:,} (min: {min_rows:,})",
                severity=severity
            ))
        
        # Max row count check
        max_rows = completeness_config.get("max_row_count")
        if max_rows is not None:
            actual_rows = len(df)
            passed = actual_rows <= max_rows
            checks.append(SLACheck(
                name="Max Row Count",
                sla_type="completeness",
                expected=f"<= {max_rows:,}",
                actual=f"{actual_rows:,}",
                passed=passed,
                message=f"Row count: {actual_rows:,} (max: {max_rows:,})",
                severity=severity
            ))
        
        # Null percentage checks
        max_null_pct = completeness_config.get("max_null_pct", {})
        for col, max_pct in max_null_pct.items():
            if col in df.columns:
                actual_pct = df[col].isna().mean() * 100
                passed = actual_pct <= max_pct
                checks.append(SLACheck(
                    name=f"Null % - {col}",
                    sla_type="completeness",
                    expected=f"<= {max_pct}%",
                    actual=f"{actual_pct:.2f}%",
                    passed=passed,
                    message=f"Column '{col}' null rate: {actual_pct:.2f}% (max: {max_pct}%)",
                    severity=severity
                ))
        
        return checks
    
    def validate_schema(self, df: pd.DataFrame) -> List[SLACheck]:
        """Check schema SLAs"""
        checks = []
        schema_config = self.slas.get("schema", {})
        severity = schema_config.get("severity", "critical")
        
        # Required columns
        required_cols = schema_config.get("required_columns", [])
        for col in required_cols:
            passed = col in df.columns
            checks.append(SLACheck(
                name=f"Required Column - {col}",
                sla_type="schema",
                expected="exists",
                actual="exists" if passed else "missing",
                passed=passed,
                message=f"Column '{col}' {'exists' if passed else 'is MISSING'}",
                severity=severity
            ))
        
        # Column types
        column_types = schema_config.get("column_types", {})
        type_mapping = {
            "int": ["int64", "int32", "Int64", "Int32"],
            "float": ["float64", "float32", "Float64"],
            "string": ["object", "string", "str"],
            "bool": ["bool", "boolean"],
            "datetime": ["datetime64[ns]", "datetime64"]
        }
        
        for col, expected_type in column_types.items():
            if col in df.columns:
                actual_type = str(df[col].dtype)
                expected_types = type_mapping.get(expected_type, [expected_type])
                passed = actual_type in expected_types
                checks.append(SLACheck(
                    name=f"Column Type - {col}",
                    sla_type="schema",
                    expected=expected_type,
                    actual=actual_type,
                    passed=passed,
                    message=f"Column '{col}' type: {actual_type} (expected: {expected_type})",
                    severity=severity
                ))
        
        return checks
    
    def validate_quality(self, df: pd.DataFrame) -> List[SLACheck]:
        """Check data quality SLAs"""
        checks = []
        quality_config = self.slas.get("quality", {})
        severity = quality_config.get("severity", "medium")
        
        # Uniqueness checks
        unique_cols = quality_config.get("unique_columns", [])
        for col in unique_cols:
            if col in df.columns:
                duplicates = df[col].duplicated().sum()
                passed = duplicates == 0
                checks.append(SLACheck(
                    name=f"Unique - {col}",
                    sla_type="quality",
                    expected="0 duplicates",
                    actual=f"{duplicates} duplicates",
                    passed=passed,
                    message=f"Column '{col}' has {duplicates} duplicate values",
                    severity=severity
                ))
        
        # Range checks
        range_checks = quality_config.get("range_checks", {})
        for col, bounds in range_checks.items():
            if col in df.columns:
                min_val = bounds.get("min")
                max_val = bounds.get("max")
                
                violations = 0
                if min_val is not None:
                    violations += (df[col] < min_val).sum()
                if max_val is not None:
                    violations += (df[col] > max_val).sum()
                
                passed = violations == 0
                checks.append(SLACheck(
                    name=f"Range - {col}",
                    sla_type="quality",
                    expected=f"[{min_val}, {max_val}]",
                    actual=f"{violations} violations",
                    passed=passed,
                    message=f"Column '{col}' has {violations} out-of-range values",
                    severity=severity
                ))
        
        return checks
    
    def validate(self, df: pd.DataFrame, 
                 last_updated: Optional[datetime] = None) -> ContractValidation:
        """Run all contract validations"""
        all_checks = []
        
        # Freshness check
        if last_updated and "freshness" in self.slas:
            all_checks.append(self.validate_freshness(last_updated))
        
        # Completeness checks
        if "completeness" in self.slas:
            all_checks.extend(self.validate_completeness(df))
        
        # Schema checks
        if "schema" in self.slas:
            all_checks.extend(self.validate_schema(df))
        
        # Quality checks
        if "quality" in self.slas:
            all_checks.extend(self.validate_quality(df))
        
        # Calculate summary
        passed = sum(1 for c in all_checks if c.passed)
        failed = sum(1 for c in all_checks if not c.passed and c.severity in ["critical", "high"])
        warning = sum(1 for c in all_checks if not c.passed and c.severity in ["medium", "low"])
        
        total = len(all_checks)
        score = (passed / total * 100) if total > 0 else 100
        
        # Determine overall status
        if failed > 0:
            status = ContractStatus.FAILING
        elif warning > 0:
            status = ContractStatus.WARNING
        elif total == 0:
            status = ContractStatus.NOT_EVALUATED
        else:
            status = ContractStatus.PASSING
        
        return ContractValidation(
            contract_name=self.name,
            table_name=self.dataset.get("name", "unknown"),
            status=status,
            sla_checks=all_checks,
            passed_count=passed,
            failed_count=failed,
            warning_count=warning,
            overall_score=round(score, 1)
        )


def get_sample_contract() -> str:
    """Return a sample data contract YAML"""
    return """# DataPulse Data Contract
# Define data quality SLAs for your tables

contract:
  name: orders_contract
  version: "1.0"
  owner: data-team@company.com
  description: "Data quality contract for orders table"

dataset:
  name: orders
  schema: analytics
  database: production

slas:
  # Freshness: Data should be updated within 24 hours
  freshness:
    max_hours: 24
    severity: critical

  # Completeness: Minimum data volume and null thresholds
  completeness:
    min_row_count: 100
    max_null_pct:
      id: 0
      user_id: 0
      amount: 5
      email: 10
    severity: high

  # Schema: Required columns and types
  schema:
    required_columns:
      - id
      - user_id
      - amount
      - status
      - created_at
    column_types:
      id: int
      amount: float
      status: string
    severity: critical

  # Quality: Data validation rules
  quality:
    unique_columns:
      - id
    range_checks:
      amount:
        min: 0
        max: 100000
    severity: medium

alerts:
  on_failure: true
  on_warning: false
"""


def get_contract_templates() -> Dict[str, str]:
    """Return contract templates for common use cases"""
    return {
        "Basic Table": """contract:
  name: basic_table_contract
  version: "1.0"
  owner: your-team@company.com

dataset:
  name: your_table
  schema: public

slas:
  completeness:
    min_row_count: 1
    max_null_pct:
      id: 0
    severity: high
      
  schema:
    required_columns:
      - id
    severity: critical
""",
        "Transactional Data": """contract:
  name: transactions_contract
  version: "1.0"
  owner: finance-team@company.com

dataset:
  name: transactions
  schema: finance

slas:
  freshness:
    max_hours: 1
    severity: critical
    
  completeness:
    min_row_count: 1000
    max_null_pct:
      transaction_id: 0
      amount: 0
      timestamp: 0
    severity: critical
      
  schema:
    required_columns:
      - transaction_id
      - amount
      - timestamp
      - status
    column_types:
      amount: float
      transaction_id: int
    severity: critical
    
  quality:
    unique_columns:
      - transaction_id
    range_checks:
      amount:
        min: 0
    severity: high
""",
        "User Data": """contract:
  name: users_contract
  version: "1.0"
  owner: data-team@company.com

dataset:
  name: users
  schema: public

slas:
  freshness:
    max_hours: 24
    severity: high
    
  completeness:
    min_row_count: 100
    max_null_pct:
      user_id: 0
      email: 0
      created_at: 0
    severity: high
      
  schema:
    required_columns:
      - user_id
      - email
      - name
      - created_at
    column_types:
      user_id: int
    severity: critical
    
  quality:
    unique_columns:
      - user_id
      - email
    severity: critical
""",
        "Analytics Aggregate": """contract:
  name: daily_metrics_contract
  version: "1.0"
  owner: analytics-team@company.com

dataset:
  name: daily_metrics
  schema: analytics

slas:
  freshness:
    max_hours: 24
    severity: high
    
  completeness:
    min_row_count: 30  # At least 30 days
    max_row_count: 400  # Cap for daily data
    max_null_pct:
      date: 0
      metric_value: 5
    severity: medium
      
  schema:
    required_columns:
      - date
      - metric_name
      - metric_value
    column_types:
      metric_value: float
    severity: high
    
  quality:
    range_checks:
      metric_value:
        min: 0
    severity: low
"""
    }


def parse_contract_yaml(yaml_str: str) -> Dict[str, Any]:
    """Parse and validate contract YAML"""
    try:
        config = yaml.safe_load(yaml_str)
        
        # Validate required sections
        if "contract" not in config:
            raise ValueError("Missing 'contract' section")
        if "dataset" not in config:
            raise ValueError("Missing 'dataset' section")
        
        return {"valid": True, "config": config, "error": None}
    except yaml.YAMLError as e:
        return {"valid": False, "config": None, "error": f"YAML syntax error: {e}"}
    except ValueError as e:
        return {"valid": False, "config": None, "error": str(e)}
