Option Explicit
Dim fso, appRef, docRef, rootPath, aiPath, wasOpen, i
Set fso=CreateObject("Scripting.FileSystemObject")
rootPath=fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
aiPath=rootPath & "\outputs\ratking_run-001\ratking_run-001_edited.ai"
Set appRef=CreateObject("Illustrator.Application.30")
wasOpen=False
For i=1 To appRef.Documents.Count
    If LCase(CStr(appRef.Documents.Item(i).FullName))=LCase(aiPath) Then
        Set docRef=appRef.Documents.Item(i)
        wasOpen=True
        Exit For
    End If
Next
If Not wasOpen Then Set docRef=appRef.Open(aiPath)
WScript.Echo "OPENED " & docRef.Name & " LAYERS " & docRef.Layers.Count
If Not wasOpen Then docRef.Close 2
