# LIFE-2: Archive and Purge Job Orchestration

**Task ID:** LIFE-2  
**Parent:** TASK-106  
**Category:** Lifecycle Engine Foundation  
**Points:** 4  
**Status:** Planned (Phase 1, after LIFE-1)  
**Created:** 2026-06-22

---

## 1. Objective

Implement archive and purge job execution with orchestration, dry-run mode, state tracking, and compensating transactions for failed operations.

---

## 2. Inputs

- LIFE-1: Policy evaluation engine
- Scheduler/orchestrator infrastructure (Apache Airflow, Kubernetes CronJob, or equivalent)
- Storage infrastructure (S3, Azure Blob, GCS)
- Database connection pool

---

## 3. Outputs

**Deliverables:**
- [ ] Archive job implementation
- [ ] Purge job implementation
- [ ] Dry-run validation workflow
- [ ] Job state tracking schema
- [ ] Compensating transaction logic
- [ ] Job orchestration orchestration template
- [ ] Performance benchmarks and tuning

---

## 4. Acceptance Criteria

1. **Archive Job:**
   - [ ] Move data to cold storage with retention metadata
   - [ ] Support S3 Glacier, Azure Archive, GCS Coldline
   - [ ] Preserve data integrity (checksums)
   - [ ] Parallel processing >10MB/s throughput
   - [ ] Automatic retry on transient failures

2. **Purge Job:**
   - [ ] Delete data from warm storage after retention expires
   - [ ] Respect legal holds (never purge held records)
   - [ ] >1000 records/second throughput
   - [ ] Batch operations for efficiency
   - [ ] Soft-delete option (mark as deleted, not hard-delete)

3. **Dry-Run Mode:**
   - [ ] Preview destructive operations without applying changes
   - [ ] Generate pre-execution report with counts
   - [ ] Show what would be archived/purged
   - [ ] 100% accuracy vs. actual execution

4. **Orchestration:**
   - [ ] Schedule archive jobs nightly
   - [ ] Schedule purge jobs weekly
   - [ ] Handle job dependencies
   - [ ] Support manual job triggers
   - [ ] Job monitoring and alerting integration

---

## 5. Implementation Details

### Archive Job Implementation (Python)

