' "CPU 클럭 조절.vbs" — 더블클릭으로 GUI 실행
' Python GUI를 콘솔 창 없이 실행. 같은 폴더의 cpu_freq_gui.py를 호출.

Option Explicit

Dim fso, scriptDir, pyPath
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
pyPath = scriptDir & "\cpu_freq_gui.py"

If Not fso.FileExists(pyPath) Then
    MsgBox "cpu_freq_gui.py 파일을 찾을 수 없습니다." & vbCrLf & vbCrLf & _
           "이 VBS 파일과 같은 폴더에 cpu_freq_gui.py가 있어야 합니다." & vbCrLf & _
           "현재 경로: " & pyPath, 16, "CPU 클럭 조절"
    WScript.Quit 1
End If

Dim wsh
Set wsh = CreateObject("WScript.Shell")
' pythonw.exe = 콘솔 없는 파이썬. GUI라 콘솔 필요 없음.
' 관리자 권한 상승은 Python 스크립트 내부에서 처리.
wsh.Run "pythonw.exe " & Chr(34) & pyPath & Chr(34), 1, False
