# The review viewer: RmlUi + FreeType + Lua 5.1.1 (float numbers) -> viewer.js + viewer.wasm (emcmake, inside the pinned emsdk image).
# Sources come from viewer/core/fetch_sources.py (pins in viewer/pins.json); build with viewer/core/build.sh, not by hand.
cmake_minimum_required(VERSION 3.16)
project(napoleon_viewer C CXX)

set(SRC_ROOT "${CMAKE_SOURCE_DIR}/../../build/viewer/src" CACHE PATH "fetched sources")
set(CMAKE_CXX_STANDARD 17)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
# Reproducible objects: no absolute source paths in the output
add_compile_options("-ffile-prefix-map=${SRC_ROOT}=src" "-ffile-prefix-map=${CMAKE_SOURCE_DIR}=viewer")

# ---- FreeType: TTF only, no optional dependency (as Empire's rml_mod)
foreach(dep ZLIB BZIP2 PNG HARFBUZZ BROTLI)
  set(FT_DISABLE_${dep} ON CACHE BOOL "" FORCE)
endforeach()
add_subdirectory("${SRC_ROOT}/freetype" freetype EXCLUDE_FROM_ALL)
add_library(Freetype::Freetype ALIAS freetype)   # the name RmlUi's dependency check looks for

# ---- Lua 5.1.1 core and standard libraries (no lua.c / luac.c / print.c), luaconf.h already patched to float
file(GLOB LUA_SOURCES "${SRC_ROOT}/lua/src/*.c")
list(FILTER LUA_SOURCES EXCLUDE REGEX "/(lua|luac|print)\\.c$")
add_library(lua51 STATIC ${LUA_SOURCES})
target_include_directories(lua51 PUBLIC "${SRC_ROOT}/lua/src")
add_library(Lua::Lua INTERFACE IMPORTED)   # RmlUi uses an existing Lua::Lua target instead of find_package (and aliases it)
set_target_properties(Lua::Lua PROPERTIES INTERFACE_LINK_LIBRARIES lua51)

# ---- RmlUi: Core, FreeType font engine, Lua bindings (the viewer runs each screen's Lua view code)
set(RMLUI_SAMPLES OFF CACHE BOOL "" FORCE)
set(RMLUI_PRECOMPILED_HEADERS OFF CACHE BOOL "" FORCE)   # a PCH can carry absolute paths: keep the build reproducible
set(RMLUI_FONT_ENGINE "freetype" CACHE STRING "" FORCE)
set(RMLUI_LUA_BINDINGS ON CACHE BOOL "" FORCE)
set(RMLUI_LUA_BINDINGS_LIBRARY "lua" CACHE STRING "" FORCE)
set(RMLUI_THIRDPARTY_CONTAINERS ON CACHE BOOL "" FORCE)
add_subdirectory("${SRC_ROOT}/rmlui" rmlui EXCLUDE_FROM_ALL)
# RmlUi 6.3's Lua bindings call two Lua 5.2 functions its 5.1 shim lacks (luaL_setfuncs, lua_tointegerx): J31 report
target_compile_options(rmlui_lua PRIVATE -include "${CMAKE_SOURCE_DIR}/src/lua51_compat.h")

add_executable(viewer src/viewer.cpp "${SRC_ROOT}/rmlui/Backends/RmlUi_Renderer_GL3.cpp")
target_include_directories(viewer PRIVATE "${SRC_ROOT}/rmlui/Backends")
target_link_libraries(viewer PRIVATE RmlUi::RmlUi RmlUi::Lua lua51)
set_target_properties(viewer PROPERTIES SUFFIX ".js")
target_link_options(viewer PRIVATE
  -sMODULARIZE=1 -sEXPORT_NAME=createViewer -sENVIRONMENT=web,node
  -sMIN_WEBGL_VERSION=2 -sMAX_WEBGL_VERSION=2
  -sALLOW_MEMORY_GROWTH=1 -sFORCE_FILESYSTEM=1
  "-sEXPORTED_RUNTIME_METHODS=['FS','ccall','cwrap','HEAPU8','HEAPF32']"
  "-sEXPORTED_FUNCTIONS=['_malloc','_free']")
