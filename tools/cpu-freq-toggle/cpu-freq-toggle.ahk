#Requires AutoHotkey v2.0
; CPU Frequency Toggle - 갤럭시북이온2 / 윈도우용
; 메이플 라라 강줄기 50% 확률 입력 씹힘 회피용으로 CPU 다운클럭 토글
;
; 사용법:
;   - 단축키로 윈도우 전원 옵션의 "최대 프로세서 상태(%)"를 즉시 변경
;   - 관리자 권한 실행 필요 (powercfg 변경하려면)
;
; 단축키:
;   Ctrl + Alt + 1  →  저성능 모드  (CPU 50%) - 메이플 살치 모드
;   Ctrl + Alt + 2  →  보통 모드    (CPU 80%)
;   Ctrl + Alt + 3  →  고성능 모드  (CPU 100%) - 평소 모드
;   Ctrl + Alt + 0  →  현재 상태 표시
;   Ctrl + Alt + Q  →  종료

#SingleInstance Force

global currentMode := "?"

; 시작 시 관리자 권한 체크
if !A_IsAdmin {
    try {
        Run('*RunAs "' A_ScriptFullPath '"')
    } catch {
        MsgBox("관리자 권한이 필요합니다.`n우클릭 → 관리자 권한으로 실행 해주세요.", "권한 필요", 16)
    }
    ExitApp
}

; 트레이 아이콘 메뉴 구성
A_TrayMenu.Delete()
A_TrayMenu.Add("CPU 50% (살치모드)", (*) => SetCpuMax(50))
A_TrayMenu.Add("CPU 80% (보통)",    (*) => SetCpuMax(80))
A_TrayMenu.Add("CPU 100% (고성능)", (*) => SetCpuMax(100))
A_TrayMenu.Add()
A_TrayMenu.Add("현재 상태 확인", (*) => ShowCurrent())
A_TrayMenu.Add()
A_TrayMenu.Add("종료", (*) => ExitApp())
A_IconTip := "CPU Freq Toggle (Ctrl+Alt+1/2/3)"

; 시작 시 현재 상태 표시
ShowCurrent()

; 단축키 바인딩
^!1::SetCpuMax(50)
^!2::SetCpuMax(80)
^!3::SetCpuMax(100)
^!0::ShowCurrent()
^!q::ExitApp

SetCpuMax(percent) {
    global currentMode
    ; AC(충전기), DC(배터리) 양쪽 모두 설정
    RunWait('powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX ' percent, , "Hide")
    RunWait('powercfg /setdcvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX ' percent, , "Hide")
    RunWait('powercfg /setactive SCHEME_CURRENT', , "Hide")
    currentMode := percent "%"
    label := percent = 50 ? "살치 모드" : percent = 80 ? "보통" : percent = 100 ? "고성능" : "사용자"
    TrayTip("CPU " percent "% (" label ")", "CPU Freq Toggle", 1)
    A_IconTip := "CPU: " percent "% (" label ")"
}

ShowCurrent() {
    ; 현재 활성 전원 프로필의 PROCTHROTTLEMAX 조회
    tmpFile := A_Temp "\cpufreq_query.txt"
    RunWait(A_ComSpec ' /c powercfg /query SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX > "' tmpFile '"', , "Hide")
    if !FileExist(tmpFile) {
        TrayTip("상태 조회 실패", "CPU Freq Toggle", 3)
        return
    }
    text := FileRead(tmpFile)
    FileDelete(tmpFile)
    ac := dc := ""
    ; AC 값 (충전기)
    if RegExMatch(text, "현재 AC 전원 설정 인덱스:?\s*0x([0-9a-fA-F]+)", &m) ||
       RegExMatch(text, "Current AC Power Setting Index:?\s*0x([0-9a-fA-F]+)", &m)
        ac := Integer("0x" m[1])
    ; DC 값 (배터리)
    if RegExMatch(text, "현재 DC 전원 설정 인덱스:?\s*0x([0-9a-fA-F]+)", &m) ||
       RegExMatch(text, "Current DC Power Setting Index:?\s*0x([0-9a-fA-F]+)", &m)
        dc := Integer("0x" m[1])
    msg := "충전기: " (ac = "" ? "?" : ac "%") "  /  배터리: " (dc = "" ? "?" : dc "%")
    TrayTip(msg, "CPU Freq Toggle - 현재 상태", 1)
    A_IconTip := "CPU AC:" ac "% DC:" dc "%"
}
