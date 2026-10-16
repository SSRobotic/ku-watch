#pragma once
// Generated private settings override these defaults after local setup.
#if __has_include("cloud_private.h")
#include "cloud_private.h"
#else
#define KU_CLOUD_ENABLED false
#define KU_CLOUD_HOST ""
#define KU_CLOUD_USER ""
#define KU_CLOUD_PASSWORD ""
#endif

