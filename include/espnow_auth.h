#pragma once
#include <mbedtls/md.h>
#include "espnow_protocol.h"
#include "espnow_private.h"
namespace KuLink {
template<class P> inline void sign(P& p,Type type,uint32_t session,uint32_t sequence) {
  seal(p,type,session,sequence);uint8_t tag[32];
  mbedtls_md_hmac(mbedtls_md_info_from_type(MBEDTLS_MD_SHA256),KU_LINK_KEY,16,
    reinterpret_cast<const uint8_t*>(&p),offsetof(P,tag),tag);
  memcpy(p.tag,tag,16);p.crc=Activity::crc32(&p,sizeof(P)-4);
}
template<class P> inline bool authentic(const P& p,Type type) {
  if(!valid(p,type))return false;uint8_t tag[32];
  mbedtls_md_hmac(mbedtls_md_info_from_type(MBEDTLS_MD_SHA256),KU_LINK_KEY,16,
    reinterpret_cast<const uint8_t*>(&p),offsetof(P,tag),tag);
  uint8_t mismatch=0;for(unsigned i=0;i<16;++i)mismatch|=tag[i]^p.tag[i];return !mismatch;
}
}
