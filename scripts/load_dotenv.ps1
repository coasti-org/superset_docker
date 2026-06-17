# Powershell
# Usage:   load_dotenv.ps1 /path/to/.env
# Check:   ls env:
# or       $env:VARIABLE_NAME

param(
    [Parameter(Mandatory=$true)]
    [string]$EnvFile
)

# Check if file exists
if (!(Test-Path $EnvFile)) {
    Write-Error "File '$EnvFile' does not exist."
    exit 1
}

# Read each line, skip comments and empty lines
Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    if ($_ -match '^\s*([^=]+)=(.*)$') {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim(' ', '"', "'")
        Set-Item -Path "env:$name" -Value $value
    }
}