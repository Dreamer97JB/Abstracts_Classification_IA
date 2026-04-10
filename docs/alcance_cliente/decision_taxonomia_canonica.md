# Decision de Taxonomia Canonica

## Objetivo

Definir la mejor estrategia para el target del modelo con base en:

- `Article/Articulo_Arbor.pdf`
- `Seed/Seed.xlsx`
- `Database/Scopus_database.xlsx` hoja `Muestras`
- `requirements.md`

La recomendacion es usar el canon final del articulo como target del modelo y conservar las etiquetas legacy solo como trazabilidad.

## Recomendacion

### Opcion recomendada

Entrenar el modelo para predecir la taxonomia canonica de 6 clases del articulo:

1. Tipo 1 - Realismo fuerte
2. Tipo 2 - Realismo moderado / critico
3. Tipo 3 - Antirrealismo epistemologico
4. Tipo 4 - Pragmatismo epistemologico
5. Tipo 5 - Constructivismo moderado
6. Tipo 6 - Constructivismo fuerte / relativismo

### Por que este es el mejor camino

- Alinea el sistema con la fuente teorica oficial del proyecto.
- Evita que el modelo aprenda inconsistencias del Excel como si fueran verdad conceptual.
- Hace mas facil explicar resultados al cliente.
- Permite mantener compatibilidad historica sin contaminar el target del modelo.

## Regla operativa

Cada registro etiquetado debe tener al menos estos campos:

- `label_original`
- `label_canonica`
- `mapping_status`
- `mapping_notes`
- `source_dataset`

### Significado sugerido

- `label_original`: valor exacto del Excel
- `label_canonica`: una de las 6 clases del articulo
- `mapping_status`: `directo`, `fusionado`, `revision_manual`, `sin_etiqueta`
- `mapping_notes`: observacion de por que se asigno o por que se detuvo
- `source_dataset`: `seed` o `muestras`

## Propuesta de mapeo inicial

| Label original | Canon propuesto | Estado | Nota |
|----------------|-----------------|--------|------|
| `Tipo 1 RF` | `Tipo 1 - Realismo fuerte` | `directo` | Coincide con la numeracion del articulo |
| `Tipo 2 RM` | `Tipo 2 - Realismo moderado / critico` | `fusionado` | `RM` se integra a la familia del Tipo 2 del articulo |
| `Tipo 2 RC` | `Tipo 2 - Realismo moderado / critico` | `fusionado` | `RC` se integra a la misma familia canonica |
| `Tipo 3 AE` | `Tipo 3 - Antirrealismo epistemologico` | `directo` | Coincide con la etiqueta esperada |
| `Tipo 4 PE` | `Tipo 4 - Pragmatismo epistemologico` | `directo` | Coincide con la etiqueta esperada |
| `Tipo 5 CM` | `Tipo 5 - Constructivismo moderado` | `directo` | Coincide con la etiqueta esperada |
| `Tipo 6 CF - R` | `Tipo 6 - Constructivismo fuerte / relativismo` | `directo` | Coincide con el articulo |
| `Tipo 6 RF` | `Pendiente` | `revision_manual` | En conflicto con el articulo, que fija el Tipo 6 como constructivismo fuerte / relativismo |
| `Tipo 4 CM` | `Pendiente` | `revision_manual` | Mezcla numero y sigla de otra familia; posible error de carga o version |
| `No` | `Pendiente` | `sin_etiqueta` | No debe entrar a entrenamiento hasta definir politica |
| `<BLANK>` | `Pendiente` | `sin_etiqueta` | No debe entrar a entrenamiento hasta definir politica |

## Hallazgos concretos en los archivos

### `Seed`

- `Tipo 5 CM`: 27
- `Tipo 2 RM`: 18
- `Tipo 6 RF`: 8
- `Tipo 4 PE`: 6
- `Tipo 1 RF`: 5
- `Tipo 3 AE`: 4
- `Tipo 2 RC`: 3
- `No`: 2
- `Tipo 4 CM`: 1
- vacio: 1

### `Muestras`

- `Tipo 5 CM`: 42
- `Tipo 6 CF - R`: 27
- `Tipo 2 RC`: 15
- `Tipo 1 RF`: 5
- `Tipo 2 RM`: 5
- `Tipo 4 PE`: 3
- `Tipo 3 AE`: 2

## Implicacion para entrenamiento

### Si usar

- Todos los casos con `mapping_status = directo`
- Todos los casos con `mapping_status = fusionado`, una vez aprobado que `RM` y `RC` se unan en el canon

### No usar aun

- Todos los casos con `mapping_status = revision_manual`
- Todos los casos con `mapping_status = sin_etiqueta`

## Decision recomendada para el pipeline

### Modelo principal

El modelo debe predecir `label_canonica`.

### Compatibilidad historica

Los outputs deben conservar tambien `label_original` para auditoria y comparacion.

### Evaluacion

La metrica principal debe calcularse sobre `label_canonica`, no sobre las etiquetas legacy.

## Casos a discutir con el cliente o resolver en revision interna

1. Si `RM` y `RC` efectivamente se consolidan en una sola clase canonica.
2. Que significa `Tipo 6 RF` en `Seed` y si es error, version previa o criterio distinto.
3. Que hacer con `Tipo 4 CM`.
4. Si `No` debe convertirse en exclusion del dataset o en una categoria de revision.

## Siguiente paso recomendado

Crear una tabla canonica de entrenamiento con estas columnas:

- `record_id`
- `source_dataset`
- `title`
- `abstract`
- `label_original`
- `label_canonica`
- `mapping_status`
- `mapping_notes`
- `review_required`

Con esa tabla ya se puede arrancar Phase 2 del roadmap: armonizacion de labels y armado del gold set revisado.

---
*Documento de trabajo para discusion de alcance y preparacion del mapeo canonico.*
