"""Create a LOCAL shared ESP-NOW key only when no key exists."""
import secrets
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    target=ROOT/'include/espnow_private.h'
    if target.exists():raise SystemExit('Existing pairing key preserved. No file changed.')
    key=secrets.token_bytes(16)
    with target.open('x',encoding='utf8') as f:
        f.write('#pragma once\n// Private shared key: keep identical on both boards. Never share.\nstatic const unsigned char KU_LINK_KEY[16]={'+','.join('0x%02x'%b for b in key)+'};\n')
    print('Local shared key created. It is intentionally not printed.')
if __name__=='__main__':main()
