# Data Audit

Root: `D:\Development\Repositories\AI-models\Abstract-clasif\Abstracts_Classification_IA`

## Seed labeled

- rows: `40`
- unique texts: `40`
- text length stats: `min=113, avg=140.8, max=166`
- `Realism`: `10`
- `Constructivism`: `10`
- `Relativism`: `10`
- `Pragmatism`: `10`

## Seed generated

- rows: `500`
- unique texts: `127`
- duplicate texts: `373`
- text length stats: `min=100, avg=121.5, max=143`
- `Realism`: `125`
- `Constructivism`: `125`
- `Relativism`: `125`
- `Pragmatism`: `125`

## Cleaned dataset

- rows: `6191`
- missing abstract: `5`
- missing title: `0`
- year == 0: `215`
- blank year: `0`
- abstract length stats: `min=31, avg=867.6, max=4322`

## Final enriched output

- rows: `6191`
- confidence min: `0.5000`
- confidence avg: `0.5987`
- confidence max: `0.9972`
- confidence >= 0.8: `326`

### Predicted label distribution
- `Constructivism`: `4608`
- `Pragmatism`: `910`
- `Relativism`: `510`
- `Realism`: `163`

### Methodology distribution
- `Qualitative research (involves interviews, focus groups, thematic or content analysis, participant observation)`: `3783`
- `Quantitative research (involves numerical data, statistical analysis, surveys, experiments)`: `2408`

### Top topic labels
- `Outlier`: `1617`
- `Sociología del conocimiento`: `980`
- `Filosofía de la ciencia`: `537`
- `Filosofía de la tecnología`: `523`
- `Antropología de la ciencia`: `408`
- `Historia de la ciencia`: `331`
- `Filosofía de la educación`: `312`
- `Pedagogía de la ciencia`: `280`
- `Filosofía de la medicina`: `274`
- `Filosofía de la inteligencia artificial`: `203`
- `Epistemología feminista`: `193`
- `Filosofía económica`: `167`
- `Filosofía de la salud pública`: `150`
- `Estudios Ciencia-Tecnología-Sociedad (CTS)`: `141`
- `Naturaleza de la Ciencia (NOS)`: `75`
