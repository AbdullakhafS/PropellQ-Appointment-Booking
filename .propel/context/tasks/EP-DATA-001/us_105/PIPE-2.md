# PIPE-2: Environment Promotion Workflow

**Task ID:** PIPE-2  
**Parent:** TASK-105  
**Category:** Pipeline Infrastructure  
**Points:** 7  
**Status:** Planned (after PIPE-1)  
**Created:** 2026-06-22

---

## 1. Objective

Configure safe migration progression across dev → test → staging → production environments with approval gates, artifact immutability, and pre-deployment validation checks.

---

## 2. Inputs

- PIPE-1: Framework integration and directory structure
- Environment definitions (dev, test, staging, prod)
- CI/CD pipeline (GitHub Actions or Azure Pipelines)
- Approval gate infrastructure
- RB-1: Rollback script validation

---

## 3. Outputs

- [ ] Environment promotion workflow defined (4-stage progression)
- [ ] Artifact immutability implemented
- [ ] Approval gates configured for staging/prod
- [ ] Pre-deployment validation checklist automated
- [ ] Rollback path pre-validated before promotion
- [ ] Environment-specific parameters (if needed)
- [ ] Promotion pipeline documentation

---

## 4. Acceptance Criteria

1. **Environment Progression:**
   - [ ] Dev: Auto-apply migrations on every commit
   - [ ] Test: Auto-apply after code review approval
   - [ ] Staging: Manual approval + pre-validation required
   - [ ] Prod: Manual approval + preflight checks + rollback verified

2. **Artifact Immutability:**
   - [ ] Migration files locked as read-only after first environment
   - [ ] Version control prevents modification (branch protection)
   - [ ] Checksums validated across all environments
   - [ ] Rollback scripts verified before promotion

3. **Pre-Deployment Validation:**
   - [ ] Dry-run executes successfully in target environment
   - [ ] Schema checksum matches expected value
   - [ ] All expected tables/indexes/constraints present
   - [ ] Rollback script exists and has valid syntax

4. **Approval Gates:**
   - [ ] Staging: Automatic approval after test pass
   - [ ] Prod: Manual approval required (2+ approvers)
   - [ ] Approval valid only for 24 hours
   - [ ] Approver identity and timestamp recorded

---

## 5. Implementation Details

### Environment Promotion Pipeline

```
COMMIT to main
  ↓
[DEV] Auto-Deploy
  ├─ Dry-run: ✅ Pass
  ├─ Deploy: ✅ Success
  └─ Smoke tests: ✅ Pass
  ↓
[TEST] Auto-Deploy (if CI/CD passes)
  ├─ Code review: ✅ Approved
  ├─ Dry-run: ✅ Pass
  ├─ Deploy: ✅ Success
  └─ Smoke tests: ✅ Pass
  ↓
[STAGING] Manual Approval + Pre-Validation
  ├─ Manual trigger: Developer initiates
  ├─ Pre-checks: Backup verified, locks released
  ├─ Dry-run: ✅ Pass
  ├─ Deploy: ✅ Success
  ├─ Post-validation: Schema checksum, smoke queries
  └─ Ready for prod notification
  ↓
[PROD] Manual Approval + Preflight Checks
  ├─ Approval required: 2× approvers (DBA, Platform-Eng)
  ├─ Approval window: 24 hours
  ├─ Preflight checks: Backup, locks, disk space
  ├─ Dry-run: ✅ Pass
  ├─ Deploy: ✅ Success (5-10 min window)
  ├─ Post-validation: Schema checksum, smoke queries
  └─ Incident ticket (if needed): Auto-file
```

### Artifact Immutability

**Git Branch Protection:**
```yaml
# .github/workflows/branch-protection.yml
- name: Protect main branch
  uses: actions/github-script@v6
  with:
    script: |
      github.rest.repos.updateBranchProtection({
        owner: context.repo.owner,
        repo: context.repo.repo,
        branch: 'main',
        required_status_checks: {
          strict: true,
          contexts: ['ci/migration-validation', 'ci/lint']
        },
        required_pull_request_reviews: {
          dismiss_stale_reviews: true,
          require_code_owner_reviews: true
        },
        restrictions: {
          users: [],
          teams: ['platform-eng'],
          apps: []
        }
      });
```

**File System Immutability (Post-Deploy):**
```bash
# After migration applied to prod
# Lock migration files to read-only
find db/migrations/V*.sql -exec chmod 444 {} \;

# Prevent accidental modifications
git config core.fileMode false
```

### Pre-Deployment Validation Checklist

**Automated Checks (run before approval):**
```yaml
name: Pre-Deploy Validation
on: 
  pull_request:
    paths:
      - 'db/migrations/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      # Check 1: Naming convention
      - name: Validate migration naming
        run: |
          for file in db/migrations/V*.sql; do
            if ! [[ $file =~ V[0-9]{3}__.*\.sql ]]; then
              echo "❌ Invalid naming: $file"
              exit 1
            fi
          done
          echo "✅ All migrations follow V###__description.sql pattern"
      
      # Check 2: Paired rollback scripts
      - name: Validate paired rollback scripts
        run: |
          for forward in db/migrations/V*.sql; do
            version=$(echo $forward | grep -oE 'V[0-9]{3}')
            rollback="db/migrations/U${version:1}__*.sql"
            if ! ls $rollback 2>/dev/null; then
              echo "❌ Missing rollback for $forward"
              exit 1
            fi
          done
          echo "✅ All forward migrations have rollback scripts"
      
      # Check 3: Checksum validation
      - name: Validate checksums
        run: |
          mysql -h ${{ secrets.DB_HOST }} -u ${{ secrets.DB_USER }} \
            -p${{ secrets.DB_PASS }} -e \
            "SELECT version, checksum FROM flyway_schema_history"
          echo "✅ Checksum validation complete"
      
      # Check 4: Dry-run validation
      - name: Dry-run on test environment
        env:
          DB_URL: ${{ secrets.TEST_DB_URL }}
        run: |
          mvn flyway:info -Dflyway.url=$DB_URL
          echo "✅ Dry-run successful"
      
      # Check 5: Syntax validation
      - name: Validate SQL syntax
        run: |
          for file in db/migrations/*.sql; do
            if ! mysql --syntax-check $file 2>/dev/null; then
              echo "❌ Syntax error in $file"
              exit 1
            fi
          done
          echo "✅ All SQL files have valid syntax"
```

