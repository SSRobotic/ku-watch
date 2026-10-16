"""Record fallback build UTC until autonomous GPS/NTP or manual sync is ready."""
Import("env")
from pathlib import Path
import time

header = Path(env.subst("$PROJECT_DIR")) / "include" / "build_stamp.h"
header.write_text('#pragma once\n#define BUILD_UTC_SECONDS ' + str(int(time.time())) + 'ULL\n', encoding='utf-8')
