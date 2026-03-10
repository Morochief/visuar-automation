-- Migration: Encrypt contact_info in alert_rules
-- Usage: psql -d market_intel_db -v enc_key='your_secret_key' -f migrate_pgcrypto.sql

BEGIN;

-- 1. Enable pgcrypto
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 2. Add temporary encrypted column
ALTER TABLE alert_rules ADD COLUMN contact_info_enc BYTEA;

-- 3. Encrypt existing data
-- Note: 'enc_key' must be passed as a psql variable
UPDATE alert_rules 
SET contact_info_enc = pgp_sym_encrypt(contact_info, :'enc_key');

-- 4. Safety check: ensure no data loss (optional, but recommended)
-- SELECT count(*) FROM alert_rules WHERE contact_info_enc IS NULL;

-- 5. Swap columns
ALTER TABLE alert_rules DROP COLUMN contact_info;
ALTER TABLE alert_rules RENAME COLUMN contact_info_enc TO contact_info;

-- 6. Ensure NOT NULL constraint
ALTER TABLE alert_rules ALTER COLUMN contact_info SET NOT NULL;

COMMIT;
