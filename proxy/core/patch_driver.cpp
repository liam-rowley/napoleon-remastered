// patch_driver.cpp - in-process driver of the runtime patch engine (pure core: patch_engine.h). Called from DllMain only when
// PlanEngine(...).patches is true (exe accepted by the guard). Every site is checked and logged; writes happen only when the whole
// plan is accepted. Loader lock: GetModuleHandle, VirtualQuery, VirtualProtect, FlushInstructionCache only.
#include "runtime.h"
#include <memory>
#include <vector>

namespace wsp {
namespace {
bool Readable(const void* p, size_t n) {
    const uint8_t* a = (const uint8_t*)p; const uint8_t* end = a + n;
    while (a < end) {
        MEMORY_BASIC_INFORMATION mbi{};
        if (!VirtualQuery(a, &mbi, sizeof mbi) || mbi.State != MEM_COMMIT || (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD))) return false;
        a = (const uint8_t*)mbi.BaseAddress + mbi.RegionSize;
    }
    return true;
}
std::string Hex(const uint8_t* p, unsigned n) { std::string s; char b[4]; for (unsigned i = 0; i < n; ++i) { snprintf(b, sizeof b, i ? " %02x" : "%02x", p[i]); s += b; } return s; }
}

void PatchesRun() {
    Runtime& rt = Rt();
    const GameAdapter& ad = Adapter();
    if (!rt.plan.patches) { LOGI("patch_engine: not run (pass-through)"); return; }
    if (!rt.cfg.Bool("proxy.runtime_patches")) { LOGI("patch_engine: off (proxy.runtime_patches=0)"); return; }
    uint8_t* base = (uint8_t*)GetModuleHandleW(nullptr);
    PeInfo pe = Readable(base, 0x1000) ? ParsePe(base, 0x1000) : PeInfo{};
    ImageView v; v.data = base; v.size = pe.ok ? pe.sizeOfImage : 0; v.pe = &pe; v.file = false; v.readable = Readable;
    uint32_t delta = 0;
    if (!LoadDelta((uintptr_t)base, rt.fileImageBase, delta)) {
        LOGE("patch_engine: refused - the exe file's ImageBase is unknown (0x%08x), so no rebase delta: nothing written", (unsigned)rt.fileImageBase);
        return;
    }
    std::unique_ptr<bool[]> en(new bool[ad.nSites + 1]);
    for (size_t i = 0; i < ad.nSites; ++i) en[i] = !ad.sites[i].configKey || rt.cfg.Bool(ad.sites[i].configKey);
    const PatchPlan pl = MakePatchPlan(v, delta, ad.sites, ad.nSites, en.get());
    LOGI("patch_engine: image base %p (file ImageBase 0x%08x, delta 0x%08x)", base, (unsigned)rt.fileImageBase, (unsigned)delta);
    for (size_t i = 0; i < ad.nSites; ++i) {
        const SiteDef& d = ad.sites[i]; const SiteCheck& c = pl.sites[i];
        LOGI("patch_engine:   %-32s %s RVA 0x%08x -> %p: %s%s cur [%s]", d.id, d.kind == kHook ? "hook " : "patch", (unsigned)c.valueRva, base + c.valueRva,
             SiteStateName(c.state), c.enabled ? "" : " (key off)", Hex(c.cur, d.len).c_str());
    }
    const std::string sum = PlanSummary(pl, ad.nSites);
    if (pl.verdict == PlanVerdict::Refuse) { LOGE("%s", sum.c_str()); return; }
    LOGI("%s", sum.c_str());
    int written = 0;
    for (size_t i = 0; i < ad.nSites; ++i) {
        if (!pl.sites[i].write) continue;
        const SiteDef& d = ad.sites[i];
        uint8_t* p = base + pl.sites[i].valueRva;
        DWORD old = 0;
        if (!VirtualProtect(p, d.len, PAGE_EXECUTE_READWRITE, &old)) { LOGE("patch_engine: VirtualProtect failed at %p (%lu): %s not written", p, GetLastError(), d.id); continue; }
        memcpy(p, d.patch, d.len);
        DWORD tmp = 0; VirtualProtect(p, d.len, old, &tmp);
        FlushInstructionCache(GetCurrentProcess(), p, d.len);
        LOGI("patch_engine: wrote %s at %p: [%s] -> [%s]", d.id, p, Hex(pl.sites[i].cur, d.len).c_str(), Hex(d.patch, d.len).c_str());
        ++written;
    }
    LOGI("patch_engine: %d of %d planned sites written", written, pl.nWrite);
}

} // namespace wsp
