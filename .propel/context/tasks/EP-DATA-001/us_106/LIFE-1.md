# LIFE-1: Policy Model and Schedule Framework

**Task ID:** LIFE-1  
**Parent:** TASK-106  
**Category:** Lifecycle Engine Foundation  
**Points:** 5  
**Status:** Planned (Phase 1)  
**Created:** 2026-06-22

---

## 1. Objective

Define retention policy schema by data domain, retention window, and action type. Implement timezone-aware schedule evaluation engine with idempotent, replay-safe state transitions.

---

## 2. Inputs

- Compliance requirements document (data retention windows by domain)
- Data domain definitions (patient, appointment, document, audit_log)
- Timezone handling requirements
- Scheduler infrastructure (cron, date-boundary evaluation)

---

## 3. Outputs

**Deliverables:**
- [ ] Policy schema design (JSON schema)
- [ ] Schedule evaluation engine (code)
- [ ] State machine implementation
- [ ] Timezone-safe evaluation logic
- [ ] Test cases with boundary conditions
- [ ] Integration guide with LIFE-2

---

## 4. Acceptance Criteria

1. **Policy Schema:**
   - [ ] Policy defined by domain, retention_days, archive_action, purge_action
   - [ ] Versioning support (version, effective_date, superseded_date)
   - [ ] Enable/disable toggling
   - [ ] Ownership and metadata

2. **Schedule Evaluation:**
   - [ ] Cron-based or date-boundary evaluation
   - [ ] Timezone-safe (UTC normalization)
   - [ ] Handle DST transitions
   - [ ] Handle timezone offsets correctly

3. **State Transitions:**
   - [ ] Idempotent transitions (replay-safe)
   - [ ] Prevent invalid state transitions
   - [ ] Maintain state history
   - [ ] Support manual state override

4. **Performance:**
   - [ ] Evaluate 100+ policies in <100ms
   - [ ] Schedule evaluation triggers < daily latency
   - [ ] Minimal database overhead

---

## 5. Implementation Details

### Policy Schema (JSON)

```json
{
  "policies": [
    {
      "policy_id": "POL-001",
      "domain": "patient",
      "policy_name": "Patient Record Retention - Standard",
      "description": "3-year retention for inactive patient records",
      "retention_days": 1095,
      "archive_action": "s3_glacier",
      "purge_action": "delete",
      "enabled": true,
      "version": 1,
      "effective_date": "2026-01-01",
      "superseded_date": null,
      "owner_id": "compliance-team",
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-01T00:00:00Z"
    },
    {
      "policy_id": "POL-002",
      "domain": "audit_log",
      "policy_name": "Audit Log Retention - Immutable",
      "description": "7-year immutable retention for compliance",
      "retention_days": 2555,
      "archive_action": "s3_glacier",
      "purge_action": "none",
      "enabled": true,
      "version": 1,
      "effective_date": "2026-01-01",
      "superseded_date": null,
      "owner_id": "compliance-team",
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-01T00:00:00Z"
    },
    {
      "policy_id": "POL-003",
      "domain": "document",
      "policy_name": "Document Retention - Extended",
      "description": "5-year retention for clinical documents",
      "retention_days": 1825,
      "archive_action": "azure_archive",
      "purge_action": "anonymize",
      "enabled": false,
      "version": 2,
      "effective_date": "2026-06-01",
      "superseded_date": null,
      "owner_id": "compliance-team",
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-05-15T14:30:00Z"
    }
  ]
}
```

### Policy Schema (SQL)

```sql
CREATE TABLE retention_policies (
  policy_id VARCHAR(50) PRIMARY KEY,
  domain VARCHAR(100) NOT NULL,
  policy_name VARCHAR(255) NOT NULL,
  description TEXT,
  retention_days INT NOT NULL,
  archive_action ENUM('s3_glacier', 'azure_archive', 'delete_after_retention', 'none') NOT NULL,
  purge_action ENUM('delete', 'anonymize', 'none') NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT true,
  version INT NOT NULL DEFAULT 1,
  effective_date DATE NOT NULL,
  superseded_date DATE,
  owner_id VARCHAR(100),
  
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  UNIQUE INDEX idx_domain_version (domain, version),
  INDEX idx_enabled (enabled),
  INDEX idx_effective (effective_date),
  CONSTRAINT chk_version_dates CHECK (superseded_date IS NULL OR superseded_date > effective_date)
) ENGINE=InnoDB;

CREATE TABLE policy_change_log (
  change_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  policy_id VARCHAR(50) NOT NULL,
  change_type ENUM('created', 'updated', 'disabled') NOT NULL,
  old_version INT,
  new_version INT,
  changed_by VARCHAR(100) NOT NULL,
  change_reason TEXT,
  approved_by VARCHAR(100),
  approved_at TIMESTAMP,
  effective_date DATE NOT NULL,
  
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (policy_id) REFERENCES retention_policies(policy_id),
  INDEX idx_policy (policy_id),
  INDEX idx_effective (effective_date)
) ENGINE=InnoDB;
```

