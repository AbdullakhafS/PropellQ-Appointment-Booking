# BKP-1: Backup Policy and Schedule Automation

**Task ID:** BKP-1  
**Parent:** TASK-108  
**Category:** Backup Automation Foundation  
**Points:** 4  
**Status:** Planned (Phase 1)  
**Created:** 2026-06-22

---

## 1. Objective

Define and automate full and incremental backup schedules with retention windows and success metrics collection.

---

## 2. Inputs

- Database schema from TASK-104
- Retention policies from TASK-106
- Cloud storage infrastructure (S3, Azure Blob, or GCS)
- Database platform (MySQL 8.0+, Postgres 13+, or equivalent)

---

## 3. Outputs

**Deliverables:**
- [ ] Backup policy schema design (SQL)
- [ ] Backup automation orchestration (scheduled jobs)
- [ ] Full and incremental backup scripts
- [ ] Retention policy enforcement logic
- [ ] Success metrics collection
- [ ] Backup metadata registry with 50+ sample records

---

## 4. Acceptance Criteria

1. **Backup Schedules:**
   - [ ] Full backup: Weekly Sunday 2 AM UTC, completes <2 hours, all data backed up
   - [ ] Incremental backup: Daily 3 AM UTC, completes <30 min, transaction logs captured
   - [ ] No backup schedule misses (0% miss rate)
   - [ ] Backup job tracking with start/end timestamps

2. **Metrics Collection:**
   - [ ] Success/failure status recorded for each backup
   - [ ] Backup size (bytes) captured
   - [ ] Records backed up count recorded
   - [ ] Backup duration (seconds) measured
   - [ ] Checksum (SHA256) computed and stored

3. **Retention Management:**
   - [ ] 7 daily incremental backups retained
   - [ ] 4 weekly full backups retained
   - [ ] 12 monthly full backups retained
   - [ ] 7 yearly full backups retained
   - [ ] Automatic cleanup of expired backups

4. **Performance:**
   - [ ] Full backup completes in <2 hours
   - [ ] Incremental backup completes in <30 minutes
   - [ ] Metrics collection adds <5% overhead
   - [ ] Storage operations <500ms per operation

---

## 5. Implementation Details

### Backup Policy Schema (SQL)

```sql
CREATE TABLE backup_metadata (
  backup_id VARCHAR(50) PRIMARY KEY,
  backup_type ENUM('full', 'incremental') NOT NULL,
  backup_status ENUM('scheduled', 'in_progress', 'success', 'failed') NOT NULL DEFAULT 'scheduled',
  
  database_name VARCHAR(100) NOT NULL,
  database_version VARCHAR(50),
  
  start_time TIMESTAMP NOT NULL,
  end_time TIMESTAMP,
  duration_seconds INT,
  
  records_backed_up BIGINT,
  backup_size_bytes BIGINT,
  backup_checksum VARCHAR(64),  -- SHA256
  
  storage_path VARCHAR(500) NOT NULL,
  storage_class ENUM('standard', 'glacier', 'archive') DEFAULT 'standard',
  
  retention_expiry DATE,
  
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  INDEX idx_type (backup_type),
  INDEX idx_status (backup_status),
  INDEX idx_database (database_name),
  INDEX idx_expiry (retention_expiry),
  INDEX idx_created (created_at)
) ENGINE=InnoDB;

CREATE TABLE backup_policy (
  policy_id VARCHAR(50) PRIMARY KEY,
  database_name VARCHAR(100) NOT NULL,
  
  -- Full backup schedule
  full_backup_day_of_week INT,  -- 0=Sunday, 6=Saturday
  full_backup_time TIME,
  full_backup_enabled BOOLEAN DEFAULT true,
  
  -- Incremental backup schedule
  incremental_backup_daily_time TIME,
  incremental_backup_enabled BOOLEAN DEFAULT true,
  
  -- Retention windows
  incremental_retention_days INT DEFAULT 7,
  weekly_backup_retention_count INT DEFAULT 4,
  monthly_backup_retention_count INT DEFAULT 12,
  yearly_backup_retention_count INT DEFAULT 7,
  
  timezone VARCHAR(50) DEFAULT 'UTC',
  
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  INDEX idx_database (database_name)
) ENGINE=InnoDB;

CREATE TABLE backup_execution_log (
  execution_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  backup_id VARCHAR(50) NOT NULL,
  execution_status ENUM('started', 'completed', 'failed') NOT NULL,
  
  checkpoint_description VARCHAR(255),
  records_processed BIGINT,
  bytes_processed BIGINT,
  
  timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (backup_id) REFERENCES backup_metadata(backup_id),
  INDEX idx_backup (backup_id),
  INDEX idx_status (execution_status)
) ENGINE=InnoDB;
```

