"""
Monitoring Scheduler Module for DataPulse
Background scheduling for continuous data quality monitoring
"""

import sqlite3
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import os

# APScheduler for background jobs
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.cron import CronTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False


class CheckType(Enum):
    """Types of monitoring checks"""
    FRESHNESS = "freshness"
    VOLUME = "volume"
    NULL_RATE = "null_rate"
    SCHEMA = "schema"
    DUPLICATES = "duplicates"
    CUSTOM_RULE = "custom_rule"


class CheckStatus(Enum):
    """Status of a check execution"""
    SUCCESS = "success"
    WARNING = "warning"
    FAILURE = "failure"
    ERROR = "error"


class ScheduleInterval(Enum):
    """Pre-defined schedule intervals"""
    EVERY_5_MIN = "5min"
    EVERY_15_MIN = "15min"
    EVERY_30_MIN = "30min"
    HOURLY = "hourly"
    EVERY_6_HOURS = "6hours"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class MonitoringJob:
    """Defines a scheduled monitoring job"""
    id: str
    name: str
    table_name: str
    check_type: CheckType
    schedule_interval: ScheduleInterval
    enabled: bool
    
    # Thresholds
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    
    # For freshness checks
    max_age_hours: Optional[float] = None
    
    # For volume checks
    expected_min_rows: Optional[int] = None
    expected_max_rows: Optional[int] = None
    
    # For null rate checks
    column_name: Optional[str] = None
    max_null_rate: Optional[float] = None
    
    # Metadata
    created_at: str = ""
    last_run: Optional[str] = None
    last_status: Optional[str] = None
    
    # Alert settings
    alert_on_warning: bool = True
    alert_on_failure: bool = True
    alert_channels: List[str] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if self.alert_channels is None:
            self.alert_channels = ["slack"]


@dataclass
class CheckResult:
    """Result of a monitoring check"""
    job_id: str
    job_name: str
    table_name: str
    check_type: str
    status: CheckStatus
    timestamp: str
    
    # Results
    current_value: Optional[float] = None
    expected_value: Optional[float] = None
    threshold: Optional[float] = None
    
    # Details
    message: str = ""
    details: Dict = None
    
    # Alert info
    alert_sent: bool = False
    alert_channel: Optional[str] = None


