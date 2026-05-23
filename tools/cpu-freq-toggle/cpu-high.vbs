' CPU 100% (고성능, 평소 모드)
' 더블클릭하면 관리자 권한 요청 후 즉시 적용. 콘솔 창 안 뜸.

Option Explicit

Const PERCENT = 100
Const LABEL = "고성능"

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

wsh.Popup "CPU 최대 " & PERCENT & "% (" & LABEL & ")", 2, "CPU Freq Toggle", 64
