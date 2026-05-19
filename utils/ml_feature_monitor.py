"""
ML Feature Monitoring Module for DataPulse
Training/serving skew detection, feature drift, and feature store monitoring
Aligned with Brightspeed Requirements Section 15
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from scipy import stats


class FeatureType(Enum):
    """Types of ML features"""
    NUMERICAL = "numerical"
    CATEGORICAL = "categorical"
    BINARY = "binary"
    EMBEDDING = "embedding"
    TEXT = "text"


class DriftSeverity(Enum):
    """Severity of detected drift"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FeatureDefinition:
    """Defines a monitored ML feature"""
    name: str
    feature_type: FeatureType
    description: str
    importance_score: float  # 0-1, higher = more important
    expected_range: Optional[Tuple[float, float]]
    expected_categories: Optional[List[str]]
    null_allowed: bool
    model_name: str


@dataclass
class FeatureDriftResult:
    """Result of feature drift analysis"""
    feature_name: str
    check_time: str
    
    # Distribution comparison
    training_mean: Optional[float]
    serving_mean: Optional[float]
    training_std: Optional[float]
    serving_std: Optional[float]
    
    # Drift metrics
    psi: Optional[float]  # Population Stability Index
    ks_statistic: Optional[float]  # Kolmogorov-Smirnov
    js_divergence: Optional[float]  # Jensen-Shannon
    
    # Categorical drift
    chi_square_stat: Optional[float]
    chi_square_pval: Optional[float]
    missing_categories: List[str]
    new_categories: List[str]
    
    # Assessment
    drift_detected: bool
    drift_severity: DriftSeverity
    issues: List[str]


@dataclass
class TrainingServingSkew:
    """Detected skew between training and serving data"""
    feature_name: str
    skew_type: str  # distribution, schema, null_rate, cardinality
    training_value: Any
    serving_value: Any
    difference: float
    severity: DriftSeverity
    recommendation: str


