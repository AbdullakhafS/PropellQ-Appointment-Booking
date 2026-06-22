-- Migration: 0001__production_schema_hardening
-- Version: 1.0.0
-- Environment: development | staging | production
-- Purpose: Promote the existing schema into a production-hardened version
-- Safety: additive/constraint hardening only; no destructive operations

PRAGMA foreign_keys = ON;

-- The production schema is stored as a versioned artifact to support strict ordering.
-- This migration is intentionally idempotent via IF NOT EXISTS guards.
.read ../schema_v1_production.sql

PRAGMA user_version = 1;
