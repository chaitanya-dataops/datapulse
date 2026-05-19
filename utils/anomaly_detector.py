"""
Anomaly detection logic using statistical methods AND Machine Learning
Enterprise-grade features to compete with Bigeye/Datafold/Anomalo
No external AI APIs required - completely free!

ML Capabilities:
- Isolation Forest (unsupervised outlier detection)
- Auto-learning thresholds
- DBSCAN clustering-based anomaly detection
- Exponential smoothing forecasting
"""
import pandas as pd
import numpy as np
from scipy import stats
from scipy.spatial.distance import jensenshannon
from typing import List, Dict, Tuple, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

# ML imports
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN


class RuleType(Enum):
    """Types of custom data quality rules"""
    NOT_NULL = "not_null"
    UNIQUE = "unique"
    RANGE = "range"
    REGEX = "regex"
    CUSTOM_SQL = "custom_sql"
    FRESHNESS = "freshness"
    REFERENTIAL = "referential"


@dataclass
class DataQualityRule:
    """Custom data quality rule definition"""
    name: str
    rule_type: RuleType
    column: Optional[str] = None
    params: Optional[Dict] = None
    severity: str = "medium"
    
    
@dataclass
class SchemaChange:
    """Represents a schema change"""
    change_type: str  # 'added', 'removed', 'type_changed'
    column_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None


def detect_zscore_anomalies(
    df: pd.DataFrame, 
    value_column: str, 
    date_column: str = "date",
    threshold: float = 2.5
) -> pd.DataFrame:
    """
    Detect anomalies using Z-score method.
    Values beyond threshold standard deviations are flagged.
    
    Args:
        df: DataFrame with time series data
        value_column: Column name containing values to check
        date_column: Column name containing dates
        threshold: Z-score threshold (default 2.5)
    
    Returns:
        DataFrame with anomaly flags and details
    """
    df = df.copy()
    df = df.sort_values(date_column)
    
    # Calculate Z-scores
    mean_val = df[value_column].mean()
    std_val = df[value_column].std()
    
    if std_val == 0:
        df["z_score"] = 0
        df["is_anomaly"] = False
    else:
        df["z_score"] = (df[value_column] - mean_val) / std_val
        df["is_anomaly"] = abs(df["z_score"]) > threshold
    
    # Calculate percentage change
    df["pct_change"] = df[value_column].pct_change() * 100
    
    # Determine anomaly direction
    df["anomaly_type"] = df.apply(
        lambda row: "spike" if row["z_score"] > threshold 
                    else ("drop" if row["z_score"] < -threshold else None),
        axis=1
    )
    
    return df


def detect_row_count_anomalies(
    row_counts_df: pd.DataFrame,
    threshold: float = 2.5
) -> List[Dict]:
    """
    Detect anomalies in row count data.
    
    Returns list of anomaly dictionaries with details.
    """
    df = detect_zscore_anomalies(
        row_counts_df, 
        value_column="row_count",
        date_column="date",
        threshold=threshold
    )
    
    anomalies = []
    for _, row in df[df["is_anomaly"]].iterrows():
        anomaly = {
            "date": row["date"],
            "metric": "row_count",
            "value": row["row_count"],
            "z_score": row["z_score"],
            "pct_change": row["pct_change"],
            "type": row["anomaly_type"],
            "severity": get_severity(abs(row["z_score"])),
            "explanation": generate_row_count_explanation(row)
        }
        anomalies.append(anomaly)
    
    return anomalies


def detect_null_rate_anomalies(
    null_rates_df: pd.DataFrame,
    baseline_threshold: float = 0.05,  # 5% null rate is concerning
    spike_threshold: float = 2.0  # 2x increase is anomaly
) -> List[Dict]:
    """
    Detect anomalies in null rate data.
    
    Flags:
    1. Columns with null rate above baseline threshold
    2. Sudden spikes in null rate
    """
    anomalies = []
    
    for column in null_rates_df["column_name"].unique():
        col_df = null_rates_df[null_rates_df["column_name"] == column].copy()
        col_df = col_df.sort_values("date")
        
        # Check for absolute high null rates
        latest = col_df.iloc[-1]
        avg_rate = col_df["null_rate"].mean()
        
        # Check if latest is significantly higher than average
        if len(col_df) > 1 and avg_rate > 0:
            ratio = latest["null_rate"] / avg_rate
            if ratio > spike_threshold and latest["null_rate"] > 0.02:
                anomalies.append({
                    "date": latest["date"],
                    "metric": "null_rate",
                    "column_name": column,
                    "value": latest["null_rate"],
                    "baseline": avg_rate,
                    "type": "spike",
                    "severity": "high" if latest["null_rate"] > 0.1 else "medium",
                    "explanation": generate_null_rate_explanation(column, latest["null_rate"], avg_rate)
                })
        
        # Also flag if absolute null rate is very high
        if latest["null_rate"] > baseline_threshold:
            # Check if not already flagged as spike
            if not any(a["column_name"] == column and a["date"] == latest["date"] for a in anomalies):
                anomalies.append({
                    "date": latest["date"],
                    "metric": "null_rate",
                    "column_name": column,
                    "value": latest["null_rate"],
                    "baseline": avg_rate,
                    "type": "high_baseline",
                    "severity": "medium",
                    "explanation": f"Column '{column}' has {latest['null_rate']*100:.1f}% null values"
                })
    
    return anomalies


def get_severity(z_score: float) -> str:
    """Map Z-score to severity level"""
    if abs(z_score) > 4:
        return "critical"
    elif abs(z_score) > 3:
        return "high"
    elif abs(z_score) > 2.5:
        return "medium"
    else:
        return "low"


