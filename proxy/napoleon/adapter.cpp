// adapter.cpp - Napoleon's adapter for the proxy core: identity pin, engine sites, config keys and names, all generated from
// identity.json and the registries (generated/tables.h). Nothing else game-specific lives in the DLL yet.
#include "generated/tables.h"

namespace wsp {

const GameAdapter& Adapter() {
    static const GameAdapter a = { gen::kGameName, gen::kConfigFile, gen::kModDir, gen::kInstanceMutex, gen::kIdentity,
                                   gen::kSites, gen::kSiteCount, gen::kKeys, gen::kKeyCount };
    return a;
}

} // namespace wsp
