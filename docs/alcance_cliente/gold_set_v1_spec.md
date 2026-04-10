# Gold Set v1 Spec

## Proposito

Definir la primera version del conjunto confiable de supervision para:

- entrenamiento
- validacion
- test
- comparacion de modelos

Este documento no reemplaza la futura tabla canonica. Sirve para fijar las reglas con las que esa tabla debe construirse.

## Rol dentro del flujo

Este artefacto queda entre:

1. la decision de usar taxonomia canonica
2. la construccion del dataset entrenable

En terminos practicos:

- `decision_taxonomia_canonica.md` define **que** clases queremos
- este documento define **que filas** pueden usarse de forma confiable

## Fuente de verdad semantica

La semantica de clase se toma del articulo Arbor.

### Clases canonicas

1. `tipo_1_realismo_fuerte`
2. `tipo_2_realismo_moderado_critico`
3. `tipo_3_antirrealismo_epistemologico`
4. `tipo_4_pragmatismo_epistemologico`
5. `tipo_5_constructivismo_moderado`
6. `tipo_6_constructivismo_fuerte_relativismo`

## Fuentes supervisadas iniciales

### Incluidas como fuentes candidatas

- `Seed/Seed.xlsx`
- `Database/Scopus_database.xlsx` hoja `Muestras`

### No incluidas aun como supervision

- `Database/Google_Scholar_database.xlsx` completo
- `Database/Scopus_database.xlsx` hoja `Base`

Estas bases completas se reservan para inferencia y analisis, no para entrenamiento inicial.

## Estructura minima de la tabla canonica

Cada fila candidata debe poder convertirse a una tabla con estas columnas:

- `record_id`
- `source_dataset`
- `source_sheet`
- `title`
- `abstract`
- `year`
- `doi`
- `label_original`
- `label_canonica`
- `mapping_status`
- `mapping_notes`
- `review_required`
- `include_in_gold`

## Reglas de inclusion al Gold Set v1

Una fila entra al `gold set v1` solo si cumple todo lo siguiente:

1. Tiene `title` no vacio
2. Tiene `abstract` no vacio y con contenido util
3. Tiene `label_original` resoluble al canon
4. No presenta conflicto semantico evidente
5. No es duplicado problemático respecto a otra fila ya aceptada
6. `review_required = false`

## Reglas de exclusion del Gold Set v1

Una fila queda fuera del `gold set v1` si cumple cualquiera de estas condiciones:

1. `label_original` esta vacio
2. `label_original = No`
3. `mapping_status = revision_manual`
4. `mapping_status = sin_etiqueta`
5. El abstract es demasiado corto o no permite inferencia teorica razonable
6. Hay duplicado fuerte con otra fila ya aceptada y no hay criterio claro de deduplicacion

## Politica de mapeo inicial

### Entran directamente

- `Tipo 1 RF` -> `tipo_1_realismo_fuerte`
- `Tipo 3 AE` -> `tipo_3_antirrealismo_epistemologico`
- `Tipo 4 PE` -> `tipo_4_pragmatismo_epistemologico`
- `Tipo 5 CM` -> `tipo_5_constructivismo_moderado`
- `Tipo 6 CF - R` -> `tipo_6_constructivismo_fuerte_relativismo`

### Entran si se aprueba fusion

- `Tipo 2 RM` -> `tipo_2_realismo_moderado_critico`
- `Tipo 2 RC` -> `tipo_2_realismo_moderado_critico`

### No entran en v1

- `Tipo 6 RF`
- `Tipo 4 CM`
- `No`
- vacios

## Duplicados y leakage

## Regla general

No se permite que ejemplos duplicados o casi duplicados queden repartidos entre `train` y `test`.

### Campos de control recomendados

- `title_normalized`
- `doi_normalized`
- `abstract_hash`

### Regla operativa

Si dos filas representan esencialmente el mismo articulo:

- se conserva una sola para entrenamiento/evaluacion, o
- se agrupan y se asignan al mismo bloque de split

## Split recomendado

## Principio

El `test set` debe quedar congelado desde la primera version util.

### Si el Gold Set v1 tiene tamano suficiente

- `train`: 70%
- `val`: 15%
- `test`: 15%

### Si el Gold Set v1 es pequeno

- separar `test` fijo
- usar validacion cruzada sobre el bloque restante

### Reglas obligatorias

1. Split estratificado por `label_canonica`
2. Semilla fija y registrada
3. Version del split guardada en archivo
4. Misma particion para comparar todos los modelos

## Modelos a comparar en v1

No se recomienda elegir modelo unico antes de medir.

### Baseline 1

- `zero-shot`

Uso:

- benchmark rapido
- referencia conceptual
- apoyo para detectar desacuerdos

### Baseline 2

- `embeddings + clasificador lineal`

Ejemplos viables:

- sentence-transformers + Logistic Regression
- sentence-transformers + Linear SVM

### Baseline 3

- `SetFit` o fine-tuning ligero

Uso:

- modelo principal candidato si el gold set queda razonablemente fuerte

## Metricas minimas

- accuracy
- macro F1
- weighted F1
- precision por clase
- recall por clase
- confusion matrix

## Metricas adicionales recomendadas

- top-2 accuracy
- tasa de baja confianza
- porcentaje de abstencion
- desacuerdo entre modelos

## Politica de abstencion y outliers

El sistema no debe forzar clasificacion cuando la evidencia es debil.

### Un caso debe salir a revision si:

1. La confianza del modelo esta por debajo del umbral
2. La diferencia entre primera y segunda clase es pequena
3. `zero-shot` y supervisado discrepan
4. El abstract es pobre o ambiguo
5. La clase pertenece a una zona de conflicto historico del mapping

### Campos recomendados de salida

- `pred_label`
- `pred_score`
- `second_label`
- `second_score`
- `needs_review`
- `review_reason`

## Que entrega el Gold Set v1

Cuando este artefacto se implemente bien, debe habilitar:

1. entrenamiento reproducible
2. comparacion justa entre modelos
3. test congelado
4. analisis de error serio
5. inferencia sobre Scopus y Google con trazabilidad

## Riesgos principales

1. Que el gold set quede demasiado pequeno por exceso de exclusion
2. Que se mezclen duplicados entre split
3. Que `RM` y `RC` no deban fusionarse y sesguen el modelo
4. Que el equipo trate `zero-shot` como solucion final en vez de benchmark

## Decision GSD recomendada

No hace falta reestructurar fases otra vez.

### Camino recomendado

1. Mantener el roadmap actual
2. Abrir `discuss-phase` sobre la Fase 1
3. Cerrar en esa discusion:
   - formato de la tabla canonica
   - politica de alias y conflictos
   - estrategia de deduplicacion
   - criterio de inclusion al gold set
4. Pasar luego a planificar Phase 1

### Por que no reestructurar otra vez

Porque el roadmap ya refleja el nuevo alcance:

- Fase 1 fija canon y contratos
- Fase 2 arma el gold set y la armonizacion
- Fase 3 entrena y compara modelos

Cambiarlo otra vez ahora solo agregaria ruido.

## Resultado esperado de la siguiente conversacion

La siguiente discusion deberia terminar con decisiones cerradas sobre:

1. fusion o no de `RM` y `RC`
2. politica para `Tipo 6 RF`
3. politica para `Tipo 4 CM`
4. umbral minimo de calidad textual para entrar al gold set
5. reglas exactas de deduplicacion por `title` y `DOI`

---
*Especificacion de trabajo para construir el Gold Set v1 y preparar la discusion formal de Fase 1 y Fase 2.*
