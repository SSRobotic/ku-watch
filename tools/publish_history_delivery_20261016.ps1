$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Get-Location).Path)
$build=Join-Path $projectRoot 'output/ppt_history_v2_20261016/build'
$deliverable=Join-Path $projectRoot 'output/ppt_history_v2_20261016/deliverable'
$ready=Join-Path $projectRoot 'สไลด์/พร้อมนำเสนอ'
$package=Join-Path $deliverable 'KU_Watch_พร้อมนำเสนอ_v2'
$report=Get-Content -LiteralPath (Join-Path $build 'delivery_package_report.json') -Raw | ConvertFrom-Json
$pptName='KU_Watch_นำเสนอพร้อมภาพพัฒนาการ_v2.pptx'
$zipName='KU_Watch_พร้อมนำเสนอ_รวมภาพพัฒนาการ_v2.zip'
$published=@()
foreach($job in @(
 @{source=(Join-Path $deliverable $pptName);name=$pptName;expected=$report.pptx_sha256},
 @{source=(Join-Path $deliverable $zipName);name=$zipName;expected=$report.archive_sha256},
 @{source=(Join-Path $package 'อ่านก่อนนำเสนอ_v2.txt');name='อ่านก่อนนำเสนอ_v2.txt';expected=$null}
)){
 $sourceHash=(Get-FileHash -LiteralPath $job.source -Algorithm SHA256).Hash.ToLowerInvariant()
 if($job.expected -and $sourceHash -ne $job.expected){throw 'Validated source hash mismatch'}
 $target=Join-Path $ready $job.name
 Copy-Item -LiteralPath $job.source -Destination $target -Force
 if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sourceHash){throw 'Published copy mismatch'}
 $published+=@{path=$target;sha256=$sourceHash;bytes=(Get-Item -LiteralPath $target).Length}
}
$published | ForEach-Object { $_.sha256+'  '+[IO.Path]::GetFileName($_.path) } | Set-Content -LiteralPath (Join-Path $ready 'SHA256SUMS_v2.txt') -Encoding utf8
# Delete only the two verified copies of the superseded media archive.
$oldHash='b318098f6b3c868e699513223eb461711d1a3f4ff224fc6d9901224626b64200'
$oldPaths=@(
 (Join-Path $ready 'KU_Watch_ภาพและคลิปครบชุด.zip'),
 (Join-Path $projectRoot 'output/ppt_academic_20261016/deliverable/KU_Watch_ภาพและคลิปครบชุด.zip')
)
$deleted=@()
foreach($old in $oldPaths){
 $resolved=[IO.Path]::GetFullPath($old)
 if(-not $resolved.StartsWith($projectRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Old archive outside project'}
 if(Test-Path -LiteralPath $resolved){
  if(-not (Test-Path -LiteralPath $resolved -PathType Leaf)){throw 'Archive is not a file'}
  if((Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash.ToLowerInvariant() -ne $oldHash){throw 'Old archive changed; preserve it'}
  Remove-Item -LiteralPath $resolved
  if(Test-Path -LiteralPath $resolved){throw 'Old archive still exists'}
  $deleted+=@{path=$resolved;sha256=$oldHash}
 }
}
$original=Join-Path $ready 'KU_Watch_นำเสนอวิชาการ_18ตุลาคม2569.pptx'
if((Get-FileHash -LiteralPath $original -Algorithm SHA256).Hash.ToLowerInvariant() -ne '6f88ca1ec0048fb8e778907ac8511689537c0dddc83ec18faed3ec4669b4deb2'){throw 'Original presentation changed'}
$log=@{completed_utc=[DateTime]::UtcNow.ToString('o');published=$published;deleted_old_archives=$deleted;original_presentation_unchanged=$true}
$log | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $build 'old_archives_replaced.json') -Encoding utf8
$log | ConvertTo-Json -Depth 6
