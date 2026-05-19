"""
Historical Data Store for DataPulse
Track anomalies and health scores over time
Uses JSON file storage (can be extended to database)
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import pandas as pd


class HistoryStore:
    """Store and retrieve historical anomaly data"""
    
    def __init__(self, storage_path: str = "data/history"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, table_name: str) -> Path:
        """Get storage file path for a table"""
        safe_name = table_name.replace(".", "_").replace("/", "_")
        return self.storage_path / f"{safe_name}_history.json"
    
    def save_check_result(
        self,
        table_name: str,
        health_score: int,
        status: str,
        anomalies: List[Dict],
        metrics: Optional[Dict] = None
    ) -> bool:
        """
        Save a check result to history
        
        Args:
            table_name: Name of the table
            health_score: Overall health score
            status: Status string (Healthy, Warning, etc.)
            anomalies: List of detected anomalies
            metrics: Additional metrics to store
        """
        file_path = self._get_file_path(table_name)
        
        # Load existing history
        history = self._load_history(file_path)
        
        # Create new entry
        entry = {
            "timestamp": datetime.now().isoformat(),
            "health_score": health_score,
            "status": status,
            "anomaly_count": len(anomalies),
            "anomalies": anomalies[:20],  # Limit stored anomalies
            "metrics": metrics or {}
        }
        
        history["checks"].append(entry)
        
        # Keep only last 90 days
        cutoff = (datetime.now() - timedelta(days=90)).isoformat()
        history["checks"] = [
            c for c in history["checks"]
            if c["timestamp"] > cutoff
        ]
        
        history["last_updated"] = datetime.now().isoformat()
        history["table_name"] = table_name
        
        # Save
        try:
            with open(file_path, 'w') as f:
                json.dump(history, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Failed to save history: {e}")
            return False
    
    def _load_history(self, file_path: Path) -> Dict:
        """Load history from file"""
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "checks": [],
            "created_at": datetime.now().isoformat()
        }
    
    def get_history(
        self,
        table_name: str,
        days: int = 30
    ) -> List[Dict]:
        """Get check history for a table"""
        file_path = self._get_file_path(table_name)
        history = self._load_history(file_path)
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        return [
            c for c in history.get("checks", [])
            if c["timestamp"] > cutoff
        ]
    
    def get_health_trend(
        self,
        table_name: str,
        days: int = 30
    ) -> pd.DataFrame:
        """Get health score trend as DataFrame"""
        history = self.get_history(table_name, days)
        
        if not history:
            return pd.DataFrame()
        
        df = pd.DataFrame(history)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")
        
        return df[["timestamp", "health_score", "status", "anomaly_count"]]
    
    def get_anomaly_frequency(
        self,
        table_name: str,
        days: int = 30
    ) -> Dict[str, int]:
        """Get count of each anomaly type"""
        history = self.get_history(table_name, days)
        
        freq = {}
        for check in history:
            for anomaly in check.get("anomalies", []):
                metric = anomaly.get("metric", "unknown")
                freq[metric] = freq.get(metric, 0) + 1
        
        return dict(sorted(freq.items(), key=lambda x: x[1], reverse=True))
    
    def get_summary_stats(
        self,
        table_name: str,
        days: int = 30
    ) -> Dict:
        """Get summary statistics for a table"""
        history = self.get_history(table_name, days)
        
        if not history:
            return {
                "checks_count": 0,
                "avg_health_score": None,
                "min_health_score": None,
                "max_health_score": None,
                "total_anomalies": 0,
                "healthy_checks_pct": None
            }
        
        health_scores = [c["health_score"] for c in history]
        anomaly_counts = [c["anomaly_count"] for c in history]
        healthy_checks = sum(1 for c in history if c["status"] == "Healthy")
        
        return {
            "checks_count": len(history),
            "avg_health_score": round(sum(health_scores) / len(health_scores), 1),
            "min_health_score": min(health_scores),
            "max_health_score": max(health_scores),
            "total_anomalies": sum(anomaly_counts),
            "healthy_checks_pct": round(healthy_checks / len(history) * 100, 1)
        }
    
    def get_all_tables(self) -> List[str]:
        """Get list of all tables with history"""
        tables = []
        for file in self.storage_path.glob("*_history.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    if "table_name" in data:
                        tables.append(data["table_name"])
            except:
                pass
        return tables


def generate_mock_history(
    table_name: str,
    days: int = 30
) -> List[Dict]:
    """
    Generate mock historical data for demo purposes
    """
    import random
    
    history = []
    base_score = random.randint(75, 95)
    
    for i in range(days):
        date = datetime.now() - timedelta(days=days - i - 1)
        
        # Add some variation
        score_variation = random.randint(-15, 10)
        score = max(40, min(100, base_score + score_variation))
        
        # Occasionally have anomalies
        anomaly_count = 0
        anomalies = []
        
        if random.random() < 0.3:  # 30% chance of anomaly
            anomaly_count = random.randint(1, 3)
            anomaly_types = ["row_count", "null_rate", "distribution", "freshness"]
            for _ in range(anomaly_count):
                anomalies.append({
                    "metric": random.choice(anomaly_types),
                    "severity": random.choice(["medium", "high"]),
                    "type": random.choice(["spike", "drop", "shift"])
                })
            score = max(40, score - anomaly_count * 10)
        
        status = "Healthy" if score >= 80 else "Warning" if score >= 60 else "Critical"
        
        history.append({
            "timestamp": date.isoformat(),
            "health_score": score,
            "status": status,
            "anomaly_count": anomaly_count,
            "anomalies": anomalies,
            "metrics": {
                "row_count": random.randint(90000, 110000),
                "null_pct": round(random.uniform(0.01, 0.05), 3)
            }
        })
        
        # Trend the base score slightly
        base_score = max(70, min(95, base_score + random.randint(-2, 2)))
    
    return history