```python
import hashlib
import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3
import asyncio

class ArchiveJob:
    """Archive aged records to cold storage"""
    
    def __init__(self, config, policy_evaluator, db_connection):
        self.config = config
        self.evaluator = policy_evaluator
        self.db = db_connection
        self.s3 = boto3.client('s3')
        self.logger = logging.getLogger(__name__)
        self.metrics = {
            'records_processed': 0,
            'records_archived': 0,
            'bytes_archived': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
    
    def run(self, dry_run=False, batch_size=1000):
        """
        Execute archive job
        
        Args:
            dry_run: If True, don't actually move data
            batch_size: Records to process per batch
        """
        self.metrics['start_time'] = datetime.now(timezone.utc)
        self.logger.info(f"Archive job started (dry_run={dry_run})")
        
        try:
            for table_name in self._get_eligible_tables():
                self._archive_table(table_name, dry_run, batch_size)
            
            self._log_execution_summary(dry_run)
            return {'status': 'success', 'metrics': self.metrics}
        
        except Exception as e:
            self.logger.error(f"Archive job failed: {str(e)}")
            return {'status': 'failed', 'error': str(e), 'metrics': self.metrics}
        finally:
            self.metrics['end_time'] = datetime.now(timezone.utc)
    
    def _get_eligible_tables(self):
        """Get list of tables with active archive policies"""
        query = """
            SELECT DISTINCT domain
            FROM retention_policies
            WHERE enabled = true 
              AND archive_action != 'none'
        """
        result = self.db.query(query)
        return [row['domain'] for row in result]
    
    def _archive_table(self, table_name, dry_run, batch_size):
        """Archive records from a specific table"""
        offset = 0
        
        while True:
            # Fetch batch of eligible records
            records = self._fetch_eligible_records(table_name, batch_size, offset)
            if not records:
                break
            
            # Process batch
            for record in records:
                try:
                    self._archive_record(record, table_name, dry_run)
                except Exception as e:
                    self.logger.error(f"Failed to archive {record['record_id']}: {str(e)}")
                    self.metrics['errors'] += 1
                    self._log_archive_failure(record['record_id'], table_name, str(e))
            
            offset += batch_size
    
    def _fetch_eligible_records(self, table_name, batch_size, offset):
        """Fetch records eligible for archival"""
        query = f"""
            SELECT * FROM {table_name}
            WHERE lifecycle_state = 'operational'
              AND (
                DATEDIFF(NOW(), created_at) > 30  -- Placeholder: use policy engine
              )
            LIMIT %s OFFSET %s
        """
        return self.db.query(query, (batch_size, offset))
    
    def _archive_record(self, record, table_name, dry_run):
        """Archive a single record"""
        self.metrics['records_processed'] += 1
        
        # Serialize record to JSON
        record_json = self._serialize_record(record)
        record_bytes = record_json.encode('utf-8')
        
        # Calculate checksum
        checksum = hashlib.sha256(record_bytes).hexdigest()
        
        if not dry_run:
            # Upload to S3 Glacier
            archive_path = f"s3://{self.config['archive_bucket']}/{table_name}/{record['record_id']}.json.gz"
            
            self.s3.put_object(
                Bucket=self.config['archive_bucket'],
                Key=f"{table_name}/{record['record_id']}.json.gz",
                Body=record_bytes,
                StorageClass='GLACIER',
                Metadata={'checksum': checksum, 'original_table': table_name}
            )
            
            # Log archive metadata
            self._log_archive_metadata(record['record_id'], table_name, archive_path, checksum)
            
            # Update lifecycle state
            self.db.execute(f"""
                UPDATE {table_name}
                SET lifecycle_state = 'archived'
                WHERE record_id = %s
            """, (record['record_id'],))
        
        self.metrics['records_archived'] += 1
        self.metrics['bytes_archived'] += len(record_bytes)
    
    def _serialize_record(self, record):
        """Serialize record to JSON"""
        import json
        
        # Convert datetime objects to ISO strings
        serializable = {}
        for key, value in record.items():
            if isinstance(value, datetime):
                serializable[key] = value.isoformat()
            else:
                serializable[key] = value
        
        return json.dumps(serializable)
    
    def _log_archive_metadata(self, record_id, table_name, archive_path, checksum):
        """Log archive location and metadata"""
        query = """
            INSERT INTO archive_metadata
            (record_id, table_name, archive_location, archive_checksum, archived_at)
            VALUES (%s, %s, %s, %s, NOW())
        """
        self.db.execute(query, (record_id, table_name, archive_path, checksum))
    
    def _log_archive_failure(self, record_id, table_name, error):
        """Log failed archive attempt"""
        query = """
            INSERT INTO archive_failures
            (record_id, table_name, error_message, failed_at)
            VALUES (%s, %s, %s, NOW())
        """
        self.db.execute(query, (record_id, table_name, error))
    
    def _log_execution_summary(self, dry_run):
        """Log summary of archive execution"""
        duration = (self.metrics['end_time'] - self.metrics['start_time']).total_seconds()
        throughput_mbps = (self.metrics['bytes_archived'] / (1024*1024)) / max(duration, 1)
        
        self.logger.info(f"""
            Archive Job Summary (dry_run={dry_run}):
            - Records processed: {self.metrics['records_processed']}
            - Records archived: {self.metrics['records_archived']}
            - Bytes archived: {self.metrics['bytes_archived'] / (1024*1024):.2f} MB
            - Throughput: {throughput_mbps:.2f} MB/s
            - Errors: {self.metrics['errors']}
            - Duration: {duration:.2f}s
        """)
```

### Purge Job Implementation (Python)

