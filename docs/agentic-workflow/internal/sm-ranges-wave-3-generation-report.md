# SM Agent-Visible Input Generation Report — Wave-3

**Date:** 2026-05-18
**Source universe:** internal marker identity registry (`identity_ground_truth`)
**Value-row source:** local `output/import-ready-sm/*/bundle.yaml` files
**Generator:** `scripts/agentic_workflow/generate_sm_wave3_agent_input.py`
**Output:** `/home/zoltan/Projects/metabolicum-research/docs/agentic-workflow/input/sm-ranges/wave-3`
**Status:** generated review sample; all emitted rows are `internal_research_gate` pending identity review

Internal-only report. Do not ship this report inside the agent-visible payload.

## Scope

Wave-3 includes markers with `unreviewed_db_marker` binding status and local import-ready SM rows. It excludes wave-1, wave-2A, wave-2B, superseded aliases, canonical candidates, identity-review candidates, and any marker without import-ready rows.

`crosscheck_status` is intentionally absent from wave-3 agent-visible files. Wave-3 rows are locked to `internal_research_gate`; they are unreviewed legacy-db inputs only and cannot promote until marker identity is reviewed in the registry and a later wave regenerates them.

## Summary

- Marker files generated: `674`
- Range rows generated: `2001`
- Audit issues: `0`

### Entity Counts

| Entity type | Count |
|---|---:|
| `raw_input_marker` | 674 |

### Final Mode Counts

| Final mode | Count |
|---|---:|
| `legacy_sql_backfill_final` | 657 |
| `adult_single_site_interval_final` | 8 |
| `adult_population_table_final` | 5 |
| `adult_interval_consensus_final` | 2 |
| `adult_fragmented_multi_site_bundle_final` | 2 |

### Exclusion Reasons

| Reason | Registry markers |
|---|---:|
| `binding_status_canonical_candidate` | 106 |
| `binding_status_needs_identity_review` | 10 |
| `included` | 674 |
| `no_import_ready_rows` | 13 |
| `previous_wave_already_generated` | 307 |

### Use Counts

| Use | Row count |
|---|---:|
| `internal_research_gate` | 2001 |

### Row Count Distribution

| Rows per marker | Marker count |
|---:|---:|
| 1 | 7 |
| 2 | 87 |
| 3 | 550 |
| 4 | 14 |
| 6 | 11 |
| 7 | 1 |
| 9 | 2 |
| 11 | 1 |
| 12 | 1 |

### Excluded Invalid Status Rows

Rows whose status is not in the allowlist are excluded from the agent-visible payload.

| Marker slug | Excluded status values |
|---|---|
| `inhibin-a` | `normal-males` (1) |

### Row Unit Differences After Representation Normalization

| Top-level unit -> row unit | Row count |
|---|---:|
| `% -> Kronus` | 1 |
| `μg/L -> ng/mL` | 1 |

## Candidate Manifest

