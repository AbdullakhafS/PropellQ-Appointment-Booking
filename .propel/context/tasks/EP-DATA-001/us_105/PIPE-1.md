# PIPE-1: Migration Framework Integration

**Task ID:** PIPE-1  
**Parent:** TASK-105  
**Category:** Pipeline Infrastructure  
**Points:** 7  
**Status:** Ready to Start  
**Created:** 2026-06-22

---

## 1. Objective

Select, integrate, and configure a database migration tool (Flyway or Liquibase) with strict version ordering, deterministic execution, environment awareness, and comprehensive metadata tracking.

---

## 2. Inputs

- Database standards from TASK-104
- CI/CD pipeline infrastructure (GitHub Actions or Azure Pipelines)
- Environment configuration (dev, test, staging, prod)
- Migration naming convention standards

---

## 3. Outputs

**Deliverables:**
- [ ] Migration tool selection document (Flyway vs. Liquibase comparison)
- [ ] Integration configuration (pom.xml, build.gradle, or package.json)
- [ ] Migration directory structure created and documented
- [ ] Version naming convention enforced in CI/CD
- [ ] One-way ordering validation implementation
- [ ] Deterministic execution guarantees documented
- [ ] Dry-run capability verified
- [ ] Rollback script association validation

---

## 4. Acceptance Criteria

1. **Tool Selection & Integration:**
   - [ ] Flyway or Liquibase selected with justification
   - [ ] Tool integrated into build pipeline
   - [ ] Version management working (tracks all executed migrations)
   - [ ] Dry-run mode supports preview-only execution

2. **Versioning & Ordering:**
   - [ ] Migrations execute strictly in numerical order (V001 → V002 → V003)
   - [ ] No out-of-order execution possible
   - [ ] Version numbers are immutable (cannot be reused)
   - [ ] Attempted out-of-order deployment rejected with clear error

3. **Directory Structure:**
   - [ ] Forward migrations: `db/migrations/V###__description.sql`
   - [ ] Rollback migrations: `db/migrations/U###__description.sql`
   - [ ] Structure enforced by CI/CD validation
   - [ ] Automatic detection of new migration files

4. **Metadata Persistence:**
   - [ ] Migration history table created (`flyway_schema_history` or `databasechangelog`)
   - [ ] All migrations logged with: version, checksum, timestamp, status, duration
   - [ ] Version metadata queryable (SELECT * FROM schema_history)

5. **Checksum Validation:**
   - [ ] SHA256 checksums calculated for all migrations
   - [ ] Checksum mismatch detected and reported
   - [ ] Prevents accidental modification of executed migrations

---

## 5. Implementation Details

### Tool Comparison

| Aspect | Flyway (Open Source) | Liquibase |
|--------|-------------------|-----------|
| License | Apache 2.0 | CDDL/Commercial |
| Native SQL | ✅ Yes | ✅ Yes (with XML) |
| Dry-run | ✅ Yes | ✅ Yes |
| Ordering | ✅ Strict numeric | ✅ Strict numeric |
| Complexity | ⭐ Low | ⭐⭐ Medium |
| Community | ⭐⭐⭐ Large | ⭐⭐⭐ Large |
| Recommendation | ✅ **Recommended** | ✅ Alternative |

**Recommendation:** Flyway (simpler, native SQL, good for this use case)

### Directory Structure

```
appointment-db/
├── db/
│   ├── migrations/
│   │   ├── V001__create_patient_table.sql
│   │   ├── U001__drop_patient_table.sql
│   │   ├── V002__add_mrn_unique_constraint.sql
│   │   ├── U002__drop_mrn_unique_constraint.sql
│   │   ├── V003__add_appointment_indexes.sql
│   │   └── U003__drop_appointment_indexes.sql
│   └── seed/
│       ├── V101__seed_clinics.sql
│       └── V102__seed_specialties.sql
├── src/
│   ├── main/
│   │   └── java/
│   │       └── com/appointment/migration/
│   │           ├── MigrationRunner.java
│   │           └── MigrationValidator.java
│   └── test/
│       └── java/
│           └── com/appointment/migration/
│               └── MigrationTest.java
└── pom.xml (or build.gradle)
```

### Flyway Integration (Maven Example)

**pom.xml:**
```xml
<dependency>
    <groupId>org.flywaydb</groupId>
    <artifactId>flyway-core</artifactId>
    <version>9.22.3</version>
</dependency>
```

**flyway-maven-plugin:**
```xml
<plugin>
    <groupId>org.flywaydb</groupId>
    <artifactId>flyway-maven-plugin</artifactId>
    <version>9.22.3</version>
    <configuration>
        <locations>
            <location>filesystem:db/migrations</location>
        </locations>
        <baselineOnMigrate>true</baselineOnMigrate>
        <validateOnMigrate>true</validateOnMigrate>
    </configuration>
</plugin>
```

