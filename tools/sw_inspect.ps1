param([string]$AssemblyPath)
$ErrorActionPreference = 'Stop'
$taskInterop = 'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS (2)\api\redist\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $taskInterop
Add-Type -ReferencedAssemblies $taskInterop -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;
using SolidWorks.Interop.sldworks;
public class SwInspect {
 public static string Run(string path) {
  ISldWorks sw;
  try {sw=(ISldWorks)Marshal.GetActiveObject("SldWorks.Application");}
  catch {sw=(ISldWorks)Activator.CreateInstance(Type.GetTypeFromProgID("SldWorks.Application"));}
  var result=new StringBuilder();
  result.AppendLine("Revision="+sw.RevisionNumber());
  sw.Visible=true;
  int err=0,warn=0;
  IModelDoc2 doc=sw.OpenDoc6(path,2,3,"",ref err,ref warn);
  result.AppendLine("Open errors="+err+" warnings="+warn);
  if(doc==null)return result.ToString();
  result.AppendLine("Title="+doc.GetTitle());
  result.AppendLine("Path="+doc.GetPathName());
  result.AppendLine("Configuration="+doc.ConfigurationManager.ActiveConfiguration.Name);
  IAssemblyDoc asm=(IAssemblyDoc)doc;
  object[] comps=asm.GetComponents(false) as object[];
  result.AppendLine("Components="+(comps==null?0:comps.Length));
  if(comps!=null) foreach(object c in comps) {
   IComponent2 part=(IComponent2)c;
   result.AppendLine(part.Name2+" | "+part.GetPathName()+" | Suppression="+part.GetSuppression()+" | Loaded="+(part.GetModelDoc2()!=null));
  }
  return result.ToString();
 }
}
'@
$taskReport = [SwInspect]::Run($AssemblyPath)
New-Item -ItemType Directory -Force -Path output/mechanical | Out-Null
$taskReport | Set-Content -LiteralPath output/mechanical/assembly_inspection.txt -Encoding utf8
$taskReport
