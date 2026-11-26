Option Explicit
Dim fso, logFile, appRef, scriptPath, rootPath, logPath
Set fso = CreateObject("Scripting.FileSystemObject")
rootPath = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
logPath = rootPath & "\outputs\ratking_run-001\illustrator_run.log"
Set logFile = fso.OpenTextFile(logPath, 2, True)
logFile.WriteLine "START"
logFile.Close
Set appRef = CreateObject("Illustrator.Application.30")
Set logFile = fso.OpenTextFile(logPath, 8, True)
logFile.WriteLine "COM_CONNECTED " & appRef.Version
logFile.Close
If WScript.Arguments.Count > 0 Then
    scriptPath = Replace(rootPath, "\", "/") & "/" & Replace(WScript.Arguments.Item(0), "\", "/")
Else
    scriptPath = Replace(rootPath, "\", "/") & "/tools/render_ratking.jsx"
End If
appRef.DoJavaScript "$.evalFile(File('" & scriptPath & "'));"
Set logFile = fso.OpenTextFile(logPath, 8, True)
logFile.WriteLine "SCRIPT_RETURNED"
logFile.Close
