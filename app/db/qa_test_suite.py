#!/usr/bin/env python3
"""
Comprehensive QA Test Suite for Production Schema (v1.0)

Covers:
- QA-1: Integrity constraint validation (PK/FK/Check/Unique)
- QA-2: Latency budget validation (p95 latencies)
- QA-3: Duplicate prevention validation (uniqueness constraints)
- QA-4: Naming/semantics review (column names, table names)
- QA-5: Index effectiveness validation (index utilization)

Execution:
    python qa_test_suite.py --test all              # Run all tests
    python qa_test_suite.py --test constraints       # Run constraint tests only
    python qa_test_suite.py --test latency           # Run latency tests only
    python qa_test_suite.py --test duplicates        # Run duplicate prevention tests
    python qa_test_suite.py --test naming            # Run naming convention tests
    python qa_test_suite.py --test indexes           # Run index effectiveness tests
"""

import sqlite3
import time
import statistics
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import logging
import argparse
from enum import Enum

LOG = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s'
)

# ============================================================================
# Configuration
# ============================================================================

DB_PATH = Path('benchmark_test.db')

# SLA targets from INDEX_STRATEGY.md
SLA_TARGETS = {
    'availability_search': 100,
    'reservation_check': 50,
    'sync_dequeue': 100,
    'patient_lookup': 50,
    'reminder_audit': 100,
    'provider_timeline': 100,
}

# Naming conventions rules
NAMING_RULES = {
    'tables_lowercase': True,
    'tables_snake_case': True,
    'columns_lowercase': True,
    'columns_snake_case': True,
    'fk_format': r'^[a-z_]+_id$',
    'timestamp_format': r'_at$',
    'boolean_format': r'^(is_|has_|do_)',
    'index_prefix': r'^idx_',
}


class TestStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


# ============================================================================
# QA Test Suite
# ============================================================================

