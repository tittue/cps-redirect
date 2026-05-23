' CPU 50% (살치 모드) - 메이플 라라 강줄기용
' 더블클릭하면 관리자 권한 요청 후 즉시 적용. 콘솔 창 안 뜸.
' 키보드 후킹 없음 → 게임 안티치트 안전.

Option Explicit

Const PERCENT = 50
Const LABEL = "살치 모드"

' 권한 상승 확인용 인자
If WScript.Arguments.Count = 0 Then
    Dim objShell
    Set objShell = CreateObject("Shell.Application")
    objShell.ShellExecute "wscript.exe", _
        Chr(34) & WScript.ScriptFullName & Chr(34) & " /elevated", _
        "", "runas", 0
    WScript.Quit
End If

Dim wsh, cmd
Set wsh = CreateObject("WScript.Shell")
cmd = "cmd /c powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX " & PERCENT & _
      " && powercfg /setdcvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX " & PERCENT & _
      " && powercfg /setactive SCHEME_CURRENT"
wsh.Run cmd, 0, True

' 2초간 자동으로 닫히는 알림
wsh.Popup "CPU 최대 " & PERCENT & "% (" & LABEL & ")", 2, "CPU Freq Toggle", 64