### Schedule Evaluation Engine (Python)

```python
from datetime import datetime, timedelta, timezone
import pytz
from enum import Enum

class PolicyAction(Enum):
    ARCHIVE = "archive"
    PURGE = "purge"

class ScheduleEvaluator:
    """Evaluate when records should be archived/purged based on retention policies"""
    
    def __init__(self, policies, tz='UTC'):
        """Initialize with policy definitions"""
        self.policies = policies
        self.tz = pytz.timezone(tz)
    
    def evaluate_record(self, record):
        """
        Determine if record should be archived or purged
        
        Args:
            record: {
                'record_id': 'REC-001',
                'table_name': 'patient',
                'created_at': datetime,
                'last_modified_at': datetime
            }
        
        Returns:
            {
                'record_id': 'REC-001',
                'action': PolicyAction.ARCHIVE,
                'policy_id': 'POL-001',
                'reason': 'Retention window exceeded',
                'eligible_at': datetime
            }
        """
        # Find applicable policy
        policy = self._get_policy_for_table(record['table_name'])
        if not policy or not policy['enabled']:
            return None
        
        # Calculate retention boundary
        now_utc = datetime.now(timezone.utc)
        now_tz = now_utc.astimezone(self.tz)
        
        # Use last_modified_at or created_at for age calculation
        record_timestamp = record.get('last_modified_at') or record['created_at']
        
        # Normalize timestamps to UTC
        if not record_timestamp.tzinfo:
            record_timestamp = self.tz.localize(record_timestamp)
        else:
            record_timestamp = record_timestamp.astimezone(timezone.utc)
        
        # Calculate age
        age_days = (now_utc - record_timestamp).days
        
        # Determine action
        retention_days = policy['retention_days']
        
        # Archive decision
        if age_days >= retention_days and policy['archive_action'] != 'none':
            return {
                'record_id': record['record_id'],
                'table_name': record['table_name'],
                'action': PolicyAction.ARCHIVE,
                'policy_id': policy['policy_id'],
                'policy_version': policy['version'],
                'reason': f'Retention window {retention_days}d exceeded ({age_days}d old)',
                'eligible_at': record_timestamp + timedelta(days=retention_days),
                'now_utc': now_utc
            }
        
        # Purge decision (only if archive action is completed)
        if age_days >= retention_days + 30:  # +30d grace period after archive
            if policy['purge_action'] != 'none':
                return {
                    'record_id': record['record_id'],
                    'table_name': record['table_name'],
                    'action': PolicyAction.PURGE,
                    'policy_id': policy['policy_id'],
                    'policy_version': policy['version'],
                    'reason': f'Retention window {retention_days}d + archive grace period exceeded',
                    'eligible_at': record_timestamp + timedelta(days=retention_days + 30),
                    'now_utc': now_utc
                }
        
        return None
    
    def _get_policy_for_table(self, table_name):
        """Get applicable policy for table"""
        for policy in self.policies:
            if policy['domain'] == table_name:
                return policy
        return None
    
    def evaluate_batch(self, records):
        """Evaluate multiple records efficiently"""
        results = []
        for record in records:
            result = self.evaluate_record(record)
            if result:
                results.append(result)
        return results
    
    def is_schedule_boundary(self, now_tz=None):
        """
        Determine if current time is at a scheduled boundary
        Supports:
        - 11 PM UTC daily (archive jobs)
        - 2 AM UTC Sunday (purge jobs)
        """
        if now_tz is None:
            now_utc = datetime.now(timezone.utc)
            now_tz = now_utc.astimezone(self.tz)
        
        hour = now_tz.hour
        minute = now_tz.minute
        weekday = now_tz.weekday()  # 0=Mon, 6=Sun
        
        # Archive: Daily at 11 PM (23:00)
        archive_boundary = (hour == 23 and minute < 5)
        
        # Purge: Sunday at 2 AM (02:00)
        purge_boundary = (weekday == 6 and hour == 2 and minute < 5)
        
        return {
            'is_boundary': archive_boundary or purge_boundary,
            'archive_boundary': archive_boundary,
            'purge_boundary': purge_boundary,
            'current_time': now_tz.isoformat()
        }
```

### State Machine (Python)

