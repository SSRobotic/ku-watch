# FR-08 และ NFR-08 — สถานะ OTA

อัปเดต 10 ตุลาคม 2569: บอร์ดปัจจุบัน 2.0.8 / Hub1.0.5 เตรียมไฟล์รุ่นปัจจุบันที่ `output/ota_release/2.0.8/` แล้ว มี firmware.bin, version.txt, release.json และ manifest.template.json ยังไม่ได้กำหนด HTTPS URL และไม่ได้เปิดเซิร์ฟเวอร์ ภาพขนาด 1,263,888 ไบต์ SHA256 `304b1dfce0c8a74022e65f9a0e096d4be2f651323e9356c8db4092c2c62179f4` ตรวจ ESP32-S3 image checksum และ validation hash ผ่านด้วย esptool 4.11.0 ผลนี้ไม่แทนการทดสอบ auto-download หรือ rollback จากการตัดไฟ และภาพรุ่นเดียวกับที่ติดตั้งไม่ทำให้เกิดการอัปเดตรุ่นใหม่

`tools/ota_release.py --version 2.0.8 --template` เตรียมไฟล์ในเครื่องได้โดยไม่ต้องมีปลายทาง เมื่อมี URL จริงจึงใช้ `--url https://...` แทน `--template` เครื่องมือตรวจเลขรุ่นให้ตรง source และ literal ในภาพ ESP ไม่ใช้ app descriptor ของ Arduino เป็นเลขรุ่นของ KU Watch เพราะค่าตรงนั้นเป็นรุ่น ESP-IDF ทดสอบการปฏิเสธ version ผิด/path traversal/HTTP/URL ที่ฝัง credentials/ภาพที่ไม่ใช่ ESP ผ่านด้วย fixture ในเครื่อง

รายละเอียดด้านล่างเป็นประวัติรุ่น 2.0.2; ข้อจำกัด HTTPS ปลายทางและการตัดไฟ 3 ครั้งยังคงอยู่

ตัวเล็กรุ่น 2.0.2 มีการตรวจ manifest ตอนบูตและทุก 24 ชั่วโมง ใช้ HTTPS ที่ตรวจใบรับรอง, ตรวจ SHA256 ก่อนเลือกบูต, เขียนช่องแอปที่ไม่ได้ใช้งาน และปฏิเสธเมื่อแบตอ่านไม่ได้/ต่ำกว่า30% หรือมี WALK/การถ่ายโอนอยู่ การเปลี่ยน URL ผ่านหน้าตั้งค่าจะตรวจใหม่หลังประมาณ10วินาที ควรปิดหน้าตั้งค่าก่อนให้ทำงานอัตโนมัติ

รอบนี้ติดตั้งผ่าน Wi-Fi โดยใช้หน้าตั้งค่าที่มี authentication/CSRF ไม่ต้องเสียบ USB กลับตัวเล็ก หลักฐานการอัปเดตและข้อมูลหลังบูตอยู่ใน `output/requirements_audit_20261009/` การติดตั้งวิธีนี้ยังไม่ใช่ผลตรวจรับการอัปเดตจากเซิร์ฟเวอร์อัตโนมัติ

ส่วนเซิร์ฟเวอร์ที่เตรียม:

- `tools/ota_server.py`: gateway เฉพาะ loopback8872 รองรับอ่าน manifest/firmwareด้วย capabilityสุ่ม256บิต ไม่มีหน้าadminหรือการเขียนไฟล์
- `config/ota.local.json`: capabilityและรุ่นที่เลือก เก็บส่วนตัวและอยู่ใน .gitignore
- `output/ota_release/2.0.2/`: firmware.bin, version.txt และ manifest.template.json พร้อมSHA256ของภาพจริง ยังต้องแทนHTTPS_FIRMWARE_URLด้วยปลายทางที่ใช้งานได้
- `tools/ota_release.py`: สร้าง manifest.jsonจากไฟล์จริงเมื่อมีHTTPSURLแล้ว
- `tests/test_ota_gateway.py`: ทดสอบอ่านเฉพาะไฟล์ที่อนุญาต, ปฏิเสธtokenผิด/เส้นทางอื่น/POST และตรวจhashของmanifest ด้วยไฟล์ทดสอบในเครื่อง ไม่ส่งไฟล์ทดสอบให้นาฬิกา

การเปิด gateway และ HTTPS tunnel จริงถูก automatic approval review ปฏิเสธ โดยแจ้งเพียง `blocked by policy` ไม่มี gateway/tunnelรอบนี้เปิดสำเร็จ จึงยังไม่ตั้งURLสมมติให้นาฬิกา และยังไม่ถือว่า FR-08 auto-update ผ่าน ต้องมีHTTPSปลายทางที่เข้าถึงได้และทดสอบให้เครื่องที่มีรุ่นเก่าดาวน์โหลดรุ่นใหม่เอง

NFR-08 การตัดไฟระหว่าง OTA สามครั้งและกลับมาบูตได้ยังต้องทดสอบบนฮาร์ดแวร์จริง ไม่ใช้การอัปเดต Wi-Fi สำเร็จแทนผลนี้
