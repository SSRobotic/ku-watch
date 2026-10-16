#include "display_hardware.h"
// Keep this out of an inline COMDAT section: Xtensa IRAM literal placement
// requires an ordinary out-of-line definition for the interrupt handler.
void IRAM_ATTR HubDisplay::onTouch(){++touchIrqs;}
