// Wine smoke host (proxy/tools/build.sh smoke): stands in for the game exe. Loads the proxy d3d9.dll from its own folder through the
// import-free LoadLibrary path, calls the exports the game imports (Direct3DCreate9, D3DPERF_BeginEvent/EndEvent), unloads, exits 0.
// The script then checks the proxy's log: launch line, guard verdict, plan, backend, a clean detach.
#include <windows.h>
#include <cstdio>
typedef void* (WINAPI* Create9)(UINT);
typedef int (WINAPI* Begin)(DWORD, LPCWSTR);
typedef int (WINAPI* End)(void);
int main() {
    HMODULE h = LoadLibraryW(L".\\d3d9.dll");
    if (!h) { printf("smoke: LoadLibrary failed %lu\n", GetLastError()); return 2; }
    Begin b = (Begin)(void*)GetProcAddress(h, "D3DPERF_BeginEvent"); End e = (End)(void*)GetProcAddress(h, "D3DPERF_EndEvent");
    Create9 c = (Create9)(void*)GetProcAddress(h, "Direct3DCreate9");
    if (!b || !e || !c) { printf("smoke: missing export\n"); return 3; }
    b(0, L"smoke"); e();
    void* d3d = c(32);
    printf("smoke: Direct3DCreate9 -> %p\n", d3d);
    if (d3d) { typedef ULONG (WINAPI* Rel)(void*); ((Rel)(*(void***)d3d)[2])(d3d); }
    FreeLibrary(h);
    return 0;
}