def generate_row_count_explanation(row: pd.Series) -> str:
    """
    Generate human-readable explanation for row count anomaly.
    Rule-based - no AI required!
    """
    pct = abs(row["pct_change"])
    direction = "increased" if row["anomaly_type"] == "spike" else "decreased"
    
    explanations = []
    
    if row["anomaly_type"] == "drop" and pct > 30:
        explanations = [
            f"Row count {direction} by {pct:.0f}% compared to previous day.",
            "Possible causes:",
            "• Upstream data source delay or failure",
            "• ETL job failed or was skipped",
            "• Source system maintenance window",
            "• Data filter or partition issue"
        ]
    elif row["anomaly_type"] == "spike" and pct > 30:
        explanations = [
            f"Row count {direction} by {pct:.0f}% compared to previous day.",
            "Possible causes:",
            "• Backfill or historical data load",
            "• Duplicate data ingestion",
            "• New data source added",
            "• Partition overlap"
        ]
    else:
        explanations = [
            f"Row count {direction} by {pct:.0f}%.",
            "This deviation is outside normal variance."
        ]
    
    return "\n".join(explanations)


def generate_null_rate_explanation(column: str, current_rate: float, baseline: float) -> str:
    """
    Generate human-readable explanation for null rate anomaly.
    Rule-based - no AI required!
    """
    increase_pct = ((current_rate - baseline) / baseline * 100) if baseline > 0 else 0
    
    explanations = [
        f"Null rate for '{column}' spiked to {current_rate*100:.1f}% (baseline: {baseline*100:.1f}%)",
        "Possible causes:",
        "• Schema change in upstream source",
        "• Source system sending incomplete data",
        "• New edge case not handled by ETL",
        "• Data type mismatch causing NULL conversion"
    ]
    
    return "\n".join(explanations)


def get_health_score(row_anomalies: List[Dict], null_anomalies: List[Dict]) -> Tuple[int, str]:
    """
    Calculate overall health score for a table.
    
    Returns:
        Tuple of (score 0-100, status string)
    """
    score = 100
    
    # Deduct points for anomalies
    for anomaly in row_anomalies:
        if anomaly["severity"] == "critical":
            score -= 30
        elif anomaly["severity"] == "high":
            score -= 20
        elif anomaly["severity"] == "medium":
            score -= 10
    
    for anomaly in null_anomalies:
        if anomaly["severity"] == "high":
            score -= 15
        elif anomaly["severity"] == "medium":
            score -= 8
    
    score = max(0, score)
    
    if score >= 90:
        status = "Healthy"
    elif score >= 70:
        status = "Warning"
    elif score >= 50:
        status = "Degraded"
    else:
        status = "Critical"
    
    return score, status


# =============================================================================
# ENTERPRISE FEATURES - Competing with Bigeye/Datafold/Anomalo
# =============================================================================


def detect_schema_changes(
    current_schema: pd.DataFrame,
    previous_schema: pd.DataFrame
) -> List[Dict]:
    """
    Detect schema changes between two snapshots.
    Comparable to Bigeye/Datafold schema monitoring.
    
    Args:
        current_schema: DataFrame with columns ['column_name', 'data_type']
        previous_schema: DataFrame with columns ['column_name', 'data_type']
    
    Returns:
        List of schema change dictionaries
    """
    changes = []
    
    current_cols = set(current_schema["column_name"].tolist())
    previous_cols = set(previous_schema["column_name"].tolist())
    
    # Detect added columns
    for col in current_cols - previous_cols:
        new_type = current_schema[current_schema["column_name"] == col]["data_type"].iloc[0]
        changes.append({
            "change_type": "column_added",
            "column_name": col,
            "new_type": new_type,
            "severity": "medium",
            "explanation": f"New column '{col}' ({new_type}) was added to the table"
        })
    
    # Detect removed columns
    for col in previous_cols - current_cols:
        old_type = previous_schema[previous_schema["column_name"] == col]["data_type"].iloc[0]
        changes.append({
            "change_type": "column_removed",
            "column_name": col,
            "old_type": old_type,
            "severity": "high",
            "explanation": f"Column '{col}' ({old_type}) was removed from the table"
        })
    
    # Detect type changes
    for col in current_cols & previous_cols:
        curr_type = current_schema[current_schema["column_name"] == col]["data_type"].iloc[0]
        prev_type = previous_schema[previous_schema["column_name"] == col]["data_type"].iloc[0]
        
        if curr_type != prev_type:
            changes.append({
                "change_type": "type_changed",
                "column_name": col,
                "old_type": prev_type,
                "new_type": curr_type,
                "severity": "high",
                "explanation": f"Column '{col}' type changed from {prev_type} to {curr_type}"
            })
    
    return changes


def detect_data_freshness(
    last_update_time: datetime,
    expected_frequency_hours: float = 24,
    warning_threshold: float = 1.5,
    critical_threshold: float = 2.0
) -> Dict:
    """
    Detect if data is stale based on expected update frequency.
    Comparable to Bigeye/Anomalo freshness monitoring.
    
    Args:
        last_update_time: When the data was last updated
        expected_frequency_hours: How often data should be updated
        warning_threshold: Multiplier for warning (e.g., 1.5x expected)
        critical_threshold: Multiplier for critical (e.g., 2x expected)
    
    Returns:
        Freshness status dictionary
    """
    now = datetime.now()
    hours_since_update = (now - last_update_time).total_seconds() / 3600
    
    status = "fresh"
    severity = None
    
    if hours_since_update > expected_frequency_hours * critical_threshold:
        status = "stale"
        severity = "critical"
    elif hours_since_update > expected_frequency_hours * warning_threshold:
        status = "delayed"
        severity = "high"
    elif hours_since_update > expected_frequency_hours:
        status = "late"
        severity = "medium"
    
    return {
        "status": status,
        "last_update": last_update_time,
        "hours_since_update": round(hours_since_update, 1),
        "expected_frequency_hours": expected_frequency_hours,
        "severity": severity,
        "explanation": generate_freshness_explanation(
            status, hours_since_update, expected_frequency_hours
        ) if severity else None
    }