| Marker slug | Name | Entity | Rows | Final mode | Unit |
|---|---|---|---:|---|---|
| `1-3-beta-glucan` | 1,3 beta glucan | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | pg/mL |
| `10-hydroxycarbazepine` | 10-Hydroxycarbazepine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `11-deoxycorticosterone` | 11-Deoxycorticosterone | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/dL |
| `17-hydroxypregnenolone` | 17-Hydroxypregnenolone | `raw_input_marker` | 6 | `legacy_sql_backfill_final` | ng/dL |
| `18-hydroxycorticosterone` | 18-Hydroxycorticosterone | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/dL |
| `6-methylmercaptopurine` | 6-Methylmercaptopurine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | pmol 6-TGN/8x10^8 re |
| `9-hydroxyrisperidone` | 9-Hydroxyrisperidone | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `acacia-longifolia-ab-ige` | Wattle IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `acarboxyprothrombin` | Acarboxyprothrombin | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `acarus-siro-ab-ige` | Acarus siro IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `acer-negundo-ab-ige` | Boxelder IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `acetaminophen` | Acetaminophen | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `acetone` | Acetone | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | mg/dL |
| `acetylcholine-receptor-binding-ab` | Acetylcholine receptor binding Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | nmol/L |
| `acid-phosphatase-prostatic` | Prostatic acid phosphatase | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `acremonium-sp-ab-ige` | Acremonium sp IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `actin-smooth-muscle-ab-igg` | Actin smooth muscle IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U |
| `actinidia-chinensis-ab-ige` | Kiwifruit IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `adalimumab` | Adalimumab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `adalimumab-ab` | Adalimumab Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | μg/mL |
| `aedes-communis-ab-ige` | Aedes mosquito IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `agaricus-hortensis-ab-ige` | Mushroom IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `agrostis-stolonifera-ab-ige` | Red top grass IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `aldolase` | Aldolase | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | IU/L |
| `alkaline-phosphatase-bone` | Alkaline phosphatase.bone | `raw_input_marker` | 7 | `adult_single_site_interval_final` | μg/L |
| `allium-cepa-ab-ige` | Onion IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `allium-sativum-ab-ige` | Garlic IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `alnus-incana-ab-ige` | Grey Alder IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `alopercurus-pratensis-ab-ige` | Meadow Foxtail IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `alpha-1-fetoprotein-tumor-marker` | Alpha-1-fetoprotein.tumor marker | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `alprazolam` | ALPRAZolam | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `alternaria-alternata-ab-ige` | Alternaria alternata IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `amantadine` | Amantadine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `amaranthus-retroflexus-ab-ige` | Common pigweed IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `amaranthus-tuberculatus-ab-ige` | Water Hemp IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `ambrosia-elatior-ab-ige` | Common Ragweed IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `ambrosia-psilostachya-ab-ige` | Western Ragweed IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `ambrosia-trifida-ab-ige` | Giant Ragweed IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `amiodarone` | Amiodarone | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `amitriptyline` | Amitriptyline | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `amobarbital` | Amobarbital | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `amoxicillin-ab-ige` | Amoxicillin IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `amphetamine` | Amphetamine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `ampicillin-ab-ige` | Ampicillin IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `anacardium-occidentale-ab-ige` | Cashew nut IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `anacardium-occidentale-recombinant-rana-o-3-ab-ige` | Cashew nut recombinant (rAna o) 3 IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `ananas-comosus-ab-ige` | Pineapple IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `anaplasma-phagocytophilum-ab-igg` | Anaplasma phagocytophilum IgG Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | titer |
| `anethum-graveolens-ab-ige` | Dill IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `angiotensin-ii` | Angiotensin II | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | pg/mL |
| `anthemis-cotula-ab-ige` | Dog Fennel IgE Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | kU/L |
| `anthoxanthum-odoratum-ab-ige` | Sweet Vernal grass IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `antithrombin-ag-actual-normal` | Antithrombin Ag actual/normal in Platelet poor plasma by Immunoassay | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | % |
| `apis-mellifera-ab-ige` | Honey bee IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `apis-mellifera-ab-igg` | Honey bee IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `apium-graveolens-ab-ige` | Celery IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `apixaban` | Apixaban | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `aquaporin-4-water-channel-ab-igg` | Aquaporin 4 water channel IgG Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | 1:10 |
| `arachis-hypogaea-ab-ige` | Peanut IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `aripiprazole` | ARIPiprazole | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `artemisia-absinthium-ab-ige` | Wormwood IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `artemisia-vulgaris-ab-ige` | Mugwort IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `ascaris-sp-ab-ige` | Ascaris sp IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `asparagus-officinalis-ab-ige` | Asparagus IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `aspergillus-flavus-ab-ige` | Aspergillus flavus IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `aspergillus-fumigatus-ab-ige` | Aspergillus fumigatus IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `aspergillus-fumigatus-ab-igg` | Aspergillus fumigatus IgG Ab | `raw_input_marker` | 4 | `legacy_sql_backfill_final` | mg/L |
| `aspergillus-niger-ab-ige` | Aspergillus niger IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `astacus-astacus-ab-ige` | Crawfish IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `atriplex-lentiformis-ab-ige` | Lenscale IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `aureobasidium-pullulans-ab-ige` | Aureobasidium pullulans IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `avena-sativa-ab-ige` | Oat IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `avena-sativa-cultivated-ab-ige` | Oat pollen IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `babesia-microti-ab-igg` | Babesia microti IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | titer (1:X) |
| `baclofen` | Baclofen | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `basement-membrane-ab-igg` | Basement membrane IgG Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | AU/mL |
| `bean-black-ab-ige` | Black Bean IgE Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | kU/L |
| `bean-green-ab-ige` | Green Bean IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `bean-kidney-red-ab-ige` | Red Kidney Bean IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `bean-white-ab-ige` | White Bean IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `beef-ab-ige` | Beef IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `beet-ab-ige` | Beet IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `benztropine` | Benztropine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `bertholletia-excelsa-ab-ige` | Brazil Nut IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `bertholletia-excelsa-recombinant-rber-e-1-ab-ige` | Brazil Nut recombinant (rBer e) 1 IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `beta-hydroxybutyrate` | Beta hydroxybutyrate | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mmol/L |
| `beta-lactoglobulin-ab-ige` | Beta lactoglobulin IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `betula-verrucosa-ab-ige` | Silver Birch IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `bile-acid` | Bile acid | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | μmol/L |
| `biotinidase` | Biotinidase | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | IU/L |
| `bismuth` | Bismuth | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/L |
| `bixa-orellana-seed-ab-ige` | Annatto seed IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `blastomyces-dermatitidis-ab` | Blastomyces dermatitidis Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | IV |
| `blatella-germanica-ab-ige` | Cockroach IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `blomia-tropicalis-ab-ige` | Blomia tropicalis IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `bombus-terrestris-ab-ige` | Bumble Bee IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `bordetella-pertussis-ab-igg` | Bordetella pertussis IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | index |
| `botrytis-cinerea-ab-ige` | Botrytis cinerea IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `brassica-napus-ab-ige` | Rapeseed IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `brassica-oleracea-var-botrytis-ab-ige` | Cauliflower IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `brassica-oleracea-var-capitata-ab-ige` | Cabbage IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `brassica-oleracea-var-italica-ab-ige` | Broccoli IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `bromus-inermis-ab-ige` | Brome IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `brucella-sp-ab` | Brucella sp Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | 1:80 |
| `budgerigar-droppings-ab-ige` | Budgerigar droppings IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `bupivacaine` | Bupivacaine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `bupropion` | buPROPion | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `cadmium-blood-2` | Cadmium | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | μg/L |
| `caffeine` | Caffeine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `calcidiol` | 25-hydroxyvitamin D3 | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `calcidiol-ercalcidiol` | 25-Hydroxyvitamin D3+25-Hydroxyvitamin D2 | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `calcitonin` | Calcitonin | `raw_input_marker` | 3 | `adult_single_site_interval_final` | pg/mL |
| `camellia-sinensis-ab-ige` | Tea IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `cancer-ag-125` | Cancer Ag 125 | `raw_input_marker` | 4 | `legacy_sql_backfill_final` | U/mL |
| `cancer-ag-15-3` | Cancer Ag 15-3 | `raw_input_marker` | 4 | `legacy_sql_backfill_final` | U/mL |
| `cancer-ag-19-9` | Cancer Ag 19-9 | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | U/mL |
| `cancer-ag-27-29` | Cancer Ag 27-29 | `raw_input_marker` | 4 | `legacy_sql_backfill_final` | U/mL |
| `cancer-pagurus-ab-ige` | Crab IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `candida-albicans-ab-ige` | Candida albicans IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `capsicum-annuum-ab-ige` | Paprika IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `carbamazepine` | carBAMazepine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `carbamazepine-free` | carBAMazepine free | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `carbamazepine-total` | Carbamazepine, Total | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `carbon-dioxide` | Carbon dioxide, total | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mmol/L |
| `carcinoembryonic-ag` | Carcinoembryonic Ag | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `cardiolipin-ab-iga` | Cardiolipin IgA Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | APL |
| `cardiolipin-ab-igg` | Cardiolipin IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | GPL |
| `cardiolipin-ab-igm` | Cardiolipin IgM Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | MPL |
| `carica-papaya-ab-ige` | Papaya (Carica papaya) IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `carotene` | Carotene | `raw_input_marker` | 6 | `legacy_sql_backfill_final` | ug/dL |
| `carum-carvi-ab-ige` | Caraway IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `carya-illinoinensis-nut-ab-ige` | Pecan or Hickory Nut IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `carya-illinoinensis-tree-ab-ige` | Pecan or Hickory Tree IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `carya-ovata-ab-ige` | Shagbark Hickory IgE Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | kU/L |
| `casein-ab-ige` | Casein IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `castanea-sativa-ab-ige` | Chestnut IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `casuarina-equisetifolia-ab-ige` | Australian pine IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `cells-cd3-cd4` | CD3+CD4+ (T4 helper) cells | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | cells/µL |
| `cells-cd3-cd8` | CD3+CD8+ (T8 suppressor) cells | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | cells/uL |
| `celtis-occidentalis-ab-ige` | Hackberry tree IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `centromere-ab-igg` | Centromere IgG Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | AU/mL |
| `ceratonia-siliqua-ab-ige` | Carob IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `ceruloplasmin` | Ceruloplasmin | `raw_input_marker` | 12 | `legacy_sql_backfill_final` | mg/dL |
| `chaetomium-globosum-ab-ige` | Chaetomium globosum IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `cheese-cheddar-type-ab-ige` | Cheese cheddar type IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `cheese-mold-type-ab-ige` | Cheese mold type IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `chenopodium-album-ab-ige` | Goosefoot IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `chenopodium-quinoa-ab-ige` | Quinoa IgE Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | kU/L |
| `chicken-feather-ab-ige` | Chicken feather IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `chicken-serum-proteins-ab-ige` | Chicken serum proteins IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `chlorpromazine` | chlorproMAZINE | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `cholinesterase` | Cholinesterase | `raw_input_marker` | 6 | `legacy_sql_backfill_final` | IU/L |
| `choriomammotropin` | Choriomammotropin | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | μg/mL |
| `chromogranin-a` | Chromogranin A | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `chronic-urticaria-index` | Chronic urticaria index in Serum | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | U |
| `chymotrypsin-stool` | Chymotrypsin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U/g |
| `cicer-arientinum-ab-ige` | Chickpea IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `cinnamomum-spp-ab-ige` | Cinnamon IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `citrate` | Citrate | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mg/dL |
| `citrullus-lanatus-ab-ige` | Watermelon IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `citrus-aurantifolia-ab-ige` | Lime IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `citrus-limon-ab-ige` | Lemon IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `citrus-paradisis-ab-ige` | Grapefruit IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `citrus-reticulata-ab-ige` | Mandarin IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `citrus-sinensis-ab-ige` | Orange IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `clinical-biochemist-review` | Clinical biochemist review of results | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `clobazam` | cloBAZam | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `clomipramine` | clomiPRAMINE | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `clonidine` | cloNIDine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `clorazepate` | Clorazepate | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `clostridium-tetani-toxoid-ab-igg` | Clostridium tetani toxoid IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | Ratio |
| `clupea-harengus-ab-ige` | Herring IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `coagulation-3` | aPTT W excess hexagonal phase phospholipid in Platelet poor plasma by Coagulation assay | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | sec |
| `coagulation-actual-normal` | dRVVT actual/normal (normalized LA screen) | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | seconds |
| `coagulation-factor-ix-activity-actual-normal` | Coagulation factor IX activity actual/normal in Platelet poor plasma by Coagulation assay | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | % |
| `coagulation-factor-ix-inhibitor` | Coagulation factor IX inhibitor | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | % |
| `coagulation-factor-v-activity-actual-normal` | Coagulation factor V activity actual/normal in Platelet poor plasma by Coagulation assay | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | % |
| `coagulation-factor-vii-activity-actual-normal` | Coagulation factor VII activity actual/normal in Platelet poor plasma by Coagulation assay | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | % |
| `coagulation-factor-viii-activity-actual-normal` | Coagulation factor VIII activity actual/normal in Platelet poor plasma by Coagulation assay | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | % |
| `coagulation-factor-x-activity-actual-normal` | Coagulation factor X activity actual/normal in Platelet poor plasma by Coagulation assay | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | % |
| `coagulation-factor-xi-activity-actual-normal` | Coagulation factor XI activity actual/normal in Platelet poor plasma by Coagulation assay | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | % |
| `coagulation-factor-xii-activity-actual-normal` | Coagulation factor XII activity actual/normal in Platelet poor plasma by Coagulation assay | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | % |
| `coagulation-factor-xiii-activity-actual-normal` | Coagulation factor XIII activity actual/normal in Platelet poor plasma by Chromogenic method | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | % |
| `cocos-nucifera-ab-ige` | Coconut IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `coffea-spp-ab-ige` | Coffee IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `cold-agglutinin` | Cold agglutinin | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | 1:32 |
| `complement-c1-esterase-inhibitor` | Complement C1 esterase inhibitor | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mg/dL |
| `complement-c1-esterase-inhibitor-actual-normal` | Complement C1 esterase inhibitor actual/normal in Serum or Plasma | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | % |
| `complement-c1q` | Complement C1q | `raw_input_marker` | 6 | `legacy_sql_backfill_final` | mg/dL |
| `complement-c1q-ab` | Complement C1q Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U |
| `complement-c2` | Complement C2 | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mg/dL |
| `complement-c3a` | Complement C3a | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `complement-c5` | Complement C5 | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mg/dL |
| `complement-c5-functional` | Complement C5.functional | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U/mL |
| `complement-sc5b-9` | Complement Sc5b-9 | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `complement-total-hemolytic-ch50` | Complement total hemolytic CH50 | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U/mL |
| `coriandrum-sativum-ab-ige` | Cilantro IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `corticosterone` | Corticosterone | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/dL |
| `corylus-avellana-ab-ige` | Hazelnut IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `corylus-avellana-recombinant-rcor-a-8-ab-ige` | Hazelnut recombinant (rCor a) 8 IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `corynebacterium-diphtheriae-ab-igg` | Corynebacterium diphtheriae IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ratio |
| `coryphaena-hippurus-ab-ige` | Mahi mahi IgE Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | kU/L |
| `cow-milk-ab-ige` | Cow milk IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `cow-whey-ab-ige` | Cow whey IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `creatine` | Creatine | `raw_input_marker` | 6 | `legacy_sql_backfill_final` | mg/dL |
| `creatine-kinase-mb` | Creatine kinase.MB | `raw_input_marker` | 1 | `adult_interval_consensus_final` | ng/mL |
| `creatine-kinase-mb-creatine-kinase-total` | Creatine kinase.MB/Creatine kinase.total in Serum or Plasma by Electrophoresis | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | % |
| `cryptomeria-japonica-ab-ige` | Japanese Cedar IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `cu-2` | Copper/Creatinine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | microg/dL |
| `cucumis-melo-spp-ab-ige` | Honeydew melon IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `cucumis-sativus-ab-ige` | Cucumber IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `cucurbita-pepo-ab-ige` | Pumpkin IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `cucurbita-pepo-seed-ab-ige` | Pumpkin Seed IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `curcuma-longa-ab-ige` | Turmeric IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `curvularia-lunata-ab-ige` | Curvularia lunata IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `curvularia-specifera-ab-ige` | Curvularia specifera IgE Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | kU/L |
| `cv2-ab-igg-csf` | CV2 IgG Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ratio |
| `cyamopsis-tetragonoloba-ab-ige` | Guar gum IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `cyclobenzaprine` | Cyclobenzaprine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `cyclosporine` | cycloSPORINE | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `cynodon-dactylon-ab-ige` | Bermuda grass IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `cytomegalovirus-ab-igg-avidity` | Cytomegalovirus IgG Ab avidity | `raw_input_marker` | 3 | `legacy_sql_backfill_final` |  |
| `dactylis-glomerata-ab-ige` | Cocksfoot IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `daucus-carota-ab-ige` | Carrot IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `dehydroepiandrosterone-sulfate` | Dehydroepiandrosterone sulfate (DHEA-S) | `raw_input_marker` | 9 | `legacy_sql_backfill_final` | ug/dL |
| `dermatophagoides-farinae-ab-ige` | American house dust mite IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `dermatophagoides-microceras-ab-ige` | Dermatophagoides microceras IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `dermatophagoides-pteronyssinus-ab-ige` | European house dust mite IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `desipramine` | Desipramine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `dexamethasone` | Dexamethasone | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/dL |
| `dextromethorphan` | Dextromethorphan | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `digitoxin` | Digitoxin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `digoxin-3` | Digoxin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `digoxin-free` | Digoxin Free | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `diltiazem` | dilTIAZem | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `diphenylmethane-diisocyanate-mdi-ab-ige` | Isocyanate MDI IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `dna-double-strand-ab-igg` | DNA double strand IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | IUs |
| `dnase-b-ab-streptococcal` | Streptococcal DNAse B | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | U/mL |
| `dog-dander-ab-ige` | Dog dander IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `dolichovespula-arenaria-ab-ige` | Yellow Hornet IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `dolichovespula-maculata-ab-ige` | Whitefaced Hornet IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `dolichovespula-maculata-ab-igg` | Whitefaced Hornet IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `dopamine-2` | DOPamine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | pg/mL |
| `doxepin` | Doxepin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `duck-feather-ab-ige` | Duck feather IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `duloxetine` | DULoxetine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `egg-white-ab-ige` | Egg white IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `egg-whole-ab-ige` | Whole Egg IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `egg-yolk-ab-ige` | Egg yolk IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `ehrlichia-chaffeensis-ab-igg` | Ehrlichia chaffeensis IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | 1:n |
| `engraulis-encrasicolus-ab-ige` | Anchovy IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `ephedrine` | ePHEDrine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `epicoccum-purpurascens-ab-ige` | Epicoccum purpurascens IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `epstein-barr-virus-capsid-ab-igg` | Epstein Barr virus capsid IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U/mL |
| `epstein-barr-virus-capsid-ab-igm` | Epstein Barr virus capsid IgM Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U/mL |
| `epstein-barr-virus-early-diffuse-ab-igg` | Epstein Barr virus early diffuse IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U/mL |
| `epstein-barr-virus-nuclear-ab-igg` | Epstein Barr virus nuclear IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U/mL |
| `erythropoietin` | Erythropoietin (EPO) | `raw_input_marker` | 6 | `legacy_sql_backfill_final` | mIU/mL |
| `ethosuximide` | Ethosuximide | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `ethylene-glycol` | Ethylene glycol | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | mg/dL |
| `eucalyptus-spp-ab-ige` | Gum-Tree IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `everolimus` | Everolimus | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `fagopyrum-esculentum-ab-ige` | Buckwheat IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `fagus-grandifolia-ab-ige` | American Beech IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `felbamate` | Felbamate | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `festuca-elatior-ab-ige` | Meadow Fescue IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `finch-feather-ab-ige` | Finch feather IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `flecainide` | Flecainide | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `flounder-ab-ige` | Flounder IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `fluconazole` | Fluconazole | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `fluphenazine` | fluPHENAZine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `flurazepam` | Flurazepam | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `fluvoxamine` | fluvoxaMINE | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `formaldehyde-ab-ige` | Formaldehyde IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `fragaria-vesca-ab-ige` | Strawberry IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `franseria-acanthicarpa-ab-ige` | False ragweed IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `fraxinus-americana-ab-ige` | White Ash IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `furosemide` | Furosemide | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | μg/mL |
| `fusarium-moniliforme-ab-ige` | Fusarium moniliforme IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `gabapentin` | Gabapentin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `gadus-morhua-ab-ige` | Codfish IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `galactomannan-ag` | Galactomannan Ag | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | Index |
| `galactose-alpha-1-3-galactose-ab-ige` | Galactose-alpha-1,3-galactose (Alpha-Gal) IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `ganglioside-gm1-ab-igg-igm` | Ganglioside GM1 IgG+IgM Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | IV |
| `ganglioside-gm1-ab-igm` | Ganglioside GM1 IgM Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | IV |
| `gelatin-ab-ige` | Gelatin IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `gelatin-porcine-ab-ige` | Porcine Gelatin IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `gerbil-epithelium-ab-ige` | Gerbil epithelium IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `gliadin-peptide-ab-iga` | Gliadin peptide IgA Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | FLU |
| `gliadin-peptide-ab-igg` | Gliadin peptide IgG Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | FLU |
| `glial-fibrillary-acidic-protein` | Glial fibrillary acidic protein | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | pg/mL |
| `glucagon` | Glucagon | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | pg/mL |
| `glutamine-csf` | Glutamine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μmol/L |
| `gluten-ab-ige` | Gluten IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `glycine-max-ab-ige` | Soybean IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `glycyphagus-domesticus-ab-ige` | Glycyphagus domesticus IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `goat-epithelium-ab-ige` | Goat epithelium IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `goat-milk-ab-ige` | Goat milk IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `goose-feather-ab-ige` | Goose feather IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `guinea-pig-epithelium-ab-ige` | Guinea pig epithelium IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `gum-arabic-ab-ige` | Gum arabic IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `haemophilus-influenzae-b-ab-igg` | Haemophilus influenzae B IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `haloperidol` | Haloperidol | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `hamster-epithelium-ab-ige` | Hamster epithelium IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `haptoglobin` | Haptoglobin | `raw_input_marker` | 6 | `legacy_sql_backfill_final` | mg/dL |
| `heavy-metals-panel` | Heavy metals panel - Blood | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ug/dL |
| `helianthus-annuus-pollen-ab-ige` | Sunflower Pollen IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `helianthus-annuus-seed-ab-ige` | Sunflower Seed IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `heparin-unfractionated` | Heparin unfractionated | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | IU/mL |
| `hepatitis-b-virus-surface-ab` | Hepatitis B virus surface Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mIU/mL |
| `hepatitis-c-virus-rna` | Hepatitis C virus RNA | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | IU/mL |
| `her2-ag` | HER2 Ag | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `hexamethylene-diisocyanate-hdi-ab-ige` | Isocyanate HDI IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `hippoglossus-hippoglossus-ab-ige` | Halibut IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `histone-ab-igg` | Histone IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U |
| `hiv-1-rna` | HIV 1 RNA | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | Phone: |
| `homarus-gammarus-ab-ige` | Lobster IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `hordeum-vulgare-ab-ige` | Barley IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `horse-dander-ab-ige` | Horse dander IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `house-dust-greer-ab-ige` | House dust Greer IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `house-dust-hollister-stier-ab-ige` | House dust Hollister Stier IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `human-antimouse-ab` | Human antimouse Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `human-epididymis-protein-4` | Human epididymis protein 4 | `raw_input_marker` | 4 | `legacy_sql_backfill_final` | pmol/L |
| `hydroxyzine` | hydrOXYzine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `ibuprofen` | Ibuprofen | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `ictalurus-punctatus-ab-ige` | Catfish IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `igd` | IgD | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | mg/dL |
| `ige` | IgE | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `igg-subclass-4` | IgG subclass 4 | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mg/dL |
| `igg-synthesis-rate` | IgG synthesis rate | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mg/dL |
| `immune-complex` | Immune complex | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | µg Eq/mL |
| `inhibin-a` | Inhibin A | `raw_input_marker` | 4 | `adult_fragmented_multi_site_bundle_final` | pg/mL |
| `inhibin-b` | Inhibin B | `raw_input_marker` | 11 | `legacy_sql_backfill_final` | pg/mL |
| `insulin-ab` | Insulin Ab | `raw_input_marker` | 2 | `adult_single_site_interval_final` | % |
| `interferon-gamma` | Interferon gamma | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | pg/mL |
| `interleukin-2` | Interleukin 2 | `raw_input_marker` | 1 | `adult_single_site_interval_final` | pg/mL |
| `interleukin-2-receptor-soluble` | Interleukin 2 Receptor Soluble | `raw_input_marker` | 1 | `adult_single_site_interval_final` | pg/mL |
| `interleukin-4` | Interleukin 4 | `raw_input_marker` | 1 | `adult_single_site_interval_final` | pg/mL |
| `interleukin-8` | Interleukin 8 | `raw_input_marker` | 1 | `adult_single_site_interval_final` | pg/mL |
| `ipomoea-batatas-ab-ige` | Sweet potato IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `islet-cell-512-ab` | Islet cell 512 Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | Units/mL |
| `ispaghula-laxative-ab-ige` | Ispaghula laxative IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `itraconazole-serum-whole-blood-plasma` | Itraconazole | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `iva-ciliata-ab-ige` | Rough Marsh Elder IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `jo-1-extractable-nuclear-ab` | Jo-1 extractable nuclear Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | AU/mL |
| `juglans-california-pollen-ab-ige` | California Walnut Pollen IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `juglans-regia-recombinant-rjug-r-1-ab-ige` | English walnut recombinant (rJug r) 1 IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `juglans-spp-ab-ige` | Walnut IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `juniperus-sabinoides-ab-ige` | Mountain Juniper IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `juniperus-virginiana-ab-ige` | Red Cedar IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `kochia-scoparia-ab-ige` | Firebush IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `lacosamide` | Lacosamide | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `lactalbumin-alpha-ab-ige` | Lactalbumin alpha IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `lactic-acid` | Lactic Acid, Plasma | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mmol/L |
| `lactuca-sativa-ab-ige` | Lettuce IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `lamb-ab-ige` | Lamb IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `lamotrigine` | lamoTRIgine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `latex-ab-ige` | Latex IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `laurus-nobilis-ab-ige` | Bayleaf IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `lead-blood-2` | Lead/Creatinine | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | microg/d |
| `legionella-pneumophila-ab` | Legionella pneumophila Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | IV |
| `lens-esculenta-ab-ige` | Lentils IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `lepidoglyphus-destructor-ab-ige` | Lepidoglyphus destructor IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `levetiracetam` | levETIRAcetam | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `lidocaine` | Lidocaine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `ligustrum-vulgare-ab-ige` | Privet IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `limulus-amebocyte-lysate-test-other` | Limulus amebocyte lysate test | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | EU/mL |
| `linum-usitatissimum-ab-ige` | Flax IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `liquidambar-styraciflua-ab-ige` | Sweet gum IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `lithium` | Lithium | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mmol/L |
| `liver-kidney-microsomal-1-ab` | Liver kidney microsomal 1 Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | U |
| `loligo-sp-ab-ige` | Squid IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `lolium-perenne-ab-ige` | Perennial rye grass IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `lorazepam` | LORazepam | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `lpa-2` | Lipoprotein a | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | nmol/L |
| `lycopersicon-lycopersicum-ab-ige` | Tomato IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `lysozyme` | Lysozyme | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `macadamia-spp-ab-ige` | Macadamia IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `malt-ab-ige` | Malt IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `malus-sylvestris-ab-ige` | Apple IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `mangifera-indica-ab-ige` | Mango IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `mannose-binding-protein` | Mannose-binding protein | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `medicago-sativa-ab-ige` | Alfalfa IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `melaleuca-leucadendron-ab-ige` | Cajeput tree IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `melanogrammus-aeglefinus-ab-ige` | Haddock IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `mentha-piperita-ab-ige` | Peppermint IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `mercury-blood-2` | Mercury | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | μg/L |
| `merluccius-merluccius-ab-ige` | European Hake (Merluccius merluccius) IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `methadone` | Methadone | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `methotrexate` | Methotrexate | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μmol/L |
| `methylphenidate` | Methylphenidate | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `mexiletine` | Mexiletine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `mi-2-ab` | Mi-2 Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | 1:80 |
| `micropterus-salmoides-ab-ige` | Bass, Black IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `midazolam` | Midazolam | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `mirtazapine` | Mirtazapine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `mitochondria-m2-ab` | Mitochondria M2 Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | U |
| `mitotane` | Mitotane | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `morus-alba-ab-ige` | White mulberry IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `moth-ab-ige` | Moth IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `mouse-epithelium-ab-ige` | Mouse epithelium IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `mouse-serum-proteins-ab-ige` | Mouse serum proteins IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `mouse-urine-proteins-ab-ige` | Mouse urine proteins IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `mucor-racemosus-ab-ige` | Mucor racemosus IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `mumps-virus-ab-igg` | Mumps virus IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | AU/mL |
| `mumps-virus-ab-igm` | Mumps virus IgM Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | IV |
| `musa-spp-ab-ige` | Banana IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `muscle-specific-receptor-tyrosine-kinase-ab` | Muscle specific receptor tyrosine kinase Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | 1:ratio |
| `mustard-ab-ige` | Mustard IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `mutated-citrullinated-vimentin-ab` | Mutated citrullinated vimentin Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U/mL |
| `mycophenolate` | Mycophenolate | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `mycoplasma-pneumoniae-ab-igg` | Mycoplasma pneumoniae IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | IU/L |
| `mycoplasma-pneumoniae-ab-igm` | Mycoplasma pneumoniae IgM Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | IU/L |
| `myelin-associated-glycoprotein-ab-igm` | Myelin associated glycoprotein IgM Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | IV |
| `myelin-basic-protein-csf` | Myelin basic protein | `raw_input_marker` | 4 | `legacy_sql_backfill_final` | ng/mL |
| `myeloperoxidase-ab` | Myeloperoxidase Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | AU/mL |
| `myrica-spp-ab-ige` | Bayberry IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `mytilus-edulis-ab-ige` | Blue mussel IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `n-acetylprocainamide` | N-acetylprocainamide | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `neurofilament-light-chain` | Neurofilament light chain | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | pg/mL |
| `nickel` | Nickel | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/L |
| `norclozapine` | Norclozapine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `norfentanyl` | Norfentanyl | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `norsertraline` | Norsertraline | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `nortriptyline` | Nortriptyline | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `nuclear-ab` | Nuclear Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U |
| `nuclear-ab-igg` | Nuclear IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | 1:80 |
| `nuclear-pore-protein-gp210-ab` | Nuclear pore protein gp210 Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U |
| `nutmeg-ab-ige` | Nutmeg IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `observation` | Osmolality of Serum or Plasma | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mOsm/kg |
| `ocimum-basilicum-ab-ige` | Basil IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `octopus-vulgaris-ab-ige` | Octopus IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `olanzapine` | OLANZapine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `olea-europaea-ab-ige` | Olive IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `olea-europaea-pollen-ab-ige` | Olive Pollen IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `oncorhynchus-mykiss-ab-ige` | Trout IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `origanum-vulgare-ab-ige` | Oregano IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `oryza-sativa-ab-ige` | Rice IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `ostrea-edulis-ab-ige` | Oyster IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `ovalbumin-ab-ige` | Ovalbumin IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `ovomucoid-ab-ige` | Ovomucoid IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `oxalate` | Oxalate | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | μmol/L |
| `oxazepam` | Oxazepam | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `oxycodone` | oxyCODONE | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `pancreatic-polypeptide` | Pancreatic polypeptide | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | pg/mL |
| `pandalus-borealis-ab-ige` | Shrimp IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `panicum-milliaceum-ab-ige` | Common Millet IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `papaver-somniferum-ab-ige` | Poppy Seed IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `parathyrin-intact` | Parathyrin.intact | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | pg/mL |
| `parathyrin-related-protein` | Parathyrin related protein | `raw_input_marker` | 4 | `legacy_sql_backfill_final` | pmol/L |
| `parietal-cell-ab-igg` | Parietal cell IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U |
| `parietaria-officinalis-ab-ige` | Pellitory (Parietaria officinalis) IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `paspalum-notatum-ab-ige` | Bahia grass IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `pathology-study` | Pathology study | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | µg/g of tissue |
| `pecten-spp-ab-ige` | Scallop IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `penicillin-g-ab-ige` | Penicillin G IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `penicillin-v-ab-ige` | Penicillin V IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `penicillium-notatum-ab-ige` | Penicillium notatum IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `pentobarbital` | PENTobarbital | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `pepper-green-ab-ige` | Green Pepper IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `periplaneta-americana-ab-ige` | American Cockroach IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `perphenazine` | Perphenazine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `persea-americana-ab-ige` | Avocado IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `petroselinum-crispum-ab-ige` | Parsley IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `ph` | pH of Stool | `raw_input_marker` | 3 | `legacy_sql_backfill_final` |  |
| `phalaris-arundinacea-ab-ige` | Canary grass IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `phaseolus-limensis-ab-ige` | Lima Bean IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `phencyclidine` | Phencyclidine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `phenobarbital` | PHENobarbital | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `phenylalanine` | Phenylalanine | `raw_input_marker` | 1 | `adult_single_site_interval_final` | μmol/L |
| `phenytoin` | Phenytoin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `phenytoin-free` | Phenytoin Free | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `phenytoin-free-total-panel` | Phenytoin free and total panel - Serum or Plasma | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `phleum-pratense-ab-ige` | Timothy IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `phoma-betae-ab-ige` | Phoma betae IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `phosphatidylserine-ab-igg` | Phosphatidylserine IgG Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | U |
| `phosphatidylserine-prothrombin-complex-ab-igg` | Phosphatidylserine-prothrombin complex IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U |
| `phospholipase-a2-receptor-ab-igg-2` | Phospholipase A2 receptor IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | RU/mL |
| `phragmites-communis-ab-ige` | Common Reed IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `phthalic-anhydride-ab-ige` | Phthalic anhydride IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `pigeon-feather-ab-ige` | Pigeon feather IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `pimpinella-anisum-ab-ige` | Anise IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `pinus-edulis-ab-ige` | Pine Nut IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `pinus-strobus-ab-ige` | Eastern White Pine IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `pistacia-vera-ab-ige` | Pistachio IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `pisum-sativum-ab-ige` | Pea IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `plantago-lanceolata-ab-ige` | English plantain IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `plasmin-inhibitor-actual-normal` | Plasmin inhibitor actual/normal in Platelet poor plasma by Chromogenic method | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | % |
| `plasminogen-activator-tissue-type-ag` | Plasminogen activator tissue type Ag | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `plasminogen-actual-normal` | Plasminogen actual/normal in Platelet poor plasma by Chromogenic method | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | % |
| `platelet-factor-4-heparin-complex-induced-ab-igg` | Heparin induced platelet IgG Ab in Serum or Plasma by Immunoassay | `raw_input_marker` | 4 | `adult_population_table_final` | mg/dL |
| `pleuronectes-platessa-ab-ige` | Plaice IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `poa-pratensis-ab-ige` | Kentucky blue grass IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `polistes-spp-ab-ige` | Paper wasp IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `pollachius-virens-ab-ige` | Pollock IgE Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | kU/L |
| `populus-alba-ab-ige` | White Poplar IgE Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | kU/L |
| `populus-deltoides-ab-ige` | Cottonwood IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `populus-tremula-ab-ige` | Aspen IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `pork-ab-ige` | Pork IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `porphyrins` | Porphyrins | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | nmol/L |
| `posaconazole-serum-whole-blood-urine` | Posaconazole | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `pregabalin` | Pregabalin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `pregnenolone` | Pregnenolone | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `prekallikrein-activity-actual-normal` | Prekallikrein (Fletcher Factor) activity actual/normal in Platelet poor plasma by Coagulation assay | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | % |
| `procollagen-type-i-n-terminal-propeptide` | Procollagen type I.N-terminal propeptide | `raw_input_marker` | 9 | `legacy_sql_backfill_final` | μg/L |
| `promethazine` | Promethazine | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `propafenone` | Propafenone | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `prosopis-juliflora-ab-ige` | Mesquite IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `prostate-specific-ag-2` | Prostate specific Ag | `raw_input_marker` | 4 | `legacy_sql_backfill_final` | ng/mL |
| `prostate-specific-ag-free` | Prostate Specific Ag Free | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `prostate-specific-ag-protein-bound` | Prostate specific Ag.protein bound | `raw_input_marker` | 4 | `legacy_sql_backfill_final` | ng/mL |
| `protein-c-actual-normal-2` | Protein C actual/normal in Platelet poor plasma by Chromogenic method | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | % |
| `protein-c-ag-actual-normal` | Protein C Ag actual/normal in Platelet poor plasma by Immunoassay | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | % |
| `protein-s-ag-actual-normal` | Protein S Ag actual/normal in Platelet poor plasma by Immunoassay | `raw_input_marker` | 6 | `legacy_sql_backfill_final` | % |
| `protein-s-free-ag-actual-normal` | Protein S Free Ag actual/normal in Platelet poor plasma by Immunoassay | `raw_input_marker` | 6 | `legacy_sql_backfill_final` | % |
| `protein-total` | Protein, Total (CSF) | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | g/dL |
| `proteinase-3-ab` | Proteinase 3 Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | AU/mL |
| `prothrombin-activity-actual-normal` | Prothrombin activity actual/normal in Platelet poor plasma by Coagulation assay | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | % |
| `protriptyline` | Protriptyline | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `provasopressin-c-terminal` | Provasopressin.C-terminal | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | pmol/L |
| `prunus-armeniaca-ab-ige` | Apricot IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `prunus-avium-ab-ige` | Cherry IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `prunus-domestica-ab-ige` | Plum IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `prunus-dulcis-ab-ige` | Almond IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `prunus-persica-ab-ige` | Peach IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `prunus-persica-var-nucipersica-ab-ige` | Nectarine IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `pt-2` | PT panel - Platelet poor plasma by Coagulation assay | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | sec |
| `pyrus-communis-ab-ige` | Pear IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `quercus-alba-ab-ige` | White Oak IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `quercus-rubra-ab-ige` | Red Oak IgE Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | kU/L |
| `quercus-virginiana-ab-ige` | Virginia Live Oak IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `quetiapine` | QUEtiapine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `quinidine` | quiNIDine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `rabbit-epithelium-ab-ige` | Rabbit epithelium IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `rabbit-meat-ab-ige` | Rabbit meat IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `rat-epithelium-ab-ige` | Rat epithelium IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `rat-serum-proteins-ab-ige` | Rat serum proteins IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `rat-urine-proteins-ab-ige` | Rat urine proteins IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `referral-lab-test-reference-range` | Referral lab test reference range | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | Inconclusive |
| `retinol-binding-protein` | Retinol binding protein | `raw_input_marker` | 4 | `adult_population_table_final` | mg/dL |
| `rhizopus-nigricans-ab-ige` | Rhizopus nigricans IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `riboflavin` | Riboflavin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | nmol/L |
| `ribosomal-p-ab` | Ribosomal P Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | AU/mL |
| `rickettsia-typhi-ab-igg` | Rickettsia typhi IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | 1:64 |
| `risperidone-9-hydroxyrisperidone-panel` | risperiDONE and 9-Hydroxyrisperidone panel - Serum or Plasma | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `rna-polymerase-iii-ab-igg` | RNA polymerase III IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U |
| `rubella-virus-ab-igg` | Rubella virus IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | IU/mL |
| `rubella-virus-ab-igm` | Rubella virus IgM Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | AU/mL |
| `rubus-fruticosus-ab-ige` | Blackberry IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `rubus-idaeus-ab-ige` | Raspberry IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `ruditapes-spp-ab-ige` | Clam IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `rufinamide` | Rufinamide | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `rumex-acetosella-ab-ige` | Sheep Sorrel IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `rumex-crispus-ab-ige` | Yellow Dock IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `saccharomyces-cerevisiae-ab-iga` | Baker's yeast IgA Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | U |
| `saccharomyces-cerevisiae-ab-ige` | Baker's yeast IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `saccharomyces-cerevisiae-ab-igg-2` | Baker's yeast IgG Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | U |
| `saccharum-officinarum-ab-ige` | Sugar Cane IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `salicylates` | Salicylates | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `salix-caprea-ab-ige` | Willow IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `salmo-salar-ab-ige` | Salmon IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `salsola-kali-ab-ige` | Saltwort IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `sardina-pilchardus-ab-ige` | Sardine (pilchard) IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `scl-70-extractable-nuclear-ab-igg` | SCL-70 extractable nuclear IgG Ab | `raw_input_marker` | 4 | `adult_population_table_final` | mg/dL |
| `scomber-scombrus-ab-ige` | Mackerel IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `secale-cereale-ab-ige` | Rye IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `secale-cereale-pollen-ab-ige` | Cultivated Rye IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `secobarbital` | Secobarbital | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `seminal-fluid-ab-ige` | Seminal fluid IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `serotonin-release-100-iu-ml-heparin-unfractionated` | Serotonin release 100 IU/mL heparin.unfractionated | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | % |
| `sesamum-indicum-ab-ige` | Sesame Seed IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `setomelanomma-rostrata-ab-ige` | Setomelanomma rostrata IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `sheep-epithelium-ab-ige` | Sheep epithelium IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `sirolimus` | Sirolimus | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `sjogrens-syndrome-b-extractable-nuclear-ab-igg` | Sjogrens syndrome-B extractable nuclear IgG Ab | `raw_input_marker` | 4 | `adult_population_table_final` | mg/dL |
| `smith-extractable-nuclear-ab-igg` | Smith extractable nuclear IgG Ab | `raw_input_marker` | 4 | `adult_population_table_final` | mg/dL |
| `snapper-red-ab-ige` | Red Snapper IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `solanum-melongena-ab-ige` | Eggplant IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `solanum-tuberosum-ab-ige` | Potato IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `solea-solea-ab-ige` | Sole IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `solenopsis-invicta-ab-ige` | Red Imported Fire Ant IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `solidago-virgaurea-ab-ige` | Goldenrod IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `soluble-fms-like-tyrosine-kinase-1-placental-growth-factor` | Soluble fms-like tyrosine kinase-1/placental growth factor | `raw_input_marker` | 2 | `legacy_sql_backfill_final` |  |
| `soluble-liver-ab` | Soluble liver Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U |
| `soluble-liver-ab-igg` | Soluble liver IgG Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | U |
| `somatostatin` | Somatostatin | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | pg/mL |
| `sorghum-halepense-ab-ige` | Johnson grass IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `sotalol` | Sotalol | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `sp100-ab` | sp100 Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | U |
| `spinacia-oleracea-ab-ige` | Spinach IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `squamous-cell-carcinoma-ag` | Squamous cell carcinoma Ag | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `squash-zucchini-ab-ige` | Zucchini IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `staphylococcus-aureus-enterotoxin-a-ab-ige` | Staphylococcus aureus enterotoxin A IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `stemphylium-botryosum-ab-ige` | Stemphylium botryosum IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `stfr-3` | Soluble Transferrin Receptor | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `stizostedion-vitreum-ab-ige` | Walleye Pike IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `streptolysin-o-ab` | Streptolysin O Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | IU/mL |
| `swine-epithelium-ab-ige` | Swine epithelium IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `syagrus-romanzoffianum-ab-ige` | Queen Palm IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `syzygium-aromaticum-ab-ige` | Clove IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `tabanus-spp-ab-ige` | Horse Fly IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `taenia-solium-larva-ab-igg-csf` | Taenia solium larva IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U |
| `taraxacum-vulgare-ab-ige` | Dandelion IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `taxodium-distichum-ab-ige` | Bald Cypress IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `temazepam` | Temazepam | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `teriflunomide` | Teriflunomide | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `thallium` | Thallium | `raw_input_marker` | 1 | `adult_fragmented_multi_site_bundle_final` | μg/L |
| `theobroma-cacao-ab-ige` | Cocoa IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `theophylline` | Theophylline | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `thiocyanate` | Thiocyanate | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | mg/dL |
| `thiopurine-methyltransferase` | Thiopurine methyltransferase | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U/mL |
| `thrombopoietin` | Thrombopoietin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | pg/mL |
| `thunnus-albacares-ab-ige` | Tuna IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `thymus-vulgaris-ab-ige` | Thyme IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `thyroglobulin-ab` | Thyroglobulin Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | IU/mL |
| `thyroperoxidase-ab` | Thyroperoxidase Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | IU/mL |
| `thyrotropin` | Thyrotropin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mU/L |
| `thyrotropin-receptor-ab` | Thyrotropin receptor Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | units/L |
| `thyroxine-free-2` | Thyroxine (T4) free | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/dL |
| `tilapia-ab-ige` | Tilapia IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `tin` | Tin | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `tissue-transglutaminase-ab-iga` | Tissue transglutaminase IgA Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | FLU |
| `tissue-transglutaminase-ab-igg` | Tissue transglutaminase IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | FLU |
| `todarodes-pacificus-ab-ige` | Pacific Squid IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `toluene-diisocyanate-tdi-ab-ige` | Isocyanate TDI IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `topiramate` | Topiramate | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `toxoplasma-gondii-ab-igg` | Toxoplasma gondii IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | IU/mL |
| `toxoplasma-gondii-ab-igm` | Toxoplasma gondii IgM Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | AU/mL |
| `tramadol` | traMADol | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `trazodone` | traZODone | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `triacylglycerol-lipase` | Lipase | `raw_input_marker` | 6 | `legacy_sql_backfill_final` | IU/L |
| `triazolam` | Triazolam | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `trichoderma-viride-ab-ige` | Trichoderma viride IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `trichophyton-mentagrophytes-var-interdigitale-ab-ige` | Trichophyton mentagrophytes var interdigitale IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `trichophyton-rubrum-ab-ige` | Trichophyton rubrum IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `triiodothyronine-free` | Triiodothyronine (T3) Free | `raw_input_marker` | 6 | `adult_interval_consensus_final` | pg/mL |
| `trimipramine` | Trimipramine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `triticum-aestivum-ab-ige` | Wheat IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `triticum-aestivum-pollen-ab-ige` | Cultivated Wheat IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `turkey-feather-ab-ige` | Turkey feather IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `turkey-meat-ab-ige` | Turkey meat IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `tyrophagus-putrescentiae-ab-ige` | Tyrophagus putrescentiae IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `ulmus-americana-ab-ige` | White Elm IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `urtica-dioica-ab-ige` | Nettle IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `ustekinumab` | Ustekinumab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `ustilago-maydis-ab-ige` | Corn smut IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `vaccinium-myrtillus-ab-ige` | Blueberry IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `vaccinium-oxycoccos-ab-ige` | Bog cranberry IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `valproate` | Valproate | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `valproate-free` | Valproate Free | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `valproic-acid` | Valproic Acid | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `vanilla-planifolia-ab-ige` | Vanilla IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `varicella-zoster-virus-ab-igg` | Varicella zoster virus IgG Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ISR |
| `varicella-zoster-virus-ab-igm` | Varicella zoster virus IgM Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ISR |
| `vascular-endothelial-growth-factor` | Vascular endothelial growth factor | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | pg/mL |
| `vasoactive-intestinal-peptide` | Vasoactive intestinal peptide | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | pg/mL |
| `vespula-spp-ab-ige` | Yellow Jacket IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `vigabatrin` | Vigabatrin | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | ng/mL |
| `viscosity` | Viscosity of Serum | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | cP |
| `vitis-vinifera-ab-ige` | Grape IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `von-willebrand-factor-ag-actual-normal` | von Willebrand factor (vWf) Ag actual/normal in Platelet poor plasma by Immunoassay | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | % |
| `von-willebrand-factor-cleaving-protease-actual-normal` | von Willebrand factor (vWf) cleaving protease actual/normal in Platelet poor plasma by Chromogenic m | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | % |
| `von-willebrand-factor-cleaving-protease-inhibitor-2` | von Willebrand factor (vWf) cleaving protease inhibitor | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | U/mL |
| `voriconazole` | Voriconazole | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |
| `whitefish-ab-ige` | Whitefish IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `xanthium-commune-ab-ige` | Cocklebur IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `xiphias-gladius-ab-ige` | Swordfish IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `zea-mays-ab-ige` | Corn IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `zea-mays-pollen-ab-ige` | Cultivated Corn IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `zinc-transporter-8-ab` | Zinc transporter 8 Ab | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | Kronus Units/mL |
| `zingiber-officinale-ab-ige` | Ginger IgE Ab | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | kU/L |
| `ziprasidone` | Ziprasidone | `raw_input_marker` | 2 | `legacy_sql_backfill_final` | ng/mL |
| `zn-3` | Zinc/Creatinine | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | mcg/g creatinine |
| `zonisamide` | Zonisamide | `raw_input_marker` | 3 | `legacy_sql_backfill_final` | μg/mL |

## Locked Generation Rules

- Marker universe comes from the marker identity registry, not the filesystem bundle list.
- Numeric rows come from local import-ready SM bundles only after registry filtering.
- Wave-3 row schema is kept compatible with wave-1: raw `variant` and `population_scope` are not exposed.
- Age-like source variants are parsed into structured `age_min` / `age_max` when those fields are otherwise null; no-op `variant: all` is dropped.
- All wave-3 rows are `internal_research_gate`; no row is comparison-only or display eligible until marker identity is reviewed.
- Promotion path: human review confirms marker identity and row semantics; crosscheck/promotion pass records readiness; only then can a row be regenerated into a less restricted use tier.
- `crosscheck_status` is omitted from wave-3 files until the promotion pass exists; it remains a wave-1 frozen-summary concept for now.
- Rows with non-allowlisted status values are excluded from the agent-visible payload and counted in the internal report.
- Representation-equivalent unit spellings are normalized using the marker identity registry plus local typography variants; real unit differences remain row-level `unit` values.
- Agent-visible files omit provider names, provider URLs, local paths, raw extraction values, and source collection details.
- Public IDs are exposed only when PMID/PMCID/DOI can be extracted from a source URL.
