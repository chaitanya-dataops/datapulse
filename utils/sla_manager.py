"""
SLA & Escalation Module for DataPulse
Automatic severity classification, SLA enforcement, and escalation rules
Aligned with Brightspeed Requirements Section 9
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json


class Severity(Enum):
    """Severity levels for data quality issues"""
    P1 = "P1"  # Critical - immediate attention
    P2 = "P2"  # High - urgent
    P3 = "P3"  # Medium - standard
    P4 = "P4"  # Low - minor


class EscalationLevel(Enum):
    """Escalation hierarchy"""
    L1_ONCALL = "L1"      # On-call engineer
    L2_TEAM_LEAD = "L2"   # Team lead / Senior engineer
    L3_MANAGER = "L3"     # Engineering manager
    L4_DIRECTOR = "L4"    # Director / VP


@dataclass
class SLAPolicy:
    """Defines SLA expectations for a data asset"""
    name: str
    asset_pattern: str  # Regex pattern for matching assets
    freshness_hours: float
    null_rate_threshold: float
    volume_deviation_threshold: float  # Percentage
    p1_response_minutes: int
    p1_resolution_hours: int
    p2_response_minutes: int
    p2_resolution_hours: int
    p3_response_minutes: int
    p3_resolution_hours: int
    p4_response_minutes: int
    p4_resolution_hours: int
    owner_team: str
    escalation_chain: List[str]


@dataclass
class EscalationRule:
    """Defines when and how to escalate"""
    name: str
    trigger_condition: str  # Description of when to escalate
    time_threshold_minutes: int
    target_level: EscalationLevel
    notification_channels: List[str]  # slack, email, pagerduty, etc.
    message_template: str


@dataclass
class SLAViolation:
    """Tracks an SLA violation"""
    id: str
    asset_name: str
    policy_name: str
    violation_type: str  # response, resolution, metric
    severity: Severity
    detected_at: str
    target_time: str
    actual_time: Optional[str]
    breached: bool
    escalated_to: Optional[EscalationLevel]
    escalation_history: List[Dict] = field(default_factory=list)


class SLAManager:
    """Manage SLA policies and violations"""
    
    def __init__(self):
        self.policies: Dict[str, SLAPolicy] = {}
        self.escalation_rules: Dict[str, EscalationRule] = {}
        self.violations: List[SLAViolation] = []
        self.escalation_callbacks: Dict[EscalationLevel, List[Callable]] = {
            level: [] for level in EscalationLevel
        }
    
    def register_policy(self, policy: SLAPolicy):
        """Register an SLA policy"""
        self.policies[policy.name] = policy
    
    def register_escalation_rule(self, rule: EscalationRule):
        """Register an escalation rule"""
        self.escalation_rules[rule.name] = rule
    
    def register_escalation_callback(
        self, 
        level: EscalationLevel, 
        callback: Callable
    ):
        """Register a callback for escalation notifications"""
        self.escalation_callbacks[level].append(callback)
    
    def classify_severity(
        self,
        asset_name: str,
        issue_type: str,
        impact_score: float,
        affected_downstream: int
    ) -> Severity:
        """Automatically classify severity based on impact"""
        
        # Find matching policy
        policy = self._find_policy(asset_name)
        
        # Base severity from impact score
        if impact_score >= 80:
            base_severity = Severity.P1
        elif impact_score >= 60:
            base_severity = Severity.P2
        elif impact_score >= 40:
            base_severity = Severity.P3
        else:
            base_severity = Severity.P4
        
        # Elevate based on downstream impact
        if affected_downstream >= 10 and base_severity != Severity.P1:
            # Elevate by one level
            severity_order = [Severity.P4, Severity.P3, Severity.P2, Severity.P1]
            current_idx = severity_order.index(base_severity)
            base_severity = severity_order[min(current_idx + 1, 3)]
        
        # Special rules for critical asset types
        critical_patterns = ["revenue", "billing", "payment", "customer"]
        if any(p in asset_name.lower() for p in critical_patterns):
            if base_severity in [Severity.P3, Severity.P4]:
                base_severity = Severity.P2
        
        return base_severity
    
    def _find_policy(self, asset_name: str) -> Optional[SLAPolicy]:
        """Find the best matching policy for an asset"""
        import re
        for policy in self.policies.values():
            if re.match(policy.asset_pattern, asset_name):
                return policy
        return None
    
    def check_sla_compliance(
        self,
        asset_name: str,
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if asset metrics comply with SLA"""
        
        policy = self._find_policy(asset_name)
        if not policy:
            return {
                "asset": asset_name,
                "has_policy": False,
                "compliant": None,
                "message": "No SLA policy found for this asset"
            }
        
        violations = []
        
        # Check freshness
        if "last_updated_hours" in metrics:
            if metrics["last_updated_hours"] > policy.freshness_hours:
                violations.append({
                    "type": "freshness",
                    "expected": f"<{policy.freshness_hours} hours",
                    "actual": f"{metrics['last_updated_hours']} hours"
                })
        
        # Check null rate
        if "null_rate" in metrics:
            if metrics["null_rate"] > policy.null_rate_threshold:
                violations.append({
                    "type": "null_rate",
                    "expected": f"<{policy.null_rate_threshold}%",
                    "actual": f"{metrics['null_rate']}%"
                })
        
        # Check volume
        if "volume_deviation" in metrics:
            if abs(metrics["volume_deviation"]) > policy.volume_deviation_threshold:
                violations.append({
                    "type": "volume",
                    "expected": f"within {policy.volume_deviation_threshold}%",
                    "actual": f"{metrics['volume_deviation']}% deviation"
                })
        
        return {
            "asset": asset_name,
            "policy": policy.name,
            "has_policy": True,
            "compliant": len(violations) == 0,
            "violations": violations,
            "owner_team": policy.owner_team
        }
    
    def get_response_sla(self, severity: Severity, policy_name: str) -> int:
        """Get response time SLA in minutes"""
        if policy_name not in self.policies:
            # Default SLAs
            defaults = {
                Severity.P1: 15,
                Severity.P2: 30,
                Severity.P3: 60,
                Severity.P4: 240
            }
            return defaults.get(severity, 60)
        
        policy = self.policies[policy_name]
        sla_map = {
            Severity.P1: policy.p1_response_minutes,
            Severity.P2: policy.p2_response_minutes,
            Severity.P3: policy.p3_response_minutes,
            Severity.P4: policy.p4_response_minutes
        }
        return sla_map.get(severity, 60)
    
    def get_resolution_sla(self, severity: Severity, policy_name: str) -> int:
        """Get resolution time SLA in hours"""
        if policy_name not in self.policies:
            # Default SLAs
            defaults = {
                Severity.P1: 2,
                Severity.P2: 4,
                Severity.P3: 8,
                Severity.P4: 24
            }
            return defaults.get(severity, 8)
        
        policy = self.policies[policy_name]
        sla_map = {
            Severity.P1: policy.p1_resolution_hours,
            Severity.P2: policy.p2_resolution_hours,
            Severity.P3: policy.p3_resolution_hours,
            Severity.P4: policy.p4_resolution_hours
        }
        return sla_map.get(severity, 8)
    
    def should_escalate(
        self,
        issue_created_at: datetime,
        current_level: EscalationLevel,
        severity: Severity
    ) -> Optional[EscalationLevel]:
        """Determine if issue should be escalated"""
        
        elapsed_minutes = (datetime.now() - issue_created_at).total_seconds() / 60
        
        # Escalation thresholds by severity
        escalation_times = {
            Severity.P1: {
                EscalationLevel.L1_ONCALL: 15,
                EscalationLevel.L2_TEAM_LEAD: 30,
                EscalationLevel.L3_MANAGER: 60,
                EscalationLevel.L4_DIRECTOR: 120
            },
            Severity.P2: {
                EscalationLevel.L1_ONCALL: 30,
                EscalationLevel.L2_TEAM_LEAD: 60,
                EscalationLevel.L3_MANAGER: 180,
                EscalationLevel.L4_DIRECTOR: 480
            },
            Severity.P3: {
                EscalationLevel.L1_ONCALL: 60,
                EscalationLevel.L2_TEAM_LEAD: 240,
                EscalationLevel.L3_MANAGER: 480,
                EscalationLevel.L4_DIRECTOR: None  # Don't escalate
            },
            Severity.P4: {
                EscalationLevel.L1_ONCALL: 240,
                EscalationLevel.L2_TEAM_LEAD: 480,
                EscalationLevel.L3_MANAGER: None,
                EscalationLevel.L4_DIRECTOR: None
            }
        }
        
        thresholds = escalation_times.get(severity, {})
        level_order = [
            EscalationLevel.L1_ONCALL,
            EscalationLevel.L2_TEAM_LEAD,
            EscalationLevel.L3_MANAGER,
            EscalationLevel.L4_DIRECTOR
        ]
        
        current_idx = level_order.index(current_level)
        
        # Check if next level escalation is needed
        for next_level in level_order[current_idx + 1:]:
            threshold = thresholds.get(next_level)
            if threshold is not None and elapsed_minutes >= threshold:
                return next_level
        
        return None
    
    def escalate(
        self,
        violation_id: str,
        target_level: EscalationLevel,
        reason: str
    ):
        """Perform escalation"""
        for v in self.violations:
            if v.id == violation_id:
                v.escalated_to = target_level
                v.escalation_history.append({
                    "level": target_level.value,
                    "timestamp": datetime.now().isoformat(),
                    "reason": reason
                })
                
                # Trigger callbacks
                for callback in self.escalation_callbacks[target_level]:
                    try:
                        callback(v, reason)
                    except Exception:
                        pass  # Log error in production
                
                return True
        return False
    
    def get_sla_dashboard_metrics(self) -> Dict[str, Any]:
        """Get metrics for SLA dashboard"""
        
        total = len(self.violations)
        breached = len([v for v in self.violations if v.breached])
        
        # By severity
        by_severity = {s.value: 0 for s in Severity}
        for v in self.violations:
            by_severity[v.severity.value] += 1
        
        # By type
        by_type = {}
        for v in self.violations:
            by_type[v.violation_type] = by_type.get(v.violation_type, 0) + 1
        
        return {
            "total_violations": total,
            "breached": breached,
            "compliance_rate": round((total - breached) / total * 100, 1) if total > 0 else 100.0,
            "by_severity": by_severity,
            "by_type": by_type,
            "active_escalations": len([v for v in self.violations if v.escalated_to])
        }


