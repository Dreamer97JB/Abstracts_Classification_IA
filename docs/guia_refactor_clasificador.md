# Guia de refactor del clasificador de abstracts

## 1. Diagnostico honesto del estado actual

La POC si sirve para demostrar valor, pero hoy el proyecto tiene varios riesgos si se quiere reutilizar con nuevas categorias y entregar resultados mas confiables.

### Lo que si funciona

- Ya existe un flujo real desde `googleScholarPeriodAbs.xlsx` hasta CSVs enriquecidos.
- Tienes un dataset limpio de trabajo (`abstracs_cleaned.csv`) con `6191` filas.
- Hay seeds manuales (`seed_labeled.csv`) y seeds sinteticas (`seed_generated.csv`).
- Ya se exploraron varias tecnicas: zero-shot, fine-tuning, SetFit, BERTopic, metodologia y NER.
- El equipo nuevo tiene GPU local y eso abre la puerta a entrenamientos mejores y mas rapidos.

### Lo que esta fragil

- El pipeline esta concentrado en notebooks.
- No hay `requirements`, `pyproject`, lockfile ni bootstrap reproducible.
- El notebook principal mezcla instalacion, entrenamiento, inferencia, analisis y visualizacion.
- La trazabilidad entre etapas depende de nombres de CSV y ejecucion manual.
- La evaluacion formal del clasificador filosofico no esta consolidada.

## 2. Hallazgos criticos del repo actual

### Notebook legado

`old/Christian_Escobar_Abstract_Classification_fix2.ipynb`:

- nace en Google Colab / Google Drive
- arranca con `facebook/bart-large-mnli` para clasificacion zero-shot
- luego prueba fine-tuning con `xlm-roberta-base`
- incorpora `train_test_split`, `accuracy` y `f1_macro`
- hace clustering y analisis posteriores en el mismo notebook

### Notebook actual

`AbstractsV2.ipynb`:

- trabaja ya en entorno local con GPU
- migra a una estrategia hibrida `SetFit + zero-shot`
- usa `seed_generated.csv` para entrenar SetFit
- produce `classified_articles_setfit.csv` como salida intermedia
- hace BERTopic global y luego reasigna etiquetas manuales de topicos
- clasifica metodologia con zero-shot
- extrae autores con NER
- genera graficas HTML y varios CSV finales

### Problemas de datos detectados

- `seed_labeled.csv` tiene `40` ejemplos, balanceados `10` por clase.
- `seed_generated.csv` tiene `500` filas, pero solo `127` textos unicos.
- Eso implica `373` duplicados exactos en seeds sinteticas.
- Los textos sinteticos miden en promedio `121.5` caracteres, mientras los abstracts reales promedian `867.6`.
- Hay una brecha grande entre la distribucion de entrenamiento sintetico y el texto real.

### Problemas del clasificador actual

- La salida filosofica esta fuertemente desbalanceada:
  - `Constructivism`: `4608`
  - `Pragmatism`: `910`
  - `Relativism`: `510`
  - `Realism`: `163`
- La confianza media observada en el notebook fue `0.4846`.
- En el CSV final actual, `Confidence` media ronda `0.5987`, pero ese campo se reutiliza en distintas tareas y eso confunde la trazabilidad.

### Problemas de topicos

- El pipeline fuerza los abstracts a un conjunto de topicos dominantes.
- Aun asi `1617` filas terminan en `Outlier`.
- Eso sugiere que la taxonomia de subtemas todavia no esta lo bastante estable o que los embeddings/clustering necesitan rehacerse con mejor criterio.

## 3. Conclusiones practicas

### No recomiendo seguir creciendo solo en notebook

El notebook fue una buena decision para sacar la POC y entregar algo funcionando. No fue un error. Pero para la siguiente etapa ya conviene separar responsabilidades.

### Si recomiendo refactorizar

No hace falta tirar todo a la basura. Lo correcto es:

1. conservar notebooks como espacio exploratorio
2. mover limpieza, auditoria, entrenamiento e inferencia a scripts
3. dejar configurables las categorias y rutas
4. agregar evaluacion reproducible

## 4. Arquitectura objetivo recomendada

```text
data/
  raw/
  interim/
  processed/
  external/

docs/
models/
notebooks/
reports/
scripts/
tests/

src/
  abstract_classifier/
    config.py
    data_prep.py
    seeds.py
    dataset.py
    train.py
    predict.py
    topics.py
    evaluation.py
```

## 5. Estrategia de modelado recomendada

### Fase A. Preparacion seria de datos

