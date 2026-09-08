' VBScript to run Adult Content Blocker silently in the background without a CMD window
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Ensure working directory is set to script directory
WshShell.CurrentDirectory = scriptDir

exePath = scriptDir & "\WindowsSecurityShield.exe"
guardianExePath = scriptDir & "\WindowsSecurityGuardian.exe"

If fso.FileExists(exePath) Then
    ' Run compiled standalone executable
    WshShell.Run """" & exePath & """", 0, False
Else
    ' Fallback to pythonw.exe with blocker.py silently
    WshShell.Run "pythonw.exe """ & scriptDir & "\blocker.py""", 0, False
End If
