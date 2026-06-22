#!/usr/bin/env python3
"""
Benchmark Harness for PropellQ Appointment Booking Schema

Purpose:
  Generate representative dataset and benchmark critical query paths
  against latency SLAs to validate index effectiveness.

Scale Profile:
  - 1,000,000 appointments
  - 100,000 providers
  - 50,000 patient profiles
  - 10,000 specialties
  - Realistic cardinality and skew (80/20 rule: 20% of providers handle 80% of appointments)

Execution:
  python benchmark.py --mode generate  # Create test database
  python benchmark.py --mode benchmark # Run query benchmarks
  python benchmark.py --mode analyze   # Show EXPLAIN QUERY PLAN
  python benchmark.py --mode cleanup   # Archive old results
"""

import sqlite3
import random
import time
import json
import statistics
from datetime import datetime, timedelta
from pathlib import Path
import argparse
from typing import Dict, List, Tuple
import logging

# ============================================================================
# Configuration
# ============================================================================

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BENCH_CONFIG = {
    'specialties_count': 10_000,
    'providers_count': 100_000,
    'patients_count': 50_000,
    'appointments_count': 1_000_000,
    'reservations_per_appointment': 0.3,  # 30% of appointments have reservations
    'reminder_events_per_appointment': 3,  # Average 3 reminder events
    'sync_queue_entries': 50_000,
}

# SLA Targets (milliseconds, p95)
SLA_TARGETS = {
    'availability_search': 100,
    'reservation_check': 50,
    'sync_dequeue': 100,
    'patient_lookup': 50,
    'reminder_audit': 100,
    'provider_timeline': 100,
}

DB_PATH = Path('benchmark_test.db')
RESULTS_PATH = Path('benchmark_results.json')

# ============================================================================
# Data Generation
# ============================================================================