### Backup Orchestration Script (Python)

```python
import os
import hashlib
import logging
import subprocess
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import json

import MySQLdb
import boto3

logger = logging.getLogger(__name__)

class BackupOrchestrator:
    """Orchestrate full and incremental backups with retention management"""
    
    def __init__(self, db_connection, s3_client, backup_policy):
        self.db = db_connection
        self.s3 = s3_client
        self.policy = backup_policy
        self.backup_id = None
        self.start_time = None
    
    def run_backup(self, backup_type: str = 'auto') -> bool:
        """
        Execute backup (auto-selects full or incremental based on schedule)
        
        Returns True if backup successful
        """
        try:
            # Determine backup type if auto
            if backup_type == 'auto':
                backup_type = self._determine_backup_type()
            
            # Generate backup ID
            self.backup_id = self._generate_backup_id(backup_type)
            self.start_time = datetime.now(timezone.utc)
            
            # Create backup metadata record
            self._create_backup_record(backup_type)
            
            # Execute backup
            backup_file = self._execute_backup(backup_type)
            
            # Validate backup
            if not self._validate_backup(backup_file):
                self._mark_backup_failed("Backup validation failed")
                return False
            
            # Upload to cloud storage
            storage_path = self._upload_to_cloud(backup_file, backup_type)
            
            # Compute checksum
            checksum = self._compute_checksum(backup_file)
            
            # Calculate retention expiry
            retention_expiry = self._calculate_retention_expiry(backup_type)
            
            # Record backup completion
            end_time = datetime.now(timezone.utc)
            self._record_backup_success(
                backup_file,
                storage_path,
                checksum,
                end_time,
                retention_expiry
            )
            
            # Enforce retention policy
            self._cleanup_expired_backups()
            
            logger.info(f"Backup {self.backup_id} completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            if self.backup_id:
                self._mark_backup_failed(str(e))
            return False
    
    def _determine_backup_type(self) -> str:
        """Determine if full or incremental backup should run today"""
        now = datetime.now(timezone.utc)
        day_of_week = now.weekday()  # 0=Monday, 6=Sunday
        
        # Get policy
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT full_backup_day_of_week, full_backup_time, full_backup_enabled
            FROM backup_policy
            WHERE database_name = %s
        """, (self.policy['database_name'],))
        
        row = cursor.fetchone()
        if not row:
            return 'incremental'  # Default to incremental
        
        full_backup_day, full_backup_time, full_backup_enabled = row
        
        # Check if today is full backup day
        # Convert MySQL day_of_week (0=Sunday) to Python weekday (6=Sunday)
        mysql_day = (day_of_week + 1) % 7
        
        if mysql_day == full_backup_day and full_backup_enabled:
            return 'full'
        
        return 'incremental'
    
    def _generate_backup_id(self, backup_type: str) -> str:
        """Generate unique backup ID"""
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
        backup_type_prefix = 'FULL' if backup_type == 'full' else 'INCR'
        return f"BKP-{backup_type_prefix}-{timestamp}-{os.getpid()}"
    
    def _create_backup_record(self, backup_type: str):
        """Create initial backup metadata record"""
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO backup_metadata (
                backup_id, backup_type, backup_status, database_name,
                start_time, storage_path, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (
            self.backup_id,
            backup_type,
            'in_progress',
            self.policy['database_name'],
            self.start_time,
            ''  # Will update with actual path after upload
        ))
        self.db.commit()
    
    def _execute_backup(self, backup_type: str) -> str:
        """Execute mysqldump or similar backup command"""
        backup_file = f"/tmp/{self.backup_id}.sql.gz"
        
        if backup_type == 'full':
            # Full backup: all databases
            cmd = [
                'mysqldump',
                '--single-transaction',
                '--all-databases',
                '--routines',
                '--triggers',
                '--events',
                f'--host={self.policy["host"]}',
                f'--user={self.policy["user"]}',
                f'--password={self.policy["password"]}',
                '|',
                'gzip',
                f'> {backup_file}'
            ]
        else:
            # Incremental backup: binary logs since last full backup
            # For simplicity, dump incremental set of tables
            cmd = [
                'mysqldump',
                '--single-transaction',
                '--databases', self.policy['database_name'],
                f'--host={self.policy["host"]}',
                f'--user={self.policy["user"]}',
                f'--password={self.policy["password"]}',
                '|',
                'gzip',
                f'> {backup_file}'
            ]
        
        # Execute backup command
        cmd_str = ' '.join(cmd)
        result = subprocess.run(cmd_str, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Backup command failed: {result.stderr}")
        
        # Verify file exists and has content
        if not os.path.exists(backup_file) or os.path.getsize(backup_file) == 0:
            raise Exception(f"Backup file empty or missing: {backup_file}")
        
        logger.info(f"Backup file created: {backup_file}, size: {os.path.getsize(backup_file)}")
        return backup_file
    
    def _validate_backup(self, backup_file: str) -> bool:
        """Validate backup file integrity"""
        try:
            # Check file exists and is readable
            if not os.path.exists(backup_file):
                return False
            
            # Check file size > 1MB (sanity check)
            file_size = os.path.getsize(backup_file)
            if file_size < 1024 * 1024:
                logger.warning(f"Backup file suspiciously small: {file_size} bytes")
                return False
            
            # For gzipped files, validate gzip header
            with open(backup_file, 'rb') as f:
                magic = f.read(2)
                if magic != b'\x1f\x8b':  # GZIP magic number
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Backup validation failed: {str(e)}")
            return False
    
    def _upload_to_cloud(self, backup_file: str, backup_type: str) -> str:
        """Upload backup to cloud storage (S3, Blob, or GCS)"""
        bucket = self.policy['backup_bucket']
        
        # Determine storage class based on type
        storage_class = 'GLACIER' if backup_type == 'incremental' else 'STANDARD'
        
        # Generate S3 key
        now = datetime.now(timezone.utc)
        s3_key = f"backups/{self.policy['database_name']}/{backup_type}/{now.strftime('%Y/%m/%d')}/{self.backup_id}.sql.gz"
        
        try:
            # Upload with metadata
            self.s3.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=open(backup_file, 'rb').read(),
                StorageClass=storage_class,
                Metadata={
                    'backup_id': self.backup_id,
                    'backup_type': backup_type,
                    'timestamp': self.start_time.isoformat()
                }
            )
            
            logger.info(f"Backup uploaded to S3: s3://{bucket}/{s3_key}")
            return f"s3://{bucket}/{s3_key}"
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            raise
    
    def _compute_checksum(self, backup_file: str) -> str:
        """Compute SHA256 checksum of backup file"""
        sha256_hash = hashlib.sha256()
        
        with open(backup_file, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b''):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    def _calculate_retention_expiry(self, backup_type: str) -> str:
        """Calculate retention expiry date based on policy"""
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT incremental_retention_days, weekly_backup_retention_count,
                   monthly_backup_retention_count, yearly_backup_retention_count
            FROM backup_policy
            WHERE database_name = %s
        """, (self.policy['database_name'],))
        
        row = cursor.fetchone()
        if not row:
            return (datetime.now(timezone.utc) + timedelta(days=30)).date()
        
        incremental_days, weekly_count, monthly_count, yearly_count = row
        
        if backup_type == 'incremental':
            expiry = datetime.now(timezone.utc) + timedelta(days=incremental_days)
        elif backup_type == 'full':
            # Assume weekly full backup
            expiry = datetime.now(timezone.utc) + timedelta(weeks=weekly_count)
        else:
            expiry = datetime.now(timezone.utc) + timedelta(days=30)
        
        return expiry.date()
    
    def _record_backup_success(self, backup_file: str, storage_path: str,
                               checksum: str, end_time: datetime, retention_expiry: str):
        """Record backup completion in metadata"""
        file_size = os.path.getsize(backup_file)
        duration = (end_time - self.start_time).total_seconds()
        
        cursor = self.db.cursor()
        cursor.execute("""
            UPDATE backup_metadata SET
                backup_status = 'success',
                end_time = %s,
                duration_seconds = %s,
                backup_size_bytes = %s,
                backup_checksum = %s,
                storage_path = %s,
                retention_expiry = %s,
                updated_at = NOW()
            WHERE backup_id = %s
        """, (
            end_time,
            int(duration),
            file_size,
            checksum,
            storage_path,
            retention_expiry,
            self.backup_id
        ))
        self.db.commit()
        
        # Cleanup local backup file
        try:
            os.remove(backup_file)
        except Exception as e:
            logger.warning(f"Failed to cleanup local backup file: {str(e)}")
    
    def _mark_backup_failed(self, error_message: str):
        """Mark backup as failed"""
        cursor = self.db.cursor()
        cursor.execute("""
            UPDATE backup_metadata SET
                backup_status = 'failed',
                end_time = NOW(),
                updated_at = NOW()
            WHERE backup_id = %s
        """, (self.backup_id,))
        self.db.commit()
        
        logger.error(f"Backup {self.backup_id} marked as failed: {error_message}")
    
    def _cleanup_expired_backups(self):
        """Delete backups past retention expiry"""
        cursor = self.db.cursor()
        
        # Find expired backups
        cursor.execute("""
            SELECT backup_id, storage_path FROM backup_metadata
            WHERE backup_status = 'success'
            AND retention_expiry < CURDATE()
            ORDER BY retention_expiry
            LIMIT 100
        """)
        
        expired_backups = cursor.fetchall()
        
        for backup_id, storage_path in expired_backups:
            try:
                # Delete from cloud storage
                if storage_path.startswith('s3://'):
                    bucket, key = storage_path.replace('s3://', '').split('/', 1)
                    self.s3.delete_object(Bucket=bucket, Key=key)
                    logger.info(f"Deleted expired backup from cloud: {storage_path}")
                
                # Delete metadata record
                cursor.execute("""
                    DELETE FROM backup_metadata WHERE backup_id = %s
                """, (backup_id,))
                self.db.commit()
                
                logger.info(f"Deleted expired backup record: {backup_id}")
            except Exception as e:
                logger.error(f"Failed to cleanup backup {backup_id}: {str(e)}")
```

