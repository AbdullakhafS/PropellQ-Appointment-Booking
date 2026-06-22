PRAGMA foreign_keys = ON;

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
    photo_url TEXT,
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
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (provider_id) REFERENCES providers (id),
    FOREIGN KEY (specialty_id) REFERENCES specialties (id)
);

CREATE INDEX IF NOT EXISTS idx_appointments_status_date
    ON appointments (status, appointment_date, start_time, id);

CREATE INDEX IF NOT EXISTS idx_appointments_specialty_date
    ON appointments (specialty_id, appointment_date, start_time, id);

CREATE INDEX IF NOT EXISTS idx_appointments_provider_date
    ON appointments (provider_id, appointment_date, start_time, id);

CREATE INDEX IF NOT EXISTS idx_providers_name
    ON providers (name);

CREATE INDEX IF NOT EXISTS idx_specialties_name
    ON specialties (name);