```python
class PurgeJob:
    """Purge aged records from operational storage"""
    
    def __init__(self, config, policy_evaluator, db_connection):
        self.config = config
        self.evaluator = policy_evaluator
        self.db = db_connection
        self.logger = logging.getLogger(__name__)
        self.metrics = {
            'records_processed': 0,
            'records_purged': 0,
            'records_excluded_legal_hold': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
    
    def run(self, dry_run=False, batch_size=1000, soft_delete=True):
        """
        Execute purge job
        
        Args:
            dry_run: If True, don't actually delete data
            batch_size: Records to process per batch
            soft_delete: If True, mark as deleted; if False, hard delete
        """
        self.metrics['start_time'] = datetime.now(timezone.utc)
        self.logger.info(f"Purge job started (dry_run={dry_run}, soft_delete={soft_delete})")
        
        try:
            for table_name in self._get_eligible_tables():
                self._purge_table(table_name, dry_run, batch_size, soft_delete)
            
            self._log_execution_summary(dry_run)
            return {'status': 'success', 'metrics': self.metrics}
        
        except Exception as e:
            self.logger.error(f"Purge job failed: {str(e)}")
            return {'status': 'failed', 'error': str(e), 'metrics': self.metrics}
        finally:
            self.metrics['end_time'] = datetime.now(timezone.utc)
    
    def _get_eligible_tables(self):
        """Get list of tables with active purge policies"""
        query = """
            SELECT DISTINCT domain
            FROM retention_policies
            WHERE enabled = true AND purge_action != 'none'
        """
        result = self.db.query(query)
        return [row['domain'] for row in result]
    
    def _purge_table(self, table_name, dry_run, batch_size, soft_delete):
        """Purge records from a specific table"""
        offset = 0
        
        while True:
            # Fetch batch of purgeable records (excluding legal holds)
            records = self._fetch_purgeable_records(table_name, batch_size, offset)
            if not records:
                break
            
            # Process batch
            record_ids = [r['record_id'] for r in records]
            
            # Check for legal holds
            held_record_ids = self._check_legal_holds(record_ids, table_name)
            purgeable_ids = [r for r in record_ids if r not in held_record_ids]
            
            # Log held record exclusions
            self.metrics['records_excluded_legal_hold'] += len(held_record_ids)
            self._log_hold_exclusions(held_record_ids, table_name)
            
            # Purge non-held records
            if purgeable_ids and not dry_run:
                if soft_delete:
                    self._soft_delete(purgeable_ids, table_name)
                else:
                    self._hard_delete(purgeable_ids, table_name)
            
            self.metrics['records_purged'] += len(purgeable_ids)
            self.metrics['records_processed'] += len(record_ids)
            
            offset += batch_size
    
    def _fetch_purgeable_records(self, table_name, batch_size, offset):
        """Fetch records eligible for purge"""
        query = f"""
            SELECT * FROM {table_name}
            WHERE lifecycle_state = 'archived'
              AND DATEDIFF(NOW(), archived_at) > 30
            LIMIT %s OFFSET %s
        """
        return self.db.query(query, (batch_size, offset))
    
    def _check_legal_holds(self, record_ids, table_name):
        """Check which records have active legal holds"""
        if not record_ids:
            return []
        
        placeholders = ','.join(['%s'] * len(record_ids))
        query = f"""
            SELECT DISTINCT record_id
            FROM legal_holds
            WHERE table_name = %s
              AND record_id IN ({placeholders})
              AND hold_status = 'active'
        """
        params = [table_name] + record_ids
        results = self.db.query(query, params)
        return [r['record_id'] for r in results]
    
    def _soft_delete(self, record_ids, table_name):
        """Mark records as deleted (soft delete)"""
        placeholders = ','.join(['%s'] * len(record_ids))
        query = f"""
            UPDATE {table_name}
            SET 
              is_deleted = true,
              deleted_at = NOW(),
              lifecycle_state = 'purged'
            WHERE record_id IN ({placeholders})
        """
        self.db.execute(query, record_ids)
    
    def _hard_delete(self, record_ids, table_name):
        """Permanently delete records (hard delete)"""
        placeholders = ','.join(['%s'] * len(record_ids))
        query = f"""
            DELETE FROM {table_name}
            WHERE record_id IN ({placeholders})
        """
        self.db.execute(query, record_ids)
    
    def _log_hold_exclusions(self, held_record_ids, table_name):
        """Log records excluded due to legal holds"""
        for record_id in held_record_ids:
            query = """
                INSERT INTO hold_exclusion_log
                (record_id, table_name, excluded_at)
                VALUES (%s, %s, NOW())
            """
            self.db.execute(query, (record_id, table_name))
```

### Job Orchestration (Apache Airflow DAG)

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.date_time import DateTimeSensor
from datetime import datetime, timedelta

default_args = {
    'owner': 'data-platform',
    'start_date': datetime(2026, 1, 1),
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'on_failure_callback': lambda context: notify_failure(context)
}

dag = DAG(
    'lifecycle_archive_purge',
    default_args=default_args,
    schedule_interval='0 23 * * *',  # Daily at 11 PM
    tags=['lifecycle', 'archive', 'purge']
)

