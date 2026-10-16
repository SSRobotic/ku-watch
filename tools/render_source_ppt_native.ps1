param([Parameter(Mandatory=$true)][string]$Path,[Parameter(Mandatory=$true)][string]$OutputDir)
$ErrorActionPreference='Stop'
$source=(Resolve-Path -LiteralPath $Path).Path
$dest=[IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputDir))
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$app=$null;$deck=$null
try {
 $app=New-Object -ComObject PowerPoint.Application
 $deck=$app.Presentations.Open($source,-1,0,0)
 for($n=1;$n -le $deck.Slides.Count;$n++){$deck.Slides.Item($n).Export((Join-Path $dest ('slide-{0:D2}.png' -f $n)),'PNG',1600,900)}
 @{source=$source;slides=$deck.Slides.Count;renderer='Microsoft PowerPoint native COM';read_only=$true} | ConvertTo-Json | Set-Content (Join-Path $dest 'render.json') -Encoding utf8
} finally {
 if($deck){$deck.Close()}
 if($app){$app.Quit();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)}
}
