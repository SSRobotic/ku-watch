#pragma once
#include <map>
#include <string>
#include <vector>
#include <cstring>
#include <memory>
#define FILE_READ "r"
#define FILE_WRITE "w"
inline std::map<std::string,std::vector<uint8_t>> flashFiles;
inline int flashWriteLimit=-1;
inline size_t flashTotal=1048576;
class File {
  std::string filename;bool valid_=false,root_=false;size_t at=0,next=0;
  std::vector<std::string> names;
public:
  File()=default;
  File(std::string n,bool valid,bool root=false):filename(n),valid_(valid),root_(root) {
    if(root)for(const auto& f:flashFiles)names.push_back(f.first);
  }
  explicit operator bool() const {return valid_;}
  const char* name() const{return filename.c_str();}
  File openNextFile(){if(!root_ || next==names.size())return {};return File(names[next++],true);}
  size_t size()const{return valid_ && !root_?flashFiles[filename].size():0;}
  bool seek(size_t position){at=position;return valid_;}
  size_t read(uint8_t* out,size_t bytes){
    if(!valid_ || at>size())return 0;bytes=std::min(bytes,size()-at);
    memcpy(out,flashFiles[filename].data()+at,bytes);at+=bytes;return bytes;
  }
  size_t write(const uint8_t* in,size_t bytes){
    if(!valid_)return 0;if(flashWriteLimit>=0)bytes=std::min(bytes,size_t(flashWriteLimit));
    auto& data=flashFiles[filename];if(at+bytes>data.size())data.resize(at+bytes);
    memcpy(data.data()+at,in,bytes);at+=bytes;return bytes;
  }
  void flush(){}void close(){valid_=false;}
};
struct FakeFS {
  File open(const char* n,const char* mode="r") {
    if(!strcmp(n,"/"))return File("/",true,true);
    if(!strcmp(mode,"w")){flashFiles[n].clear();return File(n,true);}
    return File(n,exists(n));
  }
  bool exists(const char* n){return flashFiles.count(n);}
  bool remove(const char* n){return flashFiles.erase(n)>0;}
  size_t totalBytes(){return flashTotal;}
  size_t usedBytes(){size_t sum=0;for(const auto& f:flashFiles)sum+=f.second.size()+4096;return sum;}
};
inline FakeFS LittleFS;