class QATestSuite:
    """Comprehensive QA test suite for schema validation."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        self.results = []
    
    def connect(self):
        """Connect to database."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute('PRAGMA foreign_keys = ON')
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def run_all_tests(self):
        """Execute all QA tests."""
        LOG.info("Starting comprehensive QA test suite...")
        
        test_categories = [
            ('QA-1: Integrity Constraints', self.qa1_integrity_constraints),
            ('QA-2: Latency Budget', self.qa2_latency_budget),
            ('QA-3: Duplicate Prevention', self.qa3_duplicate_prevention),
            ('QA-4: Naming/Semantics', self.qa4_naming_semantics),
            ('QA-5: Index Effectiveness', self.qa5_index_effectiveness),
        ]
        
        for category_name, test_func in test_categories:
            try:
                test_func()
            except Exception as e:
                LOG.error(f"Error in {category_name}: {e}", exc_info=True)
        
        self._print_summary()
        self._save_results()
    
    def run_category(self, category: str):
        """Run specific test category."""
        category_map = {
            'constraints': ('QA-1: Integrity Constraints', self.qa1_integrity_constraints),
            'latency': ('QA-2: Latency Budget', self.qa2_latency_budget),
            'duplicates': ('QA-3: Duplicate Prevention', self.qa3_duplicate_prevention),
            'naming': ('QA-4: Naming/Semantics', self.qa4_naming_semantics),
            'indexes': ('QA-5: Index Effectiveness', self.qa5_index_effectiveness),
        }
        
        if category not in category_map:
            LOG.error(f"Unknown category: {category}")
            return
        
        category_name, test_func = category_map[category]
        LOG.info(f"Running {category_name}...")
        try:
            test_func()
        except Exception as e:
            LOG.error(f"Error in {category_name}: {e}", exc_info=True)
        
        self._print_summary()
        self._save_results()
    
    # ========================================================================
    # QA-1: Integrity Constraint Validation
    # ========================================================================
    
    def qa1_integrity_constraints(self):
        """Test PK/FK/Check/Unique constraint implementation."""
        LOG.info("\n" + "="*80)
        LOG.info("QA-1: INTEGRITY CONSTRAINT VALIDATION")
        LOG.info("="*80)
        
        # Test 1: Foreign key constraints enabled
        result = self._test_fk_enabled()
        self.results.append(result)
        
        # Test 2: Foreign key referential integrity
        result = self._test_fk_referential()
        self.results.append(result)
        
        # Test 3: Primary key constraints
        result = self._test_pk_constraints()
        self.results.append(result)
        
        # Test 4: Check constraints
        result = self._test_check_constraints()
        self.results.append(result)
        
        # Test 5: Unique constraints
        result = self._test_unique_constraints()
        self.results.append(result)
    
    def _test_fk_enabled(self) -> Dict:
        """Verify FK enforcement is enabled."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('PRAGMA foreign_keys')
            enabled = cursor.fetchone()[0] == 1
            
            status = TestStatus.PASS if enabled else TestStatus.FAIL
            message = "Foreign keys are enabled" if enabled else "Foreign keys are NOT enabled"
            
            LOG.info(f"[{status.value}] {message}")
            return {
                'test': 'FK enforcement enabled',
                'status': status.value,
                'message': message,
            }
        except Exception as e:
            return self._error_result('FK enforcement check', str(e))
    
    def _test_fk_referential(self) -> Dict:
        """Test foreign key referential integrity."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('PRAGMA foreign_key_check')
            violations = cursor.fetchall()
            
            status = TestStatus.PASS if not violations else TestStatus.FAIL
            message = "No FK violations found"
            if violations:
                message = f"Found {len(violations)} FK violations"
                for v in violations[:5]:
                    message += f"\n  - {v}"
            
            LOG.info(f"[{status.value}] {message}")
            return {
                'test': 'FK referential integrity',
                'status': status.value,
                'message': message,
                'violation_count': len(violations),
            }
        except Exception as e:
            return self._error_result('FK referential check', str(e))
    
    def _test_pk_constraints(self) -> Dict:
        """Verify primary key constraints."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ''')
            tables = [row[0] for row in cursor.fetchall()]
            
            missing_pk = []
            for table in tables:
                cursor.execute(f'PRAGMA table_info({table})')
                columns = cursor.fetchall()
                pk_found = any(col[5] > 0 for col in columns)  # pk field is index 5
                if not pk_found:
                    missing_pk.append(table)
            
            status = TestStatus.PASS if not missing_pk else TestStatus.FAIL
            message = f"All {len(tables)} tables have primary keys"
            if missing_pk:
                message = f"Tables missing PKs: {', '.join(missing_pk)}"
            
            LOG.info(f"[{status.value}] {message}")
            return {
                'test': 'Primary key constraints',
                'status': status.value,
                'message': message,
                'tables_checked': len(tables),
                'tables_missing_pk': len(missing_pk),
            }
        except Exception as e:
            return self._error_result('PK constraint check', str(e))
    
    def _test_check_constraints(self) -> Dict:
        """Verify CHECK constraints are enforced."""
        try:
            # Test status CHECK on appointments
            cursor = self.conn.cursor()
            
            # Try to insert invalid status (should fail if constraint exists)
            test_passed = True
            try:
                cursor.execute(
                    'INSERT INTO appointments (provider_id, specialty_id, appointment_date, '
                    'start_time, end_time, location, status) '
                    'VALUES (1, 1, "2026-07-15", "10:00:00", "10:30:00", "Office", "invalid_status")'
                )
                # If we get here, constraint is not enforced
                test_passed = False
                cursor.execute('ROLLBACK')
            except sqlite3.IntegrityError:
                # Expected: constraint violation
                test_passed = True
            
            status = TestStatus.PASS if test_passed else TestStatus.FAIL
            message = "CHECK constraints properly enforced" if test_passed else "CHECK constraints NOT enforced"
            
            LOG.info(f"[{status.value}] {message}")
            return {
                'test': 'CHECK constraints',
                'status': status.value,
                'message': message,
            }
        except Exception as e:
            return self._error_result('CHECK constraint check', str(e))
    
    def _test_unique_constraints(self) -> Dict:
        """Verify UNIQUE constraints."""
        try:
            cursor = self.conn.cursor()
            
            # Test email uniqueness
            cursor.execute('''
                SELECT COUNT(DISTINCT email) as unique_emails, COUNT(*) as total_patients 
                FROM patient_profiles
            ''')
            unique_emails, total_patients = cursor.fetchone()
            
            email_unique = unique_emails == total_patients
            
            # Test phone uniqueness
            cursor.execute('''
                SELECT COUNT(DISTINCT phone) as unique_phones, COUNT(*) as total_patients 
                FROM patient_profiles
            ''')
            unique_phones, _ = cursor.fetchone()
            phone_unique = unique_phones == total_patients
            
            status = TestStatus.PASS if (email_unique and phone_unique) else TestStatus.FAIL
            message = f"Uniqueness verified: emails={email_unique}, phones={phone_unique}"
            
            LOG.info(f"[{status.value}] {message}")
            return {
                'test': 'UNIQUE constraints',
                'status': status.value,
                'message': message,
                'email_unique': email_unique,
                'phone_unique': phone_unique,
            }
        except Exception as e:
            return self._error_result('UNIQUE constraint check', str(e))
    
    # ========================================================================
    # QA-2: Latency Budget Validation
    # ========================================================================
    
    def qa2_latency_budget(self):
        """Test query latency against SLA targets."""
        LOG.info("\n" + "="*80)
        LOG.info("QA-2: LATENCY BUDGET VALIDATION")
        LOG.info("="*80)
        
        queries = [
            ('availability_search', self._query_availability_search),
            ('reservation_check', self._query_reservation_check),
            ('sync_dequeue', self._query_sync_dequeue),
            ('patient_lookup', self._query_patient_lookup),
            ('reminder_audit', self._query_reminder_audit),
            ('provider_timeline', self._query_provider_timeline),
        ]
        
        for query_name, query_func in queries:
            result = self._test_query_latency(query_name, query_func)
            self.results.append(result)
    
    def _test_query_latency(self, query_name: str, query_func, iterations: int = 20) -> Dict:
        """Measure query latency and validate against SLA."""
        try:
            latencies = []
            for _ in range(iterations):
                start = time.perf_counter()
                query_func()
                elapsed = (time.perf_counter() - start) * 1000
                latencies.append(elapsed)
            
            p50 = statistics.median(latencies)
            p95 = sorted(latencies)[int(len(latencies) * 0.95)]
            p99 = sorted(latencies)[int(len(latencies) * 0.99)]
            
            sla_target = SLA_TARGETS.get(query_name, 100)
            status = TestStatus.PASS if p95 <= sla_target else TestStatus.FAIL
            
            message = f"{query_name}: p50={p50:.1f}ms, p95={p95:.1f}ms (SLA={sla_target}ms)"
            LOG.info(f"[{status.value}] {message}")
            
            return {
                'test': f'Latency: {query_name}',
                'status': status.value,
                'p50_ms': round(p50, 2),
                'p95_ms': round(p95, 2),
                'p99_ms': round(p99, 2),
                'sla_target_ms': sla_target,
                'message': message,
            }
        except Exception as e:
            return self._error_result(f'Latency test: {query_name}', str(e))
    
    def _query_availability_search(self):
        """Query: Find available appointments."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM appointments 
            WHERE status = ? AND specialty_id = ? AND appointment_date = ?
            ORDER BY start_time LIMIT 20
        ''', ('available', 1, '2026-07-15'))
        cursor.fetchall()
    
    def _query_reservation_check(self):
        """Query: Check active reservations."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM appointment_reservations 
            WHERE appointment_id = ? AND status = ? LIMIT 1
        ''', (1, 'active'))
        cursor.fetchone()
    
    def _query_sync_dequeue(self):
        """Query: Dequeue pending syncs."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM calendar_sync_queue 
            WHERE status = ? AND retry_count < ? ORDER BY created_at LIMIT 100
        ''', ('pending', 3))
        cursor.fetchall()
    
    def _query_patient_lookup(self):
        """Query: Patient lookup by email."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM patient_profiles WHERE email = ?', ('patient1@example.com',))
        cursor.fetchone()
    
    def _query_reminder_audit(self):
        """Query: Reminder audit trail."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM reminder_log 
            WHERE appointment_id = ? AND reminder_type IN (?, ?, ?)
            ORDER BY created_at DESC LIMIT 10
        ''', (1, '48h', '24h', '2h'))
        cursor.fetchall()
    
    def _query_provider_timeline(self):
        """Query: Provider availability timeline."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM appointments 
            WHERE provider_id = ? AND status = ? 
            AND appointment_date BETWEEN ? AND ?
            ORDER BY start_time
        ''', (1, 'available', '2026-07-15', '2026-08-15'))
        cursor.fetchall()
    
    # ========================================================================
    # QA-3: Duplicate Prevention Validation
    # ========================================================================
    
    def qa3_duplicate_prevention(self):
        """Test duplicate prevention through uniqueness constraints."""
        LOG.info("\n" + "="*80)
        LOG.info("QA-3: DUPLICATE PREVENTION VALIDATION")
        LOG.info("="*80)
        
        # Test 1: Email uniqueness enforcement
        result = self._test_email_uniqueness()
        self.results.append(result)
        
        # Test 2: Phone uniqueness enforcement
        result = self._test_phone_uniqueness()
        self.results.append(result)
        
        # Test 3: Reservation token uniqueness
        result = self._test_token_uniqueness()
        self.results.append(result)
    
    def _test_email_uniqueness(self) -> Dict:
        """Test email uniqueness constraint."""
        try:
            cursor = self.conn.cursor()
            
            # Try to insert duplicate email (should fail)
            test_passed = False
            try:
                cursor.execute('''
                    INSERT INTO patient_profiles 
                    (first_name, last_name, email, phone) 
                    VALUES (?, ?, ?, ?)
                ''', ('Test', 'User', 'patient1@example.com', '+15555551234'))
                cursor.execute('ROLLBACK')
            except sqlite3.IntegrityError:
                test_passed = True
            
            status = TestStatus.PASS if test_passed else TestStatus.FAIL
            message = "Email uniqueness constraint enforced" if test_passed else "Email constraint NOT enforced"
            
            LOG.info(f"[{status.value}] {message}")
            return {
                'test': 'Email uniqueness',
                'status': status.value,
                'message': message,
            }
        except Exception as e:
            return self._error_result('Email uniqueness test', str(e))
    
    def _test_phone_uniqueness(self) -> Dict:
        """Test phone uniqueness constraint."""
        try:
            cursor = self.conn.cursor()
            
            # Try to insert duplicate phone (should fail)
            test_passed = False
            try:
                cursor.execute('''
                    INSERT INTO patient_profiles 
                    (first_name, last_name, email, phone) 
                    VALUES (?, ?, ?, ?)
                ''', ('Test', 'User2', 'test@example.com', '+1555555999'))
                cursor.execute('ROLLBACK')
            except sqlite3.IntegrityError:
                test_passed = True
            
            status = TestStatus.PASS if test_passed else TestStatus.FAIL
            message = "Phone uniqueness constraint enforced" if test_passed else "Phone constraint NOT enforced"
            
            LOG.info(f"[{status.value}] {message}")
            return {
                'test': 'Phone uniqueness',
                'status': status.value,
                'message': message,
            }
        except Exception as e:
            return self._error_result('Phone uniqueness test', str(e))
    
    def _test_token_uniqueness(self) -> Dict:
        """Test reservation token uniqueness."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT COUNT(DISTINCT reservation_token) as unique_tokens, 
                       COUNT(*) as total_reservations 
                FROM appointment_reservations
            ''')
            unique_tokens, total_reservations = cursor.fetchone()
            
            test_passed = unique_tokens == total_reservations
            status = TestStatus.PASS if test_passed else TestStatus.FAIL
            message = f"Tokens unique: {unique_tokens} unique / {total_reservations} total"
            
            LOG.info(f"[{status.value}] {message}")
            return {
                'test': 'Reservation token uniqueness',
                'status': status.value,
                'message': message,
                'unique_count': unique_tokens,
                'total_count': total_reservations,
            }
        except Exception as e:
            return self._error_result('Token uniqueness test', str(e))
    
    # ========================================================================
    # QA-4: Naming/Semantics Review
    # ========================================================================
    
    def qa4_naming_semantics(self):
        """Validate naming conventions and semantic consistency."""
        LOG.info("\n" + "="*80)
        LOG.info("QA-4: NAMING/SEMANTICS REVIEW")
        LOG.info("="*80)
        
        # Test 1: Table naming conventions
        result = self._test_table_naming()
        self.results.append(result)
        
        # Test 2: Column naming conventions
        result = self._test_column_naming()
        self.results.append(result)
        
        # Test 3: Index naming conventions
        result = self._test_index_naming()
        self.results.append(result)
    
    def _test_table_naming(self) -> Dict:
        """Validate table naming conventions."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            ''')
            tables = [row[0] for row in cursor.fetchall()]
            
            violations = []
            for table in tables:
                # Check lowercase
                if table != table.lower():
                    violations.append(f"{table}: not lowercase")
                # Check snake_case
                if not re.match(r'^[a-z_]+$', table):
                    violations.append(f"{table}: not snake_case")
                # Check no reserved words
                if table in ['order', 'group', 'user', 'comment']:
                    violations.append(f"{table}: reserved word")
            
            status = TestStatus.PASS if not violations else TestStatus.WARN
            message = f"Checked {len(tables)} tables"
            if violations:
                message += f"; {len(violations)} naming issues"
            
            LOG.info(f"[{status.value}] {message}")
            return {
                'test': 'Table naming conventions',
                'status': status.value,
                'message': message,
                'tables_checked': len(tables),
                'violations': violations[:5],
            }
        except Exception as e:
            return self._error_result('Table naming test', str(e))
    
    def _test_column_naming(self) -> Dict:
        """Validate column naming conventions."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ''')
            tables = [row[0] for row in cursor.fetchall()]
            
            violations = []
            column_count = 0
            for table in tables:
                cursor.execute(f'PRAGMA table_info({table})')
                columns = cursor.fetchall()
                for col in columns:
                    column_count += 1
                    col_name = col[1]
                    
                    # Check lowercase
                    if col_name != col_name.lower():
                        violations.append(f"{table}.{col_name}: not lowercase")
                    # Check snake_case
                    if not re.match(r'^[a-z_]+$', col_name):
                        violations.append(f"{table}.{col_name}: not snake_case")
            
            status = TestStatus.PASS if not violations else TestStatus.WARN
            message = f"Checked {column_count} columns across {len(tables)} tables"
            if violations:
                message += f"; {len(violations)} naming issues"
            
            LOG.info(f"[{status.value}] {message}")
            return {
                'test': 'Column naming conventions',
                'status': status.value,
                'message': message,
                'columns_checked': column_count,
                'violations': violations[:5],
            }
        except Exception as e:
            return self._error_result('Column naming test', str(e))
    
    def _test_index_naming(self) -> Dict:
        """Validate index naming conventions."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
            ''')
            indexes = [row[0] for row in cursor.fetchall()]
            
            violations = []
            for idx in indexes:
                # Check idx_ prefix
                if not idx.startswith('idx_'):
                    violations.append(f"{idx}: missing idx_ prefix")
                # Check snake_case
                if not re.match(r'^idx_[a-z_]+$', idx):
                    violations.append(f"{idx}: not snake_case")
            
            status = TestStatus.PASS if not violations else TestStatus.WARN
            message = f"Checked {len(indexes)} indexes"
            if violations:
                message += f"; {len(violations)} naming issues"
            
            LOG.info(f"[{status.value}] {message}")
            return {
                'test': 'Index naming conventions',
                'status': status.value,
                'message': message,
                'indexes_checked': len(indexes),
                'violations': violations[:5],
            }
        except Exception as e:
            return self._error_result('Index naming test', str(e))
    
    # ========================================================================
    # QA-5: Index Effectiveness Validation
    # ========================================================================
    
    def qa5_index_effectiveness(self):
        """Validate that indexes are being used effectively."""
        LOG.info("\n" + "="*80)
        LOG.info("QA-5: INDEX EFFECTIVENESS VALIDATION")
        LOG.info("="*80)
        
        # Test 1: All expected indexes exist
        result = self._test_indexes_exist()
        self.results.append(result)
        
        # Test 2: Indexes are used by queries
        result = self._test_indexes_used()
        self.results.append(result)
    
    def _test_indexes_exist(self) -> Dict:
        """Verify all mandatory indexes are created."""
        try:
            expected_indexes = [
                'idx_appointments_status_date',
                'idx_appointments_specialty_date',
                'idx_appointments_provider_date',
                'idx_patient_profiles_email',
                'idx_reservations_active',
                'idx_calendar_sync_queue_dequeue',
                'idx_reminder_log_lookup',
            ]
            
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
            ''')
            existing_indexes = [row[0] for row in cursor.fetchall()]
            
            missing = [idx for idx in expected_indexes if idx not in existing_indexes]
            status = TestStatus.PASS if not missing else TestStatus.FAIL
            message = f"Found {len(existing_indexes)} indexes"
            if missing:
                message += f"; Missing: {', '.join(missing)}"
            
            LOG.info(f"[{status.value}] {message}")
            return {
                'test': 'Indexes exist',
                'status': status.value,
                'message': message,
                'expected_count': len(expected_indexes),
                'existing_count': len(existing_indexes),
                'missing': missing,
            }
        except Exception as e:
            return self._error_result('Indexes exist test', str(e))
    
    def _test_indexes_used(self) -> Dict:
        """Verify indexes are used by hot-path queries."""
        try:
            test_queries = [
                ('Availability Search', '''
                    SELECT * FROM appointments 
                    WHERE status = 'available' AND specialty_id = 1 
                    AND appointment_date = '2026-07-15' ORDER BY start_time LIMIT 20
                '''),
                ('Patient Lookup', '''
                    SELECT * FROM patient_profiles WHERE email = 'patient1@example.com'
                '''),
                ('Reservation Check', '''
                    SELECT * FROM appointment_reservations 
                    WHERE appointment_id = 1 AND status = 'active' LIMIT 1
                '''),
            ]
            
            cursor = self.conn.cursor()
            all_using_index = True
            
            for query_name, query_sql in test_queries:
                cursor.execute(f'EXPLAIN QUERY PLAN {query_sql}')
                plan = cursor.fetchone()[3]  # Plan is column 3
                
                uses_index = 'SEARCH' in plan and 'SCAN' not in plan
                status = 'Using Index' if uses_index else 'Full Scan'
                LOG.info(f"  {query_name}: {status}")
                
                if not uses_index:
                    all_using_index = False
            
            status = TestStatus.PASS if all_using_index else TestStatus.WARN
            message = "Hot-path queries using indexes" if all_using_index else "Some queries using full scans"
            
            LOG.info(f"[{status.value}] {message}")
            return {
                'test': 'Indexes used by queries',
                'status': status.value,
                'message': message,
                'queries_checked': len(test_queries),
            }
        except Exception as e:
            return self._error_result('Indexes used test', str(e))
    
    # ========================================================================
    # Utilities
    # ========================================================================
    
    def _error_result(self, test_name: str, error: str) -> Dict:
        """Create error result."""
        LOG.error(f"[ERROR] {test_name}: {error}")
        return {
            'test': test_name,
            'status': TestStatus.FAIL.value,
            'message': f"Error: {error}",
        }
    
    def _print_summary(self):
        """Print test results summary."""
        passed = sum(1 for r in self.results if r.get('status') == TestStatus.PASS.value)
        failed = sum(1 for r in self.results if r.get('status') == TestStatus.FAIL.value)
        warned = sum(1 for r in self.results if r.get('status') == TestStatus.WARN.value)
        
        LOG.info("\n" + "="*80)
        LOG.info("TEST SUMMARY")
        LOG.info("="*80)
        LOG.info(f"Total Tests: {len(self.results)}")
        LOG.info(f"Passed:      {passed}")
        LOG.info(f"Failed:      {failed}")
        LOG.info(f"Warned:      {warned}")
        LOG.info("="*80)
        
        if failed > 0:
            LOG.warning(f"\n⚠️  {failed} test(s) FAILED - Please review")
        else:
            LOG.info("\n✅ All tests PASSED")
    
    def _save_results(self):
        """Save results to JSON."""
        output_file = Path('qa_test_results.json')
        with open(output_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'results': self.results,
                'summary': {
                    'total': len(self.results),
                    'passed': sum(1 for r in self.results if r.get('status') == TestStatus.PASS.value),
                    'failed': sum(1 for r in self.results if r.get('status') == TestStatus.FAIL.value),
                    'warned': sum(1 for r in self.results if r.get('status') == TestStatus.WARN.value),
                },
            }, f, indent=2)
        LOG.info(f"\nResults saved to {output_file}")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='QA Test Suite for Schema v1.0')
    parser.add_argument('--test', choices=['all', 'constraints', 'latency', 'duplicates', 'naming', 'indexes'],
                       default='all', help='Test category to run')
    parser.add_argument('--db', default='benchmark_test.db', help='Database path')
    args = parser.parse_args()
    
    db_path = Path(args.db)
    
    if not db_path.exists():
        LOG.error(f"Database not found: {db_path}")
        LOG.error("Run: python benchmark.py --mode generate")
        return 1
    
    try:
        suite = QATestSuite(db_path)
        suite.connect()
        
        if args.test == 'all':
            suite.run_all_tests()
        else:
            suite.run_category(args.test)
        
        suite.close()
        return 0
    
    except Exception as e:
        LOG.error(f"Fatal error: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    exit(main())
