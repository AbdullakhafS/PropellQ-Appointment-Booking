# RULE-1: Completeness and Validity Rule Set

**Task ID:** RULE-1  
**Parent:** TASK-107  
**Category:** Rule Engineering Foundation  
**Points:** 4  
**Status:** Planned (Phase 1)  
**Created:** 2026-06-22

---

## 1. Objective

Define and implement required-field, datatype, range, and domain value validations with rule versioning and packing by domain.

---

## 2. Inputs

- Data schema from TASK-104
- Clinical domain requirements
- Existing data quality baseline
- Field-level constraints (nullable, min/max, enums)

---

## 3. Outputs

**Deliverables:**
- [ ] Rule schema design (SQL, JSON schema)
- [ ] Rule evaluator engine (SQL or Python)
- [ ] Rule registry with 50+ initial rules
- [ ] Rule versioning and deprecation system
- [ ] Rule pack definitions by domain
- [ ] Rule testing framework with 20+ test cases

---

## 4. Acceptance Criteria

1. **Rule Definition:**
   - [ ] Rule schema supports all rule types (completeness, type, range, domain)
   - [ ] Rules versioned with effective dates
   - [ ] Rules include owner/rationale metadata
   - [ ] Rules support enable/disable toggle

2. **Rule Coverage:**
   - [ ] Completeness: All required fields in 4+ domains (patient, appointment, medication, coding)
   - [ ] Datatype: All fields have type validation (string, int, date, decimal)
   - [ ] Range: Min/max bounds for numeric fields, length for strings
   - [ ] Domain: Enum validation for status fields, lookup table references

3. **Performance:**
   - [ ] <5ms per rule evaluation
   - [ ] <100ms validation for single record across all rules
   - [ ] <5s batch validation per 1000 records

4. **Maintainability:**
   - [ ] Rules queryable by domain/type/severity
   - [ ] Rule changes tracked in audit log
   - [ ] Easy rule addition without code changes (configuration-driven)

---

## 5. Implementation Details

### Rule Schema (SQL)

```sql
CREATE TABLE validation_rules (
  rule_id VARCHAR(50) PRIMARY KEY,
  domain VARCHAR(100) NOT NULL,
  rule_type ENUM('completeness', 'datatype', 'range', 'domain', 'format') NOT NULL,
  rule_name VARCHAR(255) NOT NULL,
  rule_description TEXT,
  
  -- Rule definition (one of: expression for SQL, or structured params)
  rule_expression TEXT,  -- SQL WHERE clause or rule DSL
  field_name VARCHAR(100),
  
  -- Parameters for structured rules
  min_value INT,
  max_value INT,
  allowed_values TEXT,  -- JSON array of allowed values
  pattern VARCHAR(255),  -- Regex pattern for format validation
  
  severity ENUM('critical', 'high', 'medium', 'low') NOT NULL DEFAULT 'high',
  
  enabled BOOLEAN NOT NULL DEFAULT true,
  version INT NOT NULL DEFAULT 1,
  effective_date DATE NOT NULL,
  deprecated_date DATE,
  
  owner_id VARCHAR(100),
  owner_team VARCHAR(100),
  rationale TEXT,
  
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  INDEX idx_domain (domain),
  INDEX idx_type (rule_type),
  INDEX idx_severity (severity),
  INDEX idx_enabled (enabled)
) ENGINE=InnoDB;

CREATE TABLE rule_audit_log (
  audit_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  rule_id VARCHAR(50) NOT NULL,
  change_type ENUM('created', 'updated', 'enabled', 'disabled', 'deprecated') NOT NULL,
  old_version INT,
  new_version INT,
  changed_by VARCHAR(100),
  change_reason TEXT,
  
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (rule_id) REFERENCES validation_rules(rule_id),
  INDEX idx_rule (rule_id),
  INDEX idx_change_type (change_type)
) ENGINE=InnoDB;
```

### Rule Definitions (Sample JSON)

```json
{
  "rules": [
    {
      "rule_id": "COMP-001",
      "domain": "patient",
      "rule_type": "completeness",
      "rule_name": "Patient MRN Required",
      "field_name": "mrn",
      "severity": "critical",
      "version": 1,
      "effective_date": "2026-01-01",
      "owner": "clinical-data-team",
      "rationale": "MRN is unique patient identifier in EMR"
    },
    {
      "rule_id": "TYPE-001",
      "domain": "appointment",
      "rule_type": "datatype",
      "rule_name": "Appointment Status Valid Type",
      "field_name": "appointment_status",
      "allowed_values": ["pending", "confirmed", "completed", "cancelled", "no_show"],
      "severity": "high",
      "version": 1
    },
    {
      "rule_id": "RANGE-001",
      "domain": "appointment",
      "rule_type": "range",
      "rule_name": "Appointment Duration Valid Range",
      "field_name": "duration_minutes",
      "min_value": 15,
      "max_value": 480,
      "severity": "medium",
      "version": 1,
      "rationale": "Appointments between 15 min and 8 hours"
    },
    {
      "rule_id": "FORMAT-001",
      "domain": "patient",
      "rule_type": "format",
      "rule_name": "Email Format Valid",
      "field_name": "email",
      "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
      "severity": "low",
      "version": 1
    }
  ]
}
```

