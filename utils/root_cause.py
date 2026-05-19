"""
Root Cause Analysis Module for DataPulse
Automatically identify why anomalies occurred
100% local processing
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from scipy import stats


@dataclass
class RootCause:
    """A potential root cause for an anomaly"""
    dimension: str
    value: str
    contribution: float  # Percentage contribution to anomaly
    baseline_value: float
    current_value: float
    change_pct: float
    confidence: str  # high, medium, low
    explanation: str


@dataclass
class RCAResult:
    """Result of root cause analysis"""
    anomaly_type: str
    metric: str
    anomaly_value: float
    expected_value: float
    deviation_pct: float
    root_causes: List[RootCause]
    summary: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class RootCauseAnalyzer:
    """Analyze anomalies to identify root causes"""
    
    def __init__(self):
        self.analysis_history: List[RCAResult] = []
    
    def analyze_metric_by_dimension(
        self,
        baseline_df: pd.DataFrame,
        current_df: pd.DataFrame,
        metric_col: str,
        dimension_col: str,
        agg_func: str = "sum"
    ) -> List[RootCause]:
        """
        Analyze how a metric changed across a dimension
        """
        root_causes = []
        
        # Aggregate by dimension
        if agg_func == "sum":
            baseline_agg = baseline_df.groupby(dimension_col)[metric_col].sum()
            current_agg = current_df.groupby(dimension_col)[metric_col].sum()
        elif agg_func == "mean":
            baseline_agg = baseline_df.groupby(dimension_col)[metric_col].mean()
            current_agg = current_df.groupby(dimension_col)[metric_col].mean()
        elif agg_func == "count":
            baseline_agg = baseline_df.groupby(dimension_col)[metric_col].count()
            current_agg = current_df.groupby(dimension_col)[metric_col].count()
        else:
            baseline_agg = baseline_df.groupby(dimension_col)[metric_col].sum()
            current_agg = current_df.groupby(dimension_col)[metric_col].sum()
        
        # Calculate total change
        total_baseline = baseline_agg.sum()
        total_current = current_agg.sum()
        total_change = total_current - total_baseline
        
        if abs(total_change) < 0.001:
            return root_causes  # No significant change
        
        # Analyze each dimension value
        all_values = set(baseline_agg.index) | set(current_agg.index)
        
        for value in all_values:
            baseline_val = baseline_agg.get(value, 0)
            current_val = current_agg.get(value, 0)
            change = current_val - baseline_val
            
            if baseline_val > 0:
                change_pct = (change / baseline_val) * 100
            elif current_val > 0:
                change_pct = 100  # New value appeared
            else:
                change_pct = 0
            
            # Contribution to total change
            contribution = (change / total_change * 100) if total_change != 0 else 0
            
            # Only include significant contributors
            if abs(contribution) >= 5 or abs(change_pct) >= 20:
                # Determine confidence
                if abs(contribution) >= 30:
                    confidence = "high"
                elif abs(contribution) >= 15:
                    confidence = "medium"
                else:
                    confidence = "low"
                
                # Generate explanation
                if change > 0:
                    direction = "increased"
                else:
                    direction = "decreased"
                
                explanation = (
                    f"{dimension_col}='{value}' {direction} by {abs(change_pct):.1f}%, "
                    f"contributing {abs(contribution):.1f}% to the overall change"
                )
                
                root_causes.append(RootCause(
                    dimension=dimension_col,
                    value=str(value),
                    contribution=round(contribution, 2),
                    baseline_value=round(baseline_val, 2),
                    current_value=round(current_val, 2),
                    change_pct=round(change_pct, 2),
                    confidence=confidence,
                    explanation=explanation
                ))
        
        # Sort by absolute contribution
        root_causes.sort(key=lambda x: abs(x.contribution), reverse=True)
        
        return root_causes[:10]  # Top 10 causes
    
    def analyze_anomaly(
        self,
        baseline_df: pd.DataFrame,
        current_df: pd.DataFrame,
        metric_col: str,
        dimension_cols: List[str],
        anomaly_type: str = "value_change"
    ) -> RCAResult:
        """
        Perform full root cause analysis on an anomaly
        """
        # Calculate overall anomaly
        if metric_col in baseline_df.columns and metric_col in current_df.columns:
            expected = baseline_df[metric_col].sum()
            actual = current_df[metric_col].sum()
        else:
            expected = len(baseline_df)
            actual = len(current_df)
        
        deviation_pct = ((actual - expected) / expected * 100) if expected != 0 else 0
        
        # Analyze each dimension
        all_causes = []
        for dim_col in dimension_cols:
            if dim_col in baseline_df.columns and dim_col in current_df.columns:
                causes = self.analyze_metric_by_dimension(
                    baseline_df, current_df, metric_col, dim_col
                )
                all_causes.extend(causes)
        
        # Sort all causes by contribution
        all_causes.sort(key=lambda x: abs(x.contribution), reverse=True)
        top_causes = all_causes[:5]
        
        # Generate summary
        if top_causes:
            main_cause = top_causes[0]
            summary = (
                f"The {anomaly_type} anomaly is primarily driven by "
                f"{main_cause.dimension}='{main_cause.value}' "
                f"({main_cause.change_pct:+.1f}% change, "
                f"{abs(main_cause.contribution):.1f}% contribution)"
            )
        else:
            summary = "No significant root causes identified. The change appears distributed across all segments."
        
        result = RCAResult(
            anomaly_type=anomaly_type,
            metric=metric_col,
            anomaly_value=round(actual, 2),
            expected_value=round(expected, 2),
            deviation_pct=round(deviation_pct, 2),
            root_causes=top_causes,
            summary=summary
        )
        
        self.analysis_history.append(result)
        return result
    
    def correlate_columns(
        self,
        df: pd.DataFrame,
        target_col: str,
        candidate_cols: List[str]
    ) -> List[Tuple[str, float]]:
        """
        Find columns most correlated with anomalous column
        """
        correlations = []
        
        if target_col not in df.columns:
            return correlations
        
        target = df[target_col]
        
        for col in candidate_cols:
            if col not in df.columns or col == target_col:
                continue
            
            try:
                if pd.api.types.is_numeric_dtype(df[col]):
                    # Pearson correlation for numeric
                    corr, _ = stats.pearsonr(
                        target.dropna(),
                        df[col].loc[target.dropna().index].dropna()
                    )
                else:
                    # Use ANOVA for categorical
                    groups = [target[df[col] == val].dropna() for val in df[col].unique()]
                    groups = [g for g in groups if len(g) > 0]
                    if len(groups) >= 2:
                        f_stat, p_value = stats.f_oneway(*groups)
                        corr = 1 - p_value  # Convert to correlation-like score
                    else:
                        corr = 0
                
                if not np.isnan(corr):
                    correlations.append((col, abs(corr)))
            except:
                continue
        
        correlations.sort(key=lambda x: x[1], reverse=True)
        return correlations[:10]


def generate_mock_rca_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generate mock data for RCA demo"""
    np.random.seed(42)
    
    regions = ["North", "South", "East", "West"]
    products = ["A", "B", "C", "D"]
    channels = ["Online", "Retail", "Wholesale"]
    
    n = 1000
    
    # Baseline - normal distribution
    baseline = pd.DataFrame({
        "region": np.random.choice(regions, n, p=[0.3, 0.25, 0.25, 0.2]),
        "product": np.random.choice(products, n, p=[0.3, 0.3, 0.25, 0.15]),
        "channel": np.random.choice(channels, n, p=[0.4, 0.35, 0.25]),
        "revenue": np.random.normal(100, 20, n),
        "quantity": np.random.poisson(5, n)
    })
    
    # Current - with anomaly in South region
    np.random.seed(123)
    current = pd.DataFrame({
        "region": np.random.choice(regions, n, p=[0.3, 0.1, 0.3, 0.3]),  # South dropped
        "product": np.random.choice(products, n, p=[0.25, 0.25, 0.25, 0.25]),
        "channel": np.random.choice(channels, n, p=[0.5, 0.3, 0.2]),  # Online increased
        "revenue": np.random.normal(95, 25, n),  # Slightly lower
        "quantity": np.random.poisson(4, n)  # Slightly lower
    })
    
    # Make the South anomaly more pronounced
    current.loc[current["region"] == "South", "revenue"] *= 0.5
    
    return baseline, current


def get_rca_recommendations(rca_result: RCAResult) -> List[str]:
    """Generate actionable recommendations from RCA"""
    recommendations = []
    
    for cause in rca_result.root_causes[:3]:
        if cause.change_pct < -20:
            recommendations.append(
                f"🔍 Investigate drop in {cause.dimension}='{cause.value}': "
                f"Check for data source issues, business changes, or external factors"
            )
        elif cause.change_pct > 20:
            recommendations.append(
                f"📈 Review increase in {cause.dimension}='{cause.value}': "
                f"Verify data quality and confirm if this is expected business growth"
            )
        
        if cause.confidence == "high":
            recommendations.append(
                f"⚠️ High confidence: {cause.dimension}='{cause.value}' is a primary driver. "
                f"Consider adding monitoring alert for this segment"
            )
    
    if not recommendations:
        recommendations.append(
            "✅ No significant segment-level issues detected. "
            "The change appears evenly distributed."
        )
    
    return recommendations
