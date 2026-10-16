Add-Type -Path 'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS (2)\api\redist\SolidWorks.Interop.sldworks.dll'
Add-Type -Path 'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS (2)\api\redist\SolidWorks.Interop.swconst.dll'
([type]'SolidWorks.Interop.sldworks.ITableAnnotation').GetMethods()|Where-Object Name -Match 'ColumnType'|ForEach-Object ToString
[SolidWorks.Interop.swconst.swDocumentTypes_e].Assembly.GetTypes()|Where-Object Name -Match 'ColumnType'|ForEach-Object{$_.Name;$t=$_;[Enum]::GetNames($t)|ForEach-Object{$_+'='+[int][Enum]::Parse($t, $_)}}
