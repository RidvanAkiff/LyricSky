Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
baseDir = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = baseDir

venvReady = baseDir & "\.venv\.ready"
venvPyw = baseDir & "\.venv\Scripts\pythonw.exe"
If fso.FileExists(venvReady) And fso.FileExists(venvPyw) Then
    pyw = """" & venvPyw & """"
Else
    pyw = "pythonw.exe"
End If

shell.Run pyw & " """ & baseDir & "\wallpaper.py""", 0, False
