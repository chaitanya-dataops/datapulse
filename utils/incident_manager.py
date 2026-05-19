"""
Incident Management Module for DataPulse
Automated incident creation, lifecycle tracking, correlation, and de-duplication
Aligned with Brightspeed Requirements Section 10
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import json


class IncidentStatus(Enum):
    """Incident lifecycle states"""
    DETECTED = "detected"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentSeverity(Enum):
    """Incident severity levels based on business impact"""
    P1_CRITICAL = "P1"  # Business-critical, executive dashboards affected
    P2_HIGH = "P2"      # Important datasets, SLA-bound
    P3_MEDIUM = "P3"    # Standard datasets, limited impact
    P4_LOW = "P4"       # Non-critical, experimental data


@dataclass
class IncidentEvent:
    """A single event in incident lifecycle"""
    timestamp: str
    action: str
    user: str
    details: str


@dataclass
class Incident:
    """Full incident record with context"""
    id: str
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    
    # Affected assets
    affected_datasets: List[str]
    affected_pipelines: List[str]
    affected_dashboards: List[str]
    affected_consumers: List[str]
    
    # Root cause & symptoms
    primary_symptom: str
    root_cause: Optional[str]
    related_checks: List[str]
    
    # Ownership
    owner: str
    assigned_to: Optional[str]
    
    # Timing
    detected_at: str
    acknowledged_at: Optional[str]
    resolved_at: Optional[str]
    closed_at: Optional[str]
    
    # SLA
    sla_breach_risk: bool
    sla_target_hours: int
    
    # Correlation
    parent_incident_id: Optional[str]  # For correlated incidents
    correlated_incidents: List[str]
    
    # History
    events: List[IncidentEvent] = field(default_factory=list)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "status": self.status.value,
            "affected_datasets": self.affected_datasets,
            "affected_pipelines": self.affected_pipelines,
            "affected_dashboards": self.affected_dashboards,
            "affected_consumers": self.affected_consumers,
            "primary_symptom": self.primary_symptom,
            "root_cause": self.root_cause,
            "owner": self.owner,
            "assigned_to": self.assigned_to,
            "detected_at": self.detected_at,
            "acknowledged_at": self.acknowledged_at,
            "resolved_at": self.resolved_at,
            "sla_breach_risk": self.sla_breach_risk,
            "sla_target_hours": self.sla_target_hours,
            "events": [{"timestamp": e.timestamp, "action": e.action, "user": e.user, "details": e.details} for e in self.events],
            "tags": self.tags
        }


class IncidentManager:
    """Manage incident lifecycle"""
    
    def __init__(self):
        self.incidents: Dict[str, Incident] = {}
        self.incident_history: List[Incident] = []
    
    def create_incident(
        self,
        title: str,
        description: str,
        severity: IncidentSeverity,
        affected_datasets: List[str],
        primary_symptom: str,
        owner: str = "data-team",
        affected_pipelines: List[str] = None,
        affected_dashboards: List[str] = None,
        affected_consumers: List[str] = None,
        related_checks: List[str] = None,
        sla_target_hours: int = 4
    ) -> Incident:
        """Create a new incident with full context"""
        
        incident_id = f"INC-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        incident = Incident(
            id=incident_id,
            title=title,
            description=description,
            severity=severity,
            status=IncidentStatus.DETECTED,
            affected_datasets=affected_datasets,
            affected_pipelines=affected_pipelines or [],
            affected_dashboards=affected_dashboards or [],
            affected_consumers=affected_consumers or [],
            primary_symptom=primary_symptom,
            root_cause=None,
            related_checks=related_checks or [],
            owner=owner,
            assigned_to=None,
            detected_at=datetime.now().isoformat(),
            acknowledged_at=None,
            resolved_at=None,
            closed_at=None,
            sla_breach_risk=False,
            sla_target_hours=sla_target_hours,
            parent_incident_id=None,
            correlated_incidents=[],
            events=[IncidentEvent(
                timestamp=datetime.now().isoformat(),
                action="CREATED",
                user="system",
                details=f"Incident created: {title}"
            )],
            tags=[]
        )
        
        # Check for correlation with existing incidents
        self._correlate_incident(incident)
        
        self.incidents[incident_id] = incident
        return incident
    
    def _correlate_incident(self, incident: Incident):
        """Check if this incident correlates with existing ones"""
        for existing_id, existing in self.incidents.items():
            if existing.status in [IncidentStatus.CLOSED, IncidentStatus.RESOLVED]:
                continue
            
            # Check for overlapping affected datasets
            overlap = set(incident.affected_datasets) & set(existing.affected_datasets)
            if overlap:
                incident.parent_incident_id = existing_id
                existing.correlated_incidents.append(incident.id)
                incident.events.append(IncidentEvent(
                    timestamp=datetime.now().isoformat(),
                    action="CORRELATED",
                    user="system",
                    details=f"Correlated with existing incident {existing_id}"
                ))
                break
    
    def acknowledge_incident(self, incident_id: str, user: str) -> bool:
        """Acknowledge an incident"""
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        incident.status = IncidentStatus.ACKNOWLEDGED
        incident.acknowledged_at = datetime.now().isoformat()
        incident.assigned_to = user
        incident.events.append(IncidentEvent(
            timestamp=datetime.now().isoformat(),
            action="ACKNOWLEDGED",
            user=user,
            details=f"Incident acknowledged by {user}"
        ))
        return True
    
    def start_investigation(self, incident_id: str, user: str) -> bool:
        """Start investigating an incident"""
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        incident.status = IncidentStatus.INVESTIGATING
        incident.events.append(IncidentEvent(
            timestamp=datetime.now().isoformat(),
            action="INVESTIGATING",
            user=user,
            details=f"Investigation started by {user}"
        ))
        return True
    
    def set_root_cause(self, incident_id: str, root_cause: str, user: str) -> bool:
        """Set the root cause for an incident"""
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        incident.root_cause = root_cause
        incident.events.append(IncidentEvent(
            timestamp=datetime.now().isoformat(),
            action="ROOT_CAUSE_IDENTIFIED",
            user=user,
            details=f"Root cause identified: {root_cause}"
        ))
        return True
    
    def mitigate_incident(self, incident_id: str, user: str, mitigation_notes: str) -> bool:
        """Mark incident as mitigated"""
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        incident.status = IncidentStatus.MITIGATED
        incident.events.append(IncidentEvent(
            timestamp=datetime.now().isoformat(),
            action="MITIGATED",
            user=user,
            details=f"Mitigation applied: {mitigation_notes}"
        ))
        return True
    
    def resolve_incident(self, incident_id: str, user: str, resolution_notes: str) -> bool:
        """Resolve an incident"""
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = datetime.now().isoformat()
        incident.events.append(IncidentEvent(
            timestamp=datetime.now().isoformat(),
            action="RESOLVED",
            user=user,
            details=f"Incident resolved: {resolution_notes}"
        ))
        return True
    
    def close_incident(self, incident_id: str, user: str) -> bool:
        """Close an incident"""
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        incident.status = IncidentStatus.CLOSED
        incident.closed_at = datetime.now().isoformat()
        incident.events.append(IncidentEvent(
            timestamp=datetime.now().isoformat(),
            action="CLOSED",
            user=user,
            details="Incident closed"
        ))
        
        # Move to history
        self.incident_history.append(incident)
        return True
    
    def check_sla_breach(self, incident_id: str) -> Dict[str, Any]:
        """Check if incident is at risk of SLA breach"""
        if incident_id not in self.incidents:
            return {"error": "Incident not found"}
        
        incident = self.incidents[incident_id]
        detected = datetime.fromisoformat(incident.detected_at)
        elapsed_hours = (datetime.now() - detected).total_seconds() / 3600
        
        remaining_hours = incident.sla_target_hours - elapsed_hours
        
        if remaining_hours <= 0:
            breach_status = "BREACHED"
            incident.sla_breach_risk = True
        elif remaining_hours <= 1:
            breach_status = "CRITICAL"
            incident.sla_breach_risk = True
        elif remaining_hours <= 2:
            breach_status = "AT_RISK"
            incident.sla_breach_risk = True
        else:
            breach_status = "ON_TRACK"
            incident.sla_breach_risk = False
        
        return {
            "status": breach_status,
            "elapsed_hours": round(elapsed_hours, 2),
            "remaining_hours": round(max(0, remaining_hours), 2),
            "sla_target_hours": incident.sla_target_hours,
            "breach_risk": incident.sla_breach_risk
        }
    
    def get_active_incidents(self) -> List[Incident]:
        """Get all active (non-closed) incidents"""
        return [i for i in self.incidents.values() 
                if i.status not in [IncidentStatus.CLOSED]]
    
    def get_incidents_by_severity(self, severity: IncidentSeverity) -> List[Incident]:
        """Get incidents filtered by severity"""
        return [i for i in self.incidents.values() if i.severity == severity]
    
    def get_incident_metrics(self) -> Dict[str, Any]:
        """Get incident metrics for dashboard"""
        all_incidents = list(self.incidents.values()) + self.incident_history
        active = self.get_active_incidents()
        
        # Calculate MTTR for resolved incidents
        resolved = [i for i in all_incidents if i.resolved_at]
        if resolved:
            mttr_values = []
            for i in resolved:
                detected = datetime.fromisoformat(i.detected_at)
                resolved_time = datetime.fromisoformat(i.resolved_at)
                mttr_values.append((resolved_time - detected).total_seconds() / 3600)
            avg_mttr = sum(mttr_values) / len(mttr_values)
        else:
            avg_mttr = 0
        
        # Count by severity
        severity_counts = {s.value: 0 for s in IncidentSeverity}
        for i in active:
            severity_counts[i.severity.value] += 1
        
        # Count by status
        status_counts = {s.value: 0 for s in IncidentStatus}
        for i in active:
            status_counts[i.status.value] += 1
        
        return {
            "total_incidents": len(all_incidents),
            "active_incidents": len(active),
            "resolved_last_7_days": len([i for i in resolved if i.resolved_at and 
                datetime.fromisoformat(i.resolved_at) > datetime.now() - timedelta(days=7)]),
            "avg_mttr_hours": round(avg_mttr, 2),
            "by_severity": severity_counts,
            "by_status": status_counts,
            "sla_breaches": len([i for i in active if i.sla_breach_risk])
        }


def auto_create_incident_from_anomaly(
    anomaly: Dict[str, Any],
    affected_table: str,
    manager: IncidentManager
) -> Incident:
    """Automatically create incident from detected anomaly"""
    
    # Determine severity based on anomaly characteristics
    severity_score = anomaly.get("severity_score", 50)
    if severity_score >= 80:
        severity = IncidentSeverity.P1_CRITICAL
        sla_hours = 2
    elif severity_score >= 60:
        severity = IncidentSeverity.P2_HIGH
        sla_hours = 4
    elif severity_score >= 40:
        severity = IncidentSeverity.P3_MEDIUM
        sla_hours = 8
    else:
        severity = IncidentSeverity.P4_LOW
        sla_hours = 24
    
    return manager.create_incident(
        title=f"{anomaly.get('type', 'Anomaly')} detected in {affected_table}",
        description=anomaly.get("description", "Anomaly detected by automated monitoring"),
        severity=severity,
        affected_datasets=[affected_table],
        primary_symptom=anomaly.get("symptom", "Data quality degradation"),
        related_checks=[anomaly.get("check_name", "unknown")],
        sla_target_hours=sla_hours
    )


def generate_mock_incidents() -> List[Dict]:
    """Generate mock incident data for demo"""
    return [
        {
            "id": "INC-20260520-A1B2C3D4",
            "title": "Freshness SLA breach - orders table",
            "severity": "P1",
            "status": "investigating",
            "affected_datasets": ["analytics.orders", "analytics.order_items"],
            "detected_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "owner": "data-platform",
            "sla_remaining": "0.5 hours"
        },
        {
            "id": "INC-20260520-E5F6G7H8",
            "title": "Null rate spike - customer_email column",
            "severity": "P2",
            "status": "acknowledged",
            "affected_datasets": ["analytics.customers"],
            "detected_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            "owner": "customer-data",
            "sla_remaining": "3 hours"
        },
        {
            "id": "INC-20260519-I9J0K1L2",
            "title": "Schema change detected - revenue table",
            "severity": "P3",
            "status": "resolved",
            "affected_datasets": ["finance.revenue"],
            "detected_at": (datetime.now() - timedelta(days=1)).isoformat(),
            "owner": "finance-data",
            "sla_remaining": "N/A"
        }
    ]