### Rule Evaluator Engine (Python)

```python
class RuleEvaluator:
    """Evaluate validation rules against records"""
    
    def __init__(self, db_connection, rule_cache=None):
        self.db = db_connection
        self.rules = rule_cache or {}
        self.load_rules()
    
    def load_rules(self):
        """Load enabled rules from database"""
        query = """
            SELECT * FROM validation_rules
            WHERE enabled = true AND deprecated_date IS NULL
            ORDER BY domain, rule_type
        """
        rules = self.db.query(query)
        self.rules = {rule['rule_id']: rule for rule in rules}
    
    def evaluate_record(self, record, domain, table_name):
        """
        Evaluate a single record against all applicable rules
        
        Returns list of violations
        """
        violations = []
        
        # Get rules for this domain
        domain_rules = [r for r in self.rules.values() if r['domain'] == domain]
        
        for rule in domain_rules:
            try:
                violation = self._evaluate_rule(record, rule, table_name)
                if violation:
                    violations.append(violation)
            except Exception as e:
                # Log rule evaluation error
                self._log_rule_error(rule['rule_id'], str(e))
        
        return violations
    
    def _evaluate_rule(self, record, rule, table_name):
        """Evaluate a single rule"""
        rule_type = rule['rule_type']
        
        if rule_type == 'completeness':
            return self._check_completeness(record, rule)
        elif rule_type == 'datatype':
            return self._check_datatype(record, rule)
        elif rule_type == 'range':
            return self._check_range(record, rule)
        elif rule_type == 'domain':
            return self._check_domain(record, rule)
        elif rule_type == 'format':
            return self._check_format(record, rule)
        
        return None
    
    def _check_completeness(self, record, rule):
        """Check if required field is present and not null"""
        field = rule['field_name']
        
        if field not in record or record[field] is None:
            return {
                'rule_id': rule['rule_id'],
                'rule_name': rule['rule_name'],
                'field': field,
                'violation_type': 'completeness',
                'severity': rule['severity'],
                'message': f"Required field '{field}' is missing or NULL"
            }
        
        return None
    
    def _check_datatype(self, record, rule):
        """Check if field matches expected datatype"""
        field = rule['field_name']
        value = record.get(field)
        
        if value is None:
            return None  # NULL is allowed unless it's completeness rule
        
        allowed_values = rule.get('allowed_values', [])
        
        if allowed_values:
            if isinstance(allowed_values, str):
                allowed_values = eval(allowed_values)  # Parse JSON array
            
            if value not in allowed_values:
                return {
                    'rule_id': rule['rule_id'],
                    'field': field,
                    'value': value,
                    'violation_type': 'datatype',
                    'severity': rule['severity'],
                    'message': f"Value '{value}' not in allowed values: {allowed_values}"
                }
        
        return None
    
    def _check_range(self, record, rule):
        """Check if numeric value is within range"""
        field = rule['field_name']
        value = record.get(field)
        
        if value is None:
            return None
        
        try:
            value_num = float(value)
        except (TypeError, ValueError):
            return {
                'rule_id': rule['rule_id'],
                'field': field,
                'value': value,
                'violation_type': 'range',
                'severity': rule['severity'],
                'message': f"Value '{value}' cannot be converted to number"
            }
        
        min_val = rule.get('min_value')
        max_val = rule.get('max_value')
        
        if min_val is not None and value_num < min_val:
            return {
                'rule_id': rule['rule_id'],
                'field': field,
                'value': value,
                'violation_type': 'range',
                'severity': rule['severity'],
                'message': f"Value {value} is below minimum {min_val}"
            }
        
        if max_val is not None and value_num > max_val:
            return {
                'rule_id': rule['rule_id'],
                'field': field,
                'value': value,
                'violation_type': 'range',
                'severity': rule['severity'],
                'message': f"Value {value} is above maximum {max_val}"
            }
        
        return None
    
    def _check_format(self, record, rule):
        """Check if value matches regex pattern"""
        import re
        
        field = rule['field_name']
        value = record.get(field)
        
        if value is None:
            return None
        
        pattern = rule.get('pattern')
        if not pattern:
            return None
        
        if not re.match(pattern, str(value)):
            return {
                'rule_id': rule['rule_id'],
                'field': field,
                'value': value,
                'violation_type': 'format',
                'severity': rule['severity'],
                'message': f"Value '{value}' does not match pattern '{pattern}'"
            }
        
        return None
    
    def evaluate_batch(self, records, domain, table_name):
        """Evaluate multiple records efficiently"""
        all_violations = []
        
        for record in records:
            violations = self.evaluate_record(record, domain, table_name)
            all_violations.extend(violations)
        
        return all_violations
    
    def _log_rule_error(self, rule_id, error_message):
        """Log rule evaluation error"""
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error evaluating rule {rule_id}: {error_message}")
```

