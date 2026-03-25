# Guia AMD Radeon RX 9070 + WSL + ROCm

## Recomendacion corta

Con una `AMD Radeon RX 9070`, mi recomendacion principal para este proyecto es:

- Windows como host
- `WSL2 + Ubuntu 24.04` como entorno de desarrollo y entrenamiento
- ROCm dentro de WSL para PyTorch y el pipeline NLP/ML

## Estado validado en esta maquina

Al `2026-03-24` ya deje validado esto en tu equipo:

- `WSL2` instalado con `Ubuntu 24.04.4 LTS`
- ROCm para WSL instalado
- `rocminfo` detecta la GPU `AMD Radeon RX 9070` con arquitectura `gfx1201`
- entorno Python en WSL creado en `~/.venvs/abstracts-rocm`
- `PyTorch 2.9.1 + ROCm 7.2` funcionando con `torch.cuda.is_available() == True`
- kernel de Jupyter registrado como `abstracts-rocm`

Verificacion real obtenida:

- `torch 2.9.1+rocm7.2.0.git7e1940d4`
- `pandas 2.2.3`
- `scikit-learn 1.6.1`
- `transformers 4.51.3`
- `sentence-transformers 4.1.0`
- `setfit 1.1.3`
- `bertopic 0.17.4`

Conclusion practica:

- la parte de GPU ya quedo lista
- ya podemos entrenar desde WSL con la AMD
- el siguiente trabajo fuerte ya es de pipeline y de modelo, no de infraestructura base

## Por que recomiendo WSL

Segun la documentacion oficial de AMD que revise hoy:

- la `Radeon RX 9070` aparece soportada en ROCm sobre Linux y WSL
- en `WSL`, AMD marca soporte oficial de `PyTorch 2.9.1` con `ROCm 7.2`
- en `Windows`, AMD si soporta PyTorch, pero aclara que no todo el stack ROCm esta soportado todavia

Conclusion practica:

- si solo quisieras una prueba rapida de PyTorch, Windows puede servir
- si quieres un pipeline serio, reproducible y con menos friccion futura, conviene `WSL + Ubuntu`

## Estado actual de esta maquina

Hoy el escenario queda asi:

- Windows mantiene una `.venv` util para auditoria y trabajo CPU
- WSL ya es el entorno serio de entrenamiento
- la GPU AMD ya esta visible dentro de Ubuntu
- el entorno Python principal para ML debe ser `~/.venvs/abstracts-rocm`

Conclusion:

- Windows ya no es el cuello de botella
- el camino recomendado para el proyecto es trabajar el entrenamiento desde WSL

## Camino recomendado

### Opcion recomendada

1. Instalar `WSL2`
2. Instalar `Ubuntu 24.04`
3. Instalar el software oficial de AMD para `WSL2`
4. Crear un entorno Python dentro de Ubuntu
5. Instalar `PyTorch ROCm` y luego el stack del proyecto

### Opcion alternativa

Seguir solo en Windows y probar PyTorch ROCm para Windows.

No es mi opcion favorita para este repo porque el pipeline completo que quieres montar va mas alla de PyTorch: necesitas limpieza, entrenamiento, exportacion, topicos, evaluacion, y conviene una base mas estable de Linux.

## Lo que falta instalar

### En Windows host

Necesitas estos componentes:

1. `WSL2`
2. `Ubuntu 24.04`
3. `AMD Software: Adrenalin Edition for WSL2`

### En Ubuntu dentro de WSL

Necesitas:

1. `python3.12`
2. `python3.12-venv`
3. `python3-pip`
4. `build-essential`
5. `git`
6. `PyTorch ROCm`
7. dependencias del proyecto: `pandas`, `numpy`, `scikit-learn`, `transformers`, `datasets`, `accelerate`, `sentence-transformers`, `setfit`, `bertopic`, `hdbscan`, `umap-learn`, `plotly`, `nltk`

## Paso a paso sugerido

### Paso 1. Reutilizar el bootstrap del repo

Ya deje un bootstrap reproducible:

- `scripts/bootstrap_wsl_rocm.sh`
- `scripts/verify_wsl_rocm.sh`
- `requirements/wsl-rocm-7.2.txt`

Desde Ubuntu dentro del repo puedes correr:

```bash
bash scripts/bootstrap_wsl_rocm.sh
```

Y para revisar que todo sigue sano:

```bash
bash scripts/verify_wsl_rocm.sh
```

## Paso 2. Activar el entorno de trabajo

```bash
source ~/.venvs/abstracts-rocm/bin/activate
```

Si quieres abrir notebooks desde WSL:

```bash
jupyter lab
```

Y seleccionas el kernel:

- `Python (abstracts-rocm)`

## Paso 3. Recomendacion practica sobre el repo

Tu repo actual funciona desde `/mnt/d/...`, pero para entrenamientos mas pesados puede convenir mover una copia a filesystem Linux, por ejemplo:

```bash
mkdir -p ~/workspaces
cd ~/workspaces
git clone /mnt/d/Development/Repositories/AI-models/Abstract-clasif/Abstracts_Classification_IA
```

No es obligatorio hoy, pero si notas lentitud en lectura/escritura, esa es la primera optimizacion simple.

## Paso 4. Lo siguiente ya no es infraestructura

Con la GPU funcionando, el siguiente bloque de trabajo ya es:

1. modularizar el notebook
2. separar limpieza, etiquetas, entrenamiento, evaluacion e inferencia
3. dejar el clasificador preparado para recibir las nuevas categorias reales del cliente

## Como orientaria el repo a las etiquetas reales del cliente

Cuando el cliente te entregue etiquetas reales, yo moveria el flujo asi:

1. `data/raw/` para fuente original
2. `data/labels/` para semillas y datasets etiquetados reales
3. `data/interim/` para limpieza
4. `data/processed/` para splits de entrenamiento y evaluacion
5. `models/` para checkpoints
6. `reports/` para metricas, confusion matrix y errores

Y separaria por scripts:

- `prepare_dataset`
- `validate_labels`
- `train_baseline`
- `train_final_model`
- `predict_dataset`
- `discover_topics`
- `build_report`

## Mi recomendacion final para ti

Si quieres hacerlo bien en serio, haria esto en este orden:

1. mantener el entorno Windows actual como respaldo CPU
2. usar `WSL + Ubuntu 24.04` como entorno principal
3. aprovechar la `RX 9070` ya validada en ROCm
4. rehacer el pipeline con las etiquetas reales del cliente
5. cerrar primero la clasificacion principal
6. luego volver a subtemas, metodologia y visualizaciones

## Fuentes oficiales revisadas

- AMD Linux compatibility matrix: https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/native_linux/native_linux_compatibility.html
- AMD WSL compatibility matrix: https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/wsl/wsl_compatibility.html
- AMD Windows compatibility matrix: https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/windows/windows_compatibility.html
- AMD PyTorch install for Radeon on WSL: https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/install/installrad/wsl/install-pytorch.html
- Microsoft WSL install: https://learn.microsoft.com/en-us/windows/wsl/install