def generate_freshness_explanation(status: str, hours: float, expected: float) -> str:
    """Generate explanation for freshness issues"""
    explanations = {
        "stale": [
            f"Data is {hours:.1f} hours old (expected: every {expected:.0f} hours)",
            "Possible causes:",
            "• ETL pipeline failure",
            "• Source system outage",
            "• Scheduler/orchestrator issue",
            "• Upstream dependency failure"
        ],
        "delayed": [
            f"Data update is delayed ({hours:.1f}h vs expected {expected:.0f}h)",
            "Possible causes:",
            "• Processing backlog",
            "• Resource constraints",
            "• Slow upstream queries"
        ],
        "late": [
            f"Data is slightly late ({hours:.1f}h vs expected {expected:.0f}h)",
            "Monitor for continued delays"
        ]
    }
    return "\n".join(explanations.get(status, ["Unknown status"]))


def detect_distribution_shift(
    current_data: pd.Series,
    historical_data: pd.Series,
    n_bins: int = 20,
    threshold: float = 0.1
) -> Dict:
    """
    Detect distribution shifts using Jensen-Shannon divergence.
    Comparable to Anomalo/Bigeye distribution monitoring.
    
    Args:
        current_data: Recent data sample
        historical_data: Historical baseline data
        n_bins: Number of bins for histogram
        threshold: JS divergence threshold for anomaly
    
    Returns:
        Distribution shift analysis
    """
    # Handle edge cases
    if len(current_data) < 10 or len(historical_data) < 10:
        return {"shift_detected": False, "reason": "Insufficient data"}
    
    # Create histograms with same bins
    all_data = pd.concat([current_data, historical_data])
    bins = np.histogram_bin_edges(all_data.dropna(), bins=n_bins)
    
    hist_current, _ = np.histogram(current_data.dropna(), bins=bins, density=True)
    hist_historical, _ = np.histogram(historical_data.dropna(), bins=bins, density=True)
    
    # Add small epsilon to avoid division by zero
    epsilon = 1e-10
    hist_current = hist_current + epsilon
    hist_historical = hist_historical + epsilon
    
    # Normalize
    hist_current = hist_current / hist_current.sum()
    hist_historical = hist_historical / hist_historical.sum()
    
    # Calculate Jensen-Shannon divergence
    js_divergence = jensenshannon(hist_current, hist_historical)
    
    shift_detected = js_divergence > threshold
    
    # Determine shift characteristics
    current_mean = current_data.mean()
    historical_mean = historical_data.mean()
    current_std = current_data.std()
    historical_std = historical_data.std()
    
    shift_type = None
    if shift_detected:
        if current_mean > historical_mean * 1.1:
            shift_type = "mean_increase"
        elif current_mean < historical_mean * 0.9:
            shift_type = "mean_decrease"
        elif current_std > historical_std * 1.5:
            shift_type = "variance_increase"
        else:
            shift_type = "shape_change"
    
    return {
        "shift_detected": shift_detected,
        "js_divergence": round(js_divergence, 4),
        "threshold": threshold,
        "shift_type": shift_type,
        "current_mean": round(current_mean, 2),
        "historical_mean": round(historical_mean, 2),
        "current_std": round(current_std, 2),
        "historical_std": round(historical_std, 2),
        "severity": "high" if js_divergence > threshold * 2 else "medium" if shift_detected else None,
        "explanation": generate_distribution_explanation(
            shift_type, js_divergence, current_mean, historical_mean
        ) if shift_detected else None
    }


def generate_distribution_explanation(shift_type: str, divergence: float, 
                                       current_mean: float, historical_mean: float) -> str:
    """Generate explanation for distribution shifts"""
    explanations = {
        "mean_increase": [
            f"Data distribution shifted upward (mean: {historical_mean:.2f} → {current_mean:.2f})",
            "Possible causes:",
            "• Business seasonality or growth",
            "• Data source change",
            "• Filter/logic change in ETL",
            "• Currency or unit conversion issue"
        ],
        "mean_decrease": [
            f"Data distribution shifted downward (mean: {historical_mean:.2f} → {current_mean:.2f})",
            "Possible causes:",
            "• Business decline or seasonality",
            "• Missing data segments",
            "• Filter removing records",
            "• Calculation logic change"
        ],
        "variance_increase": [
            "Data variance has significantly increased",
            "Possible causes:",
            "• New outlier data sources",
            "• Data quality degradation",
            "• Schema/type conversion issues"
        ],
        "shape_change": [
            f"Distribution shape changed (JS divergence: {divergence:.4f})",
            "Possible causes:",
            "• Underlying data characteristics changed",
            "• Multiple data sources merged",
            "• Business process change"
        ]
    }
    return "\n".join(explanations.get(shift_type, ["Distribution shift detected"]))


