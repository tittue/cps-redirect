' Python 버전을 콘솔 창 없이 실행하는 VBS 래퍼 (50%)
' 같은 폴더의 cpu_freq.py를 호출함. 파이썬이 설치돼 있어야 함.

Option Explicit

Dim fso, scriptDir, pyPath
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
pyPath = scriptDir & "\cpu_freq.py"

If Not fso.FileExists(pyPath) Then
    MsgBox "cpu_freq.py를 찾을 수 없습니다." & vbCrLf & pyPath, 16, "CPU Freq Toggle"
    WScript.Quit 1
End If

Dim wsh
Set wsh = CreateObject("WScript.Shell")
' pythonw.exe로 콘솔 창 없이 실행 (관리자 권한 상승은 파이썬 스크립트가 처리)
wsh.Run "pythonw.exe " & Chr(34) & pyPath & Chr(34) & " 50", 0, False
