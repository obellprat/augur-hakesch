-- Update existing NAM records that have the old default values
UPDATE "NAM" 
SET "precipitation_factor" = 0.7
WHERE "precipitation_factor" = 1.0;

UPDATE "NAM" 
SET "water_balance_mode" = 'cumulative'
WHERE "water_balance_mode" = 'simple';