class MonitoringStore:
    """SQLite storage for monitoring results"""
    
    def __init__(self, db_path: str = "monitoring.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monitoring_jobs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                table_name TEXT NOT NULL,
                check_type TEXT NOT NULL,
                schedule_interval TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                config TEXT,
                created_at TEXT,
                last_run TEXT,
                last_status TEXT
            )
        """)
        
        # Results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS check_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                job_name TEXT,
                table_name TEXT,
                check_type TEXT,
                status TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                current_value REAL,
                expected_value REAL,
                threshold REAL,
                message TEXT,
                details TEXT,
                alert_sent INTEGER DEFAULT 0,
                FOREIGN KEY (job_id) REFERENCES monitoring_jobs(id)
            )
        """)
        
        # Alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                result_id INTEGER,
                severity TEXT,
                message TEXT,
                channel TEXT,
                sent_at TEXT,
                acknowledged INTEGER DEFAULT 0,
                acknowledged_by TEXT,
                acknowledged_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_job(self, job: MonitoringJob):
        """Save or update a monitoring job"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        config = json.dumps({
            "warning_threshold": job.warning_threshold,
            "critical_threshold": job.critical_threshold,
            "max_age_hours": job.max_age_hours,
            "expected_min_rows": job.expected_min_rows,
            "expected_max_rows": job.expected_max_rows,
            "column_name": job.column_name,
            "max_null_rate": job.max_null_rate,
            "alert_on_warning": job.alert_on_warning,
            "alert_on_failure": job.alert_on_failure,
            "alert_channels": job.alert_channels
        })
        
        cursor.execute("""
            INSERT OR REPLACE INTO monitoring_jobs 
            (id, name, table_name, check_type, schedule_interval, enabled, config, created_at, last_run, last_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job.id, job.name, job.table_name, job.check_type.value,
            job.schedule_interval.value, 1 if job.enabled else 0,
            config, job.created_at, job.last_run, job.last_status
        ))
        
        conn.commit()
        conn.close()
    
    def get_job(self, job_id: str) -> Optional[MonitoringJob]:
        """Get a job by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM monitoring_jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_job(row)
    
    def get_all_jobs(self) -> List[MonitoringJob]:
        """Get all monitoring jobs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM monitoring_jobs ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_job(row) for row in rows]
    
    def get_enabled_jobs(self) -> List[MonitoringJob]:
        """Get all enabled jobs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM monitoring_jobs WHERE enabled = 1")
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_job(row) for row in rows]
    
    def _row_to_job(self, row) -> MonitoringJob:
        """Convert database row to MonitoringJob"""
        config = json.loads(row[6]) if row[6] else {}
        
        return MonitoringJob(
            id=row[0],
            name=row[1],
            table_name=row[2],
            check_type=CheckType(row[3]),
            schedule_interval=ScheduleInterval(row[4]),
            enabled=bool(row[5]),
            warning_threshold=config.get("warning_threshold"),
            critical_threshold=config.get("critical_threshold"),
            max_age_hours=config.get("max_age_hours"),
            expected_min_rows=config.get("expected_min_rows"),
            expected_max_rows=config.get("expected_max_rows"),
            column_name=config.get("column_name"),
            max_null_rate=config.get("max_null_rate"),
            created_at=row[7],
            last_run=row[8],
            last_status=row[9],
            alert_on_warning=config.get("alert_on_warning", True),
            alert_on_failure=config.get("alert_on_failure", True),
            alert_channels=config.get("alert_channels", ["slack"])
        )
    
    def delete_job(self, job_id: str):
        """Delete a job"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM monitoring_jobs WHERE id = ?", (job_id,))
        conn.commit()
        conn.close()
    
    def toggle_job(self, job_id: str, enabled: bool):
        """Enable or disable a job"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE monitoring_jobs SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, job_id)
        )
        conn.commit()
        conn.close()
    
    def save_result(self, result: CheckResult) -> int:
        """Save a check result"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO check_results 
            (job_id, job_name, table_name, check_type, status, timestamp, 
             current_value, expected_value, threshold, message, details, alert_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.job_id, result.job_name, result.table_name, result.check_type,
            result.status.value, result.timestamp, result.current_value,
            result.expected_value, result.threshold, result.message,
            json.dumps(result.details) if result.details else None,
            1 if result.alert_sent else 0
        ))
        
        result_id = cursor.lastrowid
        
        # Update job's last run info
        cursor.execute("""
            UPDATE monitoring_jobs 
            SET last_run = ?, last_status = ?
            WHERE id = ?
        """, (result.timestamp, result.status.value, result.job_id))
        
        conn.commit()
        conn.close()
        
        return result_id
    
    def get_results(self, job_id: str = None, limit: int = 100) -> List[Dict]:
        """Get check results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if job_id:
            cursor.execute(
                "SELECT * FROM check_results WHERE job_id = ? ORDER BY timestamp DESC LIMIT ?",
                (job_id, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM check_results ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "job_id": row[1],
                "job_name": row[2],
                "table_name": row[3],
                "check_type": row[4],
                "status": row[5],
                "timestamp": row[6],
                "current_value": row[7],
                "expected_value": row[8],
                "threshold": row[9],
                "message": row[10],
                "details": json.loads(row[11]) if row[11] else None,
                "alert_sent": bool(row[12])
            })
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total jobs
        cursor.execute("SELECT COUNT(*) FROM monitoring_jobs")
        total_jobs = cursor.fetchone()[0]
        
        # Enabled jobs
        cursor.execute("SELECT COUNT(*) FROM monitoring_jobs WHERE enabled = 1")
        enabled_jobs = cursor.fetchone()[0]
        
        # Results in last 24 hours
        yesterday = (datetime.now() - timedelta(hours=24)).isoformat()
        cursor.execute(
            "SELECT COUNT(*) FROM check_results WHERE timestamp > ?",
            (yesterday,)
        )
        checks_24h = cursor.fetchone()[0]
        
        # Failures in last 24 hours
        cursor.execute(
            "SELECT COUNT(*) FROM check_results WHERE timestamp > ? AND status = 'failure'",
            (yesterday,)
        )
        failures_24h = cursor.fetchone()[0]
        
        # Success rate
        cursor.execute(
            "SELECT COUNT(*) FROM check_results WHERE timestamp > ? AND status = 'success'",
            (yesterday,)
        )
        successes_24h = cursor.fetchone()[0]
        
        success_rate = (successes_24h / checks_24h * 100) if checks_24h > 0 else 100
        
        conn.close()
        
        return {
            "total_jobs": total_jobs,
            "enabled_jobs": enabled_jobs,
            "checks_24h": checks_24h,
            "failures_24h": failures_24h,
            "success_rate": round(success_rate, 1)
        }


class MonitoringScheduler:
    """Background scheduler for monitoring jobs"""
    
    def __init__(self, store: MonitoringStore, check_executor: Callable = None):
        self.store = store
        self.check_executor = check_executor or self._default_executor
        self.scheduler = None
        self._running = False
        
        if SCHEDULER_AVAILABLE:
            self.scheduler = BackgroundScheduler()
    
    def start(self):
        """Start the scheduler"""
        if not SCHEDULER_AVAILABLE:
            print("APScheduler not available. Install with: pip install apscheduler")
            return False
        
        if self._running:
            return True
        
        # Load and schedule all enabled jobs
        jobs = self.store.get_enabled_jobs()
        for job in jobs:
            self._schedule_job(job)
        
        self.scheduler.start()
        self._running = True
        print(f"Scheduler started with {len(jobs)} jobs")
        return True
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler and self._running:
            self.scheduler.shutdown()
            self._running = False
            print("Scheduler stopped")
    
    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self._running
    
    def _get_trigger(self, interval: ScheduleInterval):
        """Convert interval to APScheduler trigger"""
        triggers = {
            ScheduleInterval.EVERY_5_MIN: IntervalTrigger(minutes=5),
            ScheduleInterval.EVERY_15_MIN: IntervalTrigger(minutes=15),
            ScheduleInterval.EVERY_30_MIN: IntervalTrigger(minutes=30),
            ScheduleInterval.HOURLY: IntervalTrigger(hours=1),
            ScheduleInterval.EVERY_6_HOURS: IntervalTrigger(hours=6),
            ScheduleInterval.DAILY: CronTrigger(hour=6, minute=0),  # 6 AM daily
            ScheduleInterval.WEEKLY: CronTrigger(day_of_week='mon', hour=6, minute=0),
        }
        return triggers.get(interval, IntervalTrigger(hours=1))
    
    def _schedule_job(self, job: MonitoringJob):
        """Schedule a single job"""
        if not self.scheduler:
            return
        
        trigger = self._get_trigger(job.schedule_interval)
        
        self.scheduler.add_job(
            func=self._run_job,
            trigger=trigger,
            id=job.id,
            name=job.name,
            args=[job],
            replace_existing=True
        )
    
    def add_job(self, job: MonitoringJob):
        """Add a new job"""
        self.store.save_job(job)
        if self._running and job.enabled:
            self._schedule_job(job)
    
    def get_jobs(self):
        """Get all scheduled jobs from APScheduler"""
        if self.scheduler and self._running:
            return self.scheduler.get_jobs()
        return []
    
    def get_all_jobs(self) -> List[MonitoringJob]:
        """Get all monitoring jobs from store"""
        return self.store.get_all_jobs()
    
    def remove_job(self, job_id: str):
        """Remove a job"""
        self.store.delete_job(job_id)
        if self.scheduler:
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass
    
    def enable_job(self, job_id: str):
        """Enable a job"""
        self.store.toggle_job(job_id, True)
        job = self.store.get_job(job_id)
        if job and self._running:
            self._schedule_job(job)
    
    def disable_job(self, job_id: str):
        """Disable a job"""
        self.store.toggle_job(job_id, False)
        if self.scheduler:
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass
    
    def run_job_now(self, job_id: str) -> CheckResult:
        """Run a job immediately"""
        job = self.store.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        return self._run_job(job)
    
    def _run_job(self, job: MonitoringJob) -> CheckResult:
        """Execute a monitoring job"""
        result = self.check_executor(job)
        self.store.save_result(result)
        
        # Send alert if needed
        if result.status == CheckStatus.FAILURE and job.alert_on_failure:
            self._send_alert(job, result)
        elif result.status == CheckStatus.WARNING and job.alert_on_warning:
            self._send_alert(job, result)
        
        return result
    
    def _send_alert(self, job: MonitoringJob, result: CheckResult):
        """Send alert for a check result"""
        # This would integrate with the notifications module
        print(f"ALERT: {job.name} - {result.status.value}: {result.message}")
        result.alert_sent = True
    
    def _default_executor(self, job: MonitoringJob) -> CheckResult:
        """Default check executor (mock implementation)"""
        # In production, this would actually run the checks against BigQuery
        import random
        
        status = random.choices(
            [CheckStatus.SUCCESS, CheckStatus.WARNING, CheckStatus.FAILURE],
            weights=[0.8, 0.15, 0.05]
        )[0]
        
        return CheckResult(
            job_id=job.id,
            job_name=job.name,
            table_name=job.table_name,
            check_type=job.check_type.value,
            status=status,
            timestamp=datetime.now().isoformat(),
            current_value=random.uniform(0, 100),
            threshold=job.warning_threshold,
            message=f"{job.check_type.value} check completed with status: {status.value}",
            details={"executed_at": datetime.now().isoformat()}
        )


def create_freshness_job(
    table_name: str,
    max_age_hours: float,
    interval: ScheduleInterval = ScheduleInterval.HOURLY,
    name: str = None
) -> MonitoringJob:
    """Helper to create a freshness monitoring job"""
    import uuid
    
    return MonitoringJob(
        id=f"freshness_{uuid.uuid4().hex[:8]}",
        name=name or f"Freshness: {table_name}",
        table_name=table_name,
        check_type=CheckType.FRESHNESS,
        schedule_interval=interval,
        enabled=True,
        max_age_hours=max_age_hours,
        warning_threshold=max_age_hours * 0.8,
        critical_threshold=max_age_hours
    )


def create_volume_job(
    table_name: str,
    expected_min: int,
    expected_max: int,
    interval: ScheduleInterval = ScheduleInterval.HOURLY,
    name: str = None
) -> MonitoringJob:
    """Helper to create a volume monitoring job"""
    import uuid
    
    return MonitoringJob(
        id=f"volume_{uuid.uuid4().hex[:8]}",
        name=name or f"Volume: {table_name}",
        table_name=table_name,
        check_type=CheckType.VOLUME,
        schedule_interval=interval,
        enabled=True,
        expected_min_rows=expected_min,
        expected_max_rows=expected_max
    )


def create_null_rate_job(
    table_name: str,
    column_name: str,
    max_null_rate: float,
    interval: ScheduleInterval = ScheduleInterval.HOURLY,
    name: str = None
) -> MonitoringJob:
    """Helper to create a null rate monitoring job"""
    import uuid
    
    return MonitoringJob(
        id=f"null_{uuid.uuid4().hex[:8]}",
        name=name or f"Null Rate: {table_name}.{column_name}",
        table_name=table_name,
        check_type=CheckType.NULL_RATE,
        schedule_interval=interval,
        enabled=True,
        column_name=column_name,
        max_null_rate=max_null_rate,
        warning_threshold=max_null_rate * 0.8,
        critical_threshold=max_null_rate
    )


# Global scheduler instance
_scheduler_instance = None


def get_scheduler() -> MonitoringScheduler:
    """Get or create the global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        store = MonitoringStore()
        _scheduler_instance = MonitoringScheduler(store)
    return _scheduler_instance


def generate_sample_jobs() -> List[MonitoringJob]:
    """Generate sample monitoring jobs for demo"""
    return [
        create_freshness_job("analytics.orders", max_age_hours=2, interval=ScheduleInterval.EVERY_15_MIN),
        create_freshness_job("analytics.customers", max_age_hours=4, interval=ScheduleInterval.HOURLY),
        create_volume_job("analytics.events", expected_min=10000, expected_max=100000, interval=ScheduleInterval.EVERY_30_MIN),
        create_null_rate_job("analytics.orders", "customer_id", max_null_rate=0.01, interval=ScheduleInterval.HOURLY),
        create_null_rate_job("analytics.customers", "email", max_null_rate=0.05, interval=ScheduleInterval.DAILY),
    ]
