"""
Mock data generator for testing and demos
Enterprise features to compete with Bigeye/Datafold/Anomalo
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional


def generate_mock_table_list():
    """Generate a list of mock tables"""
    return [
        {"table_name": "sales_daily", "dataset": "analytics", "row_count": 2500000},
        {"table_name": "user_events", "dataset": "raw", "row_count": 15000000},
        {"table_name": "transactions", "dataset": "finance", "row_count": 500000},
    ]


def generate_mock_row_counts(table_name: str, days: int = 30) -> pd.DataFrame:
    """Generate mock row count data with some anomalies"""
    np.random.seed(42)  # For reproducibility
    
    dates = [datetime.now() - timedelta(days=x) for x in range(days, 0, -1)]
    
    # Base row count with some variance
    if table_name == "sales_daily":
        base_count = 85000
        variance = 5000
    elif table_name == "user_events":
        base_count = 500000
        variance = 50000
    else:
        base_count = 15000
        variance = 2000
    
    row_counts = []
    for i, date in enumerate(dates):
        count = base_count + np.random.randint(-variance, variance)
        
        # Inject anomalies
        if i == len(dates) - 3:  # 3 days ago - big drop
            count = int(base_count * 0.53)  # 47% drop
        if i == len(dates) - 7:  # 7 days ago - spike
            count = int(base_count * 1.4)  # 40% spike
            
        row_counts.append(count)
    
    return pd.DataFrame({
        "date": dates,
        "row_count": row_counts
    })


def generate_mock_null_rates(table_name: str, days: int = 30) -> pd.DataFrame:
    """Generate mock null rate data with anomalies"""
    np.random.seed(123)
    
    dates = [datetime.now() - timedelta(days=x) for x in range(days, 0, -1)]
    
    # Column info varies by table
    if table_name == "sales_daily":
        columns = ["customer_id", "amount", "product_id"]
        base_null_rates = [0.02, 0.001, 0.005]  # 2%, 0.1%, 0.5%
    elif table_name == "user_events":
        columns = ["user_id", "event_type", "session_id"]
        base_null_rates = [0.01, 0.0, 0.03]
    else:
        columns = ["id", "value", "timestamp"]
        base_null_rates = [0.0, 0.02, 0.01]
    
    data = []
    for i, date in enumerate(dates):
        for col, base_rate in zip(columns, base_null_rates):
            rate = base_rate + np.random.uniform(-0.005, 0.005)
            rate = max(0, rate)  # Can't be negative
            
            # Inject anomaly on customer_id column
            if col == "customer_id" and i == len(dates) - 4:  # 4 days ago
                rate = 0.12  # Spike to 12%
            
            data.append({
                "date": date,
                "column_name": col,
                "null_rate": rate
            })
    
    return pd.DataFrame(data)


def generate_mock_column_stats(table_name: str) -> pd.DataFrame:
    """Generate mock column statistics"""
    if table_name == "sales_daily":
        return pd.DataFrame([
            {"column_name": "customer_id", "data_type": "STRING", "null_count": 1700, "total_count": 85000, "distinct_count": 45000},
            {"column_name": "amount", "data_type": "FLOAT64", "null_count": 85, "total_count": 85000, "distinct_count": 8500},
            {"column_name": "product_id", "data_type": "STRING", "null_count": 425, "total_count": 85000, "distinct_count": 1200},
            {"column_name": "sale_date", "data_type": "DATE", "null_count": 0, "total_count": 85000, "distinct_count": 30},
            {"column_name": "region", "data_type": "STRING", "null_count": 0, "total_count": 85000, "distinct_count": 5},
        ])
    elif table_name == "user_events":
        return pd.DataFrame([
            {"column_name": "user_id", "data_type": "STRING", "null_count": 5000, "total_count": 500000, "distinct_count": 125000},
            {"column_name": "event_type", "data_type": "STRING", "null_count": 0, "total_count": 500000, "distinct_count": 25},
            {"column_name": "session_id", "data_type": "STRING", "null_count": 15000, "total_count": 500000, "distinct_count": 200000},
            {"column_name": "timestamp", "data_type": "TIMESTAMP", "null_count": 0, "total_count": 500000, "distinct_count": 500000},
        ])
    else:
        return pd.DataFrame([
            {"column_name": "id", "data_type": "STRING", "null_count": 0, "total_count": 15000, "distinct_count": 15000},
            {"column_name": "value", "data_type": "FLOAT64", "null_count": 300, "total_count": 15000, "distinct_count": 5000},
            {"column_name": "timestamp", "data_type": "TIMESTAMP", "null_count": 150, "total_count": 15000, "distinct_count": 15000},
        ])


# =============================================================================
# ENTERPRISE MOCK DATA - For Bigeye/Datafold/Anomalo competing features
# =============================================================================


def generate_mock_schema_snapshot(table_name: str, version: str = "current") -> pd.DataFrame:
    """Generate mock schema snapshots for schema change detection"""
    
    if table_name == "sales_daily":
        if version == "current":
            return pd.DataFrame([
                {"column_name": "customer_id", "data_type": "STRING"},
                {"column_name": "amount", "data_type": "FLOAT64"},
                {"column_name": "product_id", "data_type": "STRING"},
                {"column_name": "sale_date", "data_type": "DATE"},
                {"column_name": "region", "data_type": "STRING"},
                {"column_name": "discount_pct", "data_type": "FLOAT64"},  # New column
            ])
        else:  # previous
            return pd.DataFrame([
                {"column_name": "customer_id", "data_type": "STRING"},
                {"column_name": "amount", "data_type": "FLOAT64"},
                {"column_name": "product_id", "data_type": "INTEGER"},  # Type changed
                {"column_name": "sale_date", "data_type": "DATE"},
                {"column_name": "region", "data_type": "STRING"},
                {"column_name": "currency", "data_type": "STRING"},  # Removed column
            ])
    else:
        # Default schema
        if version == "current":
            return pd.DataFrame([
                {"column_name": "id", "data_type": "STRING"},
                {"column_name": "value", "data_type": "FLOAT64"},
                {"column_name": "timestamp", "data_type": "TIMESTAMP"},
            ])
        else:
            return pd.DataFrame([
                {"column_name": "id", "data_type": "STRING"},
                {"column_name": "value", "data_type": "FLOAT64"},
                {"column_name": "timestamp", "data_type": "TIMESTAMP"},
            ])


def generate_mock_freshness_data(table_name: str) -> Dict:
    """Generate mock freshness data for staleness detection"""
    
    # Simulate different freshness states
    freshness_scenarios = {
        "sales_daily": {
            "last_update": datetime.now() - timedelta(hours=2),
            "expected_frequency_hours": 24,
            "is_fresh": True
        },
        "user_events": {
            "last_update": datetime.now() - timedelta(hours=38),  # Stale!
            "expected_frequency_hours": 24,
            "is_fresh": False
        },
        "transactions": {
            "last_update": datetime.now() - timedelta(hours=6),
            "expected_frequency_hours": 4,  # Should update every 4 hours
            "is_fresh": False
        }
    }
    
    return freshness_scenarios.get(table_name, {
        "last_update": datetime.now() - timedelta(hours=1),
        "expected_frequency_hours": 24,
        "is_fresh": True
    })


def generate_mock_distribution_data(table_name: str, column_name: str) -> Dict[str, pd.Series]:
    """Generate mock distribution data for distribution shift detection"""
    np.random.seed(42)
    
    if table_name == "sales_daily" and column_name == "amount":
        # Historical: Normal distribution around $100
        historical = pd.Series(np.random.normal(100, 25, 1000))
        # Current: Shifted distribution (prices increased)
        current = pd.Series(np.random.normal(120, 30, 200))  # Mean shifted up
    elif table_name == "user_events" and column_name == "session_duration":
        # Historical: Log-normal distribution
        historical = pd.Series(np.random.lognormal(3, 1, 1000))
        # Current: Similar distribution
        current = pd.Series(np.random.lognormal(3, 1, 200))
    else:
        # Default: No shift
        historical = pd.Series(np.random.normal(50, 10, 1000))
        current = pd.Series(np.random.normal(50, 10, 200))
    
    return {"historical": historical, "current": current}


def generate_mock_duplicate_data(table_name: str) -> pd.DataFrame:
    """Generate mock data with duplicates for duplicate detection"""
    np.random.seed(42)
    
    if table_name == "sales_daily":
        n_rows = 1000
        n_duplicates = 35  # 3.5% duplicates
        
        # Generate unique records
        data = {
            "transaction_id": [f"TXN{i:06d}" for i in range(n_rows - n_duplicates)],
            "customer_id": np.random.choice([f"CUST{i:04d}" for i in range(500)], n_rows - n_duplicates),
            "amount": np.random.uniform(10, 500, n_rows - n_duplicates),
            "sale_date": [datetime.now() - timedelta(days=np.random.randint(0, 30)) 
                         for _ in range(n_rows - n_duplicates)]
        }
        df = pd.DataFrame(data)
        
        # Add duplicates
        duplicates = df.sample(n_duplicates, random_state=42)
        df = pd.concat([df, duplicates], ignore_index=True)
        
        return df
    else:
        # Default: minimal duplicates
        n_rows = 500
        data = {
            "id": [f"ID{i:05d}" for i in range(n_rows)],
            "value": np.random.uniform(0, 100, n_rows)
        }
        return pd.DataFrame(data)


def generate_mock_cardinality_history(table_name: str, column_name: str) -> Dict:
    """Generate mock cardinality history for cardinality anomaly detection"""
    
    cardinality_data = {
        ("sales_daily", "customer_id"): {
            "current_distinct": 48000,
            "historical_distinct": 45000,
            "total_rows": 85000
        },
        ("sales_daily", "product_id"): {
            "current_distinct": 800,  # Dropped significantly!
            "historical_distinct": 1200,
            "total_rows": 85000
        },
        ("user_events", "user_id"): {
            "current_distinct": 125000,
            "historical_distinct": 120000,
            "total_rows": 500000
        }
    }
    
    return cardinality_data.get((table_name, column_name), {
        "current_distinct": 1000,
        "historical_distinct": 1000,
        "total_rows": 10000
    })


def generate_mock_rule_test_data(table_name: str) -> pd.DataFrame:
    """Generate mock data for custom rule validation testing"""
    np.random.seed(42)
    
    if table_name == "sales_daily":
        n_rows = 1000
        
        # Generate data with some rule violations
        data = {
            "customer_id": [f"CUST{i:04d}" if np.random.random() > 0.02 else None 
                           for i in range(n_rows)],  # 2% nulls
            "amount": np.concatenate([
                np.random.uniform(10, 1000, n_rows - 5),
                [-50, -20, 1500, 2000, 5000]  # 5 violations: negative + over limit
            ]),
            "email": [f"user{i}@example.com" if np.random.random() > 0.05 else "invalid-email"
                     for i in range(n_rows)],  # 5% invalid emails
            "product_id": [f"PROD{np.random.randint(1, 1000):04d}" for _ in range(n_rows)]
        }
        return pd.DataFrame(data)
    else:
        return pd.DataFrame({
            "id": range(100),
            "value": np.random.uniform(0, 100, 100)
        })


def generate_mock_comparison_data(table_name: str) -> Dict[str, pd.DataFrame]:
    """Generate mock data for data comparison/diff feature"""
    np.random.seed(42)
    
    if table_name == "sales_daily":
        # Previous snapshot
        previous = pd.DataFrame({
            "transaction_id": [f"TXN{i:06d}" for i in range(100)],
            "customer_id": [f"CUST{np.random.randint(1, 500):04d}" for _ in range(100)],
            "amount": np.random.uniform(50, 200, 100).round(2),
            "status": ["completed"] * 95 + ["pending"] * 5
        })
        
        # Current snapshot with changes
        current = previous.copy()
        
        # Modify some values
        current.loc[10:15, "amount"] = current.loc[10:15, "amount"] * 1.1  # 6 value changes
        current.loc[50:52, "status"] = "refunded"  # 3 status changes
        
        # Add new rows
        new_rows = pd.DataFrame({
            "transaction_id": [f"TXN{i:06d}" for i in range(100, 108)],
            "customer_id": [f"CUST{np.random.randint(1, 500):04d}" for _ in range(8)],
            "amount": np.random.uniform(50, 200, 8).round(2),
            "status": ["completed"] * 8
        })
        current = pd.concat([current, new_rows], ignore_index=True)
        
        # Remove some rows (simulate deletions)
        current = current.drop(index=[95, 96, 97]).reset_index(drop=True)
        
        return {"current": current, "previous": previous}
    else:
        df = pd.DataFrame({
            "id": range(50),
            "value": np.random.uniform(0, 100, 50)
        })
        return {"current": df, "previous": df}


def generate_mock_historical_values(table_name: str, metric: str = "row_count") -> pd.Series:
    """Generate historical values for trend forecasting"""
    np.random.seed(42)
    
    if metric == "row_count":
        # Generate trending data with some noise
        base = 80000
        trend = np.linspace(0, 10000, 30)  # Upward trend
        noise = np.random.normal(0, 2000, 30)
        values = base + trend + noise
    else:
        # Generic metric
        values = np.random.uniform(100, 200, 30)
    
    return pd.Series(values)
