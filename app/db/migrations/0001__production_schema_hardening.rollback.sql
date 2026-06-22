-- Rollback: 0001__production_schema_hardening.rollback
-- Version: 1.0.0
-- Strategy: restore from backup artifact generated before forward migration
-- Safety: emergency restore only

-- This script is intentionally non-destructive and expects the operator to
-- restore the backed-up database file captured by the migration pipeline.
SELECT 'Restore the pre-migration backup file to roll back 0001__production_schema_hardening' AS rollback_instructions;
