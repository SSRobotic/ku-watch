#include <cstdio>
#include <cstdlib>
#include "robot_pet.h"
#include "button.h"
constexpr uint8_t INA226_I2C_ADDRESS=0x44;
namespace Pin {constexpr int PAGE_COUNT=11;}
#include "face.h"
static unsigned checks=0;
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"FAIL %d %s\n",__LINE__,#x);exit(1);}}while(0)
static void preview(const char* path,const Face::State& s) {
  static Face::Canvas canvas;canvas.render(s);FILE* f=fopen(path,"wb");CHECK(f);fprintf(f,"P6\n240 240\n255\n");
  for(auto v:canvas.pixels){uint8_t p[]={uint8_t(((v>>11)&31)*255/31),uint8_t(((v>>5)&63)*255/63),uint8_t((v&31)*255/31)};fwrite(p,1,3,f);}fclose(f);
}
int main() {
  RobotPet::Model pet;CHECK(pet.saved.food==3 && pet.saved.xp==0);CHECK(RobotPet::level(0)==1 && RobotPet::stage(0)==0);
  CHECK(!pet.activity(0,60000,10));CHECK(!pet.activity(1,60000,NAN));CHECK(!pet.activity(1,60000,-1));CHECK(!pet.activity(1,86400001,0));
  CHECK(pet.activity(1,60000,100));CHECK(pet.saved.xp==3 && pet.saved.walkMs==60000 && pet.saved.walkCm==10000);
  uint32_t revision=pet.revision;CHECK(!pet.activity(1,60000,100));CHECK(pet.revision==revision && pet.saved.xp==3);
  CHECK(!pet.activity(1,50000,90));CHECK(pet.saved.xp==3);
  CHECK(pet.activity(1,300000,100));CHECK(pet.saved.xp==7 && pet.saved.food==4);
  CHECK(!pet.activity(2,30000,0));CHECK(pet.activity(3,30000,0));CHECK(pet.saved.xp==8); // seconds accumulate over short sessions
  CHECK(!pet.activity(1,600000,1000));CHECK(pet.saved.xp==8); // old activity cannot replay rewards
  CHECK(pet.feed());CHECK(pet.saved.food==3 && pet.saved.energy<=100 && pet.saved.xp==8);
  while(pet.saved.food) CHECK(pet.feed());CHECK(!pet.feed());CHECK(pet.saved.energy==100 && pet.saved.mood==100);
  auto saved=pet.snapshot();CHECK(RobotPet::valid(saved));RobotPet::Model restored;CHECK(restored.restore(saved));CHECK(restored.saved.xp==8 && restored.saved.food==0);
  saved.xp++;CHECK(!RobotPet::valid(saved));CHECK(!restored.restore(saved));CHECK(restored.saved.xp==8);
  pet.care(0);CHECK(!pet.saved.careUtc);pet.care(1791446400);CHECK(pet.saved.careUtc==1791446400);
  pet.care(1791450000);CHECK(pet.saved.mood==99);pet.care(1791440000);CHECK(pet.saved.careUtc==1791440000);
  pet.care(1791700000);CHECK(pet.saved.mood==75 && pet.saved.energy==100);
  CHECK(RobotPet::level(10)==2 && RobotPet::stage(10)==0);CHECK(RobotPet::level(30)==3 && RobotPet::stage(30)==1);
  CHECK(RobotPet::level(300)==6 && RobotPet::stage(300)==2);CHECK(RobotPet::level(2000)==9 && RobotPet::nextXp(2000)==2000);
  RobotPet::Model daily;CHECK(daily.feed(1791446400));CHECK(daily.saved.xp==1);CHECK(daily.feed(1791446500));CHECK(daily.saved.xp==1);
  CHECK(daily.feed(1791532800));CHECK(daily.saved.xp==2);CHECK(!daily.feed(1791619200));CHECK(daily.saved.xp==2);
  CHECK(daily.visit(0,1791446400));CHECK(daily.saved.xp==4);CHECK(!daily.visit(0,1791446410));CHECK(daily.saved.xp==4);
  CHECK(daily.visit(1,1791446500));CHECK(daily.saved.xp==6);CHECK(!daily.visit(2,1791446500));CHECK(!daily.visit(0,0));
  CHECK(daily.visit(0,1791532800));CHECK(daily.saved.xp==8);CHECK(!daily.visit(1,1791446400));
  CHECK(RobotPet::valid(daily.snapshot()));
  MenuTaps taps;CHECK(!taps.click(100));CHECK(!taps.leave(549,false));CHECK(taps.leave(550,false));CHECK(!taps.leave(600,false));
  CHECK(!taps.click(1000));CHECK(taps.waiting());CHECK(taps.click(1250));CHECK(!taps.waiting());CHECK(!taps.leave(2000,false));
  CHECK(!taps.click(2100));CHECK(!taps.leave(2800,true));taps.cancel();CHECK(!taps.leave(3000,false));
  CHECK(!taps.click(0xfffffff0));CHECK(taps.click(40));
  auto food=daily.saved.food;auto xp=daily.saved.xp;daily.play();CHECK(daily.saved.food==food && daily.saved.xp==xp);
  Face::State s;s.page=10;s.robotFood=3;s.robotMessage="HOLD TO FEED ME";s.robotPose=RobotPet::Pose::Wave;
  preview("output/robot_baby.ppm",s);
  s.robotXp=30;s.robotPose=RobotPet::Pose::Walk;s.robotMessage="LET US EXPLORE";preview("output/robot_buddy_demo.ppm",s);
  s.robotXp=300;s.robotPose=RobotPet::Pose::Happy;s.robotMessage="I GREW THANK YOU";preview("output/robot_hero_demo.ppm",s);
  s.page=0;s.robotBubble=true;s.robotXp=0;s.robotPose=RobotPet::Pose::Wave;s.robotMessage="LET US GO FOR A WALK";preview("output/robot_home.ppm",s);
  static Face::Canvas c;
  static Face::Canvas withoutSpeech;
  for(unsigned page=0;page<11;++page) {
    s.page=page;s.robotBubble=false;withoutSpeech.render(s);s.robotBubble=true;c.render(s);
    CHECK(!memcmp(c.pixels+34*240,withoutSpeech.pixels+34*240,(240-34)*240*sizeof(uint16_t)));
  }
  for(unsigned page=0;page<11;++page) for(unsigned pose=0;pose<RobotPet::POSE_COUNT;++pose) for(unsigned phase=0;phase<8;++phase) {
    s.page=page;s.robotPose=static_cast<RobotPet::Pose>(pose);s.robotPhase=phase;c.render(s);
    unsigned visible=0;for(int y=1;y<26;++y) for(int x=110;x<131;++x) if(c.pixels[y*240+x]!=Face::BLACK)++visible;
    CHECK(page==10 || visible>30);
  }
  for(unsigned pose=7;pose<RobotPet::POSE_COUNT;++pose) {
    s.page=10;s.robotXp=30;s.robotPose=static_cast<RobotPet::Pose>(pose);s.robotPhase=0;
    withoutSpeech.render(s);s.robotPhase=1;c.render(s);CHECK(memcmp(c.pixels,withoutSpeech.pixels,sizeof(c.pixels))!=0);
  }
  s.page=10;s.robotXp=0;s.robotPose=RobotPet::Pose::Dance;s.robotMessage="LET US DANCE";preview("output/robot_dance.ppm",s);
  printf("PASS %u robot checks\n",checks);
}
