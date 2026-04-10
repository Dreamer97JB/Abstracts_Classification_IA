# Aplicacion de la Skill `machine-learning-ops-ml-pipeline`

## Respuesta corta

Si, es factible y de hecho es una buena skill para este proyecto, con una salvedad importante:

- **si aplica** para estructurar el flujo completo de datos, mapeo canonico, `train/val/test`, entrenamiento, evaluacion, inferencia y revision
- **no conviene aplicar completa al pie de la letra** en su version mas pesada de MLOps enterprise

Para este repo, la decision correcta es usar la skill como **marco de orquestacion del pipeline**, pero adaptada a una primera version seria y medible, no a una plataforma de produccion con Kubernetes, KServe, Feast y despliegue continuo desde el dia uno.

## Donde si aporta mucho

La skill encaja muy bien en estas partes del proyecto:

1. Auditoria y versionado de datos
2. Definicion del `gold set`
3. Reglas de calidad para el seed y `Muestras`
4. Split robusto de `train/val/test`
5. Pipeline reproducible de entrenamiento
6. Comparacion de baselines
7. Medicion formal de metricas
8. Clasificacion batch del corpus completo
9. Exportes de baja confianza, conflicto y outliers

## Donde seria overkill por ahora

Estas piezas existen en la skill, pero no deberian ser prioridad en esta etapa:

- feature store tipo Feast
- serving online con FastAPI/TorchServe
- Kubernetes
- canary deployment
- drift monitoring en produccion
- IaC compleja

Para este proyecto, eso iria despues, si el clasificador demuestra utilidad real.

## Como se veria el flujo correcto para este caso

## Fase A. Canon y datos supervisados

Antes de entrenar cualquier modelo, hay que construir una verdad operativa confiable.

### Objetivo

Convertir `Seed` y `Muestras` en una tabla canonica entrenable.

### Inputs

- `Seed/Seed.xlsx`
- `Database/Scopus_database.xlsx` hoja `Muestras`
- `Article/Articulo_Arbor.pdf`

### Outputs

- tabla canonica de supervision
- tabla de conflictos
- tabla de excluidos

### Columnas minimas

- `record_id`
- `source_dataset`
- `title`
- `abstract`
- `label_original`
- `label_canonica`
- `mapping_status`
- `mapping_notes`
- `review_required`

## Fase B. Definicion del `gold set`

### Que es

El `gold set` es el subconjunto de filas que si consideramos suficientemente confiables para entrenar y medir.

### Que entra

- filas con `mapping_status = directo`
- filas con `mapping_status = fusionado`, cuando el merge este aprobado
- filas con abstract util y legible
- filas sin conflictos evidentes

### Que no entra aun

- `Tipo 6 RF`
- `Tipo 4 CM`
- `No`
- vacios
- casos con abstract muy pobre
- duplicados dudosos

### Regla clave

No todo lo etiquetado entra al `gold set`.
Primero pasa por control de calidad semantico.

## Fase C. Split duro de `train/val/test`

Aqui es donde endurecemos de verdad el pipeline.

### Reglas recomendadas

1. `test` fijo y congelado desde el inicio
2. split estratificado por `label_canonica`
3. deduplicacion por `title` y `DOI`
4. no permitir que duplicados o casi duplicados queden repartidos entre train y test
5. guardar la version del split en archivo
6. guardar semilla aleatoria

### Propuesta inicial

- `train`: 70%
- `val`: 15%
- `test`: 15%

Si el dataset canonico queda muy pequeño, usar:

- `train+val/test` fijo
- cross-validation solo dentro del bloque de entrenamiento

## Fase D. Baselines de modelado

No conviene depender solo de `zero-shot`.

### Orden recomendado

1. `Zero-shot`
   - sirve como baseline rapido
   - sirve para comparar
   - sirve para detectar desacuerdos

2. `Embeddings + clasificador ligero`
   - ejemplo: `sentence-transformers` + Logistic Regression o SVM
   - da un baseline supervisado fuerte y facil de explicar

3. `SetFit` o fine-tuning ligero
   - util si el `gold set` ya tiene suficiente señal

### Decision recomendada

- `zero-shot` como benchmark
- supervisado/few-shot como modelo principal