def run_archive_dry_run(**context):
    """Run archive job in dry-run mode"""
    from archive_job import ArchiveJob
    job = ArchiveJob(config, evaluator, db)
    result = job.run(dry_run=True)
    context['ti'].xcom_push(key='dry_run_result', value=result)

def run_archive(**context):
    """Run actual archive job"""
    from archive_job import ArchiveJob
    job = ArchiveJob(config, evaluator, db)
    result = job.run(dry_run=False)
    if result['status'] != 'success':
        raise Exception(f"Archive job failed: {result['error']}")
    context['ti'].xcom_push(key='archive_result', value=result)

def run_purge_dry_run(**context):
    """Run purge job in dry-run mode"""
    from purge_job import PurgeJob
    job = PurgeJob(config, evaluator, db)
    result = job.run(dry_run=True)
    context['ti'].xcom_push(key='dry_run_result', value=result)

def run_purge(**context):
    """Run actual purge job (Sundays only)"""
    from purge_job import PurgeJob
    job = PurgeJob(config, evaluator, db)
    result = job.run(dry_run=False)
    if result['status'] != 'success':
        raise Exception(f"Purge job failed: {result['error']}")
    context['ti'].xcom_push(key='purge_result', value=result)

# Daily archive job
archive_dry_run = PythonOperator(
    task_id='archive_dry_run',
    python_callable=run_archive_dry_run,
    dag=dag
)

archive_main = PythonOperator(
    task_id='archive_main',
    python_callable=run_archive,
    trigger_rule='all_success',
    dag=dag
)

# Weekly purge job (Sundays)
purge_sensor = DateTimeSensor(
    task_id='purge_wait_sunday',
    target_time='{{ next_execution_date.replace(hour=2, minute=0, second=0, microsecond=0) if next_execution_date.weekday() == 6 else execution_date.replace(hour=2, minute=0, second=0, microsecond=0) + timedelta(days=(6-execution_date.weekday())) }}',
    poke_interval=3600,
    dag=dag
)

purge_main = PythonOperator(
    task_id='purge_main',
    python_callable=run_purge,
    dag=dag
)

# Define dependencies
archive_dry_run >> archive_main
purge_sensor >> purge_main
```

### Job State Tracking Schema

```sql
CREATE TABLE lifecycle_job_execution (
  execution_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  job_type ENUM('archive', 'purge', 'restore') NOT NULL,
  policy_id VARCHAR(50),
  table_name VARCHAR(100),
  
  scheduled_start TIMESTAMP,
  actual_start TIMESTAMP,
  actual_end TIMESTAMP,
  duration_seconds INT,
  
  status ENUM('pending', 'running', 'success', 'failed', 'cancelled') NOT NULL,
  dry_run BOOLEAN NOT NULL DEFAULT false,
  
  records_processed INT,
  records_affected INT,
  records_excluded INT,
  bytes_processed BIGINT,
  
  error_message TEXT,
  error_count INT,
  
  executed_by VARCHAR(100),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  
  INDEX idx_job_type (job_type),
  INDEX idx_table (table_name),
  INDEX idx_status (status),
  INDEX idx_executed_at (actual_start)
) ENGINE=InnoDB;

CREATE TABLE job_execution_detail (
  detail_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  execution_id BIGINT NOT NULL,
  record_id VARCHAR(100),
  action ENUM('archived', 'purged', 'failed', 'excluded') NOT NULL,
  reason TEXT,
  
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (execution_id) REFERENCES lifecycle_job_execution(execution_id),
  INDEX idx_execution (execution_id),
  INDEX idx_record (record_id)
) ENGINE=InnoDB;
```

---

## 6. Success Metrics

- [ ] Archive throughput >10MB/s
- [ ] Purge throughput >1000 records/second
- [ ] Dry-run accuracy 100%
- [ ] Job success rate >99%
- [ ] Error recovery <5 minutes
- [ ] Job state tracking 100% coverage
- [ ] Batch processing efficiency >90%

---

## 7. Definition of Done

- [ ] Archive job implementation complete and tested
- [ ] Purge job implementation complete and tested
- [ ] Dry-run validation working with 100% accuracy
- [ ] Job orchestration configured and scheduled
- [ ] Job state tracking schema and queries working
- [ ] Compensating transaction logic for failed operations
- [ ] Performance benchmarks met or documented
- [ ] Ready for IMM-1/HOLD-1/GOV-1 integration

---

## Next Task

→ IMM-1: Immutable Retention Enforcement
