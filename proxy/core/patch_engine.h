#pragma once
// Runtime patch engine: pure core (no Windows headers, no globals; host tests in proxy/tests/test_patch_engine.cpp on a synthetic
// image). The driver (patch_driver.cpp) runs it once from DllMain when PlanEngine(...).patches is true, and writes with
// VirtualProtect + FlushInstructionCache. The exe on disk is never touched (D2).
//
// The site table is GENERATED from the engine_sites registry (proxy/tools/gen_tables.py; never edit it by hand). Byte layout of a
// site (the registry has one RVA, so the convention is fixed here and checked by the generator):
//     rva                      rva + len(anchor)
//     | anchor_bytes ...       | stock_bytes ...   (patch_bytes replace stock_bytes; a hook detours at rva + len(anchor))
// The anchor is the fixed context the site is recognised by (an opcode before an immediate, the padding before a function).
// Checks, after rebasing (RVA + the actual module base; ASLR is on): the site lies in one section's file-backed bytes (a hook in an
// executable one); anchor and stock compare equal after taking the load delta off every relocated dword (ReadUnrelocated); a
// patch's changing bytes carry no relocation. A patch site whose bytes already equal patch_bytes counts as done. ANY bad site ->
// nothing is written (all-or-nothing), and every site is still checked and logged. Disabled sites (their config key is off) are
// checked (they are part of the exe's identity) but never written.
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include "pe.h"