def generate_default_sla_policies() -> List[SLAPolicy]:
    """Generate standard SLA policies"""
    return [
        SLAPolicy(
            name="critical-revenue",
            asset_pattern=".*revenue.*|.*billing.*|.*payment.*",
            freshness_hours=1,
            null_rate_threshold=0.01,
            volume_deviation_threshold=10,
            p1_response_minutes=15,
            p1_resolution_hours=2,
            p2_response_minutes=30,
            p2_resolution_hours=4,
            p3_response_minutes=60,
            p3_resolution_hours=8,
            p4_response_minutes=240,
            p4_resolution_hours=24,
            owner_team="finance-data",
            escalation_chain=["oncall@company.com", "data-lead@company.com", "data-director@company.com"]
        ),
        SLAPolicy(
            name="standard-analytics",
            asset_pattern="analytics\\..*",
            freshness_hours=4,
            null_rate_threshold=0.05,
            volume_deviation_threshold=20,
            p1_response_minutes=30,
            p1_resolution_hours=4,
            p2_response_minutes=60,
            p2_resolution_hours=8,
            p3_response_minutes=120,
            p3_resolution_hours=24,
            p4_response_minutes=480,
            p4_resolution_hours=72,
            owner_team="analytics",
            escalation_chain=["analytics-oncall@company.com", "analytics-lead@company.com"]
        ),
        SLAPolicy(
            name="experimental",
            asset_pattern="experimental\\..*|sandbox\\..*",
            freshness_hours=24,
            null_rate_threshold=0.20,
            volume_deviation_threshold=50,
            p1_response_minutes=120,
            p1_resolution_hours=24,
            p2_response_minutes=240,
            p2_resolution_hours=48,
            p3_response_minutes=480,
            p3_resolution_hours=72,
            p4_response_minutes=1440,
            p4_resolution_hours=168,
            owner_team="data-science",
            escalation_chain=["ds-team@company.com"]
        )
    ]


