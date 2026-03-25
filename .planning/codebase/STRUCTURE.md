# Codebase Structure

**Analysis Date:** 2026-03-24

## Directory Layout

```text
Abstracts_Classification_IA/
+-- .planning/                     # Documentacion operativa del proyecto
¦   +-- codebase/                 # Mapas de codigo y arquitectura
+-- old/                          # Notebooks y archivos desplazados a archivo historico
+-- AbstractsV2.ipynb             # Notebook principal del pipeline actual
+-- googleScholarPeriodAbs.xlsx   # Fuente de datos primaria
+-- seed_generated.csv            # Semillas sinteticas para clasificacion
+-- seed_labeled.csv              # Semillas etiquetadas manualmente
+-- abstracs_cleaned.csv          # Dataset limpio tras preparacion
+-- abstracts_reclasificados_top15.csv              # Salida con topicos automaticos/top 15
+-- abstracts_clasificados_subtemas_aprobados.csv   # Salida con subtemas aprobados
+-- abstracts_clasificados_filoso´ficos.csv         # Salida con etiqueta filosofica consolidada
+-- abstracts_con_metodologia_optimizado.csv        # Salida con metodologia agregada
+-- temas_interactivos.html       # Visualizacion interactiva de temas
+-- top_15_temas_bar.html         # Visualizacion HTML de barras
+-- Abstracts-analisysv2.rar      # Paquete comprimido de artefactos/notebook
```

## Directory Purposes

**Project Root:**
- Purpose: concentrar el trabajo activo del analisis.
- Contains: notebook principal, dataset fuente, CSV intermedios/finales, visualizaciones HTML y archivos comprimidos.
- Key files: `AbstractsV2.ipynb`, `googleScholarPeriodAbs.xlsx`, `abstracs_cleaned.csv`, `abstracts_con_metodologia_optimizado.csv`

**`.planning/`:**
- Purpose: almacenar documentacion de soporte para orquestacion y mantenimiento.
- Contains: mapas de codigo y otros artefactos de planificacion.
- Key files: `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`

**`old/`:**
- Purpose: separar implementaciones historicas del flujo vigente.
- Contains: notebooks previos y archivos auxiliares ya no activos.
- Key files: `old/Christian_Escobar_Abstract_Classification_fix2.ipynb`, `old/test.txt`

## Key File Locations

**Entry Points:**
- `AbstractsV2.ipynb`: punto de ejecucion principal del pipeline actual.
- `old/Christian_Escobar_Abstract_Classification_fix2.ipynb`: referencia del pipeline previo en Colab.

**Configuration:**
- `AbstractsV2.ipynb`: contiene configuracion embebida de rutas de entrada/salida y dependencias `pip install`.
- `old/Christian_Escobar_Abstract_Classification_fix2.ipynb`: contiene configuracion historica de Google Drive/Colab.

**Core Logic:**
- `AbstractsV2.ipynb`: limpieza, clasificacion filosofica, subtemas, metodologia, autores y visualizaciones.

**Testing:**
- Not applicable: no existen carpetas, archivos ni runners de pruebas automatizadas.

## Naming Conventions

**Files:**
- Notebook activo con nombre versionado: `AbstractsV2.ipynb`
- CSV de etapa con nombre descriptivo en snake_case parcial y sufijos orientados al resultado: `abstracs_cleaned.csv`, `abstracts_reclasificados_top15.csv`, `abstracts_con_metodologia_optimizado.csv`
- HTML de visualizacion con nombres funcionales: `temas_interactivos.html`, `top_15_temas_bar.html`

**Directories:**
- Directorios funcionales y cortos: `.planning`, `old`

## Where to Add New Code

**New Feature:**
- Primary code: extender `AbstractsV2.ipynb` si la funcionalidad pertenece al mismo pipeline analitico.
- Tests: no hay ubicacion establecida hoy; si se incorporan pruebas, deben introducirse como una nueva convencion porque la estructura actual no reserva carpeta para ellas.

**New Component/Module:**
- Implementation: el patron actual es notebook-first, por lo que nuevos pasos de analisis se agregan como secciones/celdas en `AbstractsV2.ipynb`.
- Historical preservation: cuando un notebook quede obsoleto, moverlo a `old/` en lugar de mezclarlo con el flujo activo.

**Utilities:**
- Shared helpers: no existe una carpeta de utilidades compartidas; cualquier helper reusable hoy quedaria embebido en `AbstractsV2.ipynb`.

## Special Directories

**`.planning/codebase/`:**
- Purpose: documentar stack, arquitectura, estructura, calidad y riesgos del repositorio.
- Generated: Yes
- Committed: Yes

**`old/`:**
- Purpose: archivo historico de notebooks desplazados.
- Generated: No
- Committed: Yes

## Practical Placement Guidance

- Coloca nuevos datasets fuente en la raiz solo si forman parte del flujo principal del notebook y deben cargarse manualmente junto a `googleScholarPeriodAbs.xlsx`.
- Guarda nuevas salidas tabulares en la raiz con nombres que indiquen claramente la fase y las columnas agregadas, siguiendo el patron de `abstracts_*`.
- Exporta nuevas visualizaciones compartibles como `.html` en la raiz, junto a `temas_interactivos.html` y `top_15_temas_bar.html`.
- Usa `old/` para notebooks y artefactos reemplazados; no mezcles ahi archivos que sigan participando en el pipeline vigente.
- Mantén `.planning/codebase/` solo para documentacion operativa; no es una carpeta de datos ni de ejecucion.

---

*Structure analysis: 2026-03-24*
