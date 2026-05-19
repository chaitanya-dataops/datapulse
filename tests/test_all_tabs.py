"""
DataPulse Pre-Deployment Test Suite
Tests all 22 tabs and their dependencies before deployment

Run with: pytest tests/test_all_tabs.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestModuleImports:
    """Test that all required modules can be imported"""
    
    def test_import_mock_data(self):
        from data.mock_data import (
            generate_mock_table_list,
            generate_mock_row_counts,
            generate_mock_null_rates,
        )
        assert True
    
    def test_import_anomaly_detector(self):
        from utils.anomaly_detector import (
            detect_row_count_anomalies,
            detect_null_rate_anomalies,
            get_health_score,
            detect_anomalies_isolation_forest,
            detect_anomalies_dbscan,
        )
        assert True
    
    def test_import_column_profiler(self):
        from utils.column_profiler import profile_column, profile_dataframe
        assert True
    
    def test_import_history_store(self):
        from utils.history_store import HistoryStore, generate_mock_history
        assert True
    
    def test_import_notifications(self):
        from utils.notifications import SlackNotifier, generate_alert_html
        assert True
    
    def test_import_pii_detector(self):
        from utils.pii_detector import scan_dataframe_for_pii
        assert True
    
    def test_import_data_lineage(self):
        from utils.data_lineage import generate_mock_lineage, get_lineage_stats
        assert True
    
    def test_import_sql_rules(self):
        from utils.sql_rules import SQLRulesEngine, get_predefined_rules
        assert True
    
    def test_import_drift_detector(self):
        from utils.drift_detector import DriftDetector, generate_mock_drift_data
        assert True
    
    def test_import_root_cause(self):
        from utils.root_cause import RootCauseAnalyzer, generate_mock_rca_data
        assert True
    
    def test_import_data_contracts(self):
        from utils.data_contracts import DataContract, get_sample_contract
        assert True
    
    def test_import_incident_manager(self):
        from utils.incident_manager import (
            IncidentManager, IncidentStatus, IncidentSeverity,
            generate_mock_incidents
        )
        assert True
    
    def test_import_relationship_quality(self):
        from utils.relationship_quality import (
            RelationshipQualityChecker,
            generate_mock_relationship_data, generate_mock_relationship_checks
        )
        assert True
    
    def test_import_sla_manager(self):
        from utils.sla_manager import (
            SLAManager, Severity,
            generate_mock_sla_data
        )
        assert True
    
    def test_import_predictive_monitor(self):
        from utils.predictive_monitor import (
            PredictiveMonitor, generate_mock_predictions, generate_mock_trend_data
        )
        assert True
    
    def test_import_ml_feature_monitor(self):
        from utils.ml_feature_monitor import (
            MLFeatureMonitor,
            generate_mock_feature_data, generate_mock_drift_summary
        )
        assert True
    
    def test_import_conformance_validator(self):
        from utils.conformance_validator import (
            ConformanceValidator, COMMON_PATTERNS,
            generate_mock_conformance_data, generate_mock_conformance_results
        )
        assert True


class TestTab17Incidents:
    """Tests for Tab 17: Incidents"""
    
    def test_incident_manager_create(self):
        from utils.incident_manager import IncidentManager, IncidentSeverity
        manager = IncidentManager()
        incident = manager.create_incident(
            title="Test Incident",
            description="Test description",
            severity=IncidentSeverity.P3_MEDIUM,
            affected_datasets=["test_table"],
            primary_symptom="Test symptom"
        )
        assert incident is not None
        assert incident.id is not None
        assert incident.title == "Test Incident"
    
    def test_incident_lifecycle(self):
        from utils.incident_manager import IncidentManager, IncidentSeverity, IncidentStatus
        manager = IncidentManager()
        incident = manager.create_incident(
            title="Lifecycle Test",
            description="Testing lifecycle",
            severity=IncidentSeverity.P2_HIGH,
            affected_datasets=["table1"],
            primary_symptom="Data delay"
        )
        
        assert manager.acknowledge_incident(incident.id, "tester")
        assert incident.status == IncidentStatus.ACKNOWLEDGED
        
        assert manager.start_investigation(incident.id, "tester")
        assert incident.status == IncidentStatus.INVESTIGATING
        
        assert manager.resolve_incident(incident.id, "tester", "Fixed")
        assert incident.status == IncidentStatus.RESOLVED
    
    def test_generate_mock_incidents(self):
        from utils.incident_manager import generate_mock_incidents
        incidents = generate_mock_incidents()
        assert isinstance(incidents, list)
        assert len(incidents) > 0
    
    def test_incident_metrics(self):
        from utils.incident_manager import IncidentManager, IncidentSeverity
        manager = IncidentManager()
        manager.create_incident(
            title="Test",
            description="Test",
            severity=IncidentSeverity.P1_CRITICAL,
            affected_datasets=["t1"],
            primary_symptom="Test"
        )
        metrics = manager.get_incident_metrics()
        assert "active_incidents" in metrics


class TestTab18Relationships:
    """Tests for Tab 18: Relationships"""
    
    def test_relationship_quality_checker(self):
        from utils.relationship_quality import RelationshipQualityChecker
        checker = RelationshipQualityChecker()
        assert checker is not None
    
    def test_join_completeness(self):
        from utils.relationship_quality import RelationshipQualityChecker
        checker = RelationshipQualityChecker()
        
        source = pd.DataFrame({"id": [1, 2, 3, 4, 5]})
        target = pd.DataFrame({"id": [1, 2, 3]})
        
        result = checker.check_join_completeness(source, target, "id", "id")
        assert isinstance(result, dict)
        assert "join_completeness_pct" in result
        assert result["join_completeness_pct"] == 60.0
    
    def test_referential_integrity(self):
        from utils.relationship_quality import RelationshipQualityChecker
        checker = RelationshipQualityChecker()
        
        source = pd.DataFrame({"fk": [1, 2, 3, 4, 5]})
        target = pd.DataFrame({"pk": [1, 2, 3]})
        
        result = checker.check_referential_integrity(source, target, "fk", "pk")
        assert "integrity_score" in result
        assert result["broken_references"] == 2
    
    def test_detect_cardinality(self):
        from utils.relationship_quality import RelationshipQualityChecker, RelationshipType
        checker = RelationshipQualityChecker()
        
        source = pd.DataFrame({"id": [1, 1, 2, 2, 3]})  # Not unique
        target = pd.DataFrame({"id": [1, 2, 3]})  # Unique
        
        result = checker.detect_cardinality(source, target, "id", "id")
        assert result["detected_cardinality"] == RelationshipType.MANY_TO_ONE
    
    def test_generate_mock_relationship_data(self):
        from utils.relationship_quality import generate_mock_relationship_data
        customers, orders, items = generate_mock_relationship_data()
        assert len(customers) > 0
        assert len(orders) > 0
        assert len(items) > 0
    
    def test_generate_mock_relationship_checks(self):
        from utils.relationship_quality import generate_mock_relationship_checks
        checks = generate_mock_relationship_checks()
        assert isinstance(checks, list)
        assert len(checks) > 0


class TestTab19SLAEscalation:
    """Tests for Tab 19: SLA & Escalation"""
    
    def test_sla_manager(self):
        from utils.sla_manager import SLAManager
        manager = SLAManager()
        assert manager is not None
    
    def test_severity_classification(self):
        from utils.sla_manager import SLAManager, Severity
        manager = SLAManager()
        
        # High impact should be P1
        severity = manager.classify_severity(
            asset_name="analytics.orders",
            issue_type="freshness",
            impact_score=85,
            affected_downstream=5
        )
        assert severity == Severity.P1
        
        # Low impact should be P4
        severity = manager.classify_severity(
            asset_name="experimental.test",
            issue_type="freshness",
            impact_score=20,
            affected_downstream=0
        )
        assert severity == Severity.P4
    
    def test_sla_compliance_check(self):
        from utils.sla_manager import SLAManager, SLAPolicy
        manager = SLAManager()
        
        policy = SLAPolicy(
            name="test_policy",
            asset_pattern="test\\..*",
            freshness_hours=4,
            null_rate_threshold=0.05,
            volume_deviation_threshold=20,
            p1_response_minutes=15,
            p1_resolution_hours=2,
            p2_response_minutes=30,
            p2_resolution_hours=4,
            p3_response_minutes=60,
            p3_resolution_hours=8,
            p4_response_minutes=240,
            p4_resolution_hours=24,
            owner_team="test-team",
            escalation_chain=["oncall@test.com"]
        )
        manager.register_policy(policy)
        
        # Compliant case
        result = manager.check_sla_compliance(
            "test.table",
            {"last_updated_hours": 2, "null_rate": 0.03}
        )
        assert result["compliant"] == True
        
        # Non-compliant case
        result = manager.check_sla_compliance(
            "test.table",
            {"last_updated_hours": 6, "null_rate": 0.10}
        )
        assert result["compliant"] == False
    
    def test_generate_mock_sla_data(self):
        from utils.sla_manager import generate_mock_sla_data
        data = generate_mock_sla_data()
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_generate_mock_escalation_data(self):
        from utils.sla_manager import generate_mock_escalation_data
        data = generate_mock_escalation_data()
        assert isinstance(data, list)


class TestTab20Predictions:
    """Tests for Tab 20: Predictions"""
    
    def test_predictive_monitor(self):
        from utils.predictive_monitor import PredictiveMonitor
        monitor = PredictiveMonitor()
        assert monitor is not None
    
    def test_simple_forecast(self):
        from utils.predictive_monitor import PredictiveMonitor
        monitor = PredictiveMonitor()
        
        values = [100 + i * 2 + np.random.normal(0, 5) for i in range(50)]
        result = monitor.simple_forecast(values, horizon=24)
        
        assert "forecast" in result
        assert len(result["forecast"]) == 24
        assert "ci_lower" in result
        assert "ci_upper" in result
    
    def test_exponential_smoothing(self):
        from utils.predictive_monitor import PredictiveMonitor
        monitor = PredictiveMonitor()
        
        values = [100 + np.random.normal(0, 10) for _ in range(50)]
        result = monitor.exponential_smoothing_forecast(values, horizon=12)
        
        assert "forecast" in result
        assert len(result["forecast"]) == 12
    
    def test_detect_change_points(self):
        from utils.predictive_monitor import PredictiveMonitor
        monitor = PredictiveMonitor()
        
        # Create data with a clear change point
        values = [100 + np.random.normal(0, 5) for _ in range(50)]
        values.extend([150 + np.random.normal(0, 5) for _ in range(50)])
        
        change_points = monitor.detect_change_points(values)
        assert isinstance(change_points, list)
    
    def test_generate_mock_predictions(self):
        from utils.predictive_monitor import generate_mock_predictions
        predictions = generate_mock_predictions()
        assert isinstance(predictions, list)
        assert len(predictions) > 0
        assert "metric" in predictions[0]
    
    def test_generate_mock_trend_data(self):
        from utils.predictive_monitor import generate_mock_trend_data
        df = generate_mock_trend_data()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "timestamp" in df.columns


class TestTab21MLFeatures:
    """Tests for Tab 21: ML Features"""
    
    def test_ml_feature_monitor(self):
        from utils.ml_feature_monitor import MLFeatureMonitor
        monitor = MLFeatureMonitor()
        assert monitor is not None
    
    def test_psi_calculation(self):
        from utils.ml_feature_monitor import MLFeatureMonitor
        monitor = MLFeatureMonitor()
        
        # Identical distributions = PSI 0
        same_dist = [0.2, 0.3, 0.25, 0.15, 0.1]
        psi = monitor.calculate_psi(same_dist, same_dist)
        assert psi < 0.01
        
        # Different distributions = higher PSI
        training_dist = [0.4, 0.3, 0.2, 0.05, 0.05]
        serving_dist = [0.1, 0.1, 0.3, 0.3, 0.2]
        psi = monitor.calculate_psi(training_dist, serving_dist)
        assert psi > 0.1
    
    def test_generate_mock_feature_data(self):
        from utils.ml_feature_monitor import generate_mock_feature_data
        training, serving = generate_mock_feature_data()
        assert len(training) > 0
        assert len(serving) > 0
        assert list(training.columns) == list(serving.columns)
    
    def test_generate_mock_drift_summary(self):
        from utils.ml_feature_monitor import generate_mock_drift_summary
        summary = generate_mock_drift_summary()
        assert isinstance(summary, list)
        assert len(summary) > 0
        assert "feature" in summary[0]


class TestTab22Conformance:
    """Tests for Tab 22: Conformance"""
    
    def test_conformance_validator(self):
        from utils.conformance_validator import ConformanceValidator
        validator = ConformanceValidator()
        assert validator is not None
    
    def test_pattern_validation(self):
        from utils.conformance_validator import ConformanceValidator, ConformanceRule, ConformanceType
        validator = ConformanceValidator()
        
        rule = ConformanceRule(
            name="email_check",
            column="email",
            conformance_type=ConformanceType.REGEX_PATTERN,
            description="Validate email format",
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        )
        validator.register_rule(rule)
        
        df = pd.DataFrame({
            "email": ["test@example.com", "invalid", "user@test.org"]
        })
        
        result = validator.check_conformance(df, "email_check")
        assert result.conformance_pct == pytest.approx(66.67, rel=0.1)
    
    def test_enum_validation(self):
        from utils.conformance_validator import ConformanceValidator, ConformanceRule, ConformanceType
        validator = ConformanceValidator()
        
        rule = ConformanceRule(
            name="status_check",
            column="status",
            conformance_type=ConformanceType.ENUM_VALUES,
            description="Validate status values",
            allowed_values=["active", "inactive", "pending"]
        )
        validator.register_rule(rule)
        
        df = pd.DataFrame({
            "status": ["active", "inactive", "unknown", "active"]
        })
        
        result = validator.check_conformance(df, "status_check")
        assert result.conformance_pct == 75.0
    
    def test_range_validation(self):
        from utils.conformance_validator import ConformanceValidator, ConformanceRule, ConformanceType
        validator = ConformanceValidator()
        
        rule = ConformanceRule(
            name="age_check",
            column="age",
            conformance_type=ConformanceType.NUMERIC_RANGE,
            description="Age must be 0-120",
            min_value=0,
            max_value=120
        )
        validator.register_rule(rule)
        
        df = pd.DataFrame({"age": [25, 30, 150, -5, 65]})
        result = validator.check_conformance(df, "age_check")
        assert result.conformance_pct == 60.0
    
    def test_common_patterns_exist(self):
        from utils.conformance_validator import COMMON_PATTERNS
        assert "email" in COMMON_PATTERNS
        assert "phone_us" in COMMON_PATTERNS
        assert "uuid" in COMMON_PATTERNS
        assert "ip_v4" in COMMON_PATTERNS
        assert "url" in COMMON_PATTERNS
    
    def test_generate_mock_conformance_data(self):
        from utils.conformance_validator import generate_mock_conformance_data
        df = generate_mock_conformance_data()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
    
    def test_generate_mock_conformance_results(self):
        from utils.conformance_validator import generate_mock_conformance_results
        results = generate_mock_conformance_results()
        assert isinstance(results, list)
        assert len(results) > 0


class TestIntegration:
    """Integration tests"""
    
    def test_all_new_modules_together(self):
        """Test that all new modules work together"""
        from utils.incident_manager import generate_mock_incidents
        from utils.relationship_quality import generate_mock_relationship_checks
        from utils.sla_manager import generate_mock_sla_data
        from utils.predictive_monitor import generate_mock_predictions
        from utils.ml_feature_monitor import generate_mock_drift_summary
        from utils.conformance_validator import generate_mock_conformance_results
        
        # Generate mock data from all new modules
        incidents = generate_mock_incidents()
        relationships = generate_mock_relationship_checks()
        sla_data = generate_mock_sla_data()
        predictions = generate_mock_predictions()
        drift_summary = generate_mock_drift_summary()
        conformance = generate_mock_conformance_results()
        
        assert all([
            len(incidents) > 0,
            len(relationships) > 0,
            len(sla_data) > 0,
            len(predictions) > 0,
            len(drift_summary) > 0,
            len(conformance) > 0
        ])
    
    def test_app_import(self):
        """Test that app.py can be imported without errors"""
        try:
            import app
            assert True
        except Exception as e:
            pytest.fail(f"Failed to import app: {e}")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
