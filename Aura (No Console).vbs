' Minimal fallback launcher — prefer the .lnk (points at pythonw Aura.py)
Option Explicit
Dim sh, fso, dir, pyw, launcher, line
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = dir
launcher = dir & "\Aura.py"
pyw = ""
If fso.FileExists(dir & "\aura-pythonw.txt") Then
  line = Trim(fso.OpenTextFile(dir & "\aura-pythonw.txt", 1).ReadLine)
  If fso.FileExists(line) Then pyw = line
End If
If pyw = "" And fso.FileExists("C:\Python313\pythonw.exe") Then pyw = "C:\Python313\pythonw.exe"
If pyw = "" Then pyw = "pythonw"
sh.Run """" & pyw & """ """ & launcher & """", 1, False