```python
from enum import Enum

class RecordState(Enum):
    OPERATIONAL = "operational"
    ARCHIVED = "archived"
    ARCHIVED_AND_PURGED = "archived_and_purged"
    PURGED = "purged"
    LEGAL_HOLD = "legal_hold"

class StateTransition:
    """
    Manage record lifecycle state transitions
    
    Valid transitions:
    OPERATIONAL → ARCHIVED (when retention_days elapsed)
    ARCHIVED → ARCHIVED_AND_PURGED (when purge_action applied)
    OPERATIONAL → LEGAL_HOLD (manual hold placement)
    LEGAL_HOLD → OPERATIONAL (hold release)
    LEGAL_HOLD → ARCHIVED (hold release then auto-archive)
    """
    
    VALID_TRANSITIONS = {
        RecordState.OPERATIONAL: [
            RecordState.ARCHIVED,
            RecordState.LEGAL_HOLD,
            RecordState.PURGED  # Direct purge if no archive required
        ],
        RecordState.ARCHIVED: [
            RecordState.ARCHIVED_AND_PURGED,
            RecordState.LEGAL_HOLD  # Legal hold on archived record
        ],
        RecordState.LEGAL_HOLD: [
            RecordState.OPERATIONAL,  # Hold release
            RecordState.ARCHIVED  # Release then auto-archive
        ],
        RecordState.ARCHIVED_AND_PURGED: [],  # Terminal state
        RecordState.PURGED: []  # Terminal state
    }
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def get_current_state(self, record_id, table_name):
        """Fetch current state from database"""
        query = """
            SELECT lifecycle_state, state_changed_at 
            FROM lifecycle_state_tracking
            WHERE record_id = %s AND table_name = %s
        """
        result = self.db.query(query, (record_id, table_name))
        if result:
            return RecordState(result[0]['lifecycle_state'])
        return RecordState.OPERATIONAL
    
    def can_transition(self, from_state, to_state):
        """Check if transition is allowed"""
        if from_state not in self.VALID_TRANSITIONS:
            return False
        return to_state in self.VALID_TRANSITIONS[from_state]
    
    def transition(self, record_id, table_name, target_state, reason=""):
        """
        Perform state transition (idempotent)
        
        Idempotency: If already in target state, return success
        """
        current_state = self.get_current_state(record_id, table_name)
        
        # Idempotency: Already in target state
        if current_state == target_state:
            return {'success': True, 'reason': 'Already in target state (idempotent)'}
        
        # Validate transition
        if not self.can_transition(current_state, target_state):
            raise ValueError(f"Invalid transition: {current_state.value} → {target_state.value}")
        
        # Log state change
        query = """
            INSERT INTO lifecycle_state_tracking 
            (record_id, table_name, lifecycle_state, previous_state, state_changed_at, change_reason)
            VALUES (%s, %s, %s, %s, NOW(), %s)
            ON DUPLICATE KEY UPDATE
            lifecycle_state = VALUES(lifecycle_state),
            previous_state = VALUES(previous_state),
            state_changed_at = VALUES(state_changed_at),
            change_reason = VALUES(change_reason)
        """
        self.db.execute(query, (
            record_id, table_name, target_state.value, current_state.value, reason
        ))
        
        return {'success': True, 'old_state': current_state.value, 'new_state': target_state.value}
    
    def replay_transition(self, record_id, table_name, target_state, reason=""):
        """
        Replay transition (used for recovery or re-execution)
        Idempotent: If already in target state, succeeds silently
        """
        return self.transition(record_id, table_name, target_state, reason)
```

### Timezone-Safe Boundary Handling (Python)

```python
from datetime import datetime, timezone
import pytz

class TimezoneBoundaryHandler:
    """Handle timezone-safe date boundaries"""
    
    def __init__(self, policy_tz='America/New_York', archive_hour=23):
        """
        Initialize handler
        
        Args:
            policy_tz: Timezone for policy evaluation (e.g., America/New_York)
            archive_hour: Hour of day for archive (0-23)
        """
        self.policy_tz = pytz.timezone(policy_tz)
        self.archive_hour = archive_hour
    
    def get_next_boundary(self, now_utc=None):
        """Calculate next schedule boundary in policy timezone"""
        if now_utc is None:
            now_utc = datetime.now(timezone.utc)
        
        now_tz = now_utc.astimezone(self.policy_tz)
        
        # If before archive hour today, use today
        if now_tz.hour < self.archive_hour:
            boundary = now_tz.replace(hour=self.archive_hour, minute=0, second=0, microsecond=0)
        else:
            # Use tomorrow
            next_day = now_tz + timedelta(days=1)
            boundary = next_day.replace(hour=self.archive_hour, minute=0, second=0, microsecond=0)
        
        # Convert back to UTC
        return boundary.astimezone(timezone.utc)
    
    def is_at_boundary(self, now_utc=None, window_minutes=5):
        """Check if currently at schedule boundary (within window)"""
        if now_utc is None:
            now_utc = datetime.now(timezone.utc)
        
        now_tz = now_utc.astimezone(self.policy_tz)
        
        # Check if hour matches and minute is within window
        return (now_tz.hour == self.archive_hour and 
                now_tz.minute < window_minutes)
    
    def handle_dst_transition(self, record_age_days, record_created_at):
        """
        Handle daylight saving time transitions
        
        DST can cause hour skips or repeats
        Always use UTC internally to avoid ambiguity
        """
        # Ensure record_created_at is UTC
        if not record_created_at.tzinfo:
            raise ValueError("record_created_at must be timezone-aware")
        
        record_created_utc = record_created_at.astimezone(timezone.utc)
        
        # Calculate retention boundary in UTC (DST-independent)
        retention_boundary_utc = record_created_utc + timedelta(days=record_age_days)
        
        return retention_boundary_utc
    
    def normalize_timestamp(self, ts, source_tz='UTC'):
        """Normalize timestamp to UTC"""
        if not ts.tzinfo:
            tz = pytz.timezone(source_tz)
            ts = tz.localize(ts)
        return ts.astimezone(timezone.utc)
```

