-- PROPOSED migration: MO multi-category memberships + Neurological category
-- Source: metabolicum-agentic-research findings 2026-05-30 (grounded cross-ref workflow).
-- ADDITIVE + idempotent. Production is the arbiter — review before applying.
-- 40 secondary memberships across 34 markers + 1 new category (4 neuro markers).

BEGIN;

-- 1) New category: Neurological & Cognitive
INSERT INTO test_categories (name, slug, description, display_order)
VALUES ('Neurological & Cognitive', 'neurological-cognitive', 'Brain health, neurodegeneration, and cognitive biomarkers (NfL, NSE, S100B, p-tau, amyloid, GFAP)', 26)
ON CONFLICT (slug) DO NOTHING;

-- 2) Multi-category memberships (secondary; is_primary=false). Each is a standard,
--    guideline/landmark-cited clinical multi-membership (see findings doc).
INSERT INTO marker_categories (marker_slug, category_slug, is_primary) VALUES
  ('adiponectin', 'hormones', false),
  ('aldosterone', 'kidney-function', false),
  ('apob', 'cardiovascular', false),
  ('apob', 'liver-function', false),
  ('c-peptide-fasting', 'hormones', false),
  ('c-peptide-stimulated', 'hormones', false),
  ('calcitriol', 'hormones', false),
  ('calcitriol', 'kidney-function', false),
  ('ferritin', 'micronutrients', false),
  ('fgf-21', 'glycemic-insulin', false),
  ('fli', 'glycemic-insulin', false),
  ('hdl-cholesterol', 'cardiovascular', false),
  ('homa-ir', 'cardiovascular', false),
  ('homocysteine', 'kidney-function', false),
  ('homocysteine', 'micronutrients', false),
  ('hscrp', 'cardiovascular', false),
  ('leptin', 'hormones', false),
  ('lp-pla2', 'inflammatory', false),
  ('lpa', 'cardiovascular', false),
  ('magnesium-serum', 'kidney-function', false),
  ('magnesium-serum', 'micronutrients', false),
  ('nafld-fibrosis-score', 'glycemic-insulin', false),
  ('non-hdl-c', 'cardiovascular', false),
  ('oxidized-ldl', 'inflammatory', false),
  ('phosphorus', 'kidney-function', false),
  ('platelet-count', 'liver-function', false),
  ('potassium', 'kidney-function', false),
  ('pth', 'kidney-function', false),
  ('rbc-folate', 'micronutrients', false),
  ('renin', 'kidney-function', false),
  ('selenium', 'micronutrients', false),
  ('serum-iron', 'micronutrients', false),
  ('stfr', 'micronutrients', false),
  ('tg-hdl-ratio', 'cardiovascular', false),
  ('tg-hdl-ratio', 'glycemic-insulin', false),
  ('transferrin', 'micronutrients', false),
  ('transferrin-saturation', 'micronutrients', false),
  ('tyg-index', 'cardiovascular', false),
  ('uric-acid', 'cardiovascular', false),
  ('uric-acid', 'glycemic-insulin', false)
ON CONFLICT (marker_slug, category_slug) DO NOTHING;

-- 3) Neuro memberships. NOTE: these 4 markers have questionable PRIMARY categories
--    (e.g. s100b in 'electrolytes', NfL in 'specialty'). This migration only ADDS the
--    neuro membership; reassigning is_primary is left to metasync's review (see findings).
INSERT INTO marker_categories (marker_slug, category_slug, is_primary) VALUES
  ('neurofilament-light-chain', 'neurological-cognitive', false),
  ('enolase-neuron-specific', 'neurological-cognitive', false),
  ('enolase-neuron-specific-csf', 'neurological-cognitive', false),
  ('s100-calcium-binding-protein-b', 'neurological-cognitive', false)
ON CONFLICT (marker_slug, category_slug) DO NOTHING;

COMMIT;

-- ─── ROLLBACK ───
-- BEGIN;
--   DELETE FROM marker_categories WHERE (marker_slug, category_slug) IN (('adiponectin','hormones'), ('aldosterone','kidney-function'), ('apob','cardiovascular'), ('apob','liver-function'), ('c-peptide-fasting','hormones'), ('c-peptide-stimulated','hormones'), ('calcitriol','hormones'), ('calcitriol','kidney-function'), ('ferritin','micronutrients'), ('fgf-21','glycemic-insulin'), ('fli','glycemic-insulin'), ('hdl-cholesterol','cardiovascular'), ('homa-ir','cardiovascular'), ('homocysteine','kidney-function'), ('homocysteine','micronutrients'), ('hscrp','cardiovascular'), ('leptin','hormones'), ('lp-pla2','inflammatory'), ('lpa','cardiovascular'), ('magnesium-serum','kidney-function'), ('magnesium-serum','micronutrients'), ('nafld-fibrosis-score','glycemic-insulin'), ('non-hdl-c','cardiovascular'), ('oxidized-ldl','inflammatory'), ('phosphorus','kidney-function'), ('platelet-count','liver-function'), ('potassium','kidney-function'), ('pth','kidney-function'), ('rbc-folate','micronutrients'), ('renin','kidney-function'), ('selenium','micronutrients'), ('serum-iron','micronutrients'), ('stfr','micronutrients'), ('tg-hdl-ratio','cardiovascular'), ('tg-hdl-ratio','glycemic-insulin'), ('transferrin','micronutrients'), ('transferrin-saturation','micronutrients'), ('tyg-index','cardiovascular'), ('uric-acid','cardiovascular'), ('uric-acid','glycemic-insulin'), ('neurofilament-light-chain','neurological-cognitive'), ('enolase-neuron-specific','neurological-cognitive'), ('enolase-neuron-specific-csf','neurological-cognitive'), ('s100-calcium-binding-protein-b','neurological-cognitive'));
--   DELETE FROM test_categories WHERE slug = 'neurological-cognitive';
-- COMMIT;