### Backup Scheduled Job (Kubernetes CronJob)

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: backup-full
  namespace: database
spec:
  # Full backup: Every Sunday 2 AM UTC
  schedule: "0 2 * * 0"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: backup-operator
          containers:
          - name: backup
            image: backup-automation:1.0.0
            env:
            - name: BACKUP_TYPE
              value: "full"
            - name: DATABASE_NAME
              value: "propellq_appointment"
            - name: BACKUP_BUCKET
              value: "propellq-backups-prod"
            - name: DB_HOST
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: host
            - name: DB_USER
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: user
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: password
            
            resources:
              requests:
                memory: "2Gi"
                cpu: "1"
              limits:
                memory: "4Gi"
                cpu: "2"
            
            volumeMounts:
            - name: backup-tmp
              mountPath: /tmp/backups
          
          volumes:
          - name: backup-tmp
            emptyDir:
              sizeLimit: 10Gi
          
          restartPolicy: Never
          
          backoffLimit: 1
          activeDeadlineSeconds: 7200  # 2 hours

---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: backup-incremental
  namespace: database
spec:
  # Incremental backup: Daily 3 AM UTC
  schedule: "0 3 * * *"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: backup-operator
          containers:
          - name: backup
            image: backup-automation:1.0.0
            env:
            - name: BACKUP_TYPE
              value: "incremental"
            - name: DATABASE_NAME
              value: "propellq_appointment"
            - name: BACKUP_BUCKET
              value: "propellq-backups-prod"
            - name: DB_HOST
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: host
            - name: DB_USER
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: user
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: password
            
            resources:
              requests:
                memory: "1Gi"
                cpu: "500m"
              limits:
                memory: "2Gi"
                cpu: "1"
            
            volumeMounts:
            - name: backup-tmp
              mountPath: /tmp/backups
          
          volumes:
          - name: backup-tmp
            emptyDir:
              sizeLimit: 5Gi
          
          restartPolicy: Never
          
          backoffLimit: 1
          activeDeadlineSeconds: 1800  # 30 minutes