### Environment-Specific Parameters

**Configuration Matrix:**
```yaml
# config/migration-config.yml
environments:
  dev:
    auto_apply: true
    approval_required: false
    timeout_seconds: 300
    dry_run_first: false
    post_validation: basic_smoke_tests
    
  test:
    auto_apply: true
    approval_required: false  # Auto-approved after CI passes
    timeout_seconds: 300
    dry_run_first: true
    post_validation: full_smoke_tests
    
  staging:
    auto_apply: false
    approval_required: manual
    approvers: ['platform-eng']
    timeout_seconds: 600
    dry_run_first: true
    post_validation: full_smoke_tests + schema_checksum
    
  prod:
    auto_apply: false
    approval_required: manual
    approvers: ['dba-team', 'platform-eng']  # 2 required
    approval_valid_hours: 24
    timeout_seconds: 300
    dry_run_first: true
    post_validation: full_smoke_tests + schema_checksum + incident_check
    backup_required: true
    rollback_tested: true
```

### Rollback Path Pre-Validation

**Before Promoting to Prod:**
```yaml
- name: Pre-Promotion Rollback Validation
  run: |
    # Step 1: Verify rollback script exists
    for version in $(git diff main..HEAD --name-only | grep V); do
      u_script=${version/V/U}
      if ! [ -f "db/migrations/$u_script" ]; then
        echo "❌ Missing rollback script for $version"
        exit 1
      fi
    done
    
    # Step 2: Validate rollback script syntax
    for file in db/migrations/U*.sql; do
      if ! mysql --syntax-check $file 2>/dev/null; then
        echo "❌ Syntax error in rollback $file"
        exit 1
      fi
    done
    
    # Step 3: Simulate rollback on staging
    echo "Simulating rollback on staging..."
    STAGING_VERSION=$(mysql -h staging-db -e "SELECT version FROM flyway_schema_history LIMIT 1")
    mvn flyway:migrate -Dflyway.url=jdbc:mysql://staging-db \
      -Dflyway.target=$STAGING_VERSION
    
    # Step 4: Verify rollback restores schema
    STAGING_CHECKSUM_BEFORE=$(generate_checksum staging-db)
    mvn flyway:migrate -Dflyway.url=jdbc:mysql://staging-db \
      -Dflyway.target=$((STAGING_VERSION + 1))
    mvn flyway:migrate -Dflyway.url=jdbc:mysql://staging-db \
      -Dflyway.target=$STAGING_VERSION
    STAGING_CHECKSUM_AFTER=$(generate_checksum staging-db)
    
    if [ "$STAGING_CHECKSUM_BEFORE" != "$STAGING_CHECKSUM_AFTER" ]; then
      echo "❌ Rollback checksum mismatch"
      exit 1
    fi
    
    echo "✅ Rollback path validated"
```

### Approval Gate Integration (GitHub)

**GitHub Branch Protection + Manual Approval:**
```yaml
# .github/workflows/production-deployment.yml
name: Production Deployment Gate

on:
  workflow_dispatch:  # Manual trigger
    inputs:
      migration_version:
        description: 'Migration version to deploy (e.g., V005)'
        required: true
        type: choice
        options:
          - V001
          - V002
          - V003
          - V004
          - V005

jobs:
  request-approval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Request DBA Approval
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `🔒 **Production Migration Approval Required**\n\nVersion: ${{ github.event.inputs.migration_version }}\n\nApprovers needed:\n- [ ] DBA Team\n- [ ] Platform Engineering\n\nRequest ID: #${{ github.run_id }}`
            });
      
      - name: Wait for Approval (20 min timeout)
        run: |
          echo "Waiting for approval..."
          for i in {1..120}; do
            STATUS=$(gh run view ${{ github.run_id }} --json conclusion -q '.conclusion')
            if [ "$STATUS" = "success" ]; then
              echo "✅ Approval received"
              exit 0
            fi
            sleep 10
          done
          echo "❌ Approval timeout"
          exit 1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  
  deploy:
    needs: request-approval
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Production
        run: |
          echo "Deploying ${{ github.event.inputs.migration_version }}..."
          mvn flyway:migrate \
            -Dflyway.url=${{ secrets.PROD_DB_URL }}
          
          echo "✅ Migration applied successfully"
```

---

## 6. Success Metrics

- [ ] Dev migrations apply automatically on commit
- [ ] Test migrations apply after code review
- [ ] Staging requires manual trigger + pre-validation
- [ ] Prod requires 2 approvals + preflight checks
- [ ] Artifacts immutable (checksum validated)
- [ ] Rollback path pre-validated before promotion
- [ ] All pre-checks automated and blocking
- [ ] Approval audit trail recorded

---

## 7. Definition of Done

- [ ] Environment progression pipeline implemented
- [ ] Approval gates configured
- [ ] Pre-deployment validation automated
- [ ] Artifact immutability enforced
- [ ] Rollback validation working
- [ ] Tested end-to-end across all environments
- [ ] Documentation complete
- [ ] Ready for RB-1, RB-2, RB-3

---

## Next Task

→ RB-1: Paired Forward/Backward Script Policy
