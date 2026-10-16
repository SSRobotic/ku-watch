$ErrorActionPreference='Stop'
$build=Join-Path (Get-Location).Path 'output/ppt_history_v2_20261016/build'
$file=(Resolve-Path -LiteralPath 'output/ppt_history_v2_20261016/deliverable/KU_Watch_นำเสนอพร้อมภาพพัฒนาการ_v2.pptx').Path
$app=$null;$deck=$null;$show=$null;$results=@();$links=@()
try {
 $app=New-Object -ComObject PowerPoint.Application
 $deck=$app.Presentations.Open($file,-1,0,-1)
 $ids=@{};foreach($slide in $deck.Slides){$ids[[string]$slide.SlideID]=$slide.SlideIndex}
 foreach($slide in $deck.Slides){foreach($shape in $slide.Shapes){
  if($shape.ActionSettings(1).Action -eq 7){
   $sub=[string]$shape.ActionSettings(1).Hyperlink.SubAddress
   if($sub){$parts=$sub.Split(',');$links+=@{slide=$slide.SlideIndex;shape=$shape.Name;target=$sub;valid=($ids.ContainsKey($parts[0]) -and [int]$ids[$parts[0]] -eq [int]$parts[1])}}
  }
 }}
 if(@($links | Where-Object {-not $_.valid}).Count){throw 'Broken internal hyperlink'}
 $settings=$deck.SlideShowSettings;$settings.ShowType=2;$settings.ShowMediaControls=-1
 $show=$settings.Run();$show.Left=25;$show.Top=25;$show.Width=640;$show.Height=390
 for($n=1;$n -le $deck.Slides.Count;$n++){
  foreach($shape in $deck.Slides.Item($n).Shapes){if($shape.Name -like 'VIDEO_*'){
   $show.View.GotoSlide($n,0);Start-Sleep -Milliseconds 400
   $player=$show.View.Player($shape.Id);$player.CurrentPosition=0;$player.Play();Start-Sleep -Milliseconds 1400
   $pos=[int]$player.CurrentPosition;$player.Pause()
   $results+=@{slide=$n;shape=$shape.Name;length_ms=$shape.MediaFormat.Length;position_ms=$pos;passed=($pos -gt 200)}
  }}
 }
 $report=@{file=$file;sha256=(Get-FileHash -LiteralPath $file).Hash.ToLower();checked_utc=[DateTimeOffset]::UtcNow.ToString('o');method='Native Microsoft PowerPoint windowed Slide Show; all 10 embedded videos played with advancing playheads; all internal hyperlink IDs resolved';links=$links;videos=$results;passed=($results.Count -eq 10 -and @($results | Where-Object {-not $_.passed}).Count -eq 0)}
 $report | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $build 'native_playback_verified.json') -Encoding utf8
 @{videos_tested=$results.Count;links_verified=$links.Count;passed=$report.passed} | ConvertTo-Json
 if(-not $report.passed){throw 'Video playback did not advance'}
} finally {if($show){$show.View.Exit()};if($deck){$deck.Close()};if($app){$app.Quit();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)}}
