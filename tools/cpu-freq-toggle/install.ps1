<#
.SYNOPSIS
    원격 설치 스크립트 — GUI 프로그램과 보조 파일들을 바탕화면에 자동 다운로드.

.EXAMPLE
    # PowerShell에서 (관리자 권한 불필요):
    irm https://raw.githubusercontent.com/tittue/cps-redirect/claude/goal-setting-UNUvb/tools/cpu-freq-toggle/install.ps1 | iex
#>

$ErrorActionPreference = "Stop"

$baseUrl = "https://raw.githubusercontent.com/tittue/cps-redirect/claude/goal-setting-UNUvb/tools/cpu-freq-toggle"
$dest    = Join-Path $env:USERPROFILE "Desktop\CPU 클럭 조절"

# GUI 버전 (메인) + 보조 VBS들
$files = @(
    "cpu_freq_gui.py",      # GUI 프로그램 본체
    "CPU 클럭 조절.vbs",     # 더블클릭 런처 (메인)
    "cpu-low.vbs",          # 보조: 50% 단일 적용
    "cpu-high.vbs",         # 보조: 100% 단일 적용
    "cpu-toggle.vbs",       # 보조: 50% <-> 100% 토글
    "README.md"
)

Write-Host ""
Write-Host " [CPU 클럭 조절 - 자동 설치]" -ForegroundColor Cyan
Write-Host " 대상: $dest" -ForegroundColor Gray
Write-Host ""

if (-not (Test-Path $dest)) {
    New-Item -ItemType Directory -Path $dest -Force | Out-Null
}

foreach ($file in $files) {
    # URL 인코딩 (한글 파일명 처리)
    $encoded = [uri]::EscapeDataString($file)
    $url     = "$baseUrl/$encoded"
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
Write-Host " [완료] 바탕화면에 'CPU 클럭 조절' 폴더가 생성되었습니다." -ForegroundColor Green
Write-Host ""
Write-Host " >> 사용법: 폴더 안의 'CPU 클럭 조절.vbs' 더블클릭" -ForegroundColor Yellow
Write-Host ""

# 폴더 자동으로 열기
Start-Process explorer.exe $dest
