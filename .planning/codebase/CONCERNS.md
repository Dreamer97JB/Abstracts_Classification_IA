# Codebase Concerns

**Analysis Date:** 2026-03-24

## Tech Debt

**Notebook monolitico de extremo a extremo:**
- Issue: Un unico notebook mezcla ingestion, limpieza, generacion de seeds, fine-tuning, clasificacion, topic modeling, clasificacion de metodologia, NER y visualizacion. No existe separacion entre preparacion de datos, entrenamiento, evaluacion e inferencia.
- Files: `AbstractsV2.ipynb`, `old/Christian_Escobar_Abstract_Classification_fix2.ipynb`
- Impact: Cada rerun puede alterar artefactos intermedios sin trazabilidad. Es dificil aislar regresiones, rehacer una fase concreta o convertir el trabajo en pipeline reproducible.
- Fix approach: Extraer scripts o modulos separados para `data_prep`, `train`, `predict`, `topic_modeling` y `analysis`; dejar el notebook solo como exploracion.

**Instalacion y administracion del entorno dentro del notebook:**
- Issue: El notebook ejecuta `pip install`, `pip uninstall` y reinstala `torch`/CUDA inline. No hay `requirements.txt`, `environment.yml`, `pyproject.toml` ni lockfile visibles en el repositorio.
- Files: `AbstractsV2.ipynb`
- Impact: El resultado depende del estado previo de la maquina, del acceso a internet y de versiones del dia. El mismo flujo puede cambiar comportamiento o romperse al reinstalar paquetes en medio del experimento.
- Fix approach: Versionar un entorno reproducible y mover la instalacion a archivos de configuracion del proyecto; fijar versiones de `torch`, `transformers`, `setfit`, `sentence-transformers`, `bertopic`, `datasets`, `nltk`.

**Artefactos de datos y salida sin control de linaje:**
- Issue: Los CSV derivados se encadenan manualmente, pero no registran version del modelo, commit, parametros ni fecha de generacion. Los nombres indican estados manuales como "reclasificados", "aprobados" u "optimizado", sin metadatos verificables.
- Files: `abstracs_cleaned.csv`, `seed_labeled.csv`, `seed_generated.csv`, `abstracts_reclasificados_top15.csv`, `abstracts_clasificados_filosóficos.csv`, `abstracts_clasificados_subtemas_aprobados.csv`, `abstracts_con_metodologia_optimizado.csv`
- Impact: No se puede auditar que codigo produjo cada dataset ni comparar runs con rigor.
- Fix approach: Anadir manifiestos por run o columnas de trazabilidad, y producir artefactos en carpetas versionadas por fecha/hash/parametros.

## Known Bugs

**Codificacion de texto degradada en seeds y exports:**
- Symptoms: Aparecen secuencias mojibake como `â€‘`, `mÃ­nimo`, `FilosofÃ­a`, `filosoÌficos`.
- Files: `seed_labeled.csv`, `seed_generated.csv`, `abstracs_cleaned.csv`, `abstracts_clasificados_filosóficos.csv`, `AbstractsV2.ipynb`
- Trigger: Abrir o reexportar archivos con codificaciones inconsistentes entre notebook, shell y CSV.
- Workaround: Forzar UTF-8 explicito en lectura/escritura y validar round-trip antes de entrenar o publicar salidas.

**Top-15 topics fuerza outliers a temas validos:**
- Symptoms: El notebook entrena BERTopic, toma los 15 temas mas comunes y reasigna cada abstract al centroide mas cercano, eliminando la posibilidad de mantener un outlier real en esa fase.
- Files: `AbstractsV2.ipynb`, `abstracts_reclasificados_top15.csv`
- Trigger: Ejecutar las celdas de reclasificacion por centroides en `AbstractsV2.ipynb`.
- Workaround: Mantener el topic original y una columna separada para el topic forzado; no sobrescribir la senal de incertidumbre del clustering.

## Security Considerations