def detect_duplicates(
    df: pd.DataFrame,
    key_columns: List[str],
    threshold_pct: float = 1.0
) -> Dict:
    """
    Detect duplicate records based on key columns.
    Comparable to Datafold/Bigeye uniqueness checks.
    
    Args:
        df: DataFrame to check
        key_columns: Columns that should be unique together
        threshold_pct: Percentage threshold for flagging
    
    Returns:
        Duplicate analysis results
    """
    total_rows = len(df)
    if total_rows == 0:
        return {"has_duplicates": False, "reason": "Empty dataset"}
    
    # Find duplicates
    duplicates = df[df.duplicated(subset=key_columns, keep=False)]
    duplicate_count = len(duplicates)
    duplicate_pct = (duplicate_count / total_rows) * 100
    
    # Get sample of duplicate keys
    if duplicate_count > 0:
        sample_duplicates = (
            df[df.duplicated(subset=key_columns, keep='first')]
            [key_columns]
            .head(5)
            .to_dict('records')
        )
    else:
        sample_duplicates = []
    
    has_issue = duplicate_pct > threshold_pct
    
    return {
        "has_duplicates": duplicate_count > 0,
        "is_anomaly": has_issue,
        "duplicate_count": duplicate_count,
        "duplicate_pct": round(duplicate_pct, 2),
        "total_rows": total_rows,
        "key_columns": key_columns,
        "threshold_pct": threshold_pct,
        "sample_duplicates": sample_duplicates,
        "severity": "critical" if duplicate_pct > 10 else "high" if duplicate_pct > 5 else "medium",
        "explanation": generate_duplicate_explanation(
            duplicate_count, duplicate_pct, key_columns
        ) if has_issue else None
    }


def generate_duplicate_explanation(count: int, pct: float, columns: List[str]) -> str:
    """Generate explanation for duplicate issues"""
    return "\n".join([
        f"Found {count:,} duplicate records ({pct:.1f}%) on key: {', '.join(columns)}",
        "Possible causes:",
        "• Multiple ETL runs without deduplication",
        "• Source system sending duplicates",
        "• Missing DISTINCT or GROUP BY",
        "• Partition overlap in incremental loads"
    ])


def detect_cardinality_anomalies(
    current_distinct: int,
    historical_distinct: int,
    total_rows: int,
    column_name: str,
    threshold_pct: float = 20
) -> Dict:
    """
    Detect anomalies in column cardinality (distinct values).
    
    Args:
        current_distinct: Current distinct count
        historical_distinct: Historical average distinct count
        total_rows: Total row count
        column_name: Name of the column
        threshold_pct: Percentage change threshold
    
    Returns:
        Cardinality analysis results
    """
    if historical_distinct == 0:
        return {"is_anomaly": False, "reason": "No historical data"}
    
    pct_change = ((current_distinct - historical_distinct) / historical_distinct) * 100
    cardinality_ratio = current_distinct / total_rows if total_rows > 0 else 0
    
    is_anomaly = abs(pct_change) > threshold_pct
    
    anomaly_type = None
    if is_anomaly:
        if pct_change > 0:
            anomaly_type = "cardinality_increase"
        else:
            anomaly_type = "cardinality_decrease"
    
    return {
        "column_name": column_name,
        "is_anomaly": is_anomaly,
        "current_distinct": current_distinct,
        "historical_distinct": historical_distinct,
        "pct_change": round(pct_change, 1),
        "cardinality_ratio": round(cardinality_ratio, 4),
        "anomaly_type": anomaly_type,
        "severity": "high" if abs(pct_change) > 50 else "medium",
        "explanation": generate_cardinality_explanation(
            column_name, anomaly_type, pct_change, current_distinct, historical_distinct
        ) if is_anomaly else None
    }


def generate_cardinality_explanation(column: str, anomaly_type: str, 
                                      pct_change: float, current: int, historical: int) -> str:
    """Generate explanation for cardinality anomalies"""
    if anomaly_type == "cardinality_increase":
        return "\n".join([
            f"Distinct values in '{column}' increased by {pct_change:.0f}% ({historical:,} → {current:,})",
            "Possible causes:",
            "• New data sources or segments added",
            "• ID generation change",
            "• Data quality issue (fragmentation)"
        ])
    else:
        return "\n".join([
            f"Distinct values in '{column}' decreased by {abs(pct_change):.0f}% ({historical:,} → {current:,})",
            "Possible causes:",
            "• Data filter removing segments",
            "• Source system consolidation",
            "• Possible data loss"
        ])


def validate_custom_rules(
    df: pd.DataFrame,
    rules: List[DataQualityRule]
) -> List[Dict]:
    """
    Validate data against custom rules.
    Comparable to Bigeye/Datafold custom assertions.
    
    Args:
        df: DataFrame to validate
        rules: List of DataQualityRule objects
    
    Returns:
        List of validation results
    """
    results = []
    
    for rule in rules:
        result = {
            "rule_name": rule.name,
            "rule_type": rule.rule_type.value,
            "column": rule.column,
            "passed": True,
            "severity": rule.severity,
            "details": {}
        }
        
        try:
            if rule.rule_type == RuleType.NOT_NULL:
                null_count = df[rule.column].isnull().sum()
                result["passed"] = null_count == 0
                result["details"] = {"null_count": int(null_count)}
                if not result["passed"]:
                    result["explanation"] = f"Found {null_count:,} NULL values in '{rule.column}'"
                    
            elif rule.rule_type == RuleType.UNIQUE:
                duplicate_count = df[rule.column].duplicated().sum()
                result["passed"] = duplicate_count == 0
                result["details"] = {"duplicate_count": int(duplicate_count)}
                if not result["passed"]:
                    result["explanation"] = f"Found {duplicate_count:,} duplicate values in '{rule.column}'"
                    
            elif rule.rule_type == RuleType.RANGE:
                min_val = rule.params.get("min")
                max_val = rule.params.get("max")
                violations = 0
                if min_val is not None:
                    violations += (df[rule.column] < min_val).sum()
                if max_val is not None:
                    violations += (df[rule.column] > max_val).sum()
                result["passed"] = violations == 0
                result["details"] = {
                    "violations": int(violations),
                    "min": min_val,
                    "max": max_val
                }
                if not result["passed"]:
                    result["explanation"] = f"Found {violations:,} values outside range [{min_val}, {max_val}]"
                    
            elif rule.rule_type == RuleType.REGEX:
                import re
                pattern = rule.params.get("pattern", "")
                non_matches = (~df[rule.column].astype(str).str.match(pattern, na=False)).sum()
                result["passed"] = non_matches == 0
                result["details"] = {"non_matches": int(non_matches), "pattern": pattern}
                if not result["passed"]:
                    result["explanation"] = f"Found {non_matches:,} values not matching pattern '{pattern}'"
                    
        except Exception as e:
            result["passed"] = False
            result["error"] = str(e)
            result["explanation"] = f"Rule validation failed: {str(e)}"
        
        results.append(result)
    
    return results


