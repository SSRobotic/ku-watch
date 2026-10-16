$ErrorActionPreference='Stop'
$root=(Get-Location).Path
$build=Join-Path $root 'output/ppt_history_v2_20261016/build'
$plan=Get-Content -LiteralPath (Join-Path $build 'additions_plan.json') -Raw | ConvertFrom-Json
$source=[string]$plan.source
$additions=Join-Path $build 'history_additions.pptx'
$candidate=Join-Path $build 'merged_native_candidate.pptx'
$renders=Join-Path $build 'native_render'
New-Item -ItemType Directory -Force -Path $renders | Out-Null
$sourceHash=(Get-FileHash -LiteralPath $source).Hash
$app=$null;$deck=$null;$donor=$null;$overflow=@();$videos=@();$slideIds=@();$replacementIds=@{}
try {
 $app=New-Object -ComObject PowerPoint.Application
 $deck=$app.Presentations.Open($source,0,0,0)
 $donor=$app.Presentations.Open($additions,-1,0,0)
 if($deck.Slides.Count -ne 66){throw 'Unexpected source count'}
 for($n=1;$n -le 66;$n++){$slideIds+=$deck.Slides.Item($n).SlideID}
 [void]$deck.Slides.InsertFromFile($additions,66,3,$donor.Slides.Count)
 foreach($job in ($plan.replacements | Sort-Object final_slide -Descending)){
  $index=[int]$job.final_slide
  $oldId=[string]$deck.Slides.Item($index).SlideID
  [void]$deck.Slides.InsertFromFile($additions,($index-1),[int]$job.donor_slide,[int]$job.donor_slide)
  $replacementIds[$oldId]=@{id=$deck.Slides.Item($index).SlideID;number=$index}
  $deck.Slides.Item($index+1).Delete()
 }
 # Retarget existing internal links to replaced slides; all other slides keep IDs.
 foreach($slide in $deck.Slides){foreach($shape in $slide.Shapes){
  if($shape.ActionSettings(1).Action -eq 7){
   $sub=[string]$shape.ActionSettings(1).Hyperlink.SubAddress
   $id=$sub.Split(',')[0]
   if($replacementIds.ContainsKey($id)){$dest=$replacementIds[$id];$shape.ActionSettings(1).Hyperlink.SubAddress=([string]$dest.id+','+[string]$dest.number+',Slide '+[string]$dest.number)}
  }
 }}
 foreach($job in $plan.videos){
  $slide=$deck.Slides.Item([int]$job.slide)
  $media=$slide.Shapes.AddMediaObject2([string]$job.file,0,-1,[single]($job.left*.75),[single]($job.top*.75))
  $media.Name='VIDEO_'+$job.id;$media.LockAspectRatio=-1
  $naturalW=$media.Width;$naturalH=$media.Height
  $scale=[Math]::Min(($job.width*.75)/$naturalW,($job.height*.75)/$naturalH)
  $media.Width=[single]($naturalW*$scale)
  $media.Left=[single]($job.left*.75+($job.width*.75-$media.Width)/2)
  $media.Top=[single]($job.top*.75+($job.height*.75-$media.Height)/2)
  $media.MediaFormat.SetDisplayPictureFromFile([string]$job.poster)
  $media.AnimationSettings.PlaySettings.PlayOnEntry=0
  $media.AnimationSettings.PlaySettings.LoopUntilStopped=0
 }
 foreach($link in $plan.links){
  $shape=$deck.Slides.Item([int]$link.slide).Shapes.Item([string]$link.shapeName)
  $destination=$deck.Slides.Item([int]$link.targetSlide)
  $shape.ActionSettings(1).Action=7
  $shape.ActionSettings(1).Hyperlink.SubAddress=([string]$destination.SlideID+','+[string]$link.targetSlide+',Slide '+[string]$link.targetSlide)
 }
 # Explicit links allow browsing hidden appendix slides during Slide Show.
 for($n=16;$n -le $deck.Slides.Count;$n++){
  $slide=$deck.Slides.Item($n)
  foreach($direction in @('PREV','NEXT')){
   $next=if($direction -eq 'PREV'){$n-1}elseif($n -lt $deck.Slides.Count){$n+1}else{15}
   $left=if($direction -eq 'PREV'){1510}else{1690}
   $nav=$slide.Shapes.AddTextbox(1,[single]($left*.75),78,112.5,27)
   $nav.Name='NAV_'+$direction
   $nav.TextFrame2.MarginLeft=0;$nav.TextFrame2.MarginRight=0;$nav.TextFrame2.MarginTop=0;$nav.TextFrame2.MarginBottom=0
   $nav.TextFrame2.TextRange.Text=if($direction -eq 'PREV'){'ก่อนหน้า'}elseif($n -lt $deck.Slides.Count){'ถัดไป'}else{'จบภาคผนวก'}
   $nav.TextFrame2.TextRange.Font.Name='Leelawadee UI'
   $nav.TextFrame2.TextRange.Font.NameComplexScript='Leelawadee UI'
   $nav.TextFrame2.TextRange.Font.NameFarEast='Leelawadee UI'
   $nav.TextFrame2.TextRange.Font.NameAscii='Leelawadee UI'
   $nav.TextFrame2.TextRange.Font.Size=18
   $nav.TextFrame2.TextRange.Font.Fill.ForeColor.RGB=0xB06F2F
   $destination=$deck.Slides.Item($next);$nav.ActionSettings(1).Action=7
   $nav.ActionSettings(1).Hyperlink.SubAddress=([string]$destination.SlideID+','+[string]$next+',Slide '+[string]$next)
  }
 }
 for($n=1;$n -le $deck.Slides.Count;$n++){
  $slide=$deck.Slides.Item($n)
  if($n -le 66 -and $n -notin @(2,15) -and $slide.SlideID -ne $slideIds[$n-1]){throw 'Unmodified SlideID changed'}
  $slide.SlideShowTransition.Hidden=if($n -gt 14){-1}else{0}
  foreach($shape in $slide.Shapes){
   if($shape.Name -like 'VIDEO_*'){$videos+=@{slide=$n;name=$shape.Name;length_ms=$shape.MediaFormat.Length}}
   if($shape.HasTextFrame -eq -1 -and $shape.TextFrame2.HasText -eq -1){
    if($shape.TextFrame2.TextRange.BoundHeight -gt $shape.Height+5){$overflow+=@{slide=$n;shape=$shape.Name;text=$shape.TextFrame2.TextRange.Text;bound_height=$shape.TextFrame2.TextRange.BoundHeight;shape_height=$shape.Height}}
   }
  }
 }
 $deck.SaveAs($candidate,24)
 for($n=1;$n -le $deck.Slides.Count;$n++){$deck.Slides.Item($n).Export((Join-Path $renders ('slide-{0:D2}.png' -f $n)),'PNG',1600,900)}
 $report=@{application='Microsoft PowerPoint native COM';source=$source;source_hash_unchanged=((Get-FileHash -LiteralPath $source).Hash -eq $sourceHash);unmodified_slide_ids_preserved=$true;replacement_ids=$replacementIds;slides=$deck.Slides.Count;main=14;hidden=$deck.Slides.Count-14;videos=$videos;overflow=$overflow;candidate=$candidate;rendered_all=$true;new_links=$plan.links.Count}
 $report | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $build 'native_merge_report.json') -Encoding utf8
 @{slides=$deck.Slides.Count;videos=$videos.Count;overflow=$overflow.Count;original_ids_preserved=$true;rendered_all=$true} | ConvertTo-Json
} finally {
 if($donor){$donor.Close()}
 if($deck){$deck.Close()}
 if($app){$app.Quit();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)}
}
