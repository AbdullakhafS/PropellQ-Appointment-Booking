$connections = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
$tcpPids = $connections | Select-Object -ExpandProperty OwningProcess -Unique

$apiPids = Get-Process -Name PropelIQ.Api -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty Id

$dotnetApiPids = Get-CimInstance Win32_Process -Filter "Name = 'dotnet.exe'" |
  Where-Object { $_.CommandLine -match 'PropelIQ\.Api' } |
  Select-Object -ExpandProperty ProcessId

$allPids = @($tcpPids + $apiPids + $dotnetApiPids) |
  Where-Object { $_ -and $_ -ne 0 } |
  Sort-Object -Unique

foreach ($procId in $allPids) {
  Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
}

# Extra fallback for stubborn hosted processes that can keep bin artifacts locked.
Get-CimInstance Win32_Process -Filter "Name = 'PropelIQ.Api.exe'" -ErrorAction SilentlyContinue |
  ForEach-Object { Invoke-CimMethod -InputObject $_ -MethodName Terminate -ErrorAction SilentlyContinue | Out-Null }

& taskkill /F /IM PropelIQ.Api.exe /T 2>$null | Out-Null
