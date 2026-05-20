"""
Check Executor Module for DataPulse
Executes actual monitoring checks against data sources
"""

from datetime import datetime

from utils.scheduler import (
    MonitoringJob, CheckResult, CheckType, CheckStatus
)


class CheckExecutor:
    """Executes monitoring checks against data sources"""
    
    def __init__(self, use_bigquery: bool = False, project_id: str = None):
        # Parameters retained for backward compatibility with existing callers.
        self.use_bigquery = False
    
    def execute(self, job: MonitoringJob) -> CheckResult:
        """Execute a monitoring check"""
        try:
            if job.check_type == CheckType.FRESHNESS:
                return self._check_freshness(job)
            elif job.check_type == CheckType.VOLUME:
                return self._check_volume(job)
            elif job.check_type == CheckType.NULL_RATE:
                return self._check_null_rate(job)
            elif job.check_type == CheckType.SCHEMA:
                return self._check_schema(job)
            elif job.check_type == CheckType.DUPLICATES:
                return self._check_duplicates(job)
            else:
                return self._create_error_result(job, f"Unknown check type: {job.check_type}")
        except Exception as e:
            return self._create_error_result(job, str(e))
    
    def _check_freshness(self, job: MonitoringJob) -> CheckResult:
        """Check table freshness"""
        return self._check_freshness_mock(job)
    
    def _check_freshness_mock(self, job: MonitoringJob) -> CheckResult:
        """Mock freshness check"""
        import random
        
        # Simulate freshness with some variance
        hours_old = random.uniform(0.5, job.max_age_hours * 1.5 if job.max_age_hours else 12)
        max_age = job.max_age_hours or 24
        
        if hours_old > max_age:
            status = CheckStatus.FAILURE
            message = f"Table is {hours_old:.1f} hours old (threshold: {max_age}h)"
        elif hours_old > max_age * 0.8:
            status = CheckStatus.WARNING
            message = f"Table freshness approaching threshold"
        else:
            status = CheckStatus.SUCCESS
            message = f"Table is fresh ({hours_old:.1f}h old)"
        
        return CheckResult(
            job_id=job.id,
            job_name=job.name,
            table_name=job.table_name,
            check_type=job.check_type.value,
            status=status,
            timestamp=datetime.now().isoformat(),
            current_value=round(hours_old, 2),
            threshold=max_age,
            message=message
        )
    
    def _check_volume(self, job: MonitoringJob) -> CheckResult:
        """Check table volume"""
        return self._check_volume_mock(job)
    
    def _check_volume_mock(self, job: MonitoringJob) -> CheckResult:
        """Mock volume check"""
        import random
        
        min_rows = job.expected_min_rows or 1000
        max_rows = job.expected_max_rows or 100000
        
        # Usually within range, sometimes outside
        if random.random() < 0.9:
            row_count = random.randint(min_rows, max_rows)
            status = CheckStatus.SUCCESS
            message = f"Row count {row_count:,} within expected range"
        else:
            row_count = random.randint(0, min_rows - 1)
            status = CheckStatus.FAILURE
            message = f"Row count {row_count:,} below minimum {min_rows:,}"
        
        return CheckResult(
            job_id=job.id,
            job_name=job.name,
            table_name=job.table_name,
            check_type=job.check_type.value,
            status=status,
            timestamp=datetime.now().isoformat(),
            current_value=row_count,
            expected_value=(min_rows + max_rows) / 2,
            message=message
        )
    
    def _check_null_rate(self, job: MonitoringJob) -> CheckResult:
        """Check null rate"""
        return self._check_null_rate_mock(job)
    
    def _check_null_rate_mock(self, job: MonitoringJob) -> CheckResult:
        """Mock null rate check"""
        import random
        
        max_null = job.max_null_rate or 0.05
        
        # Usually good, sometimes bad
        if random.random() < 0.85:
            null_rate = random.uniform(0, max_null * 0.7)
            status = CheckStatus.SUCCESS
            message = f"Null rate {null_rate*100:.2f}% within acceptable range"
        elif random.random() < 0.5:
            null_rate = random.uniform(max_null * 0.8, max_null)
            status = CheckStatus.WARNING
            message = f"Null rate {null_rate*100:.2f}% approaching threshold"
        else:
            null_rate = random.uniform(max_null, max_null * 2)
            status = CheckStatus.FAILURE
            message = f"Null rate {null_rate*100:.2f}% exceeds threshold"
        
        return CheckResult(
            job_id=job.id,
            job_name=job.name,
            table_name=job.table_name,
            check_type=job.check_type.value,
            status=status,
            timestamp=datetime.now().isoformat(),
            current_value=round(null_rate * 100, 2),
            threshold=max_null * 100,
            message=message
        )
    
    def _check_schema(self, job: MonitoringJob) -> CheckResult:
        """Check for schema changes"""
        # Mock implementation - would compare current schema to baseline
        import random
        
        if random.random() < 0.95:
            status = CheckStatus.SUCCESS
            message = "No schema changes detected"
            details = {"columns_added": 0, "columns_removed": 0}
        else:
            status = CheckStatus.WARNING
            message = "Schema change detected: 1 column added"
            details = {"columns_added": 1, "columns_removed": 0, "new_columns": ["new_field"]}
        
        return CheckResult(
            job_id=job.id,
            job_name=job.name,
            table_name=job.table_name,
            check_type=job.check_type.value,
            status=status,
            timestamp=datetime.now().isoformat(),
            message=message,
            details=details
        )
    
    def _check_duplicates(self, job: MonitoringJob) -> CheckResult:
        """Check for duplicates"""
        # Mock implementation
        import random
        
        dup_rate = random.uniform(0, 0.1)
        
        if dup_rate < 0.01:
            status = CheckStatus.SUCCESS
            message = f"Duplicate rate: {dup_rate*100:.2f}%"
        elif dup_rate < 0.05:
            status = CheckStatus.WARNING
            message = f"Elevated duplicate rate: {dup_rate*100:.2f}%"
        else:
            status = CheckStatus.FAILURE
            message = f"High duplicate rate: {dup_rate*100:.2f}%"
        
        return CheckResult(
            job_id=job.id,
            job_name=job.name,
            table_name=job.table_name,
            check_type=job.check_type.value,
            status=status,
            timestamp=datetime.now().isoformat(),
            current_value=round(dup_rate * 100, 2),
            message=message
        )
    
    def _create_error_result(self, job: MonitoringJob, error_message: str) -> CheckResult:
        """Create an error result"""
        return CheckResult(
            job_id=job.id,
            job_name=job.name,
            table_name=job.table_name,
            check_type=job.check_type.value,
            status=CheckStatus.ERROR,
            timestamp=datetime.now().isoformat(),
            message=f"Check failed: {error_message}",
            details={"error": error_message}
        )


# Create default executor
def get_executor(use_bigquery: bool = False) -> CheckExecutor:
    """Get a check executor instance"""
    return CheckExecutor(use_bigquery=False)
