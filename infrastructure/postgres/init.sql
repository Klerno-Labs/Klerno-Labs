-- ==============================================================================
-- Klerno Labs - PostgreSQL Initialization Script
-- ==============================================================================
-- Database setup for high-performance transaction processing

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create database indexes for performance
\c klerno_db;

-- Optimize settings for this database
ALTER DATABASE klerno_db SET timezone TO 'UTC';
ALTER DATABASE klerno_db SET default_transaction_isolation TO 'read committed';

-- Create optimized indexes for common queries
-- Note: These will be created after tables are set up by the application
-- This script runs before application migrations

-- Performance monitoring view
CREATE OR REPLACE VIEW performance_stats AS
SELECT 
    schemaname,
    tablename,
    attname,
    inherited,
    null_frac,
    avg_width,
    n_distinct,
    most_common_vals,
    most_common_freqs,
    histogram_bounds
FROM pg_stats 
WHERE schemaname = 'public'
ORDER BY schemaname, tablename, attname;

-- Connection monitoring
CREATE OR REPLACE VIEW active_connections AS
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    client_hostname,
    client_port,
    backend_start,
    query_start,
    state,
    query
FROM pg_stat_activity 
WHERE state = 'active'
ORDER BY query_start DESC;

-- Grants for monitoring user (create monitoring user)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'monitoring') THEN
        CREATE ROLE monitoring WITH LOGIN PASSWORD 'monitoring_password';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE klerno_db TO monitoring;
GRANT USAGE ON SCHEMA public TO monitoring;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO monitoring;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO monitoring;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO monitoring;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO monitoring;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO monitoring;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO monitoring;