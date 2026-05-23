<#
.SYNOPSIS
    윈도우 전원 옵션의 "최대 프로세서 상태(%)"를 변경합니다.

.DESCRIPTION
    powercfg를 이용해 AC(충전기)/DC(배터리) 양쪽 모두 동일한 값으로 설정한 뒤,
    현재 활성 프로필을 다시 적용해서 즉시 반영합니다.
    관리자 권한이 필요합니다.

.PARAMETER Percent
    설정할 최대 프로세서 상태 (1~100). 기본값 100.

.EXAMPLE
    .\Set-CpuMax.ps1 -Percent 50
    CPU 최대치를 50%로 다운클럭. 메이플 라라 살치 모드.

.EXAMPLE
    .\Set-CpuMax.ps1 -Percent 100
    원래대로 100% 풀파워.
#>
[CmdletBinding()]
param(
    [ValidateRange(1, 100)]
    [int]$Percent = 100
)

# 관리자 권한 확인
$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent() `
    ).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[!] 관리자 권한으로 다시 실행합니다..." -ForegroundColor Yellow
    $args = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Percent $Percent"
    Start-Process powershell -Verb RunAs -ArgumentList $args
    exit
}

# 현재 값 조회 (변경 전)
function Get-CurrentMax {
    $out = powercfg /query SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX 2>&1
    $ac = $null; $dc = $null
    foreach ($line in $out) {
        if ($line -match '(?:현재 AC 전원 설정 인덱스|Current AC Power Setting Index):?\s*0x([0-9a-fA-F]+)') {
            $ac = [Convert]::ToInt32($matches[1], 16)
        }
        if ($line -match '(?:현재 DC 전원 설정 인덱스|Current DC Power Setting Index):?\s*0x([0-9a-fA-F]+)') {
            $dc = [Convert]::ToInt32($matches[1], 16)
        }
    }
    return [PSCustomObject]@{ AC = $ac; DC = $dc }
}

$before = Get-CurrentMax
Write-Host "변경 전: AC $($before.AC)% / DC $($before.DC)%" -ForegroundColor Cyan

# 설정 변경
powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX $Percent | Out-Null
powercfg /setdcvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX $Percent | Out-Null
powercfg /setactive SCHEME_CURRENT | Out-Null

$after = Get-CurrentMax
$mode = switch ($Percent) {
    { $_ -le 50 }  { "살치 모드" }
    { $_ -le 80 }  { "보통" }
    { $_ -le 100 } { "고성능" }
}
Write-Host "[OK] CPU 최대 $Percent% 적용 완료. ($mode)" -ForegroundColor Green
Write-Host "변경 후: AC $($after.AC)% / DC $($after.DC)%" -ForegroundColor Green