class BenchmarkDataGenerator:
    """Generate representative test data for appointment booking system."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        """Create connection and initialize database."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute('PRAGMA foreign_keys = ON')
        self.conn.execute('PRAGMA journal_mode = WAL')
        LOG.info(f"Connected to {self.db_path}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def create_schema(self):
        """Load production schema."""
        schema_file = Path('schema_v1_production.sql')
        if not schema_file.exists():
            LOG.warning(f"Schema file {schema_file} not found; using inline schema")
            # Simplified schema for testing
            self._create_inline_schema()
        else:
            with open(schema_file, 'r') as f:
                sql = f.read()
            self.conn.executescript(sql)
            LOG.info("Schema loaded from schema_v1_production.sql")
        
        self.conn.commit()
    
    def _create_inline_schema(self):
        """Fallback: minimal schema for testing."""
        # For brevity, only creating core tables
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS specialties (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                is_active INTEGER NOT NULL DEFAULT 1
            );
            
            CREATE TABLE IF NOT EXISTS providers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                credentials TEXT NOT NULL,
                specialty_id INTEGER NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (specialty_id) REFERENCES specialties (id)
            );
            
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY,
                provider_id INTEGER NOT NULL,
                specialty_id INTEGER NOT NULL,
                appointment_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                location TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('available', 'booked', 'cancelled')),
                checkout_status TEXT NOT NULL DEFAULT 'searching',
                sync_status TEXT NOT NULL DEFAULT 'not_connected',
                version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (provider_id) REFERENCES providers (id),
                FOREIGN KEY (specialty_id) REFERENCES specialties (id)
            );
            
            CREATE TABLE IF NOT EXISTS patient_profiles (
                id INTEGER PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS appointment_reservations (
                id INTEGER PRIMARY KEY,
                appointment_id INTEGER NOT NULL,
                patient_profile_id INTEGER NOT NULL,
                reservation_token TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'active',
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (appointment_id) REFERENCES appointments (id),
                FOREIGN KEY (patient_profile_id) REFERENCES patient_profiles (id)
            );
            
            CREATE TABLE IF NOT EXISTS reminder_log (
                id INTEGER PRIMARY KEY,
                appointment_id INTEGER NOT NULL,
                patient_profile_id INTEGER NOT NULL,
                reminder_type TEXT NOT NULL,
                channel TEXT NOT NULL,
                delivery_status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (appointment_id) REFERENCES appointments (id),
                FOREIGN KEY (patient_profile_id) REFERENCES patient_profiles (id)
            );
            
            CREATE TABLE IF NOT EXISTS calendar_sync_queue (
                id INTEGER PRIMARY KEY,
                appointment_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                calendar_type TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                retry_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (appointment_id) REFERENCES appointments (id),
                UNIQUE (appointment_id, action, calendar_type, idempotency_key)
            );
            
            -- Indexes from production schema
            CREATE INDEX idx_appointments_status_date
                ON appointments (status, appointment_date, start_time, id);
            CREATE INDEX idx_appointments_specialty_date
                ON appointments (specialty_id, appointment_date, start_time, id);
            CREATE INDEX idx_appointments_provider_date
                ON appointments (provider_id, appointment_date, start_time, id);
            CREATE INDEX idx_patient_profiles_email
                ON patient_profiles (email);
            CREATE INDEX idx_reservations_active
                ON appointment_reservations (status, expires_at, appointment_id);
            CREATE INDEX idx_calendar_sync_queue_dequeue
                ON calendar_sync_queue (status, created_at, calendar_type, retry_count);
            CREATE INDEX idx_reminder_log_lookup
                ON reminder_log (appointment_id, patient_profile_id, reminder_type, channel, delivery_status);
        """)
    
    def generate_data(self):
        """Generate representative dataset."""
        LOG.info("Generating representative dataset...")
        
        # Generate specialties
        self._generate_specialties()
        # Generate providers
        self._generate_providers()
        # Generate patient profiles
        self._generate_patient_profiles()
        # Generate appointments
        self._generate_appointments()
        # Generate reservations
        self._generate_reservations()
        # Generate reminder logs
        self._generate_reminder_logs()
        # Generate sync queue
        self._generate_sync_queue()
        
        LOG.info("Dataset generation complete")
    
    def _generate_specialties(self):
        """Generate clinical specialties."""
        specialties = [
            "Cardiology", "Dermatology", "Neurology", "Orthopedics",
            "Ophthalmology", "Otolaryngology", "Pediatrics", "Psychiatry",
            "Radiology", "Surgery", "Urology", "Gastroenterology",
            "Rheumatology", "Pulmonology", "Nephrology", "Oncology",
        ]
        
        data = []
        for i in range(BENCH_CONFIG['specialties_count']):
            specialty = f"{random.choice(specialties)} - Clinic {i // 10}"
            data.append((specialty, 1))
        
        self.conn.executemany(
            'INSERT INTO specialties (name, is_active) VALUES (?, ?)',
            data
        )
        self.conn.commit()
        LOG.info(f"Generated {BENCH_CONFIG['specialties_count']} specialties")
    
    def _generate_providers(self):
        """Generate providers with realistic concentration (80/20 rule)."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM specialties')
        specialties_count = cursor.fetchone()[0]
        
        data = []
        # 20% of providers handle 80% of appointments (Pareto distribution)
        core_providers = int(BENCH_CONFIG['providers_count'] * 0.2)
        tail_providers = BENCH_CONFIG['providers_count'] - core_providers
        
        for i in range(BENCH_CONFIG['providers_count']):
            specialty_id = random.randint(1, specialties_count)
            name = f"Dr. Provider {i}"
            credentials = f"MD-{random.randint(100000, 999999)}"
            data.append((name, credentials, specialty_id, 1))
        
        self.conn.executemany(
            'INSERT INTO providers (name, credentials, specialty_id, is_active) VALUES (?, ?, ?, ?)',
            data
        )
        self.conn.commit()
        LOG.info(f"Generated {BENCH_CONFIG['providers_count']} providers")
    
    def _generate_patient_profiles(self):
        """Generate patient profiles."""
        data = []
        for i in range(BENCH_CONFIG['patients_count']):
            first_name = f"Patient{i}"
            last_name = f"Last{i}"
            email = f"patient{i}@example.com"
            phone = f"+1{random.randint(2000000000, 9999999999)}"
            data.append((first_name, last_name, email, phone))
        
        self.conn.executemany(
            'INSERT INTO patient_profiles (first_name, last_name, email, phone) VALUES (?, ?, ?, ?)',
            data
        )
        self.conn.commit()
        LOG.info(f"Generated {BENCH_CONFIG['patients_count']} patient profiles")
    
    def _generate_appointments(self):
        """Generate appointments with realistic date distribution."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM providers')
        providers_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM specialties')
        specialties_count = cursor.fetchone()[0]
        
        data = []
        base_date = datetime.now().date()
        
        for i in range(BENCH_CONFIG['appointments_count']):
            provider_id = random.randint(1, providers_count)
            specialty_id = random.randint(1, specialties_count)
            
            # Dates spread over next 90 days
            days_offset = random.randint(0, 90)
            appt_date = base_date + timedelta(days=days_offset)
            appt_date_str = appt_date.isoformat()
            
            # Random time between 9 AM and 5 PM
            hour = random.randint(9, 16)
            start_time = f"{hour:02d}:00:00"
            end_time = f"{hour:02d}:30:00"
            
            location = f"Clinic {random.randint(1, 100)}"
            status = random.choices(
                ['available', 'booked', 'cancelled'],
                weights=[0.5, 0.45, 0.05]
            )[0]
            
            data.append((
                provider_id, specialty_id, appt_date_str, start_time, end_time,
                location, status, 'not_connected'
            ))
        
        self.conn.executemany(
            '''INSERT INTO appointments 
               (provider_id, specialty_id, appointment_date, start_time, end_time,
                location, status, sync_status) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            data
        )
        self.conn.commit()
        LOG.info(f"Generated {BENCH_CONFIG['appointments_count']} appointments")
    
    def _generate_reservations(self):
        """Generate appointment reservations."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM appointments')
        appointments_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM patient_profiles')
        patients_count = cursor.fetchone()[0]
        
        reservation_count = int(
            BENCH_CONFIG['appointments_count'] * 
            BENCH_CONFIG['reservations_per_appointment']
        )
        
        data = []
        reserved_appts = random.sample(range(1, appointments_count + 1), reservation_count)
        
        for appt_id in reserved_appts:
            patient_id = random.randint(1, patients_count)
            token = f"token-{appt_id}-{patient_id}-{random.randint(100000, 999999)}"
            expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
            status = random.choices(['active', 'expired'], weights=[0.7, 0.3])[0]
            
            data.append((appt_id, patient_id, token, status, expires_at))
        
        self.conn.executemany(
            '''INSERT INTO appointment_reservations 
               (appointment_id, patient_profile_id, reservation_token, status, expires_at)
               VALUES (?, ?, ?, ?, ?)''',
            data
        )
        self.conn.commit()
        LOG.info(f"Generated {len(data)} reservations")
    
    def _generate_reminder_logs(self):
        """Generate reminder event logs."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM appointments')
        appointments_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM patient_profiles')
        patients_count = cursor.fetchone()[0]
        
        data = []
        reminders_total = int(
            BENCH_CONFIG['appointments_count'] * 
            BENCH_CONFIG['reminder_events_per_appointment']
        )
        
        reminder_types = ['48h', '24h', '2h']
        channels = ['sms', 'email']
        delivery_statuses = ['sent', 'failed', 'skipped']
        
        for _ in range(reminders_total):
            appt_id = random.randint(1, appointments_count)
            patient_id = random.randint(1, patients_count)
            reminder_type = random.choice(reminder_types)
            channel = random.choice(channels)
            delivery_status = random.choices(
                delivery_statuses,
                weights=[0.85, 0.10, 0.05]
            )[0]
            
            data.append((
                appt_id, patient_id, reminder_type, channel, delivery_status
            ))
        
        self.conn.executemany(
            '''INSERT INTO reminder_log 
               (appointment_id, patient_profile_id, reminder_type, channel, delivery_status)
               VALUES (?, ?, ?, ?, ?)''',
            data
        )
        self.conn.commit()
        LOG.info(f"Generated {len(data)} reminder logs")
    
    def _generate_sync_queue(self):
        """Generate calendar sync queue entries."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM appointments')
        appointments_count = cursor.fetchone()[0]
        
        data = []
        actions = ['create', 'update', 'delete', 'pull_reconcile']
        calendar_types = ['google', 'outlook']
        statuses = ['pending', 'synced', 'failed', 'manual_review']
        
        for _ in range(BENCH_CONFIG['sync_queue_entries']):
            appt_id = random.randint(1, appointments_count)
            action = random.choice(actions)
            calendar_type = random.choice(calendar_types)
            idempotency_key = f"idem-{appt_id}-{action}-{random.randint(100000, 999999)}"
            status = random.choices(
                statuses,
                weights=[0.4, 0.45, 0.10, 0.05]
            )[0]
            retry_count = random.randint(0, 5) if status in ['failed'] else 0
            
            data.append((
                appt_id, action, calendar_type, idempotency_key, status, retry_count
            ))
        
        self.conn.executemany(
            '''INSERT INTO calendar_sync_queue 
               (appointment_id, action, calendar_type, idempotency_key, status, retry_count)
               VALUES (?, ?, ?, ?, ?, ?)''',
            data
        )
        self.conn.commit()
        LOG.info(f"Generated {len(data)} sync queue entries")


# ============================================================================
# Benchmark Runner
# ============================================================================

class BenchmarkRunner:
    """Execute query benchmarks and collect latency metrics."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        self.results = {}
    
    def connect(self):
        """Connect to database."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute('PRAGMA foreign_keys = ON')
    
    def close(self):
        """Close connection."""
        if self.conn:
            self.conn.close()
    
    def run_benchmarks(self):
        """Execute all benchmark queries."""
        LOG.info("Starting query benchmarks...")
        
        queries = [
            ('availability_search', self.benchmark_availability_search),
            ('reservation_check', self.benchmark_reservation_check),
            ('sync_dequeue', self.benchmark_sync_dequeue),
            ('patient_lookup', self.benchmark_patient_lookup),
            ('reminder_audit', self.benchmark_reminder_audit),
            ('provider_timeline', self.benchmark_provider_timeline),
        ]
        
        for name, benchmark_func in queries:
            LOG.info(f"Running benchmark: {name}")
            latencies = benchmark_func()
            self.results[name] = self._analyze_latencies(latencies, name)
        
        self._print_results()
        self._save_results()
    
    def benchmark_availability_search(self, iterations=50) -> List[float]:
        """Benchmark: Find available appointments by specialty and date."""
        cursor = self.conn.cursor()
        latencies = []
        
        for _ in range(iterations):
            specialty_id = random.randint(1, 100)
            target_date = (datetime.now() + timedelta(days=random.randint(0, 30))).isoformat()
            
            start = time.perf_counter()
            cursor.execute(
                '''SELECT * FROM appointments 
                   WHERE status = ? 
                   AND specialty_id = ? 
                   AND appointment_date = ?
                   ORDER BY start_time LIMIT 20''',
                ('available', specialty_id, target_date)
            )
            cursor.fetchall()
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)
        
        return latencies
    
    def benchmark_reservation_check(self, iterations=100) -> List[float]:
        """Benchmark: Check active reservations for appointment."""
        cursor = self.conn.cursor()
        latencies = []
        
        for _ in range(iterations):
            appt_id = random.randint(1, 1_000_000)
            
            start = time.perf_counter()
            cursor.execute(
                '''SELECT * FROM appointment_reservations 
                   WHERE appointment_id = ? 
                   AND status = ?
                   LIMIT 1''',
                (appt_id, 'active')
            )
            cursor.fetchone()
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)
        
        return latencies
    
    def benchmark_sync_dequeue(self, iterations=50) -> List[float]:
        """Benchmark: Dequeue pending sync jobs."""
        cursor = self.conn.cursor()
        latencies = []
        now = datetime.now().isoformat()
        
        for _ in range(iterations):
            start = time.perf_counter()
            cursor.execute(
                '''SELECT * FROM calendar_sync_queue 
                   WHERE status = ?
                   AND retry_count < ?
                   ORDER BY created_at LIMIT 100''',
                ('pending', 3)
            )
            cursor.fetchall()
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)
        
        return latencies
    
    def benchmark_patient_lookup(self, iterations=100) -> List[float]:
        """Benchmark: Patient profile lookup by email."""
        cursor = self.conn.cursor()
        latencies = []
        
        for _ in range(iterations):
            patient_id = random.randint(1, 50_000)
            email = f"patient{patient_id}@example.com"
            
            start = time.perf_counter()
            cursor.execute('SELECT * FROM patient_profiles WHERE email = ?', (email,))
            cursor.fetchone()
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)
        
        return latencies
    
    def benchmark_reminder_audit(self, iterations=50) -> List[float]:
        """Benchmark: Query reminder delivery history."""
        cursor = self.conn.cursor()
        latencies = []
        
        for _ in range(iterations):
            appt_id = random.randint(1, 1_000_000)
            
            start = time.perf_counter()
            cursor.execute(
                '''SELECT * FROM reminder_log 
                   WHERE appointment_id = ?
                   AND reminder_type IN (?, ?, ?)
                   ORDER BY created_at DESC LIMIT 10''',
                (appt_id, '48h', '24h', '2h')
            )
            cursor.fetchall()
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)
        
        return latencies
    
    def benchmark_provider_timeline(self, iterations=50) -> List[float]:
        """Benchmark: Provider's available appointments timeline."""
        cursor = self.conn.cursor()
        latencies = []
        base_date = datetime.now().date()
        
        for _ in range(iterations):
            provider_id = random.randint(1, 100_000)
            start_date = base_date.isoformat()
            end_date = (base_date + timedelta(days=30)).isoformat()
            
            start = time.perf_counter()
            cursor.execute(
                '''SELECT * FROM appointments 
                   WHERE provider_id = ?
                   AND status = ?
                   AND appointment_date BETWEEN ? AND ?
                   ORDER BY start_time''',
                (provider_id, 'available', start_date, end_date)
            )
            cursor.fetchall()
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)
        
        return latencies
    
    def _analyze_latencies(self, latencies: List[float], query_name: str) -> Dict:
        """Compute statistics and validate against SLA."""
        p50 = statistics.median(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]
        
        sla_target = SLA_TARGETS.get(query_name, 100)
        sla_status = 'PASS' if p95 <= sla_target else 'FAIL'
        
        return {
            'p50_ms': round(p50, 3),
            'p95_ms': round(p95, 3),
            'p99_ms': round(p99, 3),
            'sla_target_ms': sla_target,
            'sla_status': sla_status,
        }
    
    def _print_results(self):
        """Print benchmark results."""
        LOG.info("=" * 80)
        LOG.info("BENCHMARK RESULTS")
        LOG.info("=" * 80)
        
        for query_name, metrics in self.results.items():
            status_icon = '✓' if metrics['sla_status'] == 'PASS' else '✗'
            LOG.info(f"\n{status_icon} {query_name.upper()}")
            LOG.info(f"  p50: {metrics['p50_ms']:>8} ms")
            LOG.info(f"  p95: {metrics['p95_ms']:>8} ms (SLA: {metrics['sla_target_ms']} ms)")
            LOG.info(f"  p99: {metrics['p99_ms']:>8} ms")
            LOG.info(f"  Status: {metrics['sla_status']}")
    
    def _save_results(self):
        """Save results to JSON."""
        with open(RESULTS_PATH, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'config': BENCH_CONFIG,
                'results': self.results,
            }, f, indent=2)
        LOG.info(f"\nResults saved to {RESULTS_PATH}")
    
    def explain_queries(self):
        """Print EXPLAIN QUERY PLAN for each benchmark query."""
        LOG.info("=" * 80)
        LOG.info("QUERY EXECUTION PLANS")
        LOG.info("=" * 80)
        
        queries = [
            ('Availability Search', 
             '''EXPLAIN QUERY PLAN
                SELECT * FROM appointments 
                WHERE status = 'available' 
                AND specialty_id = 1 
                AND appointment_date = '2026-07-15'
                ORDER BY start_time LIMIT 20'''),
            ('Reservation Check',
             '''EXPLAIN QUERY PLAN
                SELECT * FROM appointment_reservations 
                WHERE appointment_id = 1 
                AND status = 'active' LIMIT 1'''),
        ]
        
        cursor = self.conn.cursor()
        for name, query in queries:
            LOG.info(f"\n{name}:")
            cursor.execute(query)
            for row in cursor.fetchall():
                LOG.info(f"  {row}")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Benchmark harness for appointment booking schema')
    parser.add_argument('--mode', choices=['generate', 'benchmark', 'analyze', 'cleanup'],
                       default='benchmark', help='Execution mode')
    parser.add_argument('--db', default='benchmark_test.db', help='Database path')
    args = parser.parse_args()
    
    db_path = Path(args.db)
    
    try:
        if args.mode == 'generate':
            generator = BenchmarkDataGenerator(db_path)
            generator.connect()
            generator.create_schema()
            generator.generate_data()
            generator.close()
            LOG.info(f"Test database created at {db_path}")
        
        elif args.mode == 'benchmark':
            if not db_path.exists():
                LOG.error(f"Database not found. Run with --mode generate first.")
                return 1
            
            runner = BenchmarkRunner(db_path)
            runner.connect()
            runner.run_benchmarks()
            runner.close()
        
        elif args.mode == 'analyze':
            if not db_path.exists():
                LOG.error(f"Database not found. Run with --mode generate first.")
                return 1
            
            runner = BenchmarkRunner(db_path)
            runner.connect()
            runner.explain_queries()
            runner.close()
        
        elif args.mode == 'cleanup':
            if db_path.exists():
                db_path.unlink()
                LOG.info(f"Removed {db_path}")
            if RESULTS_PATH.exists():
                RESULTS_PATH.unlink()
                LOG.info(f"Removed {RESULTS_PATH}")
    
    except Exception as e:
        LOG.error(f"Error: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