**Maven Commands:**
```bash
# Validate migrations
mvn flyway:validate

# Run migrations (dev)
mvn flyway:migrate -Dflyway.url=jdbc:mysql://localhost:3306/appointment_db

# Dry-run (info only)
mvn flyway:info

# Undo last migration (Flyway Pro only, or manual)
mvn flyway:undo
```

### Migration Script Examples

**V001__create_patient_table.sql:**
```sql
-- Description: Create core patient table with primary key and indexes
-- Author: Database Team
-- Date: 2026-06-22

CREATE TABLE patient (
  patient_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  mrn VARCHAR(50) NOT NULL UNIQUE,
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  dob DATE NOT NULL,
  gender CHAR(1) NOT NULL DEFAULT 'X',
  email VARCHAR(255) UNIQUE,
  phone_primary VARCHAR(20) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  KEY idx_patient_email (email),
  KEY idx_patient_phone (phone_primary),
  
  CHECK (gender IN ('M', 'F', 'O', 'X')),
  CHECK (dob < CURDATE())
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**U001__drop_patient_table.sql (Rollback):**
```sql
-- Undo: Drop patient table
DROP TABLE patient;
```

**V002__add_appointment_indexes.sql:**
```sql
-- Description: Add performance indexes for appointment queries
-- Index Strategy: Covers hot-path queries (patient lookup, provider schedule)

ALTER TABLE appointment ADD INDEX idx_patient_status_time 
  (patient_id, appointment_status, scheduled_start_time);

ALTER TABLE appointment ADD INDEX idx_provider_time 
  (provider_id, scheduled_start_time);

ALTER TABLE appointment ADD INDEX idx_clinic_time 
  (clinic_id, scheduled_start_time, appointment_status);
```

**U002__drop_appointment_indexes.sql:**
```sql
-- Undo: Drop appointment indexes
ALTER TABLE appointment DROP INDEX idx_patient_status_time;
ALTER TABLE appointment DROP INDEX idx_provider_time;
ALTER TABLE appointment DROP INDEX idx_clinic_time;
```

### One-Way Ordering Validation

**Java Implementation:**
```java
public class MigrationValidator {
    public void validateOrdering(List<Migration> migrations) {
        for (int i = 0; i < migrations.size() - 1; i++) {
            int current = extractVersionNumber(migrations.get(i));
            int next = extractVersionNumber(migrations.get(i + 1));
            
            if (next <= current) {
                throw new ValidationException(
                    "Out-of-order migration detected: V" + next + 
                    " cannot follow V" + current);
            }
        }
    }
    
    private int extractVersionNumber(Migration m) {
        // Extract from V001, V002, etc.
        return Integer.parseInt(m.getVersion().replaceAll("[^0-9]", ""));
    }
}
```

**CI/CD Validation (GitHub Actions):**
```yaml
- name: Validate Migration Ordering
  run: |
    MIGRATIONS=$(ls db/migrations/V*.sql | sort)
    PREV=0
    for file in $MIGRATIONS; do
      NUM=$(echo $file | grep -oE 'V[0-9]+' | grep -oE '[0-9]+')
      if [ $NUM -le $PREV ]; then
        echo "❌ Out-of-order migration: $file"
        exit 1
      fi
      PREV=$NUM
    done
    echo "✅ All migrations in order"
```

### Checksum Validation

**Flyway Built-In:**
- Flyway automatically calculates SHA1 (MD5 for backward compat) of each migration
- If migration file content changes after execution, checksum mismatch error
- Prevents accidental modifications

**Manual Verification:**
```bash
# Calculate migration checksum
sha256sum db/migrations/V001__create_patient_table.sql

# Query Flyway history
SELECT version, description, checksum, installed_on FROM flyway_schema_history;
```

### Dry-Run Capability

```bash
# Flyway info shows pending migrations without applying
mvn flyway:info -Dflyway.url=jdbc:mysql://localhost:3306/appointment_db

# Output:
# +---------+---------+---------------------+------+---------------------+---------+
# | Version | Type    | Description         | Installed On | Execution Time | State   |
# +---------+---------+---------------------+------+---------------------+---------+
# | 1       | SQL     | create patient table | 2026-06-22   | 250 ms         | Success |
# | 2       | SQL     | add indexes          | <not yet>    |                | Pending |
# +---------+---------+---------------------+------+---------------------+---------+
```

---

## 6. Success Metrics

- [ ] Tool selected and justified in documentation
- [ ] Integration complete (build pipeline runs migrations)
- [ ] Directory structure created and validated
- [ ] 10+ migrations executed in strict order
- [ ] Checksum validation working
- [ ] Dry-run mode functional
- [ ] <100ms per migration lookup
- [ ] Metadata table queryable

---

## 7. Definition of Done

- [ ] Migration tool integrated into build process
- [ ] Directory structure created and enforced
- [ ] Naming conventions validated
- [ ] 5+ sample migrations created and tested
- [ ] Checksum validation working
- [ ] Dry-run capability verified
- [ ] Peer-reviewed and approved
- [ ] Ready for PIPE-2

---

## Next Task

→ PIPE-2: Environment Promotion Workflow
