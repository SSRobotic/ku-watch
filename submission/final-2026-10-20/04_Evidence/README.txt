KU WATCH — EVIDENCE DEMO / ชุดเปิดหลักฐานสำหรับส่งต่อ

วิธีเปิด (Windows)
1. คลิกขวาไฟล์ ZIP แล้วเลือก Extract All / แยกทั้งหมด
2. เปิดโฟลเดอร์ KU_Watch_Evidence_Demo ที่แตกออกมา
3. ดับเบิลคลิก OPEN_DEMO.cmd หรือเปิด index.html ด้วย Edge / Chrome
4. กด "ดูหลักฐาน" ที่ FR-01 ถึง FR-08 แล้วกด "โหมดขึ้นจอ" เมื่อต้องการนำเสนอ

ใช้เลข 1–8 หรือปุ่มลูกศรซ้าย/ขวาเพื่อเปลี่ยนข้อ คลิปมีปุ่มเล่นและเปิดเต็มจอ
FR-04 แสดง CSV จริงครบ 61 แถว 26 คอลัมน์ เลื่อนแนวนอนเพื่อดูทุกคอลัมน์
ไฟล์ CSV / Word มีให้เปิดด้วยโปรแกรมที่รองรับ หรือดูตาราง CSV ในหน้าเว็บได้เลย

ชุดนี้เปิดออฟไลน์ได้ ไม่ต้องติดตั้ง Node.js, Python, Grafana หรือ Node-RED
เมื่อส่งต่อ ให้ส่ง ZIP ทั้งไฟล์ และเก็บ index.html, files, media และ docs ไว้ด้วยกัน
หากเปิดจากใน ZIP โดยยังไม่แตก ภาพและคลิปอาจหาไม่เจอ
เปิด index.html โดยตรงได้เช่นกันหากไม่ต้องการใช้ไฟล์ .cmd

ขอบเขตหลักฐาน
นี่คือหลักฐานที่เก็บไว้วันที่ 16 ตุลาคม 2026 ไม่ใช่ข้อมูลสดจากนาฬิกาขณะเปิดชุดนี้
แต่ละข้อระบุเวอร์ชัน ช่วงทดสอบ และข้อจำกัดตามต้นฉบับ
FR-06 ใช้ค่าจำลอง TEST แยกจากข้อมูลจริงตามที่ระบุในหน้า
ชุดนี้ไม่ใช่ผลรับรองความแม่นยำทางการแพทย์ อายุแบตเตอรี่ หรือการรับ MQTT ต่อเนื่อง 24 ชั่วโมง
ไฟล์หลักฐาน 22 ไฟล์คัดลอกตรงจากต้นฉบับ ตรวจ SHA-256 แล้ว ไม่สร้างผลทดสอบเพิ่ม

Contents: 8 functional requirements, 4 videos, 3 images, JSON results, CSV, original Word report.
Open: Extract the entire ZIP, then double-click OPEN_DEMO.cmd or index.html.
Internet access and project services are not required. Keep all extracted folders together.
The JSON/CSV files are original recorded evidence, not a live connection or a new test run.
manifest.json maps the portable filenames to their original source paths and SHA-256 hashes.
CHECKSUMS.sha256 lists the integrity hashes of the included files.
