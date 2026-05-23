' Python 버전 100% 래퍼
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
wsh.Run "pythonw.exe " & Chr(34) & pyPath & Chr(34) & " 100", 0, False