class MLFeatureMonitor:
    """Monitor ML features for drift and skew"""
    
    def __init__(self):
        self.features: Dict[str, FeatureDefinition] = {}
        self.training_baselines: Dict[str, Dict] = {}
        self.drift_history: List[FeatureDriftResult] = []
        self.skew_alerts: List[TrainingServingSkew] = []
    
    def register_feature(self, feature: FeatureDefinition):
        """Register a feature for monitoring"""
        self.features[feature.name] = feature
    
    def set_training_baseline(
        self,
        feature_name: str,
        training_data: pd.Series,
        compute_stats: bool = True
    ):
        """Set baseline from training data"""
        
        baseline = {
            "set_at": datetime.now().isoformat(),
            "sample_size": len(training_data),
            "raw_data": training_data.tolist()[:10000]  # Store sample
        }
        
        if compute_stats:
            feature = self.features.get(feature_name)
            
            if feature and feature.feature_type == FeatureType.NUMERICAL:
                baseline.update({
                    "mean": float(training_data.mean()),
                    "std": float(training_data.std()),
                    "min": float(training_data.min()),
                    "max": float(training_data.max()),
                    "median": float(training_data.median()),
                    "null_rate": float(training_data.isna().mean()),
                    "histogram": np.histogram(training_data.dropna(), bins=20)[0].tolist()
                })
            
            elif feature and feature.feature_type == FeatureType.CATEGORICAL:
                value_counts = training_data.value_counts(normalize=True)
                baseline.update({
                    "categories": value_counts.index.tolist(),
                    "category_frequencies": value_counts.values.tolist(),
                    "null_rate": float(training_data.isna().mean()),
                    "cardinality": int(training_data.nunique())
                })
            
            elif feature and feature.feature_type == FeatureType.BINARY:
                baseline.update({
                    "positive_rate": float(training_data.mean()),
                    "null_rate": float(training_data.isna().mean())
                })
        
        self.training_baselines[feature_name] = baseline
    
    def calculate_psi(
        self,
        training_dist: List[float],
        serving_dist: List[float]
    ) -> float:
        """Calculate Population Stability Index"""
        
        # Ensure same number of bins
        if len(training_dist) != len(serving_dist):
            return -1
        
        psi = 0
        for i in range(len(training_dist)):
            # Add small value to avoid log(0)
            t = max(training_dist[i], 0.0001)
            s = max(serving_dist[i], 0.0001)
            psi += (s - t) * np.log(s / t)
        
        return abs(psi)
    
    def check_feature_drift(
        self,
        feature_name: str,
        serving_data: pd.Series
    ) -> FeatureDriftResult:
        """Check for drift between training baseline and serving data"""
        
        if feature_name not in self.features:
            raise ValueError(f"Feature '{feature_name}' not registered")
        
        if feature_name not in self.training_baselines:
            raise ValueError(f"No training baseline set for '{feature_name}'")
        
        feature = self.features[feature_name]
        baseline = self.training_baselines[feature_name]
        issues = []
        
        result = FeatureDriftResult(
            feature_name=feature_name,
            check_time=datetime.now().isoformat(),
            training_mean=None,
            serving_mean=None,
            training_std=None,
            serving_std=None,
            psi=None,
            ks_statistic=None,
            js_divergence=None,
            chi_square_stat=None,
            chi_square_pval=None,
            missing_categories=[],
            new_categories=[],
            drift_detected=False,
            drift_severity=DriftSeverity.NONE,
            issues=[]
        )
        
        if feature.feature_type == FeatureType.NUMERICAL:
            # Compare distributions
            result.training_mean = baseline.get("mean")
            result.serving_mean = float(serving_data.mean())
            result.training_std = baseline.get("std")
            result.serving_std = float(serving_data.std())
            
            # KS test
            if "raw_data" in baseline:
                training_sample = np.array(baseline["raw_data"])
                serving_sample = serving_data.dropna().values
                
                ks_stat, ks_pval = stats.ks_2samp(training_sample, serving_sample)
                result.ks_statistic = float(ks_stat)
                
                if ks_pval < 0.05:
                    issues.append(f"KS test indicates distribution shift (stat={ks_stat:.3f})")
            
            # PSI
            if "histogram" in baseline:
                serving_hist = np.histogram(serving_data.dropna(), bins=20)[0]
                training_hist = np.array(baseline["histogram"])
                
                # Normalize
                training_dist = training_hist / (training_hist.sum() + 0.001)
                serving_dist = serving_hist / (serving_hist.sum() + 0.001)
                
                psi = self.calculate_psi(training_dist.tolist(), serving_dist.tolist())
                result.psi = float(psi)
                
                if psi > 0.25:
                    issues.append(f"High PSI indicates significant drift (PSI={psi:.3f})")
                elif psi > 0.1:
                    issues.append(f"Moderate PSI detected (PSI={psi:.3f})")
            
            # Mean shift
            if result.training_mean and result.training_std:
                mean_shift = abs(result.serving_mean - result.training_mean) / (result.training_std + 0.001)
                if mean_shift > 2:
                    issues.append(f"Mean shifted by {mean_shift:.1f} standard deviations")
        
        elif feature.feature_type == FeatureType.CATEGORICAL:
            training_cats = set(baseline.get("categories", []))
            serving_cats = set(serving_data.dropna().unique())
            
            result.missing_categories = list(training_cats - serving_cats)
            result.new_categories = list(serving_cats - training_cats)
            
            if result.missing_categories:
                issues.append(f"Missing categories: {result.missing_categories[:5]}")
            if result.new_categories:
                issues.append(f"New categories appeared: {result.new_categories[:5]}")
            
            # Chi-square test on overlapping categories
            common_cats = training_cats & serving_cats
            if len(common_cats) >= 2:
                training_freq = dict(zip(baseline["categories"], baseline["category_frequencies"]))
                serving_freq = serving_data.value_counts(normalize=True).to_dict()
                
                observed = [serving_freq.get(c, 0) for c in common_cats]
                expected = [training_freq.get(c, 0) for c in common_cats]
                
                # Normalize
                obs_sum = sum(observed) + 0.001
                exp_sum = sum(expected) + 0.001
                observed = [o / obs_sum for o in observed]
                expected = [e / exp_sum for e in expected]
                
                # Chi-square (simplified)
                chi2 = sum((o - e) ** 2 / (e + 0.0001) for o, e in zip(observed, expected))
                result.chi_square_stat = float(chi2)
                
                if chi2 > 20:
                    issues.append(f"Category distribution shifted significantly (chi2={chi2:.1f})")
        
        # Determine severity
        result.issues = issues
        if len(issues) == 0:
            result.drift_severity = DriftSeverity.NONE
            result.drift_detected = False
        elif len(issues) == 1:
            result.drift_severity = DriftSeverity.LOW
            result.drift_detected = True
        elif len(issues) == 2:
            result.drift_severity = DriftSeverity.MEDIUM
            result.drift_detected = True
        else:
            result.drift_severity = DriftSeverity.HIGH
            result.drift_detected = True
        
        # Elevate based on feature importance
        if result.drift_detected and feature.importance_score >= 0.8:
            if result.drift_severity == DriftSeverity.LOW:
                result.drift_severity = DriftSeverity.MEDIUM
            elif result.drift_severity == DriftSeverity.MEDIUM:
                result.drift_severity = DriftSeverity.HIGH
            elif result.drift_severity == DriftSeverity.HIGH:
                result.drift_severity = DriftSeverity.CRITICAL
        
        self.drift_history.append(result)
        return result
    
    def detect_training_serving_skew(
        self,
        feature_name: str,
        serving_data: pd.Series
    ) -> List[TrainingServingSkew]:
        """Detect skew between training and serving"""
        
        if feature_name not in self.training_baselines:
            return []
        
        baseline = self.training_baselines[feature_name]
        feature = self.features.get(feature_name)
        skews = []
        
        # Null rate skew
        training_null_rate = baseline.get("null_rate", 0)
        serving_null_rate = float(serving_data.isna().mean())
        null_diff = abs(serving_null_rate - training_null_rate)
        
        if null_diff > 0.05:
            severity = DriftSeverity.HIGH if null_diff > 0.2 else (
                DriftSeverity.MEDIUM if null_diff > 0.1 else DriftSeverity.LOW
            )
            skews.append(TrainingServingSkew(
                feature_name=feature_name,
                skew_type="null_rate",
                training_value=training_null_rate,
                serving_value=serving_null_rate,
                difference=null_diff,
                severity=severity,
                recommendation="Investigate data pipeline for null introduction"
            ))
        
        # Cardinality skew (categorical)
        if "cardinality" in baseline:
            training_card = baseline["cardinality"]
            serving_card = int(serving_data.nunique())
            card_ratio = serving_card / (training_card + 0.001)
            
            if card_ratio > 1.5 or card_ratio < 0.5:
                skews.append(TrainingServingSkew(
                    feature_name=feature_name,
                    skew_type="cardinality",
                    training_value=training_card,
                    serving_value=serving_card,
                    difference=abs(serving_card - training_card),
                    severity=DriftSeverity.MEDIUM,
                    recommendation="Check for category explosion or collapse"
                ))
        
        # Range skew (numerical)
        if feature and feature.feature_type == FeatureType.NUMERICAL:
            training_min = baseline.get("min", 0)
            training_max = baseline.get("max", 0)
            serving_min = float(serving_data.min())
            serving_max = float(serving_data.max())
            
            if serving_min < training_min * 0.8 or serving_max > training_max * 1.2:
                skews.append(TrainingServingSkew(
                    feature_name=feature_name,
                    skew_type="range",
                    training_value=f"[{training_min:.2f}, {training_max:.2f}]",
                    serving_value=f"[{serving_min:.2f}, {serving_max:.2f}]",
                    difference=max(training_min - serving_min, serving_max - training_max),
                    severity=DriftSeverity.MEDIUM,
                    recommendation="Values outside training range may cause prediction issues"
                ))
        
        self.skew_alerts.extend(skews)
        return skews
    
    def get_feature_health_summary(self) -> Dict[str, Any]:
        """Get health summary for all monitored features"""
        
        recent_checks = {}
        for check in reversed(self.drift_history):
            if check.feature_name not in recent_checks:
                recent_checks[check.feature_name] = check
        
        by_severity = {s.value: 0 for s in DriftSeverity}
        for check in recent_checks.values():
            by_severity[check.drift_severity.value] += 1
        
        return {
            "total_features": len(self.features),
            "features_with_baseline": len(self.training_baselines),
            "recent_checks": len(recent_checks),
            "features_with_drift": sum(1 for c in recent_checks.values() if c.drift_detected),
            "by_severity": by_severity,
            "total_skew_alerts": len(self.skew_alerts)
        }