**Dependencia de modelos remotos sin pinning ni cache controlada:**
- Risk: El flujo descarga modelos de Hugging Face en tiempo de ejecucion (`facebook/bart-large-mnli`, `sentence-transformers/paraphrase-mpnet-base-v2`, `dbmdz/bert-large-cased-finetuned-conll03-english`). Un cambio de version o indisponibilidad externa altera entrenamiento e inferencia.
- Files: `AbstractsV2.ipynb`
- Current mitigation: Se usa el nombre del modelo, pero no se fija revision exacta.
- Recommendations: Fijar revisiones/hash de modelos, documentar la cache local y registrar las versiones efectivas usadas en cada run.

## Performance Bottlenecks

**Clasificacion y topic modeling sobre todo el corpus desde notebook:**
- Problem: El notebook procesa `6191` abstracts con SetFit, zero-shot, embeddings y BERTopic en el mismo flujo interactivo.
- Files: `AbstractsV2.ipynb`, `abstracs_cleaned.csv`
- Cause: No hay particion clara entre entrenamiento, inferencia incremental y analisis offline; ademas se recalculan embeddings y clustering completos.
- Improvement path: Persistir embeddings/modelos, separar inferencia batch de analisis exploratorio, y usar jobs/scripts reanudables.

## Fragile Areas

**Semillas generadas sinteticamente y muy repetidas:**
- Files: `seed_labeled.csv`, `seed_generated.csv`, `AbstractsV2.ipynb`
- Why fragile: `seed_labeled.csv` contiene solo `40` ejemplos manuales balanceados (`10` por clase). `seed_generated.csv` escala a `500` filas, pero solo `127` combinaciones unicas; hay `373` duplicados exactos. La distribucion queda balanceada artificialmente (`125` por clase) y varios textos se repiten 8-9 veces con simples sustituciones de entidad.
- Safe modification: No ampliar entrenamiento con mas paraphrasing sintetico sin una auditoria de diversidad semantica. Priorizar anotacion humana incremental sobre abstracts reales del dominio.
- Test coverage: No hay pruebas ni validacion sistematica de calidad de las seeds.

**Taxonomia filosofica dependiente de mapeo manual de topics:**
- Files: `AbstractsV2.ipynb`, `abstracts_clasificados_filosóficos.csv`, `abstracts_clasificados_subtemas_aprobados.csv`
- Why fragile: Los IDs de BERTopic se asignan manualmente a etiquetas filosoficas (`Topic_ID -> Topic_Label`) dentro del notebook. Si cambia el clustering, el significado de los IDs tambien cambia. Ademas, el resultado aprobado todavia expone labels tipo bolsa de palabras como `the, of, and, to, in`.
- Safe modification: Fijar una taxonomia externa versionada y recalibrar los topics contra esa taxonomia; no asumir estabilidad de los IDs del clustering.
- Test coverage: No hay chequeos que detecten drift de IDs ni colisiones semanticas entre runs.

**Uso de una sola columna `Confidence` para tareas distintas:**
- Files: `abstracts_reclasificados_top15.csv`, `abstracts_con_metodologia_optimizado.csv`, `AbstractsV2.ipynb`
- Why fragile: El flujo anade clasificacion de metodologia y reutiliza la columna `Confidence` ya existente de la clasificacion filosofica. El archivo final conserva una sola columna, lo que mezcla o hace ambiguo que confianza corresponde a cada tarea.
- Safe modification: Usar columnas explicitas como `stance_confidence`, `methodology_confidence`, `topic_probability`.
- Test coverage: No hay pruebas que validen integridad de columnas tras cada fase.

## Scaling Limits

**Generalizacion limitada a cuatro etiquetas fijas y seeds balanceadas artificialmente:**
- Current capacity: El clasificador principal opera con `LABELS = ["Realism", "Constructivism", "Relativism", "Pragmatism"]` entrenado con seeds pequenas y sinteticas.
- Limit: La taxonomia no cubre categorias nuevas ni multi-label. Agregar nuevas corrientes obliga a rehacer seeds, verbalizers, mezcla SetFit/zero-shot y validacion manual.
- Scaling path: Definir esquema de etiquetas versionado, incorporar conjunto de validacion fuera de distribucion y evaluar estrategias jerarquicas o retrieval-assisted classification para nuevas categorias.

