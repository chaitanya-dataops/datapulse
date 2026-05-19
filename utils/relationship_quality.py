"""
Relationship Quality Module for DataPulse
Join completeness, referential integrity, and cardinality monitoring
Aligned with Brightspeed Requirements Section 11
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class RelationshipType(Enum):
    """Types of table relationships"""
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "N:N"


class CardinalityExpectation(Enum):
    """Expected cardinality patterns"""
    EXACT_MATCH = "exact_match"          # Every key should match
    PARTIAL_EXPECTED = "partial_expected" # Some orphans are acceptable
    REFERENCE_ONLY = "reference_only"     # Lookup table, not all keys used


@dataclass
class RelationshipDefinition:
    """Defines a relationship between two tables"""
    name: str
    source_table: str
    source_key: str
    target_table: str
    target_key: str
    relationship_type: RelationshipType
    cardinality_expectation: CardinalityExpectation
    orphan_threshold: float  # Acceptable percentage of orphan records
    description: str


@dataclass
class RelationshipQualityResult:
    """Results from relationship quality check"""
    relationship_name: str
    check_time: str
    
    # Join completeness
    source_row_count: int
    matched_row_count: int
    orphan_row_count: int
    join_completeness_pct: float
    
    # Referential integrity
    broken_references: List[Any]
    integrity_score: float
    
    # Cardinality
    actual_cardinality: RelationshipType
    expected_cardinality: RelationshipType
    cardinality_match: bool
    cardinality_stats: Dict[str, Any]
    
    # Status
    passed: bool
    issues: List[str]


class RelationshipQualityChecker:
    """Check quality of table relationships"""
    
    def __init__(self):
        self.relationships: Dict[str, RelationshipDefinition] = {}
        self.check_history: List[RelationshipQualityResult] = []
    
    def register_relationship(self, relationship: RelationshipDefinition):
        """Register a relationship for monitoring"""
        self.relationships[relationship.name] = relationship
    
    def check_join_completeness(
        self,
        source_df: pd.DataFrame,
        target_df: pd.DataFrame,
        source_key: str,
        target_key: str
    ) -> Dict[str, Any]:
        """Check how many source records can successfully join to target"""
        
        source_keys = set(source_df[source_key].dropna().unique())
        target_keys = set(target_df[target_key].dropna().unique())
        
        matched_keys = source_keys & target_keys
        orphan_keys = source_keys - target_keys
        
        # Count rows, not just unique keys
        source_count = len(source_df)
        matched_count = len(source_df[source_df[source_key].isin(matched_keys)])
        orphan_count = len(source_df[source_df[source_key].isin(orphan_keys)])
        
        completeness_pct = (matched_count / source_count * 100) if source_count > 0 else 100.0
        
        return {
            "source_row_count": source_count,
            "matched_row_count": matched_count,
            "orphan_row_count": orphan_count,
            "unique_source_keys": len(source_keys),
            "unique_target_keys": len(target_keys),
            "matched_key_count": len(matched_keys),
            "orphan_key_count": len(orphan_keys),
            "join_completeness_pct": round(completeness_pct, 2),
            "sample_orphan_keys": list(orphan_keys)[:10]
        }
    
    def check_referential_integrity(
        self,
        source_df: pd.DataFrame,
        target_df: pd.DataFrame,
        source_key: str,
        target_key: str
    ) -> Dict[str, Any]:
        """Check if all foreign key references are valid"""
        
        source_keys = source_df[source_key].dropna().unique()
        target_keys = set(target_df[target_key].dropna().unique())
        
        broken_refs = [k for k in source_keys if k not in target_keys]
        
        integrity_score = (len(source_keys) - len(broken_refs)) / len(source_keys) * 100 if len(source_keys) > 0 else 100.0
        
        return {
            "total_references": len(source_keys),
            "valid_references": len(source_keys) - len(broken_refs),
            "broken_references": len(broken_refs),
            "integrity_score": round(integrity_score, 2),
            "sample_broken_refs": broken_refs[:10]
        }
    
    def detect_cardinality(
        self,
        source_df: pd.DataFrame,
        target_df: pd.DataFrame,
        source_key: str,
        target_key: str
    ) -> Dict[str, Any]:
        """Detect the actual cardinality of the relationship"""
        
        # Check source side (is source key unique?)
        source_unique = source_df[source_key].nunique() == len(source_df)
        
        # Check target side (is target key unique?)
        target_unique = target_df[target_key].nunique() == len(target_df)
        
        # Determine cardinality
        if source_unique and target_unique:
            cardinality = RelationshipType.ONE_TO_ONE
        elif source_unique and not target_unique:
            cardinality = RelationshipType.ONE_TO_MANY
        elif not source_unique and target_unique:
            cardinality = RelationshipType.MANY_TO_ONE
        else:
            cardinality = RelationshipType.MANY_TO_MANY
        
        # Get duplication stats
        source_dupes = source_df[source_key].value_counts()
        target_dupes = target_df[target_key].value_counts()
        
        return {
            "detected_cardinality": cardinality,
            "source_unique": source_unique,
            "target_unique": target_unique,
            "source_key_duplicates": len(source_dupes[source_dupes > 1]) if len(source_dupes) > 0 else 0,
            "target_key_duplicates": len(target_dupes[target_dupes > 1]) if len(target_dupes) > 0 else 0,
            "max_source_duplicates": int(source_dupes.max()) if len(source_dupes) > 0 else 0,
            "max_target_duplicates": int(target_dupes.max()) if len(target_dupes) > 0 else 0,
            "avg_source_cardinality": round(source_dupes.mean(), 2) if len(source_dupes) > 0 else 0,
            "avg_target_cardinality": round(target_dupes.mean(), 2) if len(target_dupes) > 0 else 0
        }
    
    def check_relationship(
        self,
        relationship_name: str,
        source_df: pd.DataFrame,
        target_df: pd.DataFrame
    ) -> RelationshipQualityResult:
        """Run full quality check on a registered relationship"""
        
        if relationship_name not in self.relationships:
            raise ValueError(f"Relationship '{relationship_name}' not registered")
        
        rel = self.relationships[relationship_name]
        issues = []
        
        # Run checks
        join_result = self.check_join_completeness(
            source_df, target_df, rel.source_key, rel.target_key
        )
        
        integrity_result = self.check_referential_integrity(
            source_df, target_df, rel.source_key, rel.target_key
        )
        
        cardinality_result = self.detect_cardinality(
            source_df, target_df, rel.source_key, rel.target_key
        )
        
        # Evaluate against expectations
        orphan_pct = (join_result["orphan_row_count"] / join_result["source_row_count"] * 100) if join_result["source_row_count"] > 0 else 0
        
        if orphan_pct > rel.orphan_threshold:
            issues.append(f"Orphan rate {orphan_pct:.1f}% exceeds threshold {rel.orphan_threshold}%")
        
        if cardinality_result["detected_cardinality"] != rel.relationship_type:
            issues.append(f"Cardinality mismatch: expected {rel.relationship_type.value}, got {cardinality_result['detected_cardinality'].value}")
        
        if integrity_result["integrity_score"] < 95:
            issues.append(f"Referential integrity below 95%: {integrity_result['integrity_score']}%")
        
        result = RelationshipQualityResult(
            relationship_name=relationship_name,
            check_time=datetime.now().isoformat(),
            source_row_count=join_result["source_row_count"],
            matched_row_count=join_result["matched_row_count"],
            orphan_row_count=join_result["orphan_row_count"],
            join_completeness_pct=join_result["join_completeness_pct"],
            broken_references=integrity_result["sample_broken_refs"],
            integrity_score=integrity_result["integrity_score"],
            actual_cardinality=cardinality_result["detected_cardinality"],
            expected_cardinality=rel.relationship_type,
            cardinality_match=cardinality_result["detected_cardinality"] == rel.relationship_type,
            cardinality_stats=cardinality_result,
            passed=len(issues) == 0,
            issues=issues
        )
        
        self.check_history.append(result)
        return result
    
    def get_relationship_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary of all relationships"""
        
        if not self.check_history:
            return {
                "total_relationships": len(self.relationships),
                "checked_relationships": 0,
                "healthy_relationships": 0,
                "issues_detected": 0
            }
        
        recent_checks = {}
        for check in reversed(self.check_history):
            if check.relationship_name not in recent_checks:
                recent_checks[check.relationship_name] = check
        
        healthy = sum(1 for c in recent_checks.values() if c.passed)
        total_issues = sum(len(c.issues) for c in recent_checks.values())
        
        return {
            "total_relationships": len(self.relationships),
            "checked_relationships": len(recent_checks),
            "healthy_relationships": healthy,
            "unhealthy_relationships": len(recent_checks) - healthy,
            "issues_detected": total_issues,
            "avg_join_completeness": round(
                sum(c.join_completeness_pct for c in recent_checks.values()) / len(recent_checks)
                if recent_checks else 0, 2
            ),
            "avg_integrity_score": round(
                sum(c.integrity_score for c in recent_checks.values()) / len(recent_checks)
                if recent_checks else 0, 2
            )
        }


