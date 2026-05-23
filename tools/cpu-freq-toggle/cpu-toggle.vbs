' CPU Toggle - 한 파일로 50% ↔ 100% 토글
' 현재 값이 100% 이상이면 50%로, 아니면 100%로 자동 전환.
' 더블클릭만 하면 살치모드 ↔ 평소모드 왔다갔다.

Option Explicit

' 권한 상승 확인
If WScript.Arguments.Count = 0 Then
    Dim objShell
    Set objShell = CreateObject("Shell.Application")
    objShell.ShellExecute "wscript.exe", _
        Chr(34) & WScript.ScriptFullName & Chr(34) & " /elevated", _
        "", "runas", 0
    WScript.Quit
End If

Dim wsh, exec, output, line, current, target, label
Set wsh = CreateObject("WScript.Shell")

' 현재 AC 값 조회
Set exec = wsh.Exec("cmd /c powercfg /query SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX")
output = exec.StdOut.ReadAll()
current = 100  ' 기본값

' "현재 AC 전원 설정 인덱스" 또는 "Current AC Power Setting Index" 파싱
Dim re, matches, m
Set re = New RegExp
re.Pattern = "(?:AC \xc0\xfc\xbf\xf8 \xbc\xb3\xc1\xa4 \xc0\xce\xb5\xa5\xbd\xba|AC Power Setting Index)[^\r\n]*0x([0-9a-fA-F]+)"
re.IgnoreCase = True
Set matches = re.Execute(output)
If matches.Count > 0 Then
    current = CLng("&H" & matches(0).SubMatches(0))
End If

' 토글 로직: 100% 근처면 50%로, 아니면 100%로
If current >= 90 Then
    target = 50
    label = "살치 모드"
Else
    target = 100
    label = "고성능"
End If

Dim cmd
cmd = "cmd /c powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX " & target & _
      " && powercfg /setdcvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX " & target & _
      " && powercfg /setactive SCHEME_CURRENT"
wsh.Run cmd, 0, True

wsh.Popup current & "% → " & target & "% (" & label & ")", 2, "CPU Freq Toggle", 64
