-- SYL Database Init
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Ensure the database is properly set up
ALTER DATABASE syl_db SET timezone TO 'UTC';