### Initial Rule Pack - Patient Domain

```json
{
  "domain": "patient",
  "rules": [
    {
      "rule_id": "COMP-PATIENT-001",
      "rule_type": "completeness",
      "rule_name": "Patient ID Required",
      "field_name": "patient_id",
      "severity": "critical"
    },
    {
      "rule_id": "COMP-PATIENT-002",
      "rule_type": "completeness",
      "rule_name": "Patient MRN Required",
      "field_name": "mrn",
      "severity": "critical"
    },
    {
      "rule_id": "COMP-PATIENT-003",
      "rule_type": "completeness",
      "rule_name": "Patient First Name Required",
      "field_name": "first_name",
      "severity": "high"
    },
    {
      "rule_id": "RANGE-PATIENT-001",
      "rule_type": "range",
      "rule_name": "Patient Age Valid Range",
      "field_name": "age",
      "min_value": 0,
      "max_value": 150,
      "severity": "medium"
    },
    {
      "rule_id": "FORMAT-PATIENT-001",
      "rule_type": "format",
      "rule_name": "Patient Email Valid Format",
      "field_name": "email",
      "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
      "severity": "low"
    }
  ]
}
```

---

## 6. Rule Pack Management

### Rule Packs by Domain

| Domain | Rule Count | Critical | High | Medium | Low |
|--------|-----------|----------|------|--------|-----|
| **patient** | 8 | 2 | 3 | 2 | 1 |
| **appointment** | 10 | 1 | 4 | 3 | 2 |
| **medication** | 7 | 1 | 2 | 3 | 1 |
| **coding** | 6 | 1 | 2 | 2 | 1 |
| **document** | 5 | 0 | 2 | 2 | 1 |
| **provider** | 6 | 1 | 2 | 2 | 1 |

**Total: 42 rules across 6 domains**

---

## 7. Testing Strategy

### Test Cases

```python
def test_completeness_rule():
    """Test completeness check"""
    record_missing = {'first_name': 'John', 'last_name': 'Doe'}
    evaluator = RuleEvaluator(db)
    
    violations = evaluator.evaluate_record(record_missing, 'patient', 'patient')
    assert len(violations) > 0
    assert any(v['rule_id'] == 'COMP-PATIENT-001' for v in violations)

def test_range_rule():
    """Test range validation"""
    record_invalid = {'patient_id': '123', 'age': 200}  # > 150
    evaluator = RuleEvaluator(db)
    
    violations = evaluator.evaluate_record(record_invalid, 'patient', 'patient')
    assert len(violations) > 0
    assert any(v['rule_id'] == 'RANGE-PATIENT-001' for v in violations)

def test_format_rule():
    """Test format/regex validation"""
    record_invalid_email = {'patient_id': '123', 'email': 'invalid_email'}
    evaluator = RuleEvaluator(db)
    
    violations = evaluator.evaluate_record(record_invalid_email, 'patient', 'patient')
    assert len(violations) > 0
    assert any(v['rule_id'] == 'FORMAT-PATIENT-001' for v in violations)

def test_batch_evaluation():
    """Test batch evaluation performance"""
    import time
    records = [{'patient_id': f'P{i}', 'mrn': f'MRN{i}', 'age': 30} for i in range(1000)]
    evaluator = RuleEvaluator(db)
    
    start = time.time()
    violations = evaluator.evaluate_batch(records, 'patient', 'patient')
    duration = time.time() - start
    
    assert duration < 5.0  # <5s for 1000 records
```

---

## 8. Success Metrics

- [ ] 40+ rules defined and deployed
- [ ] Rule evaluation <5ms per rule
- [ ] Batch evaluation <5s per 1000 records
- [ ] All 15+ test cases passing
- [ ] Rule registry accessible and queryable
- [ ] Rule changes tracked in audit log

---

## 9. Definition of Done

- [ ] Rule schema implemented and deployed
- [ ] Rule evaluator engine working
- [ ] 40+ rules defined for 6+ domains
- [ ] Rule versioning and deprecation working
- [ ] Batch evaluation performance >1000 records/s
- [ ] All test cases passing
- [ ] Rule pack documentation published
- [ ] Ready for RULE-2 integration

---

## Next Task

→ RULE-2: Duplicate Detection Rules