def forecast_expected_value(
    historical_values: pd.Series,
    forecast_periods: int = 1
) -> Dict:
    """
    Simple trend-based forecasting for expected values.
    Uses linear regression for trend prediction.
    
    Args:
        historical_values: Time series of historical values
        forecast_periods: Number of periods to forecast
    
    Returns:
        Forecast results with confidence intervals
    """
    if len(historical_values) < 5:
        return {"success": False, "reason": "Insufficient historical data"}
    
    # Prepare data
    y = historical_values.values
    x = np.arange(len(y))
    
    # Linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    
    # Forecast
    forecast_x = np.arange(len(y), len(y) + forecast_periods)
    forecast_y = slope * forecast_x + intercept
    
    # Calculate prediction intervals (simplified)
    residuals = y - (slope * x + intercept)
    residual_std = np.std(residuals)
    
    # 95% confidence interval
    ci_multiplier = 1.96
    lower_bound = forecast_y - ci_multiplier * residual_std
    upper_bound = forecast_y + ci_multiplier * residual_std
    
    return {
        "success": True,
        "forecast_values": forecast_y.tolist(),
        "lower_bound": lower_bound.tolist(),
        "upper_bound": upper_bound.tolist(),
        "trend_direction": "increasing" if slope > 0 else "decreasing",
        "trend_slope": round(slope, 2),
        "r_squared": round(r_value ** 2, 4),
        "confidence": "high" if r_value ** 2 > 0.7 else "medium" if r_value ** 2 > 0.4 else "low"
    }


def compare_datasets(
    current_df: pd.DataFrame,
    previous_df: pd.DataFrame,
    key_columns: List[str],
    compare_columns: Optional[List[str]] = None
) -> Dict:
    """
    Compare two datasets for differences (data diff).
    Comparable to Datafold data diff feature.
    
    Args:
        current_df: Current dataset
        previous_df: Previous/baseline dataset
        key_columns: Columns to use as keys for matching
        compare_columns: Columns to compare (None = all non-key columns)
    
    Returns:
        Comparison results
    """
    if compare_columns is None:
        compare_columns = [c for c in current_df.columns if c not in key_columns]
    
    # Merge datasets
    merged = current_df.merge(
        previous_df,
        on=key_columns,
        how='outer',
        suffixes=('_current', '_previous'),
        indicator=True
    )
    
    # Categorize differences
    added_rows = (merged['_merge'] == 'left_only').sum()
    removed_rows = (merged['_merge'] == 'right_only').sum()
    matched_rows = (merged['_merge'] == 'both').sum()
    
    # Find changed values
    changed_values = {}
    matched_df = merged[merged['_merge'] == 'both']
    
    for col in compare_columns:
        curr_col = f"{col}_current"
        prev_col = f"{col}_previous"
        if curr_col in matched_df.columns and prev_col in matched_df.columns:
            changes = (matched_df[curr_col] != matched_df[prev_col]).sum()
            if changes > 0:
                changed_values[col] = int(changes)
    
    total_changes = added_rows + removed_rows + sum(changed_values.values())
    
    return {
        "total_current_rows": len(current_df),
        "total_previous_rows": len(previous_df),
        "added_rows": int(added_rows),
        "removed_rows": int(removed_rows),
        "matched_rows": int(matched_rows),
        "changed_values": changed_values,
        "total_changes": total_changes,
        "is_identical": total_changes == 0,
        "change_summary": generate_diff_summary(added_rows, removed_rows, changed_values)
    }


def generate_diff_summary(added: int, removed: int, changed: Dict) -> str:
    """Generate summary of data differences"""
    parts = []
    if added > 0:
        parts.append(f"{added:,} rows added")
    if removed > 0:
        parts.append(f"{removed:,} rows removed")
    if changed:
        total_changed = sum(changed.values())
        parts.append(f"{total_changed:,} values changed across {len(changed)} columns")
    
    if not parts:
        return "No differences found"
    return "; ".join(parts)


