param([switch]$AutoStart, [string]$RootOverride, [string]$PreviewPath, [string]$SnapshotPath, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$demoRoot = if ($RootOverride) { [IO.Path]::GetFullPath($RootOverride) } else { Split-Path -Parent $PSScriptRoot }
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$script:demoWorker = $null
$script:demoStatusPath = $null
$script:demoOpened = $false
$script:demoLastState = $null
$script:demoRunDir = $null
$script:demoStarting = $false
$script:demoStartedAt = $null
$script:demoSnapshotSaved = $false
$demoNodeCandidates = @((Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'), 'C:/Program Files/nodejs/node.exe')
$script:demoNode = $demoNodeCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
$demoGrafana = 'http://127.0.0.1:3000/d/ku-watch-live/ku-watch-e280a2-live-and-walk?from=now-15m&to=now&timezone=Asia%2FBangkok&refresh=1s&kiosk'
$demoDashboard = 'http://127.0.0.1:1880/dashboard/page1'
$demoMutex = $null
if (-not $PreviewPath) {
    $demoHash = [Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($demoRoot.ToLowerInvariant()))
    $demoKey = ([BitConverter]::ToString($demoHash)).Replace('-', '').Substring(0, 18)
    $demoMutex = New-Object Threading.Mutex($false, ('Local\KUWatchDemo-' + $demoKey))
    try { $demoOwnsMutex = $demoMutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $demoOwnsMutex = $true }
    if (-not $demoOwnsMutex) {
        [void][Windows.Forms.MessageBox]::Show('KU Watch Demo เปิดอยู่แล้วครับ ดูหน้าต่างเดิมที่แถบงานได้เลย', 'KU Watch Demo')
        $demoMutex.Dispose()
        exit 0
    }
}
function Demo-Color([string]$Hex) { [Drawing.ColorTranslator]::FromHtml($Hex) }
function Demo-Label([string]$Text, [float]$Size = 12, [bool]$Bold = $false) {
    $item = New-Object Windows.Forms.Label
    $item.Text = $Text
    $item.Font = New-Object Drawing.Font('Leelawadee UI', $Size, $(if ($Bold) { [Drawing.FontStyle]::Bold } else { [Drawing.FontStyle]::Regular }))
    $item.ForeColor = Demo-Color '#26364A'
    $item.AutoSize = $false
    $item.Dock = 'Fill'
    $item.TextAlign = 'MiddleLeft'
    return $item
}
function Demo-Button([string]$Text, [string]$Color = '#E9EFF4', [string]$Foreground = '#12304B') {
    $item = New-Object Windows.Forms.Button
    $item.Text = $Text
    $item.Font = New-Object Drawing.Font('Leelawadee UI', 11, [Drawing.FontStyle]::Bold)
    $item.BackColor = Demo-Color $Color
    $item.ForeColor = Demo-Color $Foreground
    $item.FlatStyle = 'Flat'
    $item.FlatAppearance.BorderSize = 0
    $item.Cursor = 'Hand'
    $item.Height = 44
    $item.Dock = 'Fill'
    $item.Margin = New-Object Windows.Forms.Padding(0, 0, 12, 0)
    return $item
}
function Demo-Open([string]$Target) {
    if ($NoBrowser) { return }
    try { Start-Process -FilePath $Target | Out-Null } catch { [void][Windows.Forms.MessageBox]::Show('เปิดรายการนี้ไม่ได้ครับ ใช้ปุ่มโฟลเดอร์สื่อเพื่อเปิดไฟล์โดยตรงได้', 'KU Watch Demo') }
}
function Demo-OpenDashboards {
    Demo-Open $demoDashboard
    Demo-Open $demoGrafana
    $script:demoOpened = $true
}
function Demo-Media {
    $candidates = @(
        (Join-Path $demoRoot 'submission/final-2026-10-20/START_HERE.html'),
        (Join-Path $demoRoot 'output/ppt_history_v2_20261016/deliverable/KU_Watch_พร้อมนำเสนอ_v2/ภาพและคลิป/เปิดดูภาพและคลิป.html'),
        (Join-Path $demoRoot 'output/slide_media_actual_20261016/เปิดดูภาพและคลิป.html'),
        (Join-Path $demoRoot 'สไลด์')
    )
    $target = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if ($target) { Demo-Open $target } else { Demo-Open $demoRoot }
}
function Demo-Evidence {
    $candidates = @((Join-Path $demoRoot 'output/demo_evidence/index.html'), (Join-Path $demoRoot 'submission/final-2026-10-20/04_Evidence/index.html'))
    $target = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if ($target) { Demo-Open $target }
    else { [void][Windows.Forms.MessageBox]::Show('ไม่พบหน้ารวมหลักฐานครับ ให้เปิด OPEN_EVIDENCE.cmd ในโฟลเดอร์โครงการ หรือติดตั้งหน้ารวมหลักฐานอีกครั้ง', 'KU Watch Evidence') }
}
function Demo-Start {
    if ($script:demoWorker -and -not $script:demoWorker.HasExited) { Demo-OpenDashboards; return }
    if (-not $script:demoNode) { $demoHeadline.Text = 'ไม่พบโปรแกรม Node.js'; $demoHint.Text = 'เปิดโครงการบนคอมที่ติดตั้งระบบ KU Watch ไว้ครับ'; return }
    $stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ', [Globalization.CultureInfo]::InvariantCulture)
    $script:demoRunDir = Join-Path $demoRoot ('output/demo_launcher/' + $stamp)
    [IO.Directory]::CreateDirectory($script:demoRunDir) | Out-Null
    $script:demoStatusPath = Join-Path $script:demoRunDir 'status.json'
    $arguments = @(
        ('"' + (Join-Path $demoRoot 'tools/demo_runtime.cjs') + '"'),
        '--start', '--root', ('"' + $demoRoot + '"'),
        '--run-dir', ('"' + $script:demoRunDir + '"')
    )
    $script:demoWorker = Start-Process -FilePath $script:demoNode -ArgumentList $arguments -WorkingDirectory $demoRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $script:demoRunDir 'console.stdout.log') -RedirectStandardError (Join-Path $script:demoRunDir 'console.stderr.log')
    $script:demoStarting = $true
    $script:demoStartedAt = [DateTime]::UtcNow
    $script:demoOpened = $false
    $demoStartButton.Text = 'กำลังเปิดระบบ…'
    $demoStartButton.Enabled = $false
    $demoHeadline.Text = 'กำลังเตรียม Demo'
    $demoHint.Text = 'กำลังเปิดบริการเดิม และตรวจข้อมูลล่าสุดจากนาฬิกา'
    $demoProgress.Style = 'Marquee'
}
function Demo-Refresh {
    if (-not $script:demoStatusPath -or -not (Test-Path -LiteralPath $script:demoStatusPath)) {
        if ($script:demoWorker -and $script:demoWorker.HasExited) { $demoHeadline.Text = 'เปิด Demo ไม่สำเร็จ'; $demoHint.Text = 'กดดูบันทึกเพื่อดูขั้นตอนที่ต้องตรวจ แล้วลองเปิดใหม่ครับ'; $demoStartButton.Enabled = $true; $demoStartButton.Text = 'ลองเปิด Demo อีกครั้ง'; $demoProgress.Style = 'Blocks' }
        return
    }
    try { $state = Get-Content -Raw -LiteralPath $script:demoStatusPath -Encoding UTF8 | ConvertFrom-Json } catch { return }
    $script:demoLastState = $state
    foreach ($id in @('influx', 'queue', 'node_red', 'grafana')) {
        $row = $state.services.$id
        if ($row -and $row.ready) { $demoCards[$id].Text = 'พร้อมใช้งาน'; $demoCards[$id].ForeColor = Demo-Color '#07856E' }
        elseif ($row -and $row.http -in @(401, 403)) { $demoCards[$id].Text = 'รอลงชื่อเข้าใช้'; $demoCards[$id].ForeColor = Demo-Color '#A56514' }
        else { $demoCards[$id].Text = $(if ($state.phase -eq 'starting') { 'กำลังตรวจ…' } else { 'ยังไม่พร้อม' }); $demoCards[$id].ForeColor = Demo-Color '#A56514' }
    }
    if ($state.demo_ready) {
        $demoHeadline.Text = 'พร้อม Demo • มีข้อมูลจริงเข้าระบบ'
        $demoHeadline.ForeColor = Demo-Color '#07856E'
        $demoHint.Text = 'เปิดแดชบอร์ดแล้ว ลองเปลี่ยนหน้า ขยับอุปกรณ์ หรือวางนิ้วเพื่อสาธิตได้เลย'
    } elseif ($state.backend_ready) {
        $demoHeadline.Text = 'ระบบพร้อม • รอข้อมูลจากนาฬิกา'
        $demoHeadline.ForeColor = Demo-Color '#A56514'
        $demoHint.Text = $(if ($state.mqtt.clock_warning) { 'ได้รับข้อความแล้ว แต่เวลาอุปกรณ์คลาดเคลื่อน กรุณาตรวจเวลาบนนาฬิกา' } elseif ($state.mqtt.fresh -and -not $state.database.fresh) { 'รับ MQTT ใหม่แล้ว กำลังรอยืนยันว่าบันทึกลงฐานข้อมูลได้' } else { 'เปิดตัวเล็กกับจอใหญ่ และฮอตสปอต SS แบบ 2.4 GHz ค้างไว้ครับ' })
    } elseif ($state.phase -eq 'starting') {
        $demoHeadline.Text = 'กำลังเตรียม Demo'
        $demoHint.Text = 'รอแต่ละบริการพร้อม ระบบจะเปิดแดชบอร์ดให้โดยอัตโนมัติ'
    } else {
        $demoHeadline.Text = 'มีบางส่วนยังไม่พร้อม'
        $demoHeadline.ForeColor = Demo-Color '#B45332'
        $demoHint.Text = 'ดูสถานะแต่ละส่วนด้านล่าง ระหว่างนี้เปิดคลิปสำรองได้ครับ'
    }
    if ($state.phase -eq 'error' -or ($script:demoWorker -and $script:demoWorker.HasExited)) {
        $demoHeadline.Text = 'ตัวเปิด Demo หยุดทำงาน'
        $demoHint.Text = 'บริการที่เปิดไว้ยังอยู่ กดดูบันทึกหรือลองเปิด Demo ใหม่ได้ครับ'
    }
    $demoMqttText.Text = $(if ($state.mqtt.fresh) { 'รับข้อมูลจริง: ' + $state.mqtt.live_count + ' ข้อความในรอบนี้' } elseif ($state.mqtt.connected) { 'MQTT เชื่อมต่อแล้ว • ยังไม่มีข้อมูลใหม่' } else { 'MQTT: รอการเชื่อมต่ออินเทอร์เน็ต' })
    $demoDbText.Text = $(if ($state.database.fresh) { 'ฐานข้อมูล: มีข้อมูลใหม่ • ' + $state.database.recent_rows + ' แถวใน 5 นาที' } elseif ($state.database.available) { 'ฐานข้อมูล: เปิดได้ • ยังไม่มีข้อมูลล่าสุด' } else { 'ฐานข้อมูล: กำลังตรวจการบันทึก' })
    try { $tz = [TimeZoneInfo]::FindSystemTimeZoneById('SE Asia Standard Time'); $thai = [TimeZoneInfo]::ConvertTimeFromUtc([DateTime]::Parse($state.updated_utc).ToUniversalTime(), $tz); $demoClock.Text = 'ตรวจล่าสุด ' + $thai.ToString('HH:mm:ss') + ' น.' } catch {}
    if ($state.backend_ready -and -not $script:demoOpened -and $demoAutoOpen.Checked) { Demo-OpenDashboards }
    if ($state.phase -ne 'starting') {
        $demoProgress.Style = 'Blocks'
        $demoProgress.Value = $(if ($state.demo_ready) { 100 } elseif ($state.backend_ready) { 80 } else { 30 })
        $demoStartButton.Enabled = $true
        $demoStartButton.Text = $(if ($script:demoWorker -and -not $script:demoWorker.HasExited) { 'เปิดแดชบอร์ดอีกครั้ง' } else { 'ลองเปิด Demo อีกครั้ง' })
    }
}

$demoForm = New-Object Windows.Forms.Form
$demoForm.Text = 'KU Watch Demo'
$demoForm.ClientSize = New-Object Drawing.Size(1010, 690)
$demoForm.MinimumSize = New-Object Drawing.Size(940, 720)
$demoForm.StartPosition = 'CenterScreen'
$demoForm.AutoScaleMode = 'Dpi'
$demoForm.BackColor = Demo-Color '#F2F5F8'
$demoForm.Font = New-Object Drawing.Font('Leelawadee UI', 11)
$demoForm.Icon = [Drawing.SystemIcons]::Application
$demoLayout = New-Object Windows.Forms.TableLayoutPanel
$demoLayout.Dock = 'Fill'; $demoLayout.ColumnCount = 1; $demoLayout.RowCount = 8
foreach ($height in @(93, 66, 112, 111, 69, 63, 105, 66)) { [void]$demoLayout.RowStyles.Add((New-Object Windows.Forms.RowStyle('Absolute', $height))) }
$demoForm.Controls.Add($demoLayout)
$demoHeader = New-Object Windows.Forms.Panel
$demoHeader.Dock = 'Fill'; $demoHeader.Margin = New-Object Windows.Forms.Padding(0); $demoHeader.BackColor = Demo-Color '#122D46'; $demoHeader.Padding = New-Object Windows.Forms.Padding(30, 12, 30, 10)
$demoTitle = Demo-Label 'KU WATCH' 24 $true; $demoTitle.ForeColor = [Drawing.Color]::White; $demoTitle.Dock = 'Top'; $demoTitle.Height = 43
$demoSub = Demo-Label 'P R E S E N T A T I O N   C O N T R O L' 9; $demoSub.ForeColor = Demo-Color '#93B7CF'; $demoSub.Dock = 'Bottom'; $demoSub.Height = 22
$demoHeader.Controls.Add($demoTitle); $demoHeader.Controls.Add($demoSub); $demoLayout.Controls.Add($demoHeader, 0, 0)
$demoIntro = Demo-Label 'เสียบตัวเล็กและจอใหญ่ • เปิดฮอตสปอต SS 2.4 GHz • คอมเชื่อมอินเทอร์เน็ต' 12
$demoIntro.Margin = New-Object Windows.Forms.Padding(30, 8, 30, 0); $demoLayout.Controls.Add($demoIntro, 0, 1)
$demoStatusPanel = New-Object Windows.Forms.Panel
$demoStatusPanel.Dock = 'Fill'; $demoStatusPanel.Margin = New-Object Windows.Forms.Padding(30, 0, 30, 8); $demoStatusPanel.Padding = New-Object Windows.Forms.Padding(20, 13, 20, 10); $demoStatusPanel.BackColor = [Drawing.Color]::White
$demoHeadline = Demo-Label 'เริ่ม Demo ได้ในปุ่มเดียว' 19 $true; $demoHeadline.Dock = 'Top'; $demoHeadline.Height = 40
$demoHint = Demo-Label 'เปิดระบบเดิม ตรวจข้อมูลจริง และเปิดแดชบอร์ดที่ใช้สาธิตให้พร้อม' 10.5; $demoHint.Dock = 'Fill'
$demoStatusPanel.Controls.Add($demoHint); $demoStatusPanel.Controls.Add($demoHeadline); $demoLayout.Controls.Add($demoStatusPanel, 0, 2)
$demoCardPanel = New-Object Windows.Forms.TableLayoutPanel
$demoCardPanel.Dock = 'Fill'; $demoCardPanel.ColumnCount = 4; $demoCardPanel.RowCount = 1; $demoCardPanel.Margin = New-Object Windows.Forms.Padding(30, 8, 18, 10)
$demoCards = @{}
$cardNames = [ordered]@{ grafana = 'GRAFANA'; node_red = 'NODE-RED'; influx = 'INFLUXDB'; queue = 'DATA STORAGE' }
$i = 0
foreach ($key in $cardNames.Keys) {
    [void]$demoCardPanel.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Percent', 25)))
    $card = New-Object Windows.Forms.Panel; $card.Dock = 'Fill'; $card.Margin = New-Object Windows.Forms.Padding(0, 0, 12, 0); $card.Padding = New-Object Windows.Forms.Padding(16, 10, 8, 8); $card.BackColor = [Drawing.Color]::White
    $name = Demo-Label $cardNames[$key] 10 $true; $name.Dock = 'Top'; $name.Height = 27; $name.ForeColor = Demo-Color '#6B7C90'
    $value = Demo-Label 'รอเริ่ม Demo' 12 $true; $value.Dock = 'Fill'; $demoCards[$key] = $value
    $card.Controls.Add($value); $card.Controls.Add($name); $demoCardPanel.Controls.Add($card, $i, 0); $i++
}
$demoLayout.Controls.Add($demoCardPanel, 0, 3)
$demoFacts = New-Object Windows.Forms.TableLayoutPanel
$demoFacts.ColumnCount = 2; $demoFacts.RowCount = 2; $demoFacts.Dock = 'Fill'; $demoFacts.Margin = New-Object Windows.Forms.Padding(34, 0, 34, 0)
[void]$demoFacts.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Percent', 72))); [void]$demoFacts.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Percent', 28)))
$demoMqttText = Demo-Label 'MQTT: ตรวจเมื่อเริ่ม Demo' 10.5; $demoDbText = Demo-Label 'ฐานข้อมูล: ตรวจเมื่อเริ่ม Demo' 10.5; $demoClock = Demo-Label 'ข้อมูลสดจะแสดงเมื่ออุปกรณ์ส่งจริง' 9
$demoClock.TextAlign = 'MiddleRight'; $demoClock.ForeColor = Demo-Color '#718095'
$demoFacts.Controls.Add($demoMqttText, 0, 0); $demoFacts.Controls.Add($demoDbText, 0, 1); $demoFacts.Controls.Add($demoClock, 1, 0); $demoFacts.SetRowSpan($demoClock, 2); $demoLayout.Controls.Add($demoFacts, 0, 4)
$demoStartRow = New-Object Windows.Forms.TableLayoutPanel
$demoStartRow.Dock = 'Fill'; $demoStartRow.ColumnCount = 2; $demoStartRow.Margin = New-Object Windows.Forms.Padding(30, 6, 30, 6)
[void]$demoStartRow.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Percent', 55))); [void]$demoStartRow.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Percent', 45)))
$demoStartButton = Demo-Button 'เริ่ม Demo' '#07856E' '#FFFFFF'; $demoStartButton.Font = New-Object Drawing.Font('Leelawadee UI', 15, [Drawing.FontStyle]::Bold); $demoStartButton.Add_Click({ Demo-Start })
$demoAutoOpen = New-Object Windows.Forms.CheckBox; $demoAutoOpen.Text = 'เปิดแดชบอร์ดอัตโนมัติเมื่อระบบพร้อม'; $demoAutoOpen.Checked = $true; $demoAutoOpen.Dock = 'Fill'; $demoAutoOpen.Margin = New-Object Windows.Forms.Padding(16, 0, 0, 0); $demoAutoOpen.Font = New-Object Drawing.Font('Leelawadee UI', 10)
$demoStartRow.Controls.Add($demoStartButton, 0, 0); $demoStartRow.Controls.Add($demoAutoOpen, 1, 0); $demoLayout.Controls.Add($demoStartRow, 0, 5)
$demoLinksRow = New-Object Windows.Forms.TableLayoutPanel
$demoLinksRow.ColumnCount = 5; $demoLinksRow.Dock = 'Fill'; $demoLinksRow.Margin = New-Object Windows.Forms.Padding(30, 10, 18, 6)
foreach ($column in 0..4) { [void]$demoLinksRow.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Percent', 20))) }
$demoEvidenceButton = Demo-Button 'หลักฐาน FR-01–08' '#15344E' '#FFFFFF'; $demoEvidenceButton.Add_Click({ Demo-Evidence })
$demoGraphButton = Demo-Button 'Grafana'; $demoGraphButton.Add_Click({ Demo-Open $demoGrafana })
$demoNodeButton = Demo-Button 'Node-RED'; $demoNodeButton.Add_Click({ Demo-Open $demoDashboard })
$demoMediaButton = Demo-Button 'ภาพ / คลิปสำรอง'; $demoMediaButton.Add_Click({ Demo-Media })
$demoLogButton = Demo-Button 'บันทึกรอบนี้'; $demoLogButton.Add_Click({ if ($script:demoRunDir) { Demo-Open $script:demoRunDir } else { Demo-Open $demoRoot } })
$demoLinksRow.Controls.Add($demoEvidenceButton, 0, 0); $demoLinksRow.Controls.Add($demoGraphButton, 1, 0); $demoLinksRow.Controls.Add($demoNodeButton, 2, 0); $demoLinksRow.Controls.Add($demoMediaButton, 3, 0); $demoLinksRow.Controls.Add($demoLogButton, 4, 0); $demoLayout.Controls.Add($demoLinksRow, 0, 6)
$demoFooter = New-Object Windows.Forms.Panel; $demoFooter.Dock = 'Fill'; $demoFooter.Margin = New-Object Windows.Forms.Padding(30, 0, 30, 10)
$demoProgress = New-Object Windows.Forms.ProgressBar; $demoProgress.Dock = 'Top'; $demoProgress.Height = 5; $demoProgress.Style = 'Blocks'
$demoFootnote = Demo-Label 'ปิดหน้าต่างนี้แล้วระบบเบื้องหลังยังทำงานต่อ • หาก Grafana ถาม ให้ลงชื่อเข้าใช้บัญชีเดิม' 9; $demoFootnote.Dock = 'Fill'; $demoFootnote.ForeColor = Demo-Color '#718095'
$demoFooter.Controls.Add($demoFootnote); $demoFooter.Controls.Add($demoProgress); $demoLayout.Controls.Add($demoFooter, 0, 7)
$demoTimer = New-Object Windows.Forms.Timer
$demoTimer.Interval = 700
$demoTimer.Add_Tick({
    Demo-Refresh
    if ($SnapshotPath -and -not $script:demoSnapshotSaved -and $script:demoLastState -and $script:demoLastState.phase -ne 'starting') {
        $snapshot = New-Object Drawing.Bitmap($demoForm.Width, $demoForm.Height)
        try { $demoForm.DrawToBitmap($snapshot, (New-Object Drawing.Rectangle(0, 0, $snapshot.Width, $snapshot.Height))); $snapshot.Save($SnapshotPath, [Drawing.Imaging.ImageFormat]::Png); $script:demoSnapshotSaved = $true } finally { $snapshot.Dispose() }
    }
})
$demoForm.Add_Shown({ $demoTimer.Start(); if ($AutoStart) { Demo-Start } })
$demoForm.Add_FormClosing({
    $demoTimer.Stop()
    # Only the launcher observer exits; services and soak collection stay running.
    if ($script:demoWorker -and -not $script:demoWorker.HasExited) { try { $script:demoWorker.Kill() } catch {} }
})
try {
    if ($PreviewPath) {
        $demoForm.Show()
        [Windows.Forms.Application]::DoEvents()
        $demoForm.PerformLayout()
        $bitmap = New-Object Drawing.Bitmap($demoForm.Width, $demoForm.Height)
        try { $demoForm.DrawToBitmap($bitmap, (New-Object Drawing.Rectangle(0, 0, $bitmap.Width, $bitmap.Height))); $bitmap.Save($PreviewPath, [Drawing.Imaging.ImageFormat]::Png) } finally { $bitmap.Dispose(); $demoForm.Close() }
    } else { [void]$demoForm.ShowDialog() }
} finally {
    $demoTimer.Dispose(); $demoForm.Dispose()
    if ($demoMutex) { try { $demoMutex.ReleaseMutex() } catch {}; $demoMutex.Dispose() }
}
