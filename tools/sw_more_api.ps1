Add-Type -Path 'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS (2)\api\redist\SolidWorks.Interop.sldworks.dll'
Add-Type -Path 'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS (2)\api\redist\SolidWorks.Interop.swconst.dll'
$taskQueries=@{
'IAssemblyDoc'='Explode|FixComponent|ResolveAll';
'IConfiguration'='Explode';
'IModelDoc2'='NameView|ViewNamed|InsertNote|AddDimension|AddHorizontal|AddVertical|ForceRebuild';
'IView'='DisplayMode|Scale|Position|Dimension|Balloon';
'IDrawingDoc'='AutoBalloon|SetupSheet|EditTemplate|EditSheet';
'IAutoBalloonOptions'='.';
'IAnnotation'='SetPosition|SetTextFormat|Leader|Attach';
'INote'='Height|Balloon|Text|GetAnnotation';
'ITableAnnotation'='ColumnWidth|RowHeight|Text|Title|GetAnnotation';
'IPackAndGo'='.';
'IPartDoc'='Bodies|PartBox'}
foreach($name in $taskQueries.Keys){Write-Output $name; ([type]('SolidWorks.Interop.sldworks.'+$name)).GetMethods() | Where-Object Name -Match $taskQueries[$name] | ForEach-Object ToString}
foreach($name in @('swDwgPaperSizes_e','swBOMConfigurationAnchorType_e','swBomType_e','swDisplayMode_e','swBalloonLayoutType_e')){ Write-Output $name; $t=[type]('SolidWorks.Interop.swconst.'+$name); [Enum]::GetNames($t) | ForEach-Object {$_+'='+[int][Enum]::Parse($t,$_)} }
