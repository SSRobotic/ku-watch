"""Build the Waveshare hub without changing the small watch's PlatformIO core."""
from pathlib import Path
import argparse, subprocess, hashlib, json, os, shutil
ROOT = Path(__file__).resolve().parents[1]
CLI = Path(os.environ.get("KU_ARDUINO_CLI", shutil.which("arduino-cli") or str(ROOT / "output/large_display_tools/arduino-cli/arduino-cli.exe")))
FQBN = "esp32:esp32:esp32s3:FlashSize=16M,PSRAM=opi,FlashMode=qio,USBMode=hwcdc,CDCOnBoot=cdc,PartitionScheme=app3M_fat9M_16MB"
SKETCH = ROOT / "large_display/KU_Hub"
OUT = ROOT / "output/large_build_artifacts"
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--upload",action="store_true");parser.add_argument("--port",default="COM8");args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if not args.upload:
        subprocess.run([str(CLI),"compile","--jobs","4","--fqbn",FQBN,"--build-property",f"compiler.cpp.extra_flags=-I{ROOT / 'include'}","--build-path",str(ROOT / "output/large_build"),"--output-dir",str(OUT),str(SKETCH)],check=True)
        image=OUT / "KU_Hub.ino.bin"
        (OUT / "manifest.json").write_text(json.dumps({"board":"ESP32-S3-Touch-LCD-2.1","version":"1.0.8","fqbn":FQBN,"bytes":image.stat().st_size,"sha256":hashlib.sha256(image.read_bytes()).hexdigest()},indent=2))
    else:
        # This script is large-display-only; verify the attached hardware first.
        python=Path.home()/".platformio/penv/Scripts/python.exe"
        esptool=Path.home()/".platformio/packages/tool-esptoolpy/esptool.py"
        result=subprocess.run([str(python),str(esptool),"--port",args.port,"read_mac"],capture_output=True,text=True,check=True)
        if "28:84:85:88:0b:0c" not in result.stdout.lower():
            raise RuntimeError("Attached board MAC is not the verified large display")
        backup=ROOT / "output/large_backup_20261008/flash.bin"
        if not backup.exists() or backup.stat().st_size!=16777216:raise RuntimeError("Complete large-board backup required")
        subprocess.run([str(CLI),"upload","--fqbn",FQBN,"--port",args.port,"--input-dir",str(OUT),str(SKETCH)],check=True)
if __name__=="__main__":main()