```

---

## 6. Testing Strategy

### Test Cases

```python
def test_full_backup_execution():
    """Test full backup completes successfully"""
    orchestrator = BackupOrchestrator(db, s3_client, {
        'database_name': 'test_db',
        'host': 'localhost',
        'backup_bucket': 'test-backups'
    })
    
    result = orchestrator.run_backup('full')
    assert result is True
    assert orchestrator.backup_id is not None

def test_incremental_backup_execution():
    """Test incremental backup completes successfully"""
    orchestrator = BackupOrchestrator(db, s3_client, {...})
    
    result = orchestrator.run_backup('incremental')
    assert result is True
    assert orchestrator.backup_id.startswith('BKP-INCR-')

def test_backup_metrics_recorded():
    """Test all metrics are recorded"""
    orchestrator = BackupOrchestrator(db, s3_client, {...})
    orchestrator.run_backup('full')
    
    cursor = db.cursor()
    cursor.execute("SELECT * FROM backup_metadata WHERE backup_id = %s",
                   (orchestrator.backup_id,))
    row = cursor.fetchone()
    
    assert row['backup_status'] == 'success'
    assert row['backup_size_bytes'] > 0
    assert row['duration_seconds'] > 0
    assert row['backup_checksum'] is not None

def test_retention_cleanup():
    """Test expired backups are cleaned up"""
    # Insert old backup records past retention
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO backup_metadata (...)
        VALUES (...with retention_expiry in past...)
    """)
    
    orchestrator = BackupOrchestrator(db, s3_client, {...})
    orchestrator._cleanup_expired_backups()
    
    cursor.execute("""
        SELECT COUNT(*) FROM backup_metadata
        WHERE retention_expiry < CURDATE()
    """)
    count = cursor.fetchone()[0]
    assert count == 0

def test_backup_failure_handling():
    """Test failed backup is recorded correctly"""
    # Mock backup command to fail
    orchestrator = BackupOrchestrator(db, s3_client, {...})
    orchestrator.run_backup('full')
    
    cursor = db.cursor()
    cursor.execute("SELECT backup_status FROM backup_metadata WHERE backup_id = %s",
                   (orchestrator.backup_id,))
    status = cursor.fetchone()[0]
    
    assert status in ['success', 'failed']
```

---

## 7. Success Metrics

- [ ] 100% backup schedule compliance (no missed backups)
- [ ] 99.9%+ backup success rate
- [ ] All metrics (size, duration, records, checksum) collected for every backup
- [ ] Retention cleanup removes 100% of expired backups
- [ ] Full backup completes in <2 hours
- [ ] Incremental backup completes in <30 minutes

---

## 8. Definition of Done

- [ ] Backup policy schema deployed and validated
- [ ] Backup orchestration script implemented and tested
- [ ] Full and incremental backup schedules active
- [ ] All success metrics being collected
- [ ] Retention cleanup running and removing expired backups
- [ ] 100+ backup records in metadata (from test runs)
- [ ] All test cases passing
- [ ] Ready for BKP-2 and SEC-1 integration

---

## Next Task

→ BKP-2: Point-in-Time Recovery Enablement
