$ErrorActionPreference = 'Stop'
try {
    $illustrator = [Runtime.InteropServices.Marshal]::GetActiveObject('Illustrator.Application')
    Write-Output ('ACTIVE ' + $illustrator.Version)
    Write-Output ('DOCUMENTS ' + $illustrator.Documents.Count)
} catch {
    Write-Output ('ERROR ' + $_.Exception.Message)
}