def get_comprehensive_health_score(
    row_anomalies: List[Dict],
    null_anomalies: List[Dict],
    schema_changes: Optional[List[Dict]] = None,
    freshness: Optional[Dict] = None,
    distribution_shifts: Optional[List[Dict]] = None,
    duplicate_issues: Optional[Dict] = None,
    rule_violations: Optional[List[Dict]] = None
) -> Tuple[int, str, Dict]:
    """
    Calculate comprehensive health score considering all quality dimensions.
    Enterprise-grade scoring comparable to Bigeye/Anomalo.
    
    Returns:
        Tuple of (score 0-100, status string, breakdown dict)
    """
    score = 100
    breakdown = {
        "row_count": 100,
        "null_rate": 100,
        "schema": 100,
        "freshness": 100,
        "distribution": 100,
        "duplicates": 100,
        "rules": 100
    }
    
    # Row count anomalies
    for anomaly in row_anomalies:
        if anomaly["severity"] == "critical":
            breakdown["row_count"] -= 40
        elif anomaly["severity"] == "high":
            breakdown["row_count"] -= 25
        elif anomaly["severity"] == "medium":
            breakdown["row_count"] -= 15
    
    # Null rate anomalies
    for anomaly in null_anomalies:
        if anomaly["severity"] == "high":
            breakdown["null_rate"] -= 20
        elif anomaly["severity"] == "medium":
            breakdown["null_rate"] -= 10
    
    # Schema changes
    if schema_changes:
        for change in schema_changes:
            if change["severity"] == "high":
                breakdown["schema"] -= 25
            elif change["severity"] == "medium":
                breakdown["schema"] -= 15
    
    # Freshness
    if freshness and freshness.get("severity"):
        if freshness["severity"] == "critical":
            breakdown["freshness"] -= 50
        elif freshness["severity"] == "high":
            breakdown["freshness"] -= 30
        elif freshness["severity"] == "medium":
            breakdown["freshness"] -= 15
    
    # Distribution shifts
    if distribution_shifts:
        for shift in distribution_shifts:
            if shift.get("shift_detected"):
                if shift.get("severity") == "high":
                    breakdown["distribution"] -= 25
                elif shift.get("severity") == "medium":
                    breakdown["distribution"] -= 15
    
    # Duplicates
    if duplicate_issues and duplicate_issues.get("is_anomaly"):
        if duplicate_issues["severity"] == "critical":
            breakdown["duplicates"] -= 40
        elif duplicate_issues["severity"] == "high":
            breakdown["duplicates"] -= 25
        elif duplicate_issues["severity"] == "medium":
            breakdown["duplicates"] -= 15
    
    # Rule violations
    if rule_violations:
        for rule in rule_violations:
            if not rule.get("passed"):
                if rule.get("severity") == "critical":
                    breakdown["rules"] -= 30
                elif rule.get("severity") == "high":
                    breakdown["rules"] -= 20
                elif rule.get("severity") == "medium":
                    breakdown["rules"] -= 10
    
    # Ensure minimums
    for key in breakdown:
        breakdown[key] = max(0, breakdown[key])
    
    # Calculate weighted average
    weights = {
        "row_count": 0.20,
        "null_rate": 0.15,
        "schema": 0.15,
        "freshness": 0.15,
        "distribution": 0.10,
        "duplicates": 0.15,
        "rules": 0.10
    }
    
    score = sum(breakdown[k] * weights[k] for k in breakdown)
    score = max(0, min(100, round(score)))
    
    if score >= 90:
        status = "Healthy"
    elif score >= 75:
        status = "Good"
    elif score >= 60:
        status = "Warning"
    elif score >= 40:
        status = "Degraded"
    else:
        status = "Critical"
    
    return score, status, breakdown


# =============================================================================
# MACHINE LEARNING CAPABILITIES
# =============================================================================


def detect_anomalies_isolation_forest(
    df: pd.DataFrame,
    feature_columns: List[str],
    contamination: float = 0.1,
    random_state: int = 42
) -> Dict:
    """
    Detect anomalies using Isolation Forest algorithm.
    Unsupervised ML that learns "normal" patterns automatically.
    
    This is comparable to Anomalo's ML-based detection!
    
    Args:
        df: DataFrame with data to analyze
        feature_columns: Columns to use for anomaly detection
        contamination: Expected proportion of anomalies (default 10%)
        random_state: Random seed for reproducibility
    
    Returns:
        Dictionary with anomaly detection results
    """
    if len(df) < 10:
        return {"success": False, "reason": "Insufficient data (need at least 10 rows)"}
    
    # Prepare features
    X = df[feature_columns].copy()
    
    # Handle missing values
    X = X.fillna(X.median())
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train Isolation Forest
    iso_forest = IsolationForest(
        contamination=contamination,
        random_state=random_state,
        n_estimators=100
    )
    
    # Predict anomalies (-1 = anomaly, 1 = normal)
    predictions = iso_forest.fit_predict(X_scaled)
    anomaly_scores = iso_forest.decision_function(X_scaled)
    
    # Get anomaly indices
    anomaly_mask = predictions == -1
    anomaly_indices = df.index[anomaly_mask].tolist()
    
    # Calculate feature importance (which features contributed most)
    feature_importance = {}
    if anomaly_mask.sum() > 0:
        anomaly_data = X[anomaly_mask]
        normal_data = X[~anomaly_mask]
        
        for col in feature_columns:
            if len(normal_data) > 0:
                anomaly_mean = anomaly_data[col].mean()
                normal_mean = normal_data[col].mean()
                normal_std = normal_data[col].std()
                
                if normal_std > 0:
                    deviation = abs(anomaly_mean - normal_mean) / normal_std
                    feature_importance[col] = round(deviation, 2)
    
    # Sort by importance
    feature_importance = dict(sorted(
        feature_importance.items(), 
        key=lambda x: x[1], 
        reverse=True
    ))
    
    return {
        "success": True,
        "method": "Isolation Forest",
        "total_rows": len(df),
        "anomaly_count": int(anomaly_mask.sum()),
        "anomaly_pct": round(anomaly_mask.sum() / len(df) * 100, 2),
        "anomaly_indices": anomaly_indices[:20],  # Limit to first 20
        "anomaly_scores": anomaly_scores[anomaly_mask].tolist()[:20],
        "feature_importance": feature_importance,
        "contamination": contamination,
        "severity": "high" if anomaly_mask.sum() / len(df) > 0.15 else "medium",
        "explanation": generate_isolation_forest_explanation(
            anomaly_mask.sum(), len(df), feature_importance
        )
    }


