param([Parameter(Mandatory=$true)][string]$Docx,[Parameter(Mandatory=$true)][string]$OutputDir)
$ErrorActionPreference='Stop'
$inputPath=(Resolve-Path -LiteralPath $Docx).Path
$outputPath=[IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputDir))
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null
$before=(Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash
$word=$null;$document=$null
try {
 $word=New-Object -ComObject Word.Application
 $word.Visible=$false;$word.DisplayAlerts=0;$word.AutomationSecurity=3
 $document=$word.Documents.Open($inputPath,$false,$true)
 $pageCount=$document.ComputeStatistics(2)
 $controls=@()
 foreach($control in $document.ContentControls){if($control.Type -eq 8){$controls+=@{tag=$control.Tag;checked=[bool]$control.Checked}}}
 $pdf=Join-Path $outputPath 'word-native.pdf'
 $document.ExportAsFixedFormat($pdf,17)
 $document.Close(0);$document=$null
 $after=(Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash
 if($after -ne $before){throw 'Rendering changed the evidence document'}
 $report=@{renderer='Microsoft Word native read-only PDF export';pages=$pageCount;checkbox_count=$controls.Count;checkboxes=$controls;docx_sha256=$after.ToLowerInvariant();docx_unchanged=$true;pdf=$pdf}
 $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputPath 'native_render.json') -Encoding utf8
 $report | ConvertTo-Json -Depth 5
} finally {
 if($document){$document.Close(0)}
 if($word){$word.Quit();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)}
}