## Fase E. Evaluacion seria

Si queremos que quede bien cerrado, estas metricas no son opcionales.

### Metricas minimas

- accuracy
- macro F1
- weighted F1
- recall por clase
- precision por clase
- confusion matrix

### Metricas muy utiles para este caso

- top-2 accuracy
- tasa de abstencion
- porcentaje de baja confianza
- desacuerdo entre modelos

### Que revisar a mano

- falsos positivos entre clases cercanas
- errores entre `Tipo 2` y `Tipo 1`
- errores entre `Tipo 5` y `Tipo 6`
- clases minoritarias

## Fase F. Outliers, abstencion y revision

Si el objetivo es reducir errores, no hay que forzar prediccion siempre.

### Un registro puede salir como `review_required` si:

- confianza por debajo del umbral
- diferencia pequena entre la primera y segunda clase
- desacuerdo entre `zero-shot` y supervisado
- texto demasiado corto
- falta de señal teorica clara

### Tipos de salida recomendados

- `pred_label`
- `pred_score`
- `second_label`
- `second_score`
- `needs_review`
- `review_reason`

Esto permite sacar outliers y no vender seguridad falsa.

## Fase G. Clasificacion del corpus completo

Una vez validado el mejor modelo:

1. correr inferencia sobre Scopus completo
2. opcionalmente correr sobre Google
3. exportar resultados con trazabilidad

### Columnas minimas del export final

- `record_id`
- `source_dataset`
- `title`
- `year`
- `abstract`
- `pred_label`
- `pred_score`
- `second_label`
- `second_score`
- `needs_review`
- `model_name`
- `model_version`
- `dataset_version`
- `run_id`

## Fase H. Metodologia y temas

Esto no debe mezclarse con el target principal.

### Recomendacion

- teoria = pipeline principal
- metodologia = pipeline aparte, jerarquico
- temas = modulo secundario

### Metodologia

Secuencia recomendada:

1. `NN` o `con informacion`
2. si hay informacion: `no empirico` o `empirico`
3. si es empirico: `cualitativo` o `cuantitativo`

## Pesos y balance de clases

Cuando dijiste "medir pesos", aqui hay dos interpretaciones utiles.

### 1. Pesos de clases

Como las clases no estan balanceadas, debemos considerar:

- `class_weight = balanced`
- oversampling solo si hace falta
- no oversamplear antes de separar el test

### 2. Peso de evidencia del modelo

Tambien debemos medir:

- distribucion de confianza
- calibration
- margen entre primera y segunda clase

Eso ayuda a definir el umbral de revision.

## Que debemos considerar si queremos que quede muy cerrado

### Datos

- versionado del dataset
- versionado del mapping canonico
- reglas de inclusion/exclusion
- control de duplicados

### Entrenamiento

- configuracion reproducible
- semilla fija
- logs de experimento
- comparacion entre modelos

### Test

- test congelado
- no leakage
- error analysis manual

### Produccion de resultados

- inferencia con `run_id`
- export de review cases
- export de clasificacion final
- reportes de calidad

## Version recomendada de la skill para este proyecto

### Si aplicar ahora

- Data audit
- Data quality gates
- Gold set assembly
- Split strategy
- Baselines de modelado
- Experiment tracking simple
- Batch inference
- Error analysis

### Posponer

- Model registry complejo
- Serving online
- Kubernetes
- Drift detection en produccion

## Conclusión

La skill **si aplica**, pero como marco de pipeline, no como stack enterprise completo.

La mejor lectura para este proyecto es:

- no rehacer desde cero la infraestructura
- si rehacer la verdad supervisada
- usar `zero-shot` como baseline, no como solucion final unica
- construir un `gold set` fuerte
- endurecer `train/val/test`
- habilitar abstencion y outliers
- clasificar el corpus completo con trazabilidad

## Siguiente paso recomendado

El siguiente artefacto a crear deberia ser:

- una especificacion del `gold set v1`
- una tabla de inclusion/exclusion por fila o por regla
- una propuesta de experimentos:
  - `zero-shot`
  - `embeddings + LR`
  - `SetFit`

---
*Documento de discusion para aterrizar la skill `machine-learning-ops-ml-pipeline` al caso real del proyecto.*