def generate_isolation_forest_explanation(
    anomaly_count: int, 
    total: int, 
    importance: Dict
) -> str:
    """Generate explanation for Isolation Forest results"""
    top_features = list(importance.keys())[:3]
    
    lines = [
        f"ML detected {anomaly_count} anomalous records ({anomaly_count/total*100:.1f}%)",
        "",
        "The Isolation Forest algorithm identified records that deviate",
        "significantly from the normal data patterns.",
    ]
    
    if top_features:
        lines.extend([
            "",
            "Top contributing factors:",
        ])
        for i, feat in enumerate(top_features, 1):
            lines.append(f"  {i}. {feat} (deviation score: {importance[feat]})")
    
    return "\n".join(lines)


def detect_anomalies_dbscan(
    df: pd.DataFrame,
    feature_columns: List[str],
    eps: float = 0.5,
    min_samples: int = 5
) -> Dict:
    """
    Detect anomalies using DBSCAN clustering.
    Points not belonging to any cluster are anomalies.
    
    Args:
        df: DataFrame with data to analyze
        feature_columns: Columns to use for clustering
        eps: Maximum distance between points in a cluster
        min_samples: Minimum points to form a cluster
    
    Returns:
        Dictionary with clustering-based anomaly results
    """
    if len(df) < 10:
        return {"success": False, "reason": "Insufficient data"}
    
    # Prepare and scale features
    X = df[feature_columns].copy().fillna(df[feature_columns].median())
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Apply DBSCAN
    dbscan = DBSCAN(eps=eps, min_samples=min_samples)
    clusters = dbscan.fit_predict(X_scaled)
    
    # -1 indicates noise/anomalies
    anomaly_mask = clusters == -1
    n_clusters = len(set(clusters)) - (1 if -1 in clusters else 0)
    
    return {
        "success": True,
        "method": "DBSCAN Clustering",
        "total_rows": len(df),
        "anomaly_count": int(anomaly_mask.sum()),
        "anomaly_pct": round(anomaly_mask.sum() / len(df) * 100, 2),
        "n_clusters": n_clusters,
        "anomaly_indices": df.index[anomaly_mask].tolist()[:20],
        "cluster_distribution": dict(pd.Series(clusters[clusters != -1]).value_counts()),
        "severity": "high" if anomaly_mask.sum() / len(df) > 0.2 else "medium"
    }


def auto_learn_thresholds(
    historical_df: pd.DataFrame,
    value_column: str,
    date_column: str = "date",
    confidence_level: float = 0.95
) -> Dict:
    """
    Automatically learn anomaly thresholds from historical data.
    No manual threshold configuration needed!
    
    This is a key feature of Anomalo/Bigeye - auto-calibration.
    
    Args:
        historical_df: Historical data for learning
        value_column: Column to learn thresholds for
        date_column: Date column for time ordering
        confidence_level: Confidence level for bounds (default 95%)
    
    Returns:
        Learned threshold configuration
    """
    if len(historical_df) < 14:
        return {"success": False, "reason": "Need at least 14 days of history"}
    
    df = historical_df.sort_values(date_column).copy()
    values = df[value_column].dropna()
    
    # Calculate statistics
    mean = values.mean()
    std = values.std()
    median = values.median()
    
    # Percentile-based bounds (robust to outliers)
    lower_pct = (1 - confidence_level) / 2 * 100
    upper_pct = (1 + confidence_level) / 2 * 100
    lower_bound = np.percentile(values, lower_pct)
    upper_bound = np.percentile(values, upper_pct)
    
    # Z-score based bounds
    z_multiplier = stats.norm.ppf((1 + confidence_level) / 2)
    z_lower = mean - z_multiplier * std
    z_upper = mean + z_multiplier * std
    
    # IQR-based bounds (most robust)
    q1 = values.quantile(0.25)
    q3 = values.quantile(0.75)
    iqr = q3 - q1
    iqr_lower = q1 - 1.5 * iqr
    iqr_upper = q3 + 1.5 * iqr
    
    # Trend detection
    x = np.arange(len(values))
    slope, intercept, r_value, _, _ = stats.linregress(x, values)
    trend = "increasing" if slope > std * 0.1 else "decreasing" if slope < -std * 0.1 else "stable"
    
    # Day-of-week patterns
    if date_column in df.columns:
        df["dow"] = pd.to_datetime(df[date_column]).dt.dayofweek
        dow_pattern = df.groupby("dow")[value_column].mean().to_dict()
        has_weekly_pattern = df.groupby("dow")[value_column].std().mean() > std * 0.3
    else:
        dow_pattern = {}
        has_weekly_pattern = False
    
    return {
        "success": True,
        "value_column": value_column,
        "data_points": len(values),
        "statistics": {
            "mean": round(mean, 2),
            "std": round(std, 2),
            "median": round(median, 2),
            "min": round(values.min(), 2),
            "max": round(values.max(), 2)
        },
        "learned_bounds": {
            "percentile": {
                "lower": round(lower_bound, 2),
                "upper": round(upper_bound, 2),
                "confidence": confidence_level
            },
            "zscore": {
                "lower": round(z_lower, 2),
                "upper": round(z_upper, 2),
                "z_multiplier": round(z_multiplier, 2)
            },
            "iqr": {
                "lower": round(iqr_lower, 2),
                "upper": round(iqr_upper, 2)
            }
        },
        "trend": {
            "direction": trend,
            "slope": round(slope, 4),
            "r_squared": round(r_value ** 2, 4)
        },
        "seasonality": {
            "has_weekly_pattern": has_weekly_pattern,
            "day_of_week_means": {k: round(v, 2) for k, v in dow_pattern.items()}
        },
        "recommended_method": "iqr" if has_weekly_pattern else "percentile"
    }


