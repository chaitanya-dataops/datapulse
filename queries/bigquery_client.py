"""
BigQuery client for fetching table metadata and statistics.
"""
import pandas as pd
from google.cloud import bigquery
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import config


def get_bq_client() -> bigquery.Client:
    """Get authenticated BigQuery client"""
    return bigquery.Client(project=config.GCP_PROJECT_ID)


def list_tables(dataset_id: Optional[str] = None) -> List[Dict]:
    """
    List all tables in a dataset.
    
    Args:
        dataset_id: BigQuery dataset ID. Uses config default if not provided.
    
    Returns:
        List of table info dictionaries
    """
    client = get_bq_client()
    dataset = dataset_id or config.BQ_DATASET
    
    tables = []
    for table in client.list_tables(f"{config.GCP_PROJECT_ID}.{dataset}"):
        tables.append({
            "table_name": table.table_id,
            "dataset": dataset,
            "full_name": f"{dataset}.{table.table_id}"
        })
    
    return tables


def get_row_count_history(
    dataset: str, 
    table_name: str, 
    days: int = 30
) -> pd.DataFrame:
    """
    Get daily row count history for a table.
    Uses INFORMATION_SCHEMA to get historical metadata.
    
    Note: INFORMATION_SCHEMA.TABLE_STORAGE stores daily snapshots.
    If not available, falls back to current count only.
    """
    client = get_bq_client()
    
    # Try to get historical data from TABLE_STORAGE_USAGE_TIMELINE (if available)
    # This requires appropriate permissions
    query = f"""
    SELECT
        DATE(creation_time) as date,
        SUM(total_rows) as row_count
    FROM `{config.GCP_PROJECT_ID}.{dataset}.INFORMATION_SCHEMA.PARTITIONS`
    WHERE table_name = '{table_name}'
    GROUP BY date
    ORDER BY date DESC
    LIMIT {days}
    """
    
    try:
        df = client.query(query).to_dataframe()
        if len(df) > 0:
            return df.sort_values("date")
    except Exception as e:
        print(f"Note: Could not get partition history: {e}")
    
    # Fallback: Get current row count and estimate history
    query_current = f"""
    SELECT
        COUNT(*) as row_count
    FROM `{config.GCP_PROJECT_ID}.{dataset}.{table_name}`
    """
    
    try:
        result = client.query(query_current).to_dataframe()
        current_count = result.iloc[0]["row_count"]
        
        # Create synthetic history (for demo purposes)
        # In production, you'd use a monitoring table
        dates = [datetime.now() - timedelta(days=x) for x in range(days, 0, -1)]
        return pd.DataFrame({
            "date": dates,
            "row_count": [current_count] * len(dates)
        })
    except Exception as e:
        print(f"Error getting row count: {e}")
        return pd.DataFrame(columns=["date", "row_count"])


def get_column_null_rates(
    dataset: str, 
    table_name: str,
    sample_size: int = 100000
) -> pd.DataFrame:
    """
    Calculate null rates for all columns in a table.
    Uses sampling for large tables to keep costs low.
    """
    client = get_bq_client()
    
    # First get column names
    schema_query = f"""
    SELECT column_name, data_type
    FROM `{config.GCP_PROJECT_ID}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
    WHERE table_name = '{table_name}'
    """
    
    try:
        columns_df = client.query(schema_query).to_dataframe()
    except Exception as e:
        print(f"Error getting schema: {e}")
        return pd.DataFrame()
    
    # Build null rate query
    null_checks = []
    for _, row in columns_df.iterrows():
        col = row["column_name"]
        null_checks.append(f"COUNTIF({col} IS NULL) / COUNT(*) as {col}_null_rate")
    
    if not null_checks:
        return pd.DataFrame()
    
    null_query = f"""
    SELECT
        {', '.join(null_checks)}
    FROM `{config.GCP_PROJECT_ID}.{dataset}.{table_name}`
    TABLESAMPLE SYSTEM ({min(100, sample_size * 100 // 1000000)} PERCENT)
    """
    
    try:
        result = client.query(null_query).to_dataframe()
        
        # Reshape to long format
        data = []
        for col in columns_df["column_name"]:
            null_rate_col = f"{col}_null_rate"
            if null_rate_col in result.columns:
                data.append({
                    "column_name": col,
                    "null_rate": result.iloc[0][null_rate_col],
                    "date": datetime.now()
                })
        
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Error calculating null rates: {e}")
        return pd.DataFrame()


def get_table_stats(dataset: str, table_name: str) -> Dict:
    """
    Get basic statistics about a table.
    """
    client = get_bq_client()
    
    query = f"""
    SELECT
        row_count,
        size_bytes,
        TIMESTAMP_MILLIS(last_modified_time) as last_modified
    FROM `{config.GCP_PROJECT_ID}.{dataset}.__TABLES__`
    WHERE table_id = '{table_name}'
    """
    
    try:
        result = client.query(query).to_dataframe()
        if len(result) > 0:
            row = result.iloc[0]
            return {
                "row_count": row["row_count"],
                "size_bytes": row["size_bytes"],
                "size_gb": row["size_bytes"] / (1024**3),
                "last_modified": row["last_modified"]
            }
    except Exception as e:
        print(f"Error getting table stats: {e}")
    
    return {}