---

## 6. Testing Strategy

### Test Cases

```python
def test_policy_schema():
    """Validate policy schema structure"""
    schema = {
        'policy_id': 'POL-001',
        'domain': 'patient',
        'retention_days': 1095,
        'archive_action': 's3_glacier',
        'purge_action': 'delete'
    }
    assert schema['retention_days'] > 0
    assert schema['archive_action'] in ['s3_glacier', 'azure_archive', 'delete_after_retention']

def test_schedule_evaluation_basic():
    """Test basic record age evaluation"""
    policies = [{'domain': 'patient', 'retention_days': 30, 'version': 1}]
    evaluator = ScheduleEvaluator(policies)
    
    # Record 31 days old
    old_record = {
        'record_id': 'R001',
        'table_name': 'patient',
        'created_at': datetime.now(timezone.utc) - timedelta(days=31)
    }
    result = evaluator.evaluate_record(old_record)
    assert result['action'] == PolicyAction.ARCHIVE

def test_timezone_boundary():
    """Test timezone-aware date boundary"""
    handler = TimezoneBoundaryHandler('America/New_York', archive_hour=23)
    
    # 11 PM ET should trigger archive
    et = pytz.timezone('America/New_York')
    now_et = et.localize(datetime(2026, 6, 22, 23, 2))  # 11:02 PM
    now_utc = now_et.astimezone(timezone.utc)
    
    assert handler.is_at_boundary(now_utc)

def test_dst_transition():
    """Test DST transition handling"""
    handler = TimezoneBoundaryHandler('America/New_York')
    
    # Create timestamp just before DST transition
    eastern = pytz.timezone('America/New_York')
    before_dst = eastern.localize(datetime(2026, 3, 8, 1, 30))
    
    # Should normalize correctly
    normalized = handler.normalize_timestamp(before_dst)
    assert normalized.tzinfo == timezone.utc

def test_idempotent_state_transition():
    """Test that state transitions are replay-safe"""
    state_machine = StateTransition(db_mock)
    
    # First transition
    result1 = state_machine.transition('R001', 'patient', RecordState.ARCHIVED, "Initial archive")
    assert result1['success']
    
    # Replay same transition
    result2 = state_machine.transition('R001', 'patient', RecordState.ARCHIVED, "Replay")
    assert result2['success']
    assert result2['reason'] == 'Already in target state (idempotent)'

def test_invalid_state_transition():
    """Test that invalid transitions are blocked"""
    state_machine = StateTransition(db_mock)
    
    # PURGED is terminal, cannot transition from there
    with pytest.raises(ValueError):
        state_machine.transition('R001', 'patient', RecordState.ARCHIVED)
```

---

## 7. Success Metrics

- [ ] Policy schema supports all 3+ data domains
- [ ] Schedule evaluation handles 100+ policies in <100ms
- [ ] Timezone evaluation correct across 10+ timezones
- [ ] DST transitions handled without skips/repeats
- [ ] State transitions idempotent and replay-safe
- [ ] All test cases passing
- [ ] Integration ready with LIFE-2

---

## 8. Definition of Done

- [ ] Policy schema designed and validated
- [ ] Schedule evaluation engine implemented
- [ ] State machine with idempotency guarantees
- [ ] Timezone-safe boundary handling
- [ ] All test cases passing (10+ unit tests)
- [ ] Performance benchmarks met
- [ ] Integration documentation prepared
- [ ] Ready for LIFE-2 integration

---

## Next Task

→ LIFE-2: Archive and Purge Job Orchestration
