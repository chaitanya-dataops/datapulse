"""
Statistical Drift Detection Module for DataPulse
Detects distribution changes over time using statistical tests
100% local processing with scipy
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from scipy import stats
from datetime import datetime, timedelta


@dataclass
class DriftResult:
    """Result of drift detection analysis"""
    column: str
    has_drift: bool
    drift_score: float  # 0-100, higher = more drift
    p_value: float
    test_used: str
    baseline_stats: Dict[str, float]
    current_stats: Dict[str, float]
    severity: str  # critical, high, medium, low, none
    recommendation: str


class DriftDetector:
    """Detect statistical drift between baseline and current data"""
    
    def __init__(self, significance_level: float = 0.05):
        self.significance_level = significance_level
    
    def ks_test(self, baseline: pd.Series, current: pd.Series) -> Tuple[float, float]:
        """
        Kolmogorov-Smirnov test for numeric distributions
        Returns (statistic, p_value)
        """
        # Remove nulls
        baseline_clean = baseline.dropna()
        current_clean = current.dropna()
        
        if len(baseline_clean) < 10 or len(current_clean) < 10:
            return 0, 1.0  # Not enough data
        
        statistic, p_value = stats.ks_2samp(baseline_clean, current_clean)
        return statistic, p_value
    
    def chi_square_test(self, baseline: pd.Series, current: pd.Series) -> Tuple[float, float]:
        """
        Chi-square test for categorical distributions
        Returns (statistic, p_value)
        """
        # Get value counts
        baseline_counts = baseline.value_counts()
        current_counts = current.value_counts()
        
        # Align categories
        all_categories = set(baseline_counts.index) | set(current_counts.index)
        
        if len(all_categories) < 2:
            return 0, 1.0  # Not enough categories
        
        baseline_aligned = [baseline_counts.get(cat, 0) for cat in all_categories]
        current_aligned = [current_counts.get(cat, 0) for cat in all_categories]
        
        # Normalize to expected frequencies
        total_baseline = sum(baseline_aligned)
        total_current = sum(current_aligned)
        
        if total_baseline == 0 or total_current == 0:
            return 0, 1.0
        
        # Scale current to baseline size for comparison
        expected = [c * (total_baseline / total_current) for c in current_aligned]
        
        try:
            statistic, p_value = stats.chisquare(baseline_aligned, f_exp=expected)
            return statistic, p_value
        except:
            return 0, 1.0
    
    def population_stability_index(self, baseline: pd.Series, current: pd.Series, 
                                   n_bins: int = 10) -> float:
        """
        Calculate Population Stability Index (PSI)
        PSI < 0.1: No significant change
        PSI 0.1-0.25: Moderate change
        PSI > 0.25: Significant change
        """
        # For numeric data, bin it
        if pd.api.types.is_numeric_dtype(baseline):
            baseline_clean = baseline.dropna()
            current_clean = current.dropna()
            
            if len(baseline_clean) < 10 or len(current_clean) < 10:
                return 0
            
            # Create bins from baseline
            _, bin_edges = pd.cut(baseline_clean, bins=n_bins, retbins=True)
            
            baseline_binned = pd.cut(baseline_clean, bins=bin_edges, include_lowest=True)
            current_binned = pd.cut(current_clean, bins=bin_edges, include_lowest=True)
            
            baseline_counts = baseline_binned.value_counts(normalize=True)
            current_counts = current_binned.value_counts(normalize=True)
        else:
            # For categorical data
            baseline_counts = baseline.value_counts(normalize=True)
            current_counts = current.value_counts(normalize=True)
        
        # Align indices
        all_bins = baseline_counts.index.union(current_counts.index)
        
        psi = 0
        for b in all_bins:
            baseline_pct = baseline_counts.get(b, 0.0001)  # Avoid log(0)
            current_pct = current_counts.get(b, 0.0001)
            
            # PSI formula
            psi += (current_pct - baseline_pct) * np.log(current_pct / baseline_pct)
        
        return abs(psi)
    
    def detect_drift(self, baseline: pd.Series, current: pd.Series, 
                     column_name: str) -> DriftResult:
        """
        Detect drift in a single column
        """
        is_numeric = pd.api.types.is_numeric_dtype(baseline)
        
        # Calculate statistics
        if is_numeric:
            baseline_stats = {
                "mean": float(baseline.mean()),
                "std": float(baseline.std()),
                "median": float(baseline.median()),
                "min": float(baseline.min()),
                "max": float(baseline.max()),
                "null_pct": float(baseline.isna().mean() * 100)
            }
            current_stats = {
                "mean": float(current.mean()),
                "std": float(current.std()),
                "median": float(current.median()),
                "min": float(current.min()),
                "max": float(current.max()),
                "null_pct": float(current.isna().mean() * 100)
            }
            
            # Use KS test for numeric data
            statistic, p_value = self.ks_test(baseline, current)
            test_used = "Kolmogorov-Smirnov"
        else:
            baseline_stats = {
                "unique_count": int(baseline.nunique()),
                "top_value": str(baseline.mode().iloc[0]) if len(baseline.mode()) > 0 else "N/A",
                "null_pct": float(baseline.isna().mean() * 100)
            }
            current_stats = {
                "unique_count": int(current.nunique()),
                "top_value": str(current.mode().iloc[0]) if len(current.mode()) > 0 else "N/A",
                "null_pct": float(current.isna().mean() * 100)
            }
            
            # Use Chi-square test for categorical data
            statistic, p_value = self.chi_square_test(baseline, current)
            test_used = "Chi-Square"
        
        # Calculate PSI
        psi = self.population_stability_index(baseline, current)
        
        # Determine drift
        has_drift = p_value < self.significance_level or psi > 0.1
        
        # Calculate drift score (0-100)
        drift_score = min(100, (1 - p_value) * 50 + min(psi * 200, 50))
        
        # Determine severity
        if psi > 0.25 or p_value < 0.001:
            severity = "critical"
            recommendation = "Immediate investigation required. Distribution has changed significantly."
        elif psi > 0.1 or p_value < 0.01:
            severity = "high"
            recommendation = "Review data source. Significant drift detected."
        elif psi > 0.05 or p_value < self.significance_level:
            severity = "medium"
            recommendation = "Monitor closely. Moderate drift detected."
        elif has_drift:
            severity = "low"
            recommendation = "Minor drift detected. Continue monitoring."
        else:
            severity = "none"
            recommendation = "No significant drift detected."
        
        return DriftResult(
            column=column_name,
            has_drift=has_drift,
            drift_score=round(drift_score, 2),
            p_value=round(p_value, 6),
            test_used=test_used,
            baseline_stats=baseline_stats,
            current_stats=current_stats,
            severity=severity,
            recommendation=recommendation
        )
    
    def detect_drift_dataframe(self, baseline_df: pd.DataFrame, 
                                current_df: pd.DataFrame) -> List[DriftResult]:
        """Detect drift across all columns in a DataFrame"""
        results = []
        
        # Get common columns
        common_cols = set(baseline_df.columns) & set(current_df.columns)
        
        for col in common_cols:
            result = self.detect_drift(baseline_df[col], current_df[col], col)
            results.append(result)
        
        # Sort by drift score descending
        results.sort(key=lambda x: x.drift_score, reverse=True)
        
        return results
    
    def get_drift_summary(self, results: List[DriftResult]) -> Dict[str, Any]:
        """Get summary of drift detection results"""
        drifted = [r for r in results if r.has_drift]
        
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "none": 0}
        for r in results:
            severity_counts[r.severity] += 1
        
        return {
            "total_columns": len(results),
            "columns_with_drift": len(drifted),
            "drift_rate": len(drifted) / len(results) * 100 if results else 0,
            "severity_breakdown": severity_counts,
            "top_drifted": [r.column for r in drifted[:5]],
            "overall_health": (
                "Critical" if severity_counts["critical"] > 0 else
                "Warning" if severity_counts["high"] > 0 else
                "Moderate" if severity_counts["medium"] > 0 else
                "Good"
            )
        }


def generate_mock_drift_data(table_name: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generate mock baseline and current data with some drift"""
    np.random.seed(42)
    n_baseline = 1000
    n_current = 1000
    
    # Baseline data
    baseline = pd.DataFrame({
        "user_id": range(n_baseline),
        "age": np.random.normal(35, 10, n_baseline).astype(int),
        "income": np.random.normal(60000, 15000, n_baseline),
        "score": np.random.uniform(0, 100, n_baseline),
        "category": np.random.choice(["A", "B", "C", "D"], n_baseline, p=[0.4, 0.3, 0.2, 0.1]),
        "status": np.random.choice(["active", "inactive"], n_baseline, p=[0.8, 0.2])
    })
    
    # Current data with drift
    np.random.seed(123)
    current = pd.DataFrame({
        "user_id": range(n_current),
        # Age shifted up (drift)
        "age": np.random.normal(40, 12, n_current).astype(int),
        # Income similar (no drift)
        "income": np.random.normal(61000, 15500, n_current),
        # Score shifted (drift)
        "score": np.random.uniform(20, 100, n_current),
        # Category distribution changed (drift)
        "category": np.random.choice(["A", "B", "C", "D"], n_current, p=[0.2, 0.2, 0.3, 0.3]),
        # Status similar (no drift)
        "status": np.random.choice(["active", "inactive"], n_current, p=[0.75, 0.25])
    })
    
    return baseline, current
