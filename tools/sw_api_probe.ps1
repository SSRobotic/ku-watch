Add-Type -Path 'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS (2)\api\redist\SolidWorks.Interop.sldworks.dll'
Add-Type -Path 'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS (2)\api\redist\SolidWorks.Interop.swconst.dll'
$types = @('IAssemblyDoc','IModelDoc2','IModelDocExtension','IDrawingDoc','IView','ISheet','IComponent2','IPackAndGo')
foreach($t in $types) {
 Write-Output $t
 $x=[type]('SolidWorks.Interop.sldworks.'+$t)
 $x.GetMethods() | Where-Object Name -Match 'Explod|Box|SaveAs|NewDocument|SetupSheet|CreateDrawViewFromModelView|BomTable|PackAndGo|SetScale|GetOutline|GetVisibleEntities|Transform2|ReferencedConfiguration|CreateConfiguration|NewSheet' | ForEach-Object ToString
}
[Enum]::GetNames([SolidWorks.Interop.swconst.swSaveAsOptions_e]) | ForEach-Object { $_ + '=' + [int][Enum]::Parse([SolidWorks.Interop.swconst.swSaveAsOptions_e],$_) }
