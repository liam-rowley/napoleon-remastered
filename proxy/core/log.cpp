// log.cpp - one log file per launch, UTC timestamps (empire-remastered's local-time logs caused misreads), previous launch kept.
// <dir>\<base>.log is this launch; the previous one is moved to <base>.prev.log at open. Win32 file API only (callable from
// DllMain and from the crash handler), unbuffered writes so a crash loses nothing, one lock.
#include "runtime.h"
#include <cstdarg>
#include <cstdio>

namespace wsp {
namespace {
HANDLE s_file = INVALID_HANDLE_VALUE;
LogLevel s_min = LogLevel::Info;
CRITICAL_SECTION s_cs;
bool s_csInit = false;
std::wstring s_path;
}

std::wstring LogPath() { return s_path; }

void LogOpen(const std::wstring& dir, const std::wstring& baseName, LogLevel minLevel) {
    if (!s_csInit) { InitializeCriticalSection(&s_cs); s_csInit = true; }
    s_min = minLevel;
    CreateDirectoryW(dir.c_str(), nullptr);
    s_path = dir + baseName + L".log";
    const std::wstring prev = dir + baseName + L".prev.log";
    MoveFileExW(s_path.c_str(), prev.c_str(), MOVEFILE_REPLACE_EXISTING);   // fails harmlessly on the first launch
    s_file = CreateFileW(s_path.c_str(), GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_DELETE, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
}

void LogWrite(LogLevel lvl, const char* fmt, ...) {
    if ((int)lvl < (int)s_min) return;
    char msg[2048];
    va_list ap; va_start(ap, fmt);
    vsnprintf(msg, sizeof msg, fmt, ap);
    va_end(ap);
    static const char* names[] = { "DEBUG", "INFO ", "WARN ", "ERROR" };
    SYSTEMTIME st; GetSystemTime(&st);
    char line[2200];
    const int n = snprintf(line, sizeof line, "%04d-%02d-%02dT%02d:%02d:%02d.%03dZ [%s] [t%lu] %s\r\n", st.wYear, st.wMonth, st.wDay,
                           st.wHour, st.wMinute, st.wSecond, st.wMilliseconds, names[(int)lvl], GetCurrentThreadId(), msg);
    if (!s_csInit) return;
    EnterCriticalSection(&s_cs);
    if (s_file != INVALID_HANDLE_VALUE && n > 0) { DWORD wr = 0; WriteFile(s_file, line, (DWORD)(n < (int)sizeof line ? n : (int)sizeof line - 1), &wr, nullptr); }
    LeaveCriticalSection(&s_cs);
    OutputDebugStringA(line);
}

std::string Narrow(const std::wstring& w) {
    if (w.empty()) return {};
    const int n = WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(), nullptr, 0, nullptr, nullptr);
    std::string s(n, '\0');
    WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(), &s[0], n, nullptr, nullptr);
    return s;
}

} // namespace wsp
