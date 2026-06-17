param(
    [string]$Label = "day_now",
    [int]$RowLimit = 500,
    [string]$WslDistro = "Ubuntu-24.04"
)

$ErrorActionPreference = "Stop"

$repoWin = (Get-Location).Path
$repoWsl = "/mnt/" + $repoWin.Substring(0,1).ToLower() + $repoWin.Substring(2).Replace('\','/')

$candidateOut = "reports/tmp_phase9/final_compare/candidate_predict_rocm_$Label"
$championOut = "reports/tmp_phase9/final_compare/champion_predict_rocm_$Label"

$wslScript = @"
set -euo pipefail
cd '$repoWsl'
source /home/jbarrionuevo/.venvs/abstracts-rocm/bin/activate
export PYTHONPATH=src

python -m abstract_classifier.cli predict \
  --run-id smoke_phase9_rocm_champion_$Label \
  --model-run-dir reports/phase7/benchmark/sentence_transformer_logreg \
  --output-dir $championOut \
  --source-datasets scopus_base \
  --row-limit $RowLimit

python -m abstract_classifier.cli predict \
  --run-id smoke_phase9_rocm_candidate_$Label \
  --model-run-dir reports/tmp_phase9/gold_v6_wave06/runs/gold_v6_wave06_sentence_rocm \
  --output-dir $candidateOut \
  --source-datasets scopus_base \
  --row-limit $RowLimit
"@

wsl -d $WslDistro bash -lc $wslScript

.\.venv\Scripts\python.exe scripts/canary_daily_report.py `
  --candidate-predictions "$candidateOut/predictions.csv" `
  --champion-predictions "$championOut/predictions.csv" `
  --label $Label

Write-Host ""
Write-Host "Done. Canary report:"
Write-Host "reports/tmp_phase9/final_compare/canary_reports/${Label}_canary_report.md"