def generate_mock_relationship_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generate mock tables with relationships for demo"""
    np.random.seed(42)
    
    # Customers (parent table)
    customers = pd.DataFrame({
        "customer_id": range(1, 101),
        "name": [f"Customer {i}" for i in range(1, 101)],
        "email": [f"customer{i}@example.com" for i in range(1, 101)]
    })
    
    # Orders (child of customers, parent of order_items)
    orders = pd.DataFrame({
        "order_id": range(1001, 1301),
        "customer_id": np.random.choice(range(1, 110), 300),  # Some orphans (101-109)
        "order_date": pd.date_range(end=datetime.now(), periods=300, freq="H"),
        "total": np.random.uniform(50, 500, 300).round(2)
    })
    
    # Order Items (child of orders)
    order_items = pd.DataFrame({
        "item_id": range(5001, 6001),
        "order_id": np.random.choice(range(1001, 1350), 1000),  # Some orphans (1301-1349)
        "product_name": np.random.choice(["Widget", "Gadget", "Tool", "Part"], 1000),
        "quantity": np.random.randint(1, 10, 1000),
        "price": np.random.uniform(10, 100, 1000).round(2)
    })
    
    return customers, orders, order_items


def generate_mock_relationship_checks() -> List[Dict]:
    """Generate mock relationship check results for demo"""
    return [
        {
            "relationship": "orders -> customers",
            "source": "analytics.orders",
            "target": "analytics.customers",
            "join_completeness": 97.3,
            "integrity_score": 97.3,
            "cardinality": "N:1",
            "expected_cardinality": "N:1",
            "orphan_count": 27,
            "status": "healthy"
        },
        {
            "relationship": "order_items -> orders",
            "source": "analytics.order_items",
            "target": "analytics.orders",
            "join_completeness": 83.5,
            "integrity_score": 83.5,
            "cardinality": "N:1",
            "expected_cardinality": "N:1",
            "orphan_count": 165,
            "status": "warning"
        },
        {
            "relationship": "user_sessions -> users",
            "source": "analytics.user_sessions",
            "target": "analytics.users",
            "join_completeness": 100.0,
            "integrity_score": 100.0,
            "cardinality": "N:1",
            "expected_cardinality": "N:1",
            "orphan_count": 0,
            "status": "healthy"
        }
    ]
