# Architecture

**Analysis Date:** 2026-03-24

## Pattern Overview

**Overall:** Notebook-centric, artifact-driven analysis pipeline

**Key Characteristics:**
- `AbstractsV2.ipynb` concentra limpieza, clasificacion, enriquecimiento y visualizacion en un flujo secuencial por celdas.
- El acoplamiento entre fases ocurre mediante archivos persistidos en la raiz (`.xlsx`, `.csv`, `.html`), no mediante modulos Python reutilizables.
- `old/Christian_Escobar_Abstract_Classification_fix2.ipynb` conserva una version previa orientada a Google Colab y Google Drive, separada del flujo local actual.

## Layers

**Source Data Layer:**
- Purpose: alojar la entrada primaria y semillas de clasificacion.
- Location: `googleScholarPeriodAbs.xlsx`, `seed_generated.csv`, `seed_labeled.csv`
- Contains: dataset bruto exportado desde Google Scholar y ejemplos etiquetados para la etapa supervisada/semi-supervisada.
- Depends on: carga manual de archivos en la raiz del proyecto.
- Used by: `AbstractsV2.ipynb`

**Notebook Orchestration Layer:**
- Purpose: ejecutar todo el pipeline de preparacion, clasificacion y analisis.
- Location: `AbstractsV2.ipynb`
- Contains: celdas de instalacion, carga de datos, transformaciones con `pandas`, clasificacion con `transformers`/`setfit`, topicos con BERTopic, metodologia, autores y graficos.
- Depends on: archivos de entrada en la raiz y librerias instaladas dentro del entorno del notebook.
- Used by: ejecucion manual en Jupyter/Notebook.

**Persisted Stage Outputs Layer:**
- Purpose: materializar cada fase relevante del pipeline para reuso manual entre celdas y sesiones.
- Location: `abstracs_cleaned.csv`, `abstracts_reclasificados_top15.csv`, `abstracts_clasificados_subtemas_aprobados.csv`, `abstracts_clasificados_filoso´ficos.csv`, `abstracts_con_metodologia_optimizado.csv`
- Contains: snapshots incrementales del dataset a medida que recibe nuevas columnas de clasificacion.
- Depends on: `AbstractsV2.ipynb`
- Used by: fases posteriores del mismo notebook y revision manual de resultados.

**Visualization Output Layer:**
- Purpose: publicar resultados exploratorios fuera del notebook.
- Location: `temas_interactivos.html`, `top_15_temas_bar.html`
- Contains: exportaciones HTML de visualizaciones interactivas.
- Depends on: datos clasificados generados en `AbstractsV2.ipynb`
- Used by: inspeccion manual en navegador o entrega informal de resultados.

**Legacy Archive Layer:**
- Purpose: conservar la iteracion anterior del trabajo.
- Location: `old/Christian_Escobar_Abstract_Classification_fix2.ipynb`, `old/test.txt`
- Contains: notebook historico con rutas a `/content/drive/...`, montaje de Google Drive y automatizaciones propias de Colab.
- Depends on: Google Colab/Drive en la version archivada.
- Used by: referencia historica, no por el flujo local principal.

## Data Flow

**Current Local Pipeline:**

1. `AbstractsV2.ipynb` carga `googleScholarPeriodAbs.xlsx` desde la raiz local.
2. El notebook limpia columnas, nulos y duplicados y persiste `abstracs_cleaned.csv`.
3. La clasificacion filosofica usa `abstracs_cleaned.csv` junto con `seed_generated.csv` para producir un archivo intermedio llamado `classified_articles_setfit.csv` que el notebook vuelve a leer, aunque ese artefacto no esta presente hoy en la raiz.
4. El flujo de topicos y subtemas persiste snapshots sucesivos en `abstracts_reclasificados_top15.csv` y `abstracts_clasificados_subtemas_aprobados.csv`.
5. El etiquetado filosofico final se guarda en `abstracts_clasificados_filoso´ficos.csv`.
6. La clasificacion metodologica agrega `Methodology` y persiste `abstracts_con_metodologia_optimizado.csv`.
7. Las visualizaciones exportan `temas_interactivos.html` y `top_15_temas_bar.html`.

**Legacy Colab Pipeline:**

1. `old/Christian_Escobar_Abstract_Classification_fix2.ipynb` monta Google Drive.
2. El notebook lee y escribe CSV intermedios en `/content/drive/My Drive/...`.
3. Los artefactos locales actuales sustituyen ese esquema de almacenamiento externo, pero el notebook legado sigue mostrando la organizacion previa.

**State Management:**
- El estado vivo se mantiene en `DataFrame` dentro de `AbstractsV2.ipynb`.
- El estado duradero se versiona informalmente por nombre de archivo CSV/HTML en la raiz.
- No existe capa de configuracion central ni metadatos que describan la ultima salida valida.

## Key Abstractions

**Notebook Phase:**
- Purpose: agrupar una etapa de negocio dentro del notebook.
- Examples: `AbstractsV2.ipynb`
- Pattern: secciones markdown `Fase 0` a `Fase 6` que delimitan responsabilidades.

**Artifact as Contract:**
- Purpose: servir como interfaz entre fases sin codigo modular.
- Examples: `abstracs_cleaned.csv`, `abstracts_reclasificados_top15.csv`, `abstracts_con_metodologia_optimizado.csv`
- Pattern: cada etapa agrega columnas y sobrescribe o genera un nuevo CSV con nombre descriptivo.

**Legacy Snapshot:**
- Purpose: preservar una implementacion anterior para referencia.
- Examples: `old/Christian_Escobar_Abstract_Classification_fix2.ipynb`
- Pattern: mover notebooks desplazados a `old/` en lugar de refactorizar un historial unico.

## Entry Points

**Primary Notebook Entry Point:**
- Location: `AbstractsV2.ipynb`
- Triggers: apertura manual del notebook en un entorno Jupyter.
- Responsibilities: cargar fuentes, ejecutar todas las fases analiticas y producir los CSV/HTML actuales.

**Primary Raw Dataset Entry Point:**
- Location: `googleScholarPeriodAbs.xlsx`
- Triggers: lectura inicial desde `AbstractsV2.ipynb`
- Responsibilities: actuar como fuente de verdad de los abstracts antes de limpieza.

**Legacy Notebook Entry Point:**
- Location: `old/Christian_Escobar_Abstract_Classification_fix2.ipynb`
- Triggers: apertura manual solo para consulta o recuperacion de pasos historicos.
- Responsibilities: documentar la version previa del pipeline basada en Colab/Drive.

## Error Handling

**Strategy:** manejo ad hoc dentro del notebook

**Patterns:**
- Validacion manual con inspecciones de `isnull()`, `duplicated()` y vistas tabulares en `AbstractsV2.ipynb`.
- Confirmacion de progreso mediante `print(...)` y revisiones manuales de archivos generados.
- No hay capa comun de excepciones, reintentos ni validacion automatizada de existencia de artefactos intermedios.

## Cross-Cutting Concerns

**Logging:** `AbstractsV2.ipynb` usa `print(...)` y salidas de celda como mecanismo de seguimiento.
**Validation:** la limpieza inicial en `AbstractsV2.ipynb` valida nulos, duplicados y tipos; el resto del pipeline depende de inspeccion manual de CSV.
**Authentication:** no aplica al flujo local principal; `old/Christian_Escobar_Abstract_Classification_fix2.ipynb` incluye `drive.mount(...)` y uso de servicios externos propios de Colab.

---

*Architecture analysis: 2026-03-24*