def generate_mock_sla_data() -> List[Dict]:
    """Generate mock SLA compliance data for demo"""
    return [
        {
            "asset": "analytics.orders",
            "policy": "standard-analytics",
            "freshness_sla": "4 hours",
            "actual_freshness": "2.3 hours",
            "null_rate_sla": "5%",
            "actual_null_rate": "1.2%",
            "status": "compliant",
            "owner": "analytics"
        },
        {
            "asset": "finance.revenue",
            "policy": "critical-revenue",
            "freshness_sla": "1 hour",
            "actual_freshness": "1.5 hours",
            "null_rate_sla": "1%",
            "actual_null_rate": "0.1%",
            "status": "at_risk",
            "owner": "finance-data"
        },
        {
            "asset": "analytics.customers",
            "policy": "standard-analytics",
            "freshness_sla": "4 hours",
            "actual_freshness": "6.2 hours",
            "null_rate_sla": "5%",
            "actual_null_rate": "2.1%",
            "status": "breached",
            "owner": "analytics"
        }
    ]


def generate_mock_escalation_data() -> List[Dict]:
    """Generate mock escalation data for demo"""
    return [
        {
            "incident_id": "INC-001",
            "severity": "P1",
            "current_level": "L2",
            "elapsed_time": "45 min",
            "next_escalation": "L3 in 15 min",
            "assignee": "John Doe",
            "status": "investigating"
        },
        {
            "incident_id": "INC-002",
            "severity": "P2",
            "current_level": "L1",
            "elapsed_time": "20 min",
            "next_escalation": "L2 in 10 min",
            "assignee": "Jane Smith",
            "status": "acknowledged"
        }
    ]
