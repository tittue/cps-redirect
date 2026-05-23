<#
.SYNOPSIS
    원격 설치 스크립트 — VBS 파일들을 바탕화면에 자동 다운로드.

.DESCRIPTION
    PowerShell 한 줄로 모든 VBS 파일을 GitHub에서 받아 바탕화면 폴더에 배치.

.EXAMPLE
    # PowerShell에서 (관리자 권한 불필요, 파일 다운로드만):
    irm https://raw.githubusercontent.com/tittue/cps-redirect/claude/goal-setting-UNUvb/tools/cpu-freq-toggle/install.ps1 | iex
#>

$ErrorActionPreference = "Stop"

$baseUrl = "https://raw.githubusercontent.com/tittue/cps-redirect/claude/goal-setting-UNUvb/tools/cpu-freq-toggle"
$dest    = Join-Path $env:USERPROFILE "Desktop\CPU Freq Toggle"

$files = @(
    "cpu-low.vbs",
    "cpu-mid.vbs",
    "cpu-high.vbs",
    "cpu-toggle.vbs",
    "README.md"
)

Write-Host ""
Write-Host " [CPU Freq Toggle - 자동 설치]" -ForegroundColor Cyan
Write-Host " 대상: $dest" -ForegroundColor Gray
Write-Host ""

if (-not (Test-Path $dest)) {
    New-Item -ItemType Directory -Path $dest -Force | Out-Null
}

foreach ($file in $files) {
    $url     = "$baseUrl/$file"
    $outPath = Join-Path $dest $file
    Write-Host "  - $file " -NoNewline
    try {
        Invoke-WebRequest -Uri $url -OutFile $outPath -UseBasicParsing
        Write-Host "OK" -ForegroundColor Green
    } catch {
        Write-Host "실패: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host " [완료] 바탕화면의 'CPU Freq Toggle' 폴더를 확인하세요." -ForegroundColor Green
Write-Host ""
Write-Host " 사용법:" -ForegroundColor Yellow
Write-Host "   * cpu-low.vbs    - CPU 50% (살치 모드)"
Write-Host "   * cpu-high.vbs   - CPU 100% (평소 모드)"
Write-Host "   * cpu-toggle.vbs - 50% <-> 100% 자동 토글"
Write-Host ""

# 바탕화면 폴더 자동으로 열기
Start-Process explorer.exe $dest
