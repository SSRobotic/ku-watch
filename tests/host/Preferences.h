#pragma once
#include <cstddef>
#include <cstring>
class Preferences {
public:
  static inline size_t storedSize=0;
  static inline unsigned writes=0,removes=0;
  bool begin(const char*,bool){return true;}
  size_t getBytesLength(const char*){return storedSize;}
  size_t getBytes(const char*,void* p,size_t n){std::memset(p,1,n);return n;}
  size_t putBytes(const char*,const void*,size_t n){++writes;return storedSize=n;}
  bool remove(const char*){++removes;storedSize=0;return true;}
};