def generate_mock_feature_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generate mock training and serving data for demo"""
    np.random.seed(42)
    n_train = 10000
    n_serve = 1000
    
    # Training data (baseline)
    training = pd.DataFrame({
        "user_age": np.random.normal(35, 10, n_train).clip(18, 80),
        "purchase_amount": np.random.exponential(100, n_train),
        "category": np.random.choice(["A", "B", "C", "D"], n_train, p=[0.4, 0.3, 0.2, 0.1]),
        "is_premium": np.random.choice([0, 1], n_train, p=[0.7, 0.3]),
        "session_count": np.random.poisson(5, n_train)
    })
    
    # Serving data (with drift)
    serving = pd.DataFrame({
        "user_age": np.random.normal(38, 12, n_serve).clip(18, 80),  # Mean shifted
        "purchase_amount": np.random.exponential(120, n_serve),  # Higher amounts
        "category": np.random.choice(["A", "B", "C", "E"], n_serve, p=[0.35, 0.35, 0.15, 0.15]),  # D missing, E new
        "is_premium": np.random.choice([0, 1], n_serve, p=[0.6, 0.4]),  # Higher premium rate
        "session_count": np.random.poisson(7, n_serve)  # Higher engagement
    })
    
    # Add some nulls to serving
    serving.loc[np.random.choice(n_serve, 50), "user_age"] = np.nan
    
    return training, serving


def generate_mock_drift_summary() -> List[Dict]:
    """Generate mock drift summary for demo"""
    return [
        {
            "feature": "user_age",
            "model": "churn_prediction_v2",
            "importance": 0.85,
            "drift_type": "distribution",
            "psi": 0.18,
            "severity": "medium",
            "training_mean": 35.2,
            "serving_mean": 38.1,
            "status": "drifted"
        },
        {
            "feature": "purchase_amount",
            "model": "churn_prediction_v2",
            "importance": 0.72,
            "drift_type": "distribution",
            "psi": 0.31,
            "severity": "high",
            "training_mean": 98.5,
            "serving_mean": 118.3,
            "status": "drifted"
        },
        {
            "feature": "category",
            "model": "churn_prediction_v2",
            "importance": 0.45,
            "drift_type": "categorical",
            "missing_categories": ["D"],
            "new_categories": ["E"],
            "severity": "medium",
            "status": "drifted"
        },
        {
            "feature": "session_count",
            "model": "churn_prediction_v2",
            "importance": 0.38,
            "drift_type": "distribution",
            "psi": 0.05,
            "severity": "none",
            "training_mean": 5.1,
            "serving_mean": 5.3,
            "status": "stable"
        }
    ]
