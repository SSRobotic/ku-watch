"""Plot actual completed outage evidence; never invent missing observations."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if (ROOT/'output/plot_tools').exists():sys.path.insert(0,str(ROOT/'output/plot_tools'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
OUT=ROOT/'output/delivery_20261009'
def main():
    report=json.loads((ROOT/'output/requirements_audit_20261009/broker_outage.json').read_text())
    if not report.get('passed'):raise RuntimeError('Completed real test must pass before producing a success figure')
    font=Path('C:/Windows/Fonts/tahoma.ttf')
    if font.exists():font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']='Tahoma'
    plt.rcParams['font.size']=20
    fig,ax=plt.subplots(figsize=(13.33,7.5),dpi=120)
    xs=[s['at_s']/60 for s in report['states']];ys=[s['pending'] for s in report['states']]
    ax.plot(xs,ys,color='#145B43',linewidth=3,label='ข้อมูลรอส่งในแฟลช')
    recovery_minutes=(report['recovery_verified_utc']-report['started_utc'])/60
    ax.scatter([recovery_minutes],[report['after']['pending']],color='#145B43',s=90,label='ตรวจคิวหมดหลังคืนพอร์ต MQTT')
    ax.set(title='ผลทดสอบจริง: พอร์ต MQTT ติดต่อไม่ได้ 10 นาที',xlabel='เวลาหลังเริ่มทดสอบ (นาที)',ylabel='จำนวนข้อมูลรอส่ง')
    ax.grid(alpha=.2);ax.set_ylim(bottom=0);ax.legend(loc='upper left');ax.spines[['top','right']].set_visible(False)
    fig.text(.08,.045,f"DB ครบ {report['database_outage_captures']} ข้อมูลช่วงขาด · คิวหมด · ลำดับขาด {report['missing_sequences']}\nตัวเล็ก 2.0.5 ติดต่อพอร์ตไม่ได้; Wi-Fi ยังอยู่; ไม่ได้หยุดบริการ HiveMQ",fontsize=17,color='#145B43')
    fig.tight_layout(rect=(0,.13,1,1));OUT.mkdir(parents=True,exist_ok=True)
    fig.savefig(OUT/'ผลทดสอบ_MQTT_10นาที.png');plt.close(fig)
    print('Actual evidence chart saved.')
if __name__=='__main__':main()
