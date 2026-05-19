"""
Column Profiler for DataPulse
Detailed statistics and analysis for each column
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
import re


def profile_column(
    df: pd.DataFrame,
    column_name: str
) -> Dict[str, Any]:
    """
    Generate comprehensive profile for a single column
    
    Args:
        df: DataFrame containing the column
        column_name: Name of column to profile
    
    Returns:
        Dictionary with column statistics
    """
    if column_name not in df.columns:
        return {"error": f"Column '{column_name}' not found"}
    
    col = df[column_name]
    total_rows = len(col)
    
    # Basic stats
    null_count = col.isnull().sum()
    non_null_count = total_rows - null_count
    null_pct = (null_count / total_rows * 100) if total_rows > 0 else 0
    
    # Distinct values
    distinct_count = col.nunique()
    distinct_pct = (distinct_count / non_null_count * 100) if non_null_count > 0 else 0
    
    # Determine column type
    inferred_type = infer_column_type(col)
    
    profile = {
        "column_name": column_name,
        "dtype": str(col.dtype),
        "inferred_type": inferred_type,
        "total_rows": total_rows,
        "null_count": int(null_count),
        "null_pct": round(null_pct, 2),
        "non_null_count": int(non_null_count),
        "distinct_count": int(distinct_count),
        "distinct_pct": round(distinct_pct, 2),
        "is_unique": distinct_count == non_null_count,
        "memory_usage": int(col.memory_usage(deep=True))
    }
    
    # Type-specific statistics
    if inferred_type == "numeric":
        profile.update(get_numeric_stats(col))
    elif inferred_type == "string":
        profile.update(get_string_stats(col))
    elif inferred_type == "datetime":
        profile.update(get_datetime_stats(col))
    elif inferred_type == "boolean":
        profile.update(get_boolean_stats(col))
    
    # Top values
    profile["top_values"] = get_top_values(col, n=5)
    
    # Data quality indicators
    profile["quality_score"] = calculate_quality_score(profile)
    profile["quality_issues"] = detect_quality_issues(profile, col)
    
    return profile


def infer_column_type(col: pd.Series) -> str:
    """Infer the semantic type of a column"""
    
    dtype = str(col.dtype)
    
    if pd.api.types.is_bool_dtype(col):
        return "boolean"
    elif pd.api.types.is_numeric_dtype(col):
        return "numeric"
    elif pd.api.types.is_datetime64_any_dtype(col):
        return "datetime"
    elif dtype == "object":
        # Try to infer from content
        sample = col.dropna().head(100)
        if len(sample) == 0:
            return "unknown"
        
        # Check if it's datetime-like
        try:
            pd.to_datetime(sample, errors='raise')
            return "datetime"
        except:
            pass
        
        # Check if it's numeric-like
        try:
            pd.to_numeric(sample, errors='raise')
            return "numeric"
        except:
            pass
        
        # Check if boolean-like
        unique_lower = set(str(v).lower() for v in sample.unique())
        if unique_lower.issubset({'true', 'false', 'yes', 'no', '1', '0', 't', 'f', 'y', 'n'}):
            return "boolean"
        
        return "string"
    
    return "unknown"


def get_numeric_stats(col: pd.Series) -> Dict:
    """Get statistics for numeric columns"""
    
    clean_col = col.dropna()
    
    if len(clean_col) == 0:
        return {}
    
    stats = {
        "mean": round(float(clean_col.mean()), 4),
        "std": round(float(clean_col.std()), 4),
        "min": float(clean_col.min()),
        "max": float(clean_col.max()),
        "median": float(clean_col.median()),
        "q1": float(clean_col.quantile(0.25)),
        "q3": float(clean_col.quantile(0.75)),
        "skewness": round(float(clean_col.skew()), 4),
        "kurtosis": round(float(clean_col.kurtosis()), 4),
        "zeros_count": int((clean_col == 0).sum()),
        "negative_count": int((clean_col < 0).sum()),
        "positive_count": int((clean_col > 0).sum()),
    }
    
    # IQR and outliers
    iqr = stats["q3"] - stats["q1"]
    lower_bound = stats["q1"] - 1.5 * iqr
    upper_bound = stats["q3"] + 1.5 * iqr
    outliers = ((clean_col < lower_bound) | (clean_col > upper_bound)).sum()
    
    stats["iqr"] = round(iqr, 4)
    stats["outlier_count"] = int(outliers)
    stats["outlier_pct"] = round(outliers / len(clean_col) * 100, 2)
    
    # Histogram data (10 bins)
    try:
        hist, bin_edges = np.histogram(clean_col, bins=10)
        stats["histogram"] = {
            "counts": hist.tolist(),
            "bin_edges": [round(b, 4) for b in bin_edges.tolist()]
        }
    except:
        stats["histogram"] = None
    
    return stats


def get_string_stats(col: pd.Series) -> Dict:
    """Get statistics for string columns"""
    
    clean_col = col.dropna().astype(str)
    
    if len(clean_col) == 0:
        return {}
    
    lengths = clean_col.str.len()
    
    stats = {
        "min_length": int(lengths.min()),
        "max_length": int(lengths.max()),
        "avg_length": round(float(lengths.mean()), 2),
        "empty_count": int((clean_col == "").sum()),
        "whitespace_only_count": int(clean_col.str.strip().eq("").sum()),
    }
    
    # Pattern detection
    stats["contains_digits"] = int(clean_col.str.contains(r'\d', regex=True).sum())
    stats["contains_special"] = int(clean_col.str.contains(r'[^a-zA-Z0-9\s]', regex=True).sum())
    stats["all_uppercase"] = int(clean_col.str.isupper().sum())
    stats["all_lowercase"] = int(clean_col.str.islower().sum())
    
    # Check for common patterns
    email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    phone_pattern = r'^[\d\-\+\(\)\s]+$'
    url_pattern = r'^https?://'
    
    email_matches = clean_col.str.match(email_pattern, na=False).sum()
    phone_matches = clean_col.str.match(phone_pattern, na=False).sum()
    url_matches = clean_col.str.match(url_pattern, na=False).sum()
    
    if email_matches > len(clean_col) * 0.8:
        stats["detected_pattern"] = "email"
    elif url_matches > len(clean_col) * 0.8:
        stats["detected_pattern"] = "url"
    elif phone_matches > len(clean_col) * 0.8:
        stats["detected_pattern"] = "phone"
    else:
        stats["detected_pattern"] = None
    
    return stats


def get_datetime_stats(col: pd.Series) -> Dict:
    """Get statistics for datetime columns"""
    
    try:
        clean_col = pd.to_datetime(col.dropna())
    except:
        return {}
    
    if len(clean_col) == 0:
        return {}
    
    stats = {
        "min_date": str(clean_col.min()),
        "max_date": str(clean_col.max()),
        "date_range_days": (clean_col.max() - clean_col.min()).days,
    }
    
    # Check for future dates
    now = pd.Timestamp.now()
    stats["future_dates_count"] = int((clean_col > now).sum())
    
    # Day of week distribution
    dow_counts = clean_col.dt.dayofweek.value_counts().to_dict()
    stats["day_of_week_distribution"] = {
        ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][k]: v 
        for k, v in dow_counts.items()
    }
    
    return stats


def get_boolean_stats(col: pd.Series) -> Dict:
    """Get statistics for boolean columns"""
    
    clean_col = col.dropna()
    
    if len(clean_col) == 0:
        return {}
    
    # Convert to boolean if needed
    if clean_col.dtype == 'object':
        true_vals = {'true', 'yes', '1', 't', 'y'}
        clean_col = clean_col.astype(str).str.lower().isin(true_vals)
    
    true_count = clean_col.sum()
    false_count = len(clean_col) - true_count
    
    return {
        "true_count": int(true_count),
        "false_count": int(false_count),
        "true_pct": round(true_count / len(clean_col) * 100, 2),
        "false_pct": round(false_count / len(clean_col) * 100, 2),
    }


def get_top_values(col: pd.Series, n: int = 5) -> List[Dict]:
    """Get top N most frequent values"""
    
    value_counts = col.value_counts().head(n)
    total = len(col.dropna())
    
    return [
        {
            "value": str(val)[:50],  # Truncate long values
            "count": int(count),
            "pct": round(count / total * 100, 2) if total > 0 else 0
        }
        for val, count in value_counts.items()
    ]


def calculate_quality_score(profile: Dict) -> int:
    """Calculate a data quality score (0-100) for the column"""
    
    score = 100
    
    # Penalize for nulls
    null_pct = profile.get("null_pct", 0)
    if null_pct > 50:
        score -= 30
    elif null_pct > 20:
        score -= 15
    elif null_pct > 5:
        score -= 5
    
    # Penalize for low cardinality in non-boolean
    if profile.get("inferred_type") not in ["boolean"] and profile.get("distinct_count", 1) == 1:
        score -= 20  # Constant column
    
    # Penalize for outliers in numeric
    if profile.get("outlier_pct", 0) > 10:
        score -= 10
    
    # Penalize for empty strings
    if profile.get("empty_count", 0) > 0:
        score -= 5
    
    return max(0, score)


def detect_quality_issues(profile: Dict, col: pd.Series) -> List[str]:
    """Detect potential data quality issues"""
    
    issues = []
    
    # High null rate
    if profile.get("null_pct", 0) > 20:
        issues.append(f"High null rate: {profile['null_pct']}%")
    
    # Constant column
    if profile.get("distinct_count", 0) == 1:
        issues.append("Constant value column (only 1 unique value)")
    
    # High cardinality (potential ID column)
    if profile.get("distinct_pct", 0) > 95 and profile.get("inferred_type") == "string":
        issues.append("High cardinality - possibly an ID column")
    
    # Outliers
    if profile.get("outlier_pct", 0) > 5:
        issues.append(f"Contains outliers: {profile.get('outlier_count', 0)} ({profile.get('outlier_pct', 0)}%)")
    
    # Empty strings
    if profile.get("empty_count", 0) > 0:
        issues.append(f"Contains {profile.get('empty_count', 0)} empty strings")
    
    # Negative values where unexpected
    if profile.get("negative_count", 0) > 0:
        col_name_lower = profile.get("column_name", "").lower()
        if any(kw in col_name_lower for kw in ["amount", "price", "qty", "quantity", "count", "age"]):
            issues.append(f"Contains {profile.get('negative_count', 0)} negative values (unexpected for this column)")
    
    # Future dates
    if profile.get("future_dates_count", 0) > 0:
        issues.append(f"Contains {profile.get('future_dates_count', 0)} future dates")
    
    return issues


def profile_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate profile for entire DataFrame
    
    Returns:
        Dictionary with overall stats and per-column profiles
    """
    
    overall = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "total_cells": len(df) * len(df.columns),
        "total_nulls": int(df.isnull().sum().sum()),
        "null_pct": round(df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100, 2),
        "memory_usage_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
        "duplicate_rows": int(df.duplicated().sum()),
        "profiled_at": datetime.now().isoformat()
    }
    
    # Categorize columns by type
    type_counts = {}
    columns = {}
    
    for col in df.columns:
        profile = profile_column(df, col)
        columns[col] = profile
        
        inferred_type = profile.get("inferred_type", "unknown")
        type_counts[inferred_type] = type_counts.get(inferred_type, 0) + 1
    
    overall["column_types"] = type_counts
    
    # Overall quality score (average of all columns)
    quality_scores = [c.get("quality_score", 100) for c in columns.values()]
    overall["quality_score"] = round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else 100
    
    return {
        "overall": overall,
        "columns": columns
    }
