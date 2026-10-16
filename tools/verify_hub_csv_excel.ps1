param([Parameter(Mandatory=$true)][string]$CsvPath,[Parameter(Mandatory=$true)][string]$ReportPath)
$ErrorActionPreference='Stop'
$resolvedCsv=(Resolve-Path -LiteralPath $CsvPath).Path
$beforeHash=(Get-FileHash -LiteralPath $resolvedCsv -Algorithm SHA256).Hash
$excel=$null; $workbook=$null; $sheet=$null
try {
    $excel=New-Object -ComObject Excel.Application
    $excel.Visible=$false; $excel.DisplayAlerts=$false; $excel.EnableEvents=$false; $excel.AutomationSecurity=3
    # Read-only with explicit comma delimiter. The captured file is never saved.
    $workbook=$excel.Workbooks.Open($resolvedCsv,0,$true,2)
    $sheet=$workbook.Worksheets.Item(1)
    $used=$sheet.UsedRange
    $report=[ordered]@{
        checked_utc=[DateTime]::UtcNow.ToString('o')
        tool='Microsoft Excel COM - actual CSV opened read-only'
        excel_version=$excel.Version
        file=$resolvedCsv
        rows_including_header=$used.Rows.Count
        columns=$used.Columns.Count
        first_header=$sheet.Cells.Item(1,1).Text
        last_header=$sheet.Cells.Item(1,26).Text
        first_rtc_utc=$sheet.Cells.Item(2,1).Value2
        sha256=$beforeHash.ToLowerInvariant()
        passed=($used.Columns.Count -eq 26 -and $used.Rows.Count -gt 1 -and $sheet.Cells.Item(1,1).Text -eq 'rtc_utc' -and $sheet.Cells.Item(1,26).Text -eq 'hub_fw')
    }
    $workbook.Close($false); $workbook=$null
    $afterHash=(Get-FileHash -LiteralPath $resolvedCsv -Algorithm SHA256).Hash
    if($afterHash -ne $beforeHash){throw 'Read-only validation changed the evidence file'}
    $report.file_unchanged=$true
    $report | ConvertTo-Json | Set-Content -LiteralPath $ReportPath -Encoding utf8
    $report | ConvertTo-Json
} finally {
    if($workbook){$workbook.Close($false)}
    if($excel){$excel.Quit()}
    if($sheet){[void][Runtime.InteropServices.Marshal]::ReleaseComObject($sheet)}
    if($excel){[void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)}
}
