param(
    [switch]$SmokeTest,
    [ValidateRange(1, 16)][int]$Threads = 2,
    [ValidateRange(1, 67349)][int]$Examples = 999,
    [ValidateRange(1, 50)][int]$Epochs = 3,
    [ValidateRange(8, 512)][int]$MaxLength = 128,
    [double]$LearningRate = 5e-5
)

$trainingRoot = Split-Path -Parent $PSScriptRoot
$trainingPython = Join-Path $trainingRoot '.tools\bert-tiny-venv\Scripts\python.exe'
$trainingExample = Join-Path $trainingRoot 'examples\bert_tiny_cpu'
if (-not (Test-Path -LiteralPath $trainingPython)) {
    throw 'Training environment is missing. See examples/bert_tiny_cpu/README.md.'
}

$env:HF_HOME = Join-Path $trainingExample '.cache\huggingface'
$env:HF_HUB_DISABLE_IMPLICIT_TOKEN = '1'
$env:HF_HUB_DISABLE_TELEMETRY = '1'
$env:TOKENIZERS_PARALLELISM = 'false'
$env:OMP_NUM_THREADS = "$Threads"
$env:MKL_NUM_THREADS = "$Threads"

$trainingName = if ($SmokeTest) { 'bert-tiny-smoke-' } else { 'bert-tiny-run-' }
$trainingOutput = Join-Path $trainingExample ($trainingName + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$trainingArguments = @('--threads', "$Threads", '--output', $trainingOutput)
if ($SmokeTest) { $trainingArguments += @('--examples', '30', '--epochs', '1') }
else {
    $trainingArguments += @('--examples', "$Examples", '--epochs', "$Epochs",
        '--max-length', "$MaxLength",
        '--learning-rate', $LearningRate.ToString([System.Globalization.CultureInfo]::InvariantCulture))
}

& $trainingPython -u (Join-Path $trainingExample 'train_bert_tiny.py') @trainingArguments
exit $LASTEXITCODE