- fijar un dataset fuente unico
- versionar el dataset limpio
- documentar columnas obligatorias
- separar `title`, `abstract`, `year`, `authors`, `journal`
- decidir si el texto final sera solo `abstract` o `title + abstract`

Mi recomendacion inicial:

- clasificacion principal: `title + [SEP] + abstract`
- si falta abstract: descartar de entrenamiento
- si falta title: usar solo abstract

### Fase B. Etiquetado de alta calidad

Las nuevas categorias no deberian entrenarse con seeds sinteticas repetitivas como base principal.

Mi recomendacion:

- usar seeds manuales curadas por categoria
- meta minima inicial: `40-80` ejemplos reales por categoria
- separar claramente:
  - semillas reales confirmadas
  - semillas sinteticas auxiliares
  - ejemplos dudosos para revision

### Fase C. Baseline fuerte y simple

Antes de volver a usar un pipeline hibrido, conviene crear un baseline reproducible:

1. `zero-shot` para linea base rapida
2. `SetFit` para few-shot rapido
3. `DeBERTa` o `XLM-RoBERTa` fine-tuned para el mejor modelo final

Orden recomendado:

1. baseline zero-shot
2. baseline SetFit con seeds reales
3. fine-tuning supervisado cuando ya haya suficientes etiquetas buenas

### Fase D. Evaluacion formal

Metricas minimas obligatorias:

- accuracy
- macro F1
- weighted F1
- matriz de confusion
- precision y recall por clase
- top errores por clase

Tambien recomiendo:

- umbral de confianza para mandar casos a revision manual
- split estratificado fijo
- conjunto holdout que no se toque durante iteraciones rapidas

## 6. Que hacer con BERTopic y subtemas

BERTopic puede seguir siendo util, pero no debe mezclarse con la tarea principal de clasificacion filosofica.

Recomendacion:

- primero cerrar bien la clasificacion principal
- despues trabajar subtemas como pipeline aparte
- no reutilizar la misma columna `Confidence` para tareas diferentes
- guardar cada salida con columnas propias:
  - `stance_label`
  - `stance_score`
  - `topic_id`
  - `topic_label`
  - `topic_score`
  - `methodology_label`
  - `methodology_score`

## 7. Entorno recomendado

### Recomendacion principal

- Python `3.11`
- entorno virtual local `.venv`
- CUDA `12.1` si se quiere reproducir la idea del notebook local

### Por que no recomiendo arrancar por defecto con Python 3.14

Aunque parte del stack moderno ya soporta 3.14, la ruta mas segura para este proyecto sigue siendo `3.11` porque:

- el notebook local previo corrio sobre `Python 3.11.11`
- `SetFit` no da una señal tan clara de compatibilidad madura como `torch`
- quieres estabilidad, no solo novedad

Eso es una inferencia practica basada en el notebook existente y en metadatos actuales de paquetes.

## 8. Plan de trabajo recomendado

### Semana 1

- congelar estado actual
- auditar seeds y datos
- crear entorno reproducible
- separar artefactos y rutas

### Semana 2

- definir nuevas categorias
- construir dataset etiquetado real
- entrenar zero-shot y SetFit como baseline

### Semana 3

- entrenar modelo supervisado fuerte
- evaluar con macro F1 y confusion matrix
- decidir umbral de revision manual

### Semana 4

- rehacer subtemas y metodologia como pipelines separados
- generar entregables finales y reporte ejecutivo

## 9. Entregables minimos para tu siguiente entrega profesional

- script de limpieza reproducible
- script de auditoria de datos
- entorno reproducible
- baseline con metricas
- modelo final serializado
- CSV final con trazabilidad de scores
- reporte corto explicando limitaciones y calidad

## 10. Decision recomendada para este repo

Mi recomendacion concreta es esta:

1. no seguir metiendo mas logica a `AbstractsV2.ipynb`
2. usar el notebook solo como referencia historica y exploratoria
3. migrar desde ya a scripts y archivos de configuracion
4. rehacer las seeds con ejemplos reales antes de confiar en nuevas categorias
5. tratar `abstracts_clasificados_filosóficos.csv` como salida provisional, no como verdad final

## 11. Preguntas que si conviene responder antes del entrenamiento final

- Cuales seran exactamente las nuevas categorias
- Si una fila puede tener una sola categoria o varias
- Cuantas etiquetas reales puedes conseguir por categoria
- Si el texto de entrada sera solo abstract o titulo + abstract
- Si necesitas explicabilidad para entregar al cliente

Sin esas respuestas igual podemos avanzar en la infraestructura, que es justo lo que se deja preparado en este repo.

