Add-Type -Path 'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS (2)\api\redist\SolidWorks.Interop.sldworks.dll'
foreach($n in @('ILayerMgr','ILayer','ISketchSegment')){$n;([type]('SolidWorks.Interop.sldworks.'+$n)).GetMethods()|Where-Object Name -Match 'AddLayer|CurrentLayer|Color|Layer|Width|Style|SetConstructionGeometry'|ForEach-Object ToString}
