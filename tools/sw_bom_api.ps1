Add-Type -Path 'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS (2)\api\redist\SolidWorks.Interop.sldworks.dll'
Add-Type -Path 'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS (2)\api\redist\SolidWorks.Interop.swconst.dll'
([type]'SolidWorks.Interop.sldworks.IBomTableAnnotation').GetMethods()|Where-Object Name -Match 'ColumnType|ColumnCustom'|ForEach-Object ToString
foreach($n in @('swBomTableColumnType_e','swCustomInfoType_e','swCustomPropertyAddOption_e')){$n;$t=[type]('SolidWorks.Interop.swconst.'+$n);[Enum]::GetNames($t)|ForEach-Object {$_+'='+[int][Enum]::Parse($t,$_)} }
