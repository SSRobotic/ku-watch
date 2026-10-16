param([string]$File='output/ppt_academic_20261016/build/media_candidate.pptx')
$ErrorActionPreference='Stop'
$path=(Resolve-Path -LiteralPath $File).Path
$app=$null;$deck=$null;$show=$null;$results=@()
try {
 $app=New-Object -ComObject PowerPoint.Application
 $deck=$app.Presentations.Open($path,-1,0,-1)
 $settings=$deck.SlideShowSettings
 $settings.ShowType=2
 $settings.ShowMediaControls=-1
 $show=$settings.Run()
 $show.Left=25;$show.Top=25;$show.Width=640;$show.Height=390
 for($n=1;$n -le $deck.Slides.Count;$n++) {
  $slide=$deck.Slides.Item($n)
  foreach($shape in $slide.Shapes) {
   if($shape.Name -like 'VIDEO_*') {
    $show.View.GotoSlide($n,0)
    Start-Sleep -Milliseconds 400
    $player=$show.View.Player($shape.Id)
    $player.CurrentPosition=0
    $player.Play()
    Start-Sleep -Milliseconds 1400
    $position=[int]$player.CurrentPosition
    $state=[int]$player.State
    $player.Pause()
    $results+=@{slide=$n;shape=$shape.Name;position_ms=$position;state=$state;length_ms=$shape.MediaFormat.Length;passed=($position -gt 200)}
   }
  }
 }
 $report=@{file=$path;checked_utc=[DateTimeOffset]::UtcNow.ToString('o');method='Microsoft PowerPoint windowed Slide Show, actual embedded media Player.Play and advancing CurrentPosition';videos=$results;passed=(@($results | Where-Object {-not $_.passed}).Count -eq 0 -and $results.Count -eq 9)}
 $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath 'output/ppt_academic_20261016/build/playback_verified.json' -Encoding utf8
 $report | ConvertTo-Json -Depth 6
 if(-not $report.passed){throw 'A video did not advance during native playback'}
} finally {
 if($show){$show.View.Exit()}
 if($deck){$deck.Close()}
 if($app){$app.Quit();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)}
}