def detect_with_learned_thresholds(
    current_value: float,
    learned_config: Dict,
    method: str = "auto"
) -> Dict:
    """
    Detect anomalies using auto-learned thresholds.
    
    Args:
        current_value: Current value to check
        learned_config: Config from auto_learn_thresholds()
        method: "percentile", "zscore", "iqr", or "auto"
    
    Returns:
        Anomaly detection result
    """
    if not learned_config.get("success"):
        return {"is_anomaly": False, "reason": "No learned thresholds"}
    
    # Select method
    if method == "auto":
        method = learned_config.get("recommended_method", "percentile")
    
    bounds = learned_config["learned_bounds"][method]
    lower = bounds["lower"]
    upper = bounds["upper"]
    
    is_anomaly = current_value < lower or current_value > upper
    
    anomaly_type = None
    if current_value < lower:
        anomaly_type = "below_expected"
        deviation_pct = (lower - current_value) / abs(lower) * 100 if lower != 0 else 0
    elif current_value > upper:
        anomaly_type = "above_expected"
        deviation_pct = (current_value - upper) / upper * 100 if upper != 0 else 0
    else:
        deviation_pct = 0
    
    return {
        "is_anomaly": is_anomaly,
        "current_value": current_value,
        "expected_range": [lower, upper],
        "method": method,
        "anomaly_type": anomaly_type,
        "deviation_pct": round(deviation_pct, 1) if is_anomaly else 0,
        "severity": "high" if deviation_pct > 50 else "medium" if deviation_pct > 20 else "low",
        "explanation": f"Value {current_value:.2f} is {'below' if anomaly_type == 'below_expected' else 'above'} the expected range [{lower:.2f}, {upper:.2f}]" if is_anomaly else None
    }


def exponential_smoothing_forecast(
    historical_values: pd.Series,
    alpha: float = 0.3,
    forecast_periods: int = 1
) -> Dict:
    """
    Simple exponential smoothing for time series forecasting.
    More adaptive than linear regression for recent changes.
    
    Args:
        historical_values: Time series of values
        alpha: Smoothing factor (0-1, higher = more weight on recent)
        forecast_periods: Number of periods to forecast
    
    Returns:
        Forecast with confidence intervals
    """
    if len(historical_values) < 5:
        return {"success": False, "reason": "Insufficient data"}
    
    values = historical_values.values
    n = len(values)
    
    # Calculate smoothed values
    smoothed = np.zeros(n)
    smoothed[0] = values[0]
    
    for i in range(1, n):
        smoothed[i] = alpha * values[i] + (1 - alpha) * smoothed[i-1]
    
    # Calculate errors for confidence interval
    errors = values - smoothed
    error_std = np.std(errors)
    
    # Forecast
    last_smoothed = smoothed[-1]
    forecasts = [last_smoothed] * forecast_periods
    
    # Confidence intervals (widen with forecast horizon)
    ci_multiplier = 1.96  # 95% CI
    lower_bounds = []
    upper_bounds = []
    
    for i in range(forecast_periods):
        width = ci_multiplier * error_std * np.sqrt(1 + i * 0.1)
        lower_bounds.append(forecasts[i] - width)
        upper_bounds.append(forecasts[i] + width)
    
    return {
        "success": True,
        "method": "Exponential Smoothing",
        "alpha": alpha,
        "forecast_values": [round(f, 2) for f in forecasts],
        "lower_bound": [round(l, 2) for l in lower_bounds],
        "upper_bound": [round(u, 2) for u in upper_bounds],
        "last_actual": round(values[-1], 2),
        "trend": "increasing" if values[-1] > values[-5:].mean() else "decreasing"
    }


def multivariate_anomaly_score(
    df: pd.DataFrame,
    feature_columns: List[str],
    weights: Optional[Dict[str, float]] = None
) -> pd.DataFrame:
    """
    Calculate composite anomaly scores across multiple metrics.
    Combines multiple signals into a single anomaly score.
    
    Args:
        df: DataFrame with features
        feature_columns: Columns to include in scoring
        weights: Optional weights for each feature
    
    Returns:
        DataFrame with anomaly scores
    """
    result_df = df.copy()
    
    # Default equal weights
    if weights is None:
        weights = {col: 1.0 / len(feature_columns) for col in feature_columns}
    
    # Calculate Z-scores for each feature
    z_scores = pd.DataFrame()
    for col in feature_columns:
        mean = df[col].mean()
        std = df[col].std()
        if std > 0:
            z_scores[col] = abs((df[col] - mean) / std)
        else:
            z_scores[col] = 0
    
    # Calculate weighted composite score
    result_df["anomaly_score"] = sum(
        z_scores[col] * weights.get(col, 1.0 / len(feature_columns))
        for col in feature_columns
    )
    
    # Normalize to 0-100
    max_score = result_df["anomaly_score"].max()
    if max_score > 0:
        result_df["anomaly_score"] = (result_df["anomaly_score"] / max_score * 100).round(1)
    
    # Flag anomalies
    threshold = result_df["anomaly_score"].quantile(0.9)
    result_df["is_ml_anomaly"] = result_df["anomaly_score"] > threshold
    
    return result_df