namespace wsp {

constexpr unsigned kMaxSiteBytes = 32;
enum SiteKind : uint8_t { kPatch = 0, kHook = 1 };

struct SiteDef {
    const char* id;          // engine_sites id
    uint8_t kind;            // SiteKind
    uint32_t rva;            // of the first anchor byte
    uint8_t anchorLen; uint8_t anchor[kMaxSiteBytes];
    uint8_t len;       uint8_t stock[kMaxSiteBytes];
    uint8_t patch[kMaxSiteBytes];   // kind == kPatch: len bytes
    const char* configKey;   // nullptr = always on
};

enum class SiteState : uint8_t { Stock, Done, BadEntry, Unmapped, NotCode, Relocated, BadAnchor, BadStock, Overlap };
inline const char* SiteStateName(SiteState s) {
    switch (s) {
    case SiteState::Stock: return "stock"; case SiteState::Done: return "already patched"; case SiteState::BadEntry: return "BAD TABLE ENTRY";
    case SiteState::Unmapped: return "UNMAPPED"; case SiteState::NotCode: return "NOT IN CODE"; case SiteState::Relocated: return "RELOCATED VALUE";
    case SiteState::BadAnchor: return "ANCHOR MISMATCH"; case SiteState::BadStock: return "STOCK MISMATCH"; default: return "OVERLAPS ANOTHER SITE";
    }
}
inline bool SiteStateOk(SiteState s) { return s == SiteState::Stock || s == SiteState::Done; }

struct SiteCheck {
    SiteState state = SiteState::Unmapped;
    uint32_t valueRva = 0;   // rva + anchorLen: where the patch is written / the hook goes
    bool enabled = false, write = false;
    int firstDiff = -1;      // byte index of the first mismatch (anchor or stock)
    uint8_t cur[kMaxSiteBytes] = {};
};

enum class PlanVerdict : uint8_t { Apply, NothingToDo, Refuse };
inline const char* PlanVerdictName(PlanVerdict v) { return v == PlanVerdict::Apply ? "apply" : v == PlanVerdict::NothingToDo ? "nothing to do" : "REFUSED"; }

struct PatchPlan {
    PlanVerdict verdict = PlanVerdict::Refuse;
    std::string reason;               // first bad site, or "" when all are good
    std::vector<SiteCheck> sites;
    int nOk = 0, nBad = 0, nWrite = 0, nDone = 0, nHooks = 0, bytesToChange = 0;
};

// enabled[i]: site i's config key is on (nullptr = all on). delta = actual base - preferred base (0 for a file view).
inline PatchPlan MakePatchPlan(const ImageView& v, uint32_t delta, const SiteDef* s, size_t n, const bool* enabled) {
    PatchPlan pl; char b[240];
    pl.sites.resize(n);
    if (!v.pe || !v.pe->ok) { pl.reason = "no PE headers"; pl.nBad = (int)n; if (n == 0) pl.verdict = PlanVerdict::NothingToDo; return pl; }
    for (size_t i = 0; i < n; ++i) {
        const SiteDef& d = s[i]; SiteCheck& c = pl.sites[i];
        c.enabled = enabled ? enabled[i] : true;
        c.valueRva = d.rva + d.anchorLen;
        const uint32_t total = (uint32_t)d.anchorLen + d.len;
        if (!d.id || d.anchorLen == 0 || d.len == 0 || total > 2 * kMaxSiteBytes || d.anchorLen > kMaxSiteBytes || d.len > kMaxSiteBytes ||
            (d.kind != kPatch && d.kind != kHook) || d.rva + (uint64_t)total > 0xFFFFFFFFull) c.state = SiteState::BadEntry;
        else {
            for (size_t j = 0; j < i && c.state != SiteState::Overlap; ++j) {
                const uint32_t lo = s[j].rva, hi = s[j].rva + s[j].anchorLen + s[j].len;
                if (d.rva < hi && lo < d.rva + total) c.state = SiteState::Overlap;
            }
            if (c.state != SiteState::Overlap) {
                const int sec = SectionOfRva(*v.pe, d.rva, total);
                std::vector<uint32_t> rel;
                uint8_t a[kMaxSiteBytes], cur[kMaxSiteBytes];
                if (sec < 0) c.state = SiteState::Unmapped;
                else if (d.kind == kHook && !(v.pe->sections[sec].characteristics & kScnExecute)) c.state = SiteState::NotCode;
                else if (d.kind == kPatch && (RelocsInRange(v, c.valueRva, c.valueRva + d.len, rel), !rel.empty())) c.state = SiteState::Relocated;
                else if (!ReadUnrelocated(v, d.rva, d.anchorLen, delta, a) || !ReadUnrelocated(v, c.valueRva, d.len, delta, cur)) c.state = SiteState::Unmapped;
                else {
                    memcpy(c.cur, cur, d.len);
                    for (unsigned k = 0; k < d.anchorLen; ++k) if (a[k] != d.anchor[k]) { c.firstDiff = (int)k; break; }
                    if (c.firstDiff >= 0) c.state = SiteState::BadAnchor;
                    else if (memcmp(cur, d.stock, d.len) == 0) c.state = SiteState::Stock;
                    else if (d.kind == kPatch && memcmp(cur, d.patch, d.len) == 0) c.state = SiteState::Done;
                    else {
                        c.state = SiteState::BadStock;
                        for (unsigned k = 0; k < d.len; ++k) if (cur[k] != d.stock[k]) { c.firstDiff = (int)k; break; }
                    }
                }
            }
        }
        if (!SiteStateOk(c.state)) {
            ++pl.nBad;
            if (pl.reason.empty()) {
                snprintf(b, sizeof b, "site '%s' (RVA 0x%x): %s%s", d.id ? d.id : "?", (unsigned)d.rva, SiteStateName(c.state),
                         c.firstDiff >= 0 ? (std::string(" at byte +") + std::to_string(c.firstDiff)).c_str() : "");
                pl.reason = b;
            }
            continue;
        }
        ++pl.nOk;
        if (d.kind == kHook) { ++pl.nHooks; continue; }   // hooks are installed by their feature, through the plan's checked address
        if (c.state == SiteState::Done) { ++pl.nDone; continue; }
        if (c.enabled) { c.write = true; ++pl.nWrite; for (unsigned k = 0; k < d.len; ++k) pl.bytesToChange += c.cur[k] != d.patch[k]; }
    }
    if (pl.nBad) {
        for (auto& c : pl.sites) c.write = false;
        pl.nWrite = 0; pl.bytesToChange = 0; pl.verdict = PlanVerdict::Refuse;
        return pl;
    }
    pl.verdict = pl.nWrite ? PlanVerdict::Apply : PlanVerdict::NothingToDo;
    return pl;
}

// Host/test helper: performs the plan's writes on a MAPPED-layout buffer. The driver writes the same bytes under VirtualProtect.
inline int ApplyPlanToBuffer(uint8_t* image, const PatchPlan& pl, const SiteDef* s) {
    if (pl.verdict != PlanVerdict::Apply) return 0;
    int changed = 0;
    for (size_t i = 0; i < pl.sites.size(); ++i) {
        if (!pl.sites[i].write) continue;
        for (unsigned k = 0; k < s[i].len; ++k)
            if (image[pl.sites[i].valueRva + k] != s[i].patch[k]) { image[pl.sites[i].valueRva + k] = s[i].patch[k]; ++changed; }
    }
    return changed;
}

inline std::string PlanSummary(const PatchPlan& pl, size_t n) {
    char b[300];
    snprintf(b, sizeof b, "patch_engine: %s - %u sites: %d ok, %d bad, %d to write (%d bytes), %d already patched, %d hooks verified%s%s",
             PlanVerdictName(pl.verdict), (unsigned)n, pl.nOk, pl.nBad, pl.nWrite, pl.bytesToChange, pl.nDone, pl.nHooks,
             pl.reason.empty() ? "" : "; first bad: ", pl.reason.c_str());
    return b;
}

} // namespace wsp
