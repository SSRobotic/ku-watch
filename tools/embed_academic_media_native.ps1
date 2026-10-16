param([string]$Candidate='output/ppt_academic_20261016/build/artifact_candidate.pptx',[string]$Output='output/ppt_academic_20261016/build/media_candidate.pptx',[string]$RenderDir='output/ppt_academic_20261016/build/native_render')
$ErrorActionPreference='Stop'
$root=(Get-Location).Path
$source=(Resolve-Path -LiteralPath $Candidate).Path
$target=[IO.Path]::GetFullPath((Join-Path $root $Output))
$renders=[IO.Path]::GetFullPath((Join-Path $root $RenderDir))
New-Item -ItemType Directory -Force -Path $renders | Out-Null
$plan=Get-Content -LiteralPath 'output/ppt_academic_20261016/build/deck_plan.json' -Raw | ConvertFrom-Json
$app=$null;$deck=$null;$mediaReport=@();$overflow=@()
try {
 $app=New-Object -ComObject PowerPoint.Application
 $deck=$app.Presentations.Open($source,0,0,0)
 foreach($job in $plan.videos){
  $slide=$deck.Slides.Item([int]$job.slide)
  $media=$slide.Shapes.AddMediaObject2([string]$job.file,0,-1,[single]($job.left*.75),[single]($job.top*.75))
  $media.Name='VIDEO_'+$job.id
  $media.LockAspectRatio=-1
  $naturalW=$media.Width;$naturalH=$media.Height
  $scale=[Math]::Min(($job.width*.75)/$naturalW,($job.height*.75)/$naturalH)
  $media.Width=[single]($naturalW*$scale)
  $media.Left=[single]($job.left*.75+($job.width*.75-$media.Width)/2)
  $media.Top=[single]($job.top*.75+($job.height*.75-$media.Height)/2)
  $posterSet=$false
  try{$media.MediaFormat.SetDisplayPictureFromFile([string]$job.poster);$posterSet=$true}catch{}
  $media.AnimationSettings.PlaySettings.PlayOnEntry=0
  $media.AnimationSettings.PlaySettings.LoopUntilStopped=0
  for($j=$slide.Shapes.Count;$j -ge 1;$j--){if($slide.Shapes.Item($j).Name -eq ('media-poster-'+$job.id)){$slide.Shapes.Item($j).Delete()}}
  $mediaReport+=@{slide=$job.slide;id=$job.id;source=$job.file;poster_set=$posterSet;length_ms=$media.MediaFormat.Length;width=$media.Width;height=$media.Height;embedded=$true}
 }
 foreach($link in $plan.links){
  $shape=$deck.Slides.Item([int]$link.slide).Shapes.Item([string]$link.shapeName)
  $destination=$deck.Slides.Item([int]$link.targetSlide)
  $shape.ActionSettings(1).Action=7
  $shape.ActionSettings(1).Hyperlink.SubAddress=([string]$destination.SlideID+','+[string]$link.targetSlide+',Slide '+[string]$link.targetSlide)
 }
 for($n=1;$n -le $deck.Slides.Count;$n++){
  $slide=$deck.Slides.Item($n)
  $slide.SlideShowTransition.Hidden=if($n -gt 14){-1}else{0}
  foreach($shape in $slide.Shapes){
   if($shape.HasTextFrame -eq -1 -and $shape.TextFrame2.HasText -eq -1){
    try{if($shape.TextFrame2.TextRange.BoundHeight -gt $shape.Height+5){$overflow+=@{slide=$n;shape=$shape.Name;text=$shape.TextFrame2.TextRange.Text;bound_height=$shape.TextFrame2.TextRange.BoundHeight;shape_height=$shape.Height}}}catch{}
   }
  }
 }
 $deck.SaveAs($target,24)
 for($n=1;$n -le $deck.Slides.Count;$n++){$deck.Slides.Item($n).Export((Join-Path $renders ('slide-{0:D2}.png' -f $n)),'PNG',1600,900)}
 $report=@{application='Microsoft PowerPoint native COM';slides=$deck.Slides.Count;main_slides=14;appendix_hidden=$deck.Slides.Count-14;embedded_videos=$mediaReport;links=$plan.links.Count;overflow=$overflow;rendered_all_slides=$true;candidate=$target}
 $report | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath 'output/ppt_academic_20261016/build/native_media_report.json' -Encoding utf8
 @{slides=$deck.Slides.Count;videos=$mediaReport.Count;overflow_count=$overflow.Count;rendered_all=$true} | ConvertTo-Json
} finally {
 if($deck){$deck.Close()}
 if($app){$app.Quit();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)}
}
