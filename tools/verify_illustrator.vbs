Option Explicit
Dim fso, appRef, docRef, rootPath, aiPath
Set fso=CreateObject("Scripting.FileSystemObject")
rootPath=fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
aiPath=rootPath & "\outputs\ratking_run-001\ratking_run-001_edited.ai"
Set appRef=CreateObject("Illustrator.Application.30")
Set docRef=appRef.Open(aiPath)
WScript.Echo "OPENED " & docRef.Name & " LAYERS " & docRef.Layers.Count
docRef.Close 2
