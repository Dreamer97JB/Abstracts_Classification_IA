# Abstracts Classification IA

Base de trabajo para refactorizar la POC de clasificacion de abstracts hacia
un flujo reproducible, separando:

- preparacion de datos
- auditoria de seeds y salidas
- entrenamiento e inferencia
- evaluacion y reportes

## Estado actual

El repositorio sigue siendo `notebook-first` en lo historico:
[`AbstractsV2.ipynb`](./AbstractsV2.ipynb) concentra la exploracion original y
[`old/Christian_Escobar_Abstract_Classification_fix2.ipynb`](./old/Christian_Escobar_Abstract_Classification_fix2.ipynb)
guarda la version entregada en Google Colab.

Los notebooks permanecen como artefactos **exploratorios**. La superficie
operativa nueva vive en `src/abstract_classifier/` y debe ser la fuente de
verdad para scripts, CLI y automatizacion.

Para una guia completa de diagnostico y refactor:

- ver [`docs/guia_refactor_clasificador.md`](./docs/guia_refactor_clasificador.md)
- ver [`docs/guia_amd_wsl_rocm.md`](./docs/guia_amd_wsl_rocm.md)

## Inicio rapido

1. Revisa la guia tecnica en `docs/guia_refactor_clasificador.md`.
2. Crea el entorno virtual local del repo:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_env.ps1 -Gpu
```

3. Instala las dependencias base y registra el paquete en modo editable:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements\base.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

4. Ejecuta la auditoria desde la CLI del paquete:

```powershell
.\.venv\Scripts\python.exe -m abstract_classifier.cli audit --output reports/data_audit.md
```

Compatibilidad heredada:

```powershell
.\.venv\Scripts\python.exe .\scripts\data_audit.py --output reports/data_audit.md
```

Si Windows no crea `Activate.ps1`, puedes usar directamente:

```powershell
.\.venv\Scripts\python.exe --version
```

### Superficie CLI disponible

```powershell
.\.venv\Scripts\python.exe -m abstract_classifier.cli --help
```

Comandos actuales:

- `audit`
- `prepare`
- `train`
- `evaluate`
- `predict`
- `analyze`

## Archivos clave

- `googleScholarPeriodAbs.xlsx`: snapshot original
- `abstracs_cleaned.csv`: dataset limpio usado como base
- `seed_labeled.csv`: semillas manuales historicas no canonicas
- `seed_generated.csv`: semillas sinteticas historicas no canonicas
- `abstracts_clasificados_filosoficos.csv`: clasificacion filosofica y topicos
- `abstracts_con_metodologia_optimizado.csv`: salida enriquecida mas completa actual
- `.planning/codebase/`: mapa formal del repositorio
