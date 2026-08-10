# Start rag_server.py as a detached background process (no window).
# Safe to call multiple times — skips if already running.

$projectRoot = Split-Path $PSScriptRoot -Parent
$serverScript = Join-Path $PSScriptRoot "rag_server.py"
$logFile = Join-Path $projectRoot "data\rag_server.log"
$errFile = Join-Path $projectRoot "data\rag_server_err.log"
$pidFile = Join-Path $projectRoot "data\rag_server.pid"

# Check if already running on port 8503
$listening = netstat -aon 2>$null | Select-String ":8503\s.*LISTENING"
if ($listening) {
    Write-Host "RAG server already running on port 8503."
    exit 0
}

# Find Python
$python = "python"
if (Test-Path (Join-Path $projectRoot ".venv\Scripts\python.exe")) {
    $python = Join-Path $projectRoot ".venv\Scripts\python.exe"
}

# Start as hidden background process
$proc = Start-Process -FilePath $python `
    -ArgumentList "`"$serverScript`"" `
    -WorkingDirectory $projectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError $errFile `
    -PassThru

$proc.Id | Out-File -FilePath $pidFile -Encoding ascii -NoNewline
Write-Host "RAG server started (PID $($proc.Id)), logging to data\rag_server.log"
