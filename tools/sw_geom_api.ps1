Add-Type -Path 'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS (2)\api\redist\SolidWorks.Interop.sldworks.dll'
Add-Type -Path 'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS (2)\api\redist\SolidWorks.Interop.swconst.dll'
foreach($n in @('IModelView','IView','IEdge','IVertex','IDisplayDimension','IDimension','ISketchManager')){$n;([type]('SolidWorks.Interop.sldworks.'+$n)).GetMethods()|Where-Object Name -Match 'Orientation3|VisibleEntities2|GetStartVertex|GetEndVertex|GetCurve|GetPoint|Text|GetDimension2|SystemValue|AddToDB|DisplayWhen'|ForEach-Object ToString}
[SolidWorks.Interop.swconst.swDocumentTypes_e].Assembly.GetTypes() | Where-Object Name -Match 'ViewEntity|DimensionText' | ForEach-Object {$_.FullName;$t=$_;[Enum]::GetNames($t)|ForEach-Object{$_+'='+[int][Enum]::Parse($t,$_)} }
