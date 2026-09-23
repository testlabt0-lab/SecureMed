-- =============================================================================
-- SecureMed — Supabase PostgreSQL Hardening Script (CIS Benchmark Level 1)
-- =============================================================================
-- This script applies 15 Level 1 hardening controls from the CIS PostgreSQL
-- Benchmark, tailored specifically for Supabase managed cloud databases.
--
-- How to apply:
-- 1. Open your Supabase Dashboard: https://app.supabase.com/
-- 2. Go to your project -> SQL Editor -> Create New Query.
-- 3. Paste this script and execute (Run).
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Enforce Row Level Security (RLS) on all public tables (CIS 5.x)
-- -----------------------------------------------------------------------------
-- In Supabase, any table in the public schema without RLS is directly exposed
-- through the PostgREST API. This control forces RLS on every current table.
DO $$
DECLARE
    tbl RECORD;
BEGIN
    FOR tbl IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
    LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', tbl.tablename);
        EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY;', tbl.tablename);
    END LOOP;
END $$;


-- -----------------------------------------------------------------------------
-- 2. Revoke CREATE on schema 'public' from PUBLIC (CIS 2.2)
-- -----------------------------------------------------------------------------
-- By default in older PostgreSQL, any authenticated user can create objects in
-- the public schema. CIS requires revoking this privilege.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;


-- -----------------------------------------------------------------------------
-- 3. Revoke default permissions on sensitive system catalogs (CIS 2.3)
-- -----------------------------------------------------------------------------
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO authenticated, service_role;


-- -----------------------------------------------------------------------------
-- 4. Harden search_path on all custom functions (CIS 5.3 / CVE mitigation)
-- -----------------------------------------------------------------------------
-- An unbounded search_path allows function hijacking by creating objects in
-- schemas that appear earlier in the search path.
DO $$
DECLARE
    fn RECORD;
BEGIN
    FOR fn IN
        SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS args
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public'
    LOOP
        EXECUTE format('ALTER FUNCTION public.%I(%s) SET search_path = public, pg_temp;', fn.proname, fn.args);
    END LOOP;
END $$;


-- -----------------------------------------------------------------------------
-- 5. Session Timeout: Terminate Idle Transactions (CIS 3.1.5)
-- -----------------------------------------------------------------------------
-- Prevents connection pool starvation and open locks from hung clients.
ALTER DATABASE postgres SET idle_in_transaction_session_timeout = '10min';


-- -----------------------------------------------------------------------------
-- 6. Statement Timeout: Prevent DoS & Exhaustion (CIS 3.1.6)
-- -----------------------------------------------------------------------------
-- Prevents poorly optimized queries or malicious injection from locking resources.
ALTER DATABASE postgres SET statement_timeout = '60s';


-- -----------------------------------------------------------------------------
-- 7. Client Error Suppression: Mask DB internals (CIS 4.2)
-- -----------------------------------------------------------------------------
-- Prevents detailed schema, table, and parameter leakage to the client.
ALTER DATABASE postgres SET client_min_messages = 'warning';


-- -----------------------------------------------------------------------------
-- 8. Enable Audit Logging Extension (pgaudit) (CIS 4.3)
-- -----------------------------------------------------------------------------
-- Supabase provides pgaudit as an official extension.
CREATE EXTENSION IF NOT EXISTS pgaudit;


-- -----------------------------------------------------------------------------
-- 9. Configure pgaudit to record DDL and Role changes (CIS 4.3.1)
-- -----------------------------------------------------------------------------
ALTER DATABASE postgres SET pgaudit.log = 'ddl, role';
ALTER DATABASE postgres SET pgaudit.log_catalog = off;


-- -----------------------------------------------------------------------------
-- 10. Restrict Default Privileges for Future Tables (CIS 2.2)
-- -----------------------------------------------------------------------------
-- Ensure any future table created by postgres or service_role does NOT grant
-- automatic permissions to the anonymous role.
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC, anon;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated, service_role;


-- -----------------------------------------------------------------------------
-- 11. Lock down PostgREST Anon role from direct table mutation (CIS 5.1)
-- -----------------------------------------------------------------------------
-- The Django backend connects via direct connection string / pooler as the
-- postgres or service_role user. The anon role should NOT have direct mutation rights.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;
        REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon;
        REVOKE ALL ON ALL ROUTINES IN SCHEMA public FROM anon;
    END IF;
END $$;


-- -----------------------------------------------------------------------------
-- 12. Enforce SCRAM-SHA-256 for password authentication verification (CIS 3.1.1)
-- -----------------------------------------------------------------------------
ALTER DATABASE postgres SET password_encryption = 'scram-sha-256';


-- -----------------------------------------------------------------------------
-- 13. Enable Connection Log Reporting (CIS 4.1)
-- -----------------------------------------------------------------------------
-- Ensure disconnection and connection attempts are logged into Supabase Log Engine.
ALTER DATABASE postgres SET log_disconnections = on;


-- -----------------------------------------------------------------------------
-- 14. Prevent unprivileged access to PostgreSQL Configuration (CIS 1.2)
-- -----------------------------------------------------------------------------
REVOKE EXECUTE ON FUNCTION pg_read_file(text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION pg_read_file(text, bigint, bigint) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION pg_read_file(text, bigint, bigint, boolean) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION pg_read_binary_file(text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION pg_read_binary_file(text, bigint, bigint) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION pg_read_binary_file(text, bigint, bigint, boolean) FROM PUBLIC;


-- -----------------------------------------------------------------------------
-- 15. Audit Validation Query (Verify RLS coverage across all project tables)
-- -----------------------------------------------------------------------------
-- This creates an admin view to easily verify compliance in the Supabase Table Editor.
CREATE OR REPLACE VIEW public.vw_security_cis_audit_check AS
SELECT 
    schemaname,
    tablename,
    rowsecurity AS rls_enabled,
    CASE 
        WHEN rowsecurity THEN 'PASS: RLS Active' 
        ELSE 'FAIL: RLS Missing (CIS 5.x Violation)' 
    END AS cis_status
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY rowsecurity ASC, tablename ASC;

COMMENT ON VIEW public.vw_security_cis_audit_check IS 'SecureMed CIS Benchmark Level 1 RLS Audit View';

COMMIT;

-- Verify RLS status immediately:
SELECT * FROM public.vw_security_cis_audit_check;
