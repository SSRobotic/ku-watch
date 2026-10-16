Add-Type -Path 'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS (2)\api\redist\SolidWorks.Interop.sldworks.dll'
([type]'SolidWorks.Interop.sldworks.IView').GetMethods()|Where-Object Name -Match 'Orient|Named|Transform|DisplayState|Hidden|ModelView'|ForEach-Object ToString
