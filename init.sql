-- Initialize the database with proper permissions
CREATE DATABASE mhh_client_db;
GRANT ALL PRIVILEGES ON DATABASE mhh_client_db TO mhh_user;

-- Create a schema for the application
CREATE SCHEMA IF NOT EXISTS public;
GRANT ALL ON SCHEMA public TO mhh_user;
GRANT ALL ON SCHEMA public TO public;

-- Set default privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO mhh_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO mhh_user;
