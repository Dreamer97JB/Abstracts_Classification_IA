# Taxonomy Inventory

Canonical taxonomy and legacy label mapping inventory for Phase 2 input.

Source of truth: `Article/Artículo_Arbor.pdf`

## Canonical taxonomy

- `tipo_1_realismo_fuerte`: `Tipo 1 - Realismo fuerte`
- `tipo_2_realismo_moderado_critico`: `Tipo 2 - Realismo moderado / critico`
- `tipo_3_antirrealismo_epistemologico`: `Tipo 3 - Antirrealismo epistemologico`
- `tipo_4_pragmatismo_epistemologico`: `Tipo 4 - Pragmatismo epistemologico`
- `tipo_5_constructivismo_moderado`: `Tipo 5 - Constructivismo moderado`
- `tipo_6_constructivismo_fuerte_relativismo`: `Tipo 6 - Constructivismo fuerte / relativismo`

## Supervised sources

| source_dataset | source_workbook | source_sheet | rows |
| --- | --- | --- | --- |
| muestras | Database/Scopus_database.xlsx | Muestras | 99 |
| seed | Seed/Seed.xlsx | Clasificados | 75 |

## Direct mappings

| source_dataset | label_original | count | canonical_id | label_canonica |
| --- | --- | --- | --- | --- |
| muestras | Tipo 5 CM | 42 | tipo_5_constructivismo_moderado | Tipo 5 - Constructivismo moderado |
| muestras | Tipo 6 CF - R | 27 | tipo_6_constructivismo_fuerte_relativismo | Tipo 6 - Constructivismo fuerte / relativismo |
| muestras | Tipo 1 RF | 5 | tipo_1_realismo_fuerte | Tipo 1 - Realismo fuerte |
| muestras | Tipo 4 PE | 3 | tipo_4_pragmatismo_epistemologico | Tipo 4 - Pragmatismo epistemologico |
| muestras | Tipo 3 AE | 2 | tipo_3_antirrealismo_epistemologico | Tipo 3 - Antirrealismo epistemologico |
| seed | Tipo 5 CM | 27 | tipo_5_constructivismo_moderado | Tipo 5 - Constructivismo moderado |
| seed | Tipo 4 PE | 6 | tipo_4_pragmatismo_epistemologico | Tipo 4 - Pragmatismo epistemologico |
| seed | Tipo 1 RF | 5 | tipo_1_realismo_fuerte | Tipo 1 - Realismo fuerte |
| seed | Tipo 3 AE | 4 | tipo_3_antirrealismo_epistemologico | Tipo 3 - Antirrealismo epistemologico |

## Alias mappings

| source_dataset | label_original | count | canonical_id | label_canonica |
| --- | --- | --- | --- | --- |
| muestras | Tipo 2 RC | 15 | tipo_2_realismo_moderado_critico | Tipo 2 - Realismo moderado / critico |
| muestras | Tipo 2 RM | 5 | tipo_2_realismo_moderado_critico | Tipo 2 - Realismo moderado / critico |
| seed | Tipo 2 RM | 18 | tipo_2_realismo_moderado_critico | Tipo 2 - Realismo moderado / critico |
| seed | Tipo 2 RC | 3 | tipo_2_realismo_moderado_critico | Tipo 2 - Realismo moderado / critico |

## Review-required rows

| source_dataset | row_number | title | label_original | mapping_status | mapping_notes |
| --- | --- | --- | --- | --- | --- |
| seed | 8 | The emergence of technoscientific fields and the new political sociology of science | Tipo 4 CM | revision_manual | Legacy label is unresolved and must stay in manual review. |
| seed | 16 | SOCIOLOGY OF SCIENCE AND TECHNOLOGY | No | sin_etiqueta | Explicitly marked as not labeled; exclude from gold and keep review-visible. |
| seed | 17 | Introduction: A cultural sociology of the authority of science | Tipo 6 RF | revision_manual | Legacy label is unresolved and must stay in manual review. |
| seed | 20 | The sociology of the scientific community | Tipo 6 RF | revision_manual | Legacy label is unresolved and must stay in manual review. |
| seed | 29 | “Social Priming” Through the Lens of Sociology of Science: Fuzzy Boundary, Personal Experience, and Broader Atmosphere | Tipo 6 RF | revision_manual | Legacy label is unresolved and must stay in manual review. |
| seed | 38 | Strong Programme in the Sociology of Scientific Knowledge | Tipo 6 RF | revision_manual | Legacy label is unresolved and must stay in manual review. |
| seed | 40 | PERSPECTIVES ON THE SOCIOLOGY OF SCIENCE | No | sin_etiqueta | Explicitly marked as not labeled; exclude from gold and keep review-visible. |
| seed | 51 | Actor network theory, Bruno Latour, and the CSI | Tipo 6 RF | revision_manual | Legacy label is unresolved and must stay in manual review. |
| seed | 52 | Critical feminist history of psychology versus sociology of scientific knowledge: Contrasting views of women scientists? | Tipo 6 RF | revision_manual | Legacy label is unresolved and must stay in manual review. |
| seed | 55 | Relativism in the Philosophy of Science | Tipo 6 RF | revision_manual | Legacy label is unresolved and must stay in manual review. |
| seed | 68 | Editorial Vision for Science & Education | <BLANK> | sin_etiqueta | Blank legacy label; exclude from gold and keep review-visible. |
| seed | 69 | Anthropology of Science: The Cuneiform World | Tipo 6 RF | revision_manual | Legacy label is unresolved and must stay in manual review. |
