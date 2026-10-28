// crash.cpp - in-process crash capture: a minidump into <mod>\dumps\<launch id>_<code>.dmp, named in the log.
// Mode (config proxy.minidump): 0 off; 1 (default) unhandled exceptions only, through the top-level filter, so a first-chance
// exception the engine handles itself never leaves a dump (the PC test counts dumps); 2 also dumps the first fatal first-chance
// exception (the empire-remastered behaviour; for when the engine's own top-level filter replaces ours). In every mode >= 1 the vectored handler
// logs the first few fatal first-chance exceptions with module+offset, as evidence.
// The in-process dump is empty when the heap is corrupt (empire-remastered LEARNINGS lesson 23): WER LocalDumps (proxy/tools/wer_localdumps.ps1)
// is the out-of-process backstop; read WER first.
#include "runtime.h"
#include <dbghelp.h>

namespace wsp {
namespace {
int s_mode = 0;
LPTOP_LEVEL_EXCEPTION_FILTER s_prev = nullptr;
volatile LONG s_dumped = 0, s_logged = 0;

bool Fatal(DWORD c) {
    return c == EXCEPTION_ACCESS_VIOLATION || c == EXCEPTION_ILLEGAL_INSTRUCTION || c == EXCEPTION_STACK_OVERFLOW || c == EXCEPTION_INT_DIVIDE_BY_ZERO ||
           c == EXCEPTION_PRIV_INSTRUCTION || c == EXCEPTION_IN_PAGE_ERROR || c == 0xC0000374 /* STATUS_HEAP_CORRUPTION */ || c == 0xC0000409 /* stack buffer overrun */;
}

void Where(void* addr, char* out, size_t n) {
    HMODULE mod = nullptr; wchar_t name[MAX_PATH] = L"?";
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCWSTR)addr, &mod);
    if (mod) GetModuleFileNameW(mod, name, MAX_PATH);
    const wchar_t* base = wcsrchr(name, L'\\');
    snprintf(out, n, "%ls+0x%lx", base ? base + 1 : name, mod ? (unsigned long)((BYTE*)addr - (BYTE*)mod) : 0ul);
}

void Dump(EXCEPTION_POINTERS* ep, const char* why) {
    if (InterlockedExchange(&s_dumped, 1)) return;   // one dump per launch
    const std::wstring dir = Rt().modDir + L"dumps\\";
    CreateDirectoryW(dir.c_str(), nullptr);
    wchar_t name[MAX_PATH];
    swprintf(name, MAX_PATH, L"%ls%hs_%08lx.dmp", dir.c_str(), Rt().launchId.c_str(), ep->ExceptionRecord->ExceptionCode);
    HANDLE f = CreateFileW(name, GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (f == INVALID_HANDLE_VALUE) { LOGE("crash: cannot create %ls (%lu)", name, GetLastError()); return; }
    MINIDUMP_EXCEPTION_INFORMATION mei{ GetCurrentThreadId(), ep, FALSE };
    const BOOL ok = MiniDumpWriteDump(GetCurrentProcess(), GetCurrentProcessId(), f,
                                      (MINIDUMP_TYPE)(MiniDumpWithIndirectlyReferencedMemory | MiniDumpWithDataSegs | MiniDumpWithThreadInfo | MiniDumpWithUnloadedModules),
                                      &mei, nullptr, nullptr);
    CloseHandle(f);
    LOGE("crash: minidump (%s) %s: %ls", why, ok ? "written" : "FAILED", name);
}

LONG WINAPI TopLevel(EXCEPTION_POINTERS* ep) {
    char w[300]; Where(ep->ExceptionRecord->ExceptionAddress, w, sizeof w);
    LOGE("crash: UNHANDLED exception 0x%08lx at %p = %s (thread %lu)", ep->ExceptionRecord->ExceptionCode, ep->ExceptionRecord->ExceptionAddress, w, GetCurrentThreadId());
    Dump(ep, "unhandled");
    return s_prev ? s_prev(ep) : EXCEPTION_CONTINUE_SEARCH;
}

LONG WINAPI Vectored(EXCEPTION_POINTERS* ep) {
    const DWORD code = ep->ExceptionRecord->ExceptionCode;
    if (!Fatal(code)) return EXCEPTION_CONTINUE_SEARCH;
    if (InterlockedIncrement(&s_logged) <= 5) {
        char w[300]; Where(ep->ExceptionRecord->ExceptionAddress, w, sizeof w);
        LOGW("crash: first-chance exception 0x%08lx at %s (thread %lu)%s - may be handled by the game", code, w, GetCurrentThreadId(),
             code == EXCEPTION_ACCESS_VIOLATION ? (ep->ExceptionRecord->ExceptionInformation[0] ? ", writing" : ", reading") : "");
        if (code == EXCEPTION_ACCESS_VIOLATION) LOGW("crash:   faulting address %p", (void*)ep->ExceptionRecord->ExceptionInformation[1]);
    }
    if (s_mode >= 2) Dump(ep, "first-chance");
    return EXCEPTION_CONTINUE_SEARCH;
}
} // namespace

void CrashInstall(int mode) {
    s_mode = mode;
    if (mode <= 0) { LOGI("crash: in-process minidumps off (proxy.minidump=0); WER LocalDumps still applies if enabled"); return; }
    s_prev = SetUnhandledExceptionFilter(TopLevel);
    AddVectoredExceptionHandler(1, Vectored);
    LOGI("crash: minidump mode %d (%s), dumps go to %ls", mode, mode >= 2 ? "unhandled + first fatal first-chance" : "unhandled only",
         (Rt().modDir + L"dumps\\").c_str());
}

} // namespace wsp
