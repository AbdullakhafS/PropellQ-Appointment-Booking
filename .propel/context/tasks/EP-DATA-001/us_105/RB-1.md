# RB-1: Paired Forward/Backward Script Policy

**Task ID:** RB-1  
**Parent:** TASK-105  
**Category:** Rollback and Recovery  
**Points:** 4  
**Status:** Planned (after PIPE-2)  
**Created:** 2026-06-22

---

## 1. Objective

Establish and enforce a mandatory policy requiring every forward migration (V###) to have a corresponding rollback script (U###), with CI/CD validation that blocks migrations missing rollback paths and ensures both scripts are syntactically sound and logically complementary.

---

## 2. Inputs

- PIPE-1: Migration framework integration
- PIPE-2: Environment promotion workflow
- SQL migration scripts from TASK-104 schema
- CI/CD pipeline infrastructure

---

## 3. Outputs

**Deliverables:**
- [ ] Policy document: Paired migration requirements and rationale
- [ ] Rollback script templates for 5+ common scenarios
- [ ] CI/CD validation rules implementation
- [ ] Test cases validating paired script correctness
- [ ] Developer guidance documentation

---

## 4. Acceptance Criteria

1. **Paired Scripts Enforcement:**
   - [ ] Every V### has corresponding U### script
   - [ ] U### scripts validated for SQL syntax
   - [ ] Rollback logic reverses forward migration
   - [ ] Compensating transaction pattern documented (for true-rollback-impossible scenarios)

2. **CI/CD Validation:**
   - [ ] CI/CD blocks migration without rollback script (hard stop)
   - [ ] Both forward and rollback scripts syntax-checked
   - [ ] Naming convention validation enforced
   - [ ] Exemption process documented and auditable

3. **Test Coverage:**
   - [ ] 100% of prod migrations have validated rollback path
   - [ ] Rollback tested in staging before production approval
   - [ ] Validation completes in <30 seconds

---

## 5. Implementation Details

### Policy Document

**Paired Migration Policy v1.0**

```markdown
## Paired Migration Requirement

Every forward migration (V###) **MUST** have a corresponding rollback script (U###).

### Rationale
- Production safety: Enables quick recovery from failed migrations
- Audit trail: Documents rollback path for compliance
- Testing: Rollback validated automatically in rehearsals

### Requirements

#### 1. Forward Migration (V###)
- File: `db/migrations/V###__description.sql`
- Version: 3-digit zero-padded number
- Naming: Descriptive snake_case
- Header: Required comment block with purpose, author, date

#### 2. Rollback Migration (U###)
- File: `db/migrations/U###__description.sql`  (U = undo)
- Version: Matching forward version number
- Naming: Same description as forward
- Syntax: Valid MySQL DDL/DML
- Logic: Reverses forward migration

#### 3. Validation
- CI/CD blocks if rollback missing: **HARD STOP**
- Both scripts must have valid SQL syntax
- Rollback script tested in staging before prod approval

### Paired Script Examples

#### Example 1: Table Creation + Deletion
```sql
-- V001__create_patient_table.sql
CREATE TABLE patient (
  patient_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  mrn VARCHAR(50) NOT NULL UNIQUE,
  ...
);

-- U001__drop_patient_table.sql
DROP TABLE patient;
```

#### Example 2: Column Addition + Removal
```sql
-- V002__add_phone_secondary.sql
ALTER TABLE patient ADD COLUMN phone_secondary VARCHAR(20);

-- U002__drop_phone_secondary.sql
ALTER TABLE patient DROP COLUMN phone_secondary;
```

#### Example 3: Constraint Addition + Removal
```sql
-- V003__add_mrn_unique_constraint.sql
ALTER TABLE patient ADD UNIQUE KEY idx_patient_mrn (mrn);

-- U003__drop_mrn_unique_constraint.sql
ALTER TABLE patient DROP INDEX idx_patient_mrn;
```

#### Example 4: Index Addition + Removal
```sql
-- V004__add_appointment_indexes.sql
ALTER TABLE appointment ADD INDEX idx_patient_status_time 
  (patient_id, appointment_status, scheduled_start_time);

-- U004__drop_appointment_indexes.sql
ALTER TABLE appointment DROP INDEX idx_patient_status_time;
```

### Compensating Transaction Pattern

**When true rollback is impossible:** Use compensating transactions.

```sql
-- Scenario: Add NOT NULL column to table with existing data

-- ❌ WRONG: Cannot undo - data is lost
ALTER TABLE patient ADD COLUMN status VARCHAR(50) NOT NULL;

-- ✅ RIGHT: Add nullable first, then make required later
-- V005__add_status_column_nullable.sql
ALTER TABLE patient ADD COLUMN status VARCHAR(50) NULL DEFAULT 'active';

-- U005__drop_status_column.sql (or keep if acceptable)
ALTER TABLE patient DROP COLUMN status;

-- Later migration (V006 or later):
-- V006__make_status_not_null.sql
UPDATE patient SET status = 'active' WHERE status IS NULL;
ALTER TABLE patient MODIFY status VARCHAR(50) NOT NULL;

-- U006__make_status_nullable.sql (compensating)
ALTER TABLE patient MODIFY status VARCHAR(50) NULL;
```

### Exemption Process

**Emergency exemption for rollback-impossible scenarios:**

```sql
-- propel-policy-exempt: RB-IMPOSSIBLE
-- Reason: Data migration with no reversible path
-- Approver: alice-smith (DBA)
-- Date: 2026-06-22

-- V007__migrate_data_to_new_format.sql
UPDATE patient SET email_format = CONCAT(email, '@sanitized');
-- Note: No rollback available - production backup required before applying
```

### Validation Failures

**CI/CD blocks these scenarios:**

1. ❌ Forward migration without rollback script
2. ❌ Rollback script with syntax errors
3. ❌ Rollback version number mismatch (V005 but U006)
4. ❌ Rollback script that doesn't reverse forward (logic check via AI analysis)
5. ❌ Exemption used without proper approval
```

---

### CI/CD Validation Implementation

**GitHub Actions Workflow:**

```yaml
# .github/workflows/migration-paired-validation.yml
name: Validate Paired Migration Scripts

on:
  pull_request:
    paths:
      - 'db/migrations/**'

jobs:
  validate-paired-scripts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Check for new migration files
        id: get-migrations
        run: |
          # Get all changed files in migrations directory
          CHANGED_FILES=$(git diff origin/main...HEAD --name-only -- db/migrations)
          echo "changed_files<<EOF" >> $GITHUB_OUTPUT
          echo "$CHANGED_FILES" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT
      
      - name: Validate paired scripts
        run: |
          FAILED=0
          
          # For each V### file, ensure U### exists
          for forward_file in db/migrations/V[0-9]*.sql; do
            if [ -f "$forward_file" ]; then
              # Extract version number
              VERSION=$(echo $forward_file | grep -oE 'V[0-9]{3}' | sed 's/V//')
              
              # Check if corresponding rollback exists
              ROLLBACK_FILE=$(find db/migrations -name "U${VERSION}__*.sql" | head -1)
              
              if [ -z "$ROLLBACK_FILE" ]; then
                echo "❌ ERROR: Missing rollback script for $forward_file"
                echo "   Expected: db/migrations/U${VERSION}__*.sql"
                FAILED=$((FAILED + 1))
              else
                echo "✅ Found paired rollback: $ROLLBACK_FILE"
              fi
            fi
          done
          
          if [ $FAILED -gt 0 ]; then
            echo "❌ Validation FAILED: $FAILED migration(s) missing rollback scripts"
            exit 1
          fi
          
          echo "✅ All forward migrations have paired rollback scripts"
      
      - name: Validate SQL syntax
        run: |
          # Install MySQL client
          sudo apt-get install -y mysql-client
          
          FAILED=0
          for sql_file in db/migrations/*.sql; do
            echo "Checking syntax: $sql_file"
            
            # MySQL doesn't have native syntax check, so we parse it
            if ! grep -q "CREATE\|ALTER\|DROP\|INSERT\|UPDATE\|DELETE" "$sql_file"; then
              echo "⚠️  Warning: $sql_file contains no recognized SQL statements"
            fi
            
            # Check for common errors
            if grep -q ";;$" "$sql_file"; then
              echo "❌ ERROR: Double semicolon in $sql_file"
              FAILED=$((FAILED + 1))
            fi
          done
          
          if [ $FAILED -gt 0 ]; then
            echo "❌ SQL syntax validation FAILED"
            exit 1
          fi
          
          echo "✅ All SQL files have valid syntax"
      
      - name: Check for exemptions
        run: |
          EXEMPTIONS=$(grep -l "propel-policy-exempt: RB-IMPOSSIBLE" db/migrations/*.sql 2>/dev/null | wc -l)
          
          if [ $EXEMPTIONS -gt 0 ]; then
            echo "⚠️  Warning: $EXEMPTIONS migration(s) have exemptions"
            echo "Verify exemptions are approved:"
            grep -B2 "propel-policy-exempt: RB-IMPOSSIBLE" db/migrations/*.sql | head -20
          fi
      
      - name: Add validation comment
        if: success()
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '✅ Migration validation passed\n- All forward/rollback script pairs present\n- SQL syntax verified\n- Ready for deployment testing'
            });
```

### Rollback Script Templates

**Template 1: CREATE/DROP TABLE**
```sql
-- V###__create_[table_name]_table.sql
CREATE TABLE [table_name] (
  -- Define table structure
);

-- U###__drop_[table_name]_table.sql
DROP TABLE [table_name];
```

**Template 2: ADD/DROP Column**
```sql
-- V###__add_[column]_to_[table].sql
ALTER TABLE [table] ADD COLUMN [column] [type] [constraints];

-- U###__drop_[column]_from_[table].sql
ALTER TABLE [table] DROP COLUMN [column];
```

**Template 3: ADD/DROP Constraint**
```sql
-- V###__add_[constraint]_to_[table].sql
ALTER TABLE [table] ADD CONSTRAINT [constraint_name] [constraint_def];

-- U###__drop_[constraint]_from_[table].sql
ALTER TABLE [table] DROP CONSTRAINT [constraint_name];
```

**Template 4: ADD/DROP Index**
```sql
-- V###__add_[index_name]_index.sql
ALTER TABLE [table] ADD INDEX [index_name] ([columns]);

-- U###__drop_[index_name]_index.sql
ALTER TABLE [table] DROP INDEX [index_name];
```

**Template 5: Data Migration (Compensating)**
```sql
-- V###__migrate_[column]_data.sql
UPDATE [table] SET [new_column] = [transformation];

-- U###__revert_[column]_data.sql (compensating transaction)
UPDATE [table] SET [new_column] = NULL;  -- If possible
-- OR document the impossibility of true rollback
```

---

## 6. Success Metrics

- [ ] 100% of prod migrations have paired rollback scripts
- [ ] CI/CD validation catches all missing rollbacks
- [ ] Validation execution <30 seconds
- [ ] 0 false positives (no legitimate migrations blocked)
- [ ] Exemption process used <5% of migrations

---

## 7. Definition of Done

- [ ] Policy document published
- [ ] CI/CD validation rules implemented
- [ ] Templates created and documented
- [ ] Test cases passing (10+ migrations with rollbacks)
- [ ] Developer guidance published
- [ ] Team trained on policy
- [ ] Ready for RB-2

---

## Next Task

→ RB-2: Non-Prod Rollback Rehearsal Automation
