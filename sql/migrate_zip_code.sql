-- Migration one-shot : normaliser zip_code dans la table hotels
-- Problème : pandas lisait la colonne en float64 (NaN dans la colonne → float)
--            ce qui tronquait les zéros initiaux (ex: "06120" → "6120.0")
-- Correction : strip ".0" + zero-padding à 5 chiffres pour les codes purement numériques
--
-- Usage : psql $DATABASE_URL -f sql/migrate_zip_code.sql

UPDATE hotels
SET zip_code = CASE
    -- Retirer le suffixe ".0" laissé par pandas float64
    WHEN zip_code LIKE '%.0'
        THEN LPAD(REGEXP_REPLACE(zip_code, '\.0$', ''), 5, '0')
    -- Codes numériques corrects mais sans zéro initial (ex: "6120" → "06120")
    WHEN zip_code ~ '^\d{1,4}$'
        THEN LPAD(zip_code, 5, '0')
    ELSE zip_code
END
WHERE zip_code IS NOT NULL
  AND (zip_code LIKE '%.0' OR zip_code ~ '^\d{1,4}$');
