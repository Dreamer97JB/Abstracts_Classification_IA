# Abstracts Classification IA

Base de trabajo para refactorizar la POC de clasificación de abstracts hacia un flujo reproducible, separando:

- preparación de datos
- auditoría de seeds y salidas
- entrenamiento/inferencia
- evaluación y reportes

## Estado actual

El repositorio original es `notebook-first`: [`AbstractsV2.ipynb`](./AbstractsV2.ipynb) concentra limpieza, clasificación filosófica, subtemas, metodología, NER y visualizaciones. En [`old/Christian_Escobar_Abstract_Classification_fix2.ipynb`](./old/Christian_Escobar_Abstract_Classification_fix2.ipynb) está la versión entregada en Google Colab.

Para una guía completa de diagnóstico y refactor:

- ver [`docs/guia_refactor_clasificador.md`](./docs/guia_refactor_clasificador.md)
- ver [`docs/guia_amd_wsl_rocm.md`](./docs/guia_amd_wsl_rocm.md)

## Inicio rápido

1. Revisa la guía técnica en `docs/guia_refactor_clasificador.md`.
2. Ejecuta la auditoría de datos:

```powershell
& 'C:\Users\PC\AppData\Local\Python\pythoncore-3.14-64\python.exe' .\scripts\data_audit.py --output reports/data_audit.md
```

3. Si ya tienes Python 3.11 o 3.12 instalado, crea el entorno:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_env.ps1 -Gpu
```

4. Si solo tienes Python 3.14 y quieres probar bajo tu propio riesgo:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_env.ps1 -Gpu -AllowPython314
```

Si Windows no crea `Activate.ps1`, puedes usar directamente:

```powershell
.\.venv\Scripts\python.exe --version
```

## Archivos clave

- `googleScholarPeriodAbs.xlsx`: snapshot original
- `abstracs_cleaned.csv`: dataset limpio usado como base
- `seed_labeled.csv`: semillas manuales
- `seed_generated.csv`: semillas sintéticas generadas
- `abstracts_clasificados_filosóficos.csv`: clasificación filosófica + tópicos
- `abstracts_con_metodologia_optimizado.csv`: salida enriquecida más completa actual
- `.planning/codebase/`: mapa formal del repositorio