## Dependencies at Risk

**SetFit + zero-shot fusion sin evaluacion formal:**
- Risk: La mezcla `ALPHA = 0.5` entre SetFit y zero-shot esta fijada manualmente, sin benchmark reproducible ni calibracion en holdout.
- Impact: El sistema puede parecer estable por balance artificial de clases, pero degradarse ante abstracts reales o nuevas areas tematicas.
- Migration plan: Introducir un pipeline de evaluacion con split fijo y comparar SetFit puro, zero-shot puro y ensemble calibrado antes de mantener la fusion.

## Missing Critical Features

**Conjunto de evaluacion y metricas de producto/ML:**
- Problem: No existe test set etiquetado, matriz de confusion, F1 macro, precision por clase, calibracion de confianza ni evaluacion humana documentada.
- Blocks: No se puede defender calidad de modelo ni decidir si sirve para uso productivo, revision editorial o analisis longitudinal.

**Gobernanza de etiquetas y revision humana:**
- Problem: No hay guia para etiquetar abstracts ambiguos, multi-enfoque o fuera de taxonomia. Tampoco hay proceso visible de adjudicacion ni acuerdo entre anotadores.
- Blocks: La calidad de etiquetas depende de decisiones implicitas del notebook y del postproceso manual.

**Pipeline reproducible de entrenamiento/inferencia:**
- Problem: No hay comando unico reproducible ni scripts de CI para reconstruir los artefactos desde `googleScholarPeriodAbs.xlsx`.
- Blocks: No se puede rehacer una entrega ni comparar resultados entre fechas o maquinas.

## Test Coverage Gaps

**Clasificacion filosofica principal sin validacion externa:**
- What's not tested: Exactitud sobre abstracts reales de `abstracs_cleaned.csv`, robustez a clases minoritarias y sensibilidad a textos fuera de las cuatro corrientes.
- Files: `AbstractsV2.ipynb`, `abstracs_cleaned.csv`, `seed_labeled.csv`, `seed_generated.csv`
- Risk: El output final esta muy sesgado hacia `Constructivism` (`4608/6191`), mientras `Realism` queda en `163/6191`; la confianza media previa al topic modeling es `0.4846`, con `3586` casos por debajo de `0.5` y `5022` por debajo de `0.6`.
- Priority: High

**Topic modeling y mapeo a subtemas sin validacion semantica:**
- What's not tested: Estabilidad de BERTopic entre runs, calidad del mapeo `Automatic_Topic_ID -> Topic_Label`, y comportamiento de outliers.
- Files: `AbstractsV2.ipynb`, `abstracts_reclasificados_top15.csv`, `abstracts_clasificados_filosóficos.csv`, `abstracts_clasificados_subtemas_aprobados.csv`
- Risk: `1617/6191` registros quedan en `Outlier` o en la label automatica `the, of, and, to, in`, senal de topic debil o sin depuracion suficiente.
- Priority: High

**Clasificacion de metodologia y extraccion de autores sin verificacion de producto:**
- What's not tested: Si la metodologia inferida realmente corresponde al abstract y si el NER sobre abstracts recupera autores validos en vez de nombres citados en el texto.
- Files: `AbstractsV2.ipynb`, `abstracts_con_metodologia_optimizado.csv`
- Risk: Se anade informacion que puede parecer estructurada pero no representa atributos reales del articulo; esto puede inducir dashboards o filtros erroneos.
- Priority: Medium

**Tratamiento de datos base incompleto:**
- What's not tested: Integridad del dataset tras limpieza, consistencia de anos y manejo de abstracts nulos o vacios.
- Files: `AbstractsV2.ipynb`, `googleScholarPeriodAbs.xlsx`, `abstracs_cleaned.csv`
- Risk: El CSV limpio todavia expone `5` abstracts vacios y anos con valor `0`, lo que contamina analisis temporales y etapas posteriores.
- Priority: Medium

---

*Concerns audit: 2026-03-24*
