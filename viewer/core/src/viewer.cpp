// purpose: the review viewer's wasm entry points: RmlUi 6.3 (GL3 renderer on WebGL2, FreeType fonts, Lua bindings) driven from JS
// usage: built by viewer/core/build.sh into viewer.js + viewer.wasm; called through Module.ccall from viewer/core/web/viewer_host.js
// when: change it when the host page or the headless renderer needs a new entry point; game-agnostic (viewer/core is a core candidate)
// not-a-verb: C++ source compiled into the viewer, not a script
//
// The JS side owns the files (it writes RML, RCSS, Lua, fonts and art into the in-memory file system), the frame loop and input; this
// side owns RmlUi. Pixels are read back here (viewer_read_pixels) so the review page and the PNG renderer take the same bytes.
#include <RmlUi/Core.h>
#include <RmlUi/Lua.h>
#include <emscripten/emscripten.h>
#include <emscripten/html5.h>
#include <GLES3/gl3.h>
#include <cstdio>
#include <string>
#include <vector>
#include "RmlUi_Renderer_GL3.h"

extern "C" {
#include <lauxlib.h>
#include <lua.h>
#include <lualib.h>
}

namespace {

class System : public Rml::SystemInterface {
public:
	double fixed_time = -1.0;   // >= 0: frozen clock (headless renders), else the browser clock
	double GetElapsedTime() override { return fixed_time >= 0 ? fixed_time : emscripten_get_now() / 1000.0; }
	bool LogMessage(Rml::Log::Type type, const Rml::String& message) override {
		static const char* names[] = {"always", "error", "assert", "warning", "info", "debug"};
		std::printf("[rml %s] %s\n", type < 6 ? names[type] : "?", message.c_str());
		return true;
	}
};

System g_system;
RenderInterface_GL3* g_render = nullptr;
Rml::Context* g_context = nullptr;
Rml::ElementDocument* g_document = nullptr;
EMSCRIPTEN_WEBGL_CONTEXT_HANDLE g_gl = 0;
int g_width = 0, g_height = 0;
std::vector<unsigned char> g_pixels;
float g_box[4];
std::string g_result;

}  // namespace

extern "C" {

// Create the WebGL2 context on #canvas, RmlUi with Lua, and the "main" context. Returns 1 on success.
EMSCRIPTEN_KEEPALIVE int viewer_init(int width, int height, float dp_ratio) {
	EmscriptenWebGLContextAttributes attrs;
	emscripten_webgl_init_context_attributes(&attrs);
	attrs.majorVersion = 2;
	attrs.alpha = false;
	attrs.depth = false;
	attrs.stencil = true;   // the GL3 renderer clips with the stencil buffer
	attrs.antialias = false;   // RmlUi's GL3 render layers do their own MSAA
	attrs.preserveDrawingBuffer = true;
	g_gl = emscripten_webgl_create_context("#canvas", &attrs);
	if (g_gl <= 0) {
		std::printf("[viewer] emscripten_webgl_create_context failed: %d\n", (int)g_gl);
		return 0;
	}
	emscripten_webgl_make_context_current(g_gl);
	Rml::String message;
	if (!RmlGL3::Initialize(&message)) {
		std::printf("[viewer] RmlGL3::Initialize failed: %s\n", message.c_str());
		return 0;
	}
	std::printf("[viewer] %s\n", message.c_str());
	g_render = new RenderInterface_GL3();
	if (!*g_render) {
		std::printf("[viewer] the GL3 render interface did not initialise\n");
		return 0;
	}
	g_width = width;
	g_height = height;
	emscripten_set_canvas_element_size("#canvas", width, height);
	g_render->SetViewport(width, height);
	Rml::SetSystemInterface(&g_system);
	Rml::SetRenderInterface(g_render);
	Rml::Initialise();
	Rml::Lua::Initialise();
	g_context = Rml::CreateContext("main", Rml::Vector2i(width, height));
	if (!g_context)
		return 0;
	g_context->SetDensityIndependentPixelRatio(dp_ratio);
	return 1;
}

EMSCRIPTEN_KEEPALIVE int viewer_load_font(const char* path, int fallback) {
	return Rml::LoadFontFace(path, fallback != 0) ? 1 : 0;
}

// Replace the shown document. Returns 1 on success.
EMSCRIPTEN_KEEPALIVE int viewer_load_document(const char* path) {
	if (g_document) {
		g_document->Close();
		g_context->Update();
		g_document = nullptr;
	}
	g_document = g_context->LoadDocument(path);
	if (!g_document)
		return 0;
	g_document->Show();
	return 1;
}

// New backbuffer size and dp ratio (D19: the caller computes height / 1080 x slider).
EMSCRIPTEN_KEEPALIVE void viewer_resize(int width, int height, float dp_ratio) {
	g_width = width;
	g_height = height;
	emscripten_set_canvas_element_size("#canvas", width, height);
	g_render->SetViewport(width, height);
	g_context->SetDimensions(Rml::Vector2i(width, height));
	g_context->SetDensityIndependentPixelRatio(dp_ratio);
}

// t >= 0 freezes RmlUi's clock at t seconds (deterministic renders); t < 0 returns it to the browser clock.
EMSCRIPTEN_KEEPALIVE void viewer_set_time(double t) { g_system.fixed_time = t; }

EMSCRIPTEN_KEEPALIVE void viewer_frame() {
	g_context->Update();
	g_render->BeginFrame();
	g_render->Clear();
	g_context->Render();
	g_render->EndFrame();
}

EMSCRIPTEN_KEEPALIVE void viewer_mouse_move(int x, int y, int mods) { g_context->ProcessMouseMove(x, y, mods); }
EMSCRIPTEN_KEEPALIVE void viewer_mouse_down(int button, int mods) { g_context->ProcessMouseButtonDown(button, mods); }
EMSCRIPTEN_KEEPALIVE void viewer_mouse_up(int button, int mods) { g_context->ProcessMouseButtonUp(button, mods); }
EMSCRIPTEN_KEEPALIVE void viewer_mouse_wheel(float dy, int mods) { g_context->ProcessMouseWheel(Rml::Vector2f(0.f, dy), mods); }
EMSCRIPTEN_KEEPALIVE void viewer_mouse_leave() { g_context->ProcessMouseLeave(); }

// The current backbuffer as RGBA, top row first: width * height * 4 bytes at the returned address.
EMSCRIPTEN_KEEPALIVE unsigned char* viewer_read_pixels() {
	const size_t row = (size_t)g_width * 4;
	g_pixels.resize(row * g_height);
	std::vector<unsigned char> flipped(g_pixels.size());
	glPixelStorei(GL_PACK_ALIGNMENT, 1);
	glReadPixels(0, 0, g_width, g_height, GL_RGBA, GL_UNSIGNED_BYTE, flipped.data());
	for (int y = 0; y < g_height; y++)
		std::copy(flipped.begin() + (g_height - 1 - y) * row, flipped.begin() + (g_height - y) * row, g_pixels.begin() + y * row);
	return g_pixels.data();
}

// Border box of the element with this id in backbuffer pixels: 4 floats (x, y, w, h) at the returned address, or null.
EMSCRIPTEN_KEEPALIVE float* viewer_element_box(const char* id) {
	Rml::Element* e = g_document ? g_document->GetElementById(id) : nullptr;
	if (!e)
		return nullptr;
	Rml::Vector2f at = e->GetAbsoluteOffset(Rml::BoxArea::Border);
	Rml::Vector2f size = e->GetBox().GetSize(Rml::BoxArea::Border);
	g_box[0] = at.x;
	g_box[1] = at.y;
	g_box[2] = size.x;
	g_box[3] = size.y;
	return g_box;
}

// Run a Lua chunk in a fresh state with the standard libraries and return what it returns as a string (or "error: ...").
// Needs no canvas, so the build's number test runs it under Node. The number type is compiled in, so this state proves it for
// the document state too.
EMSCRIPTEN_KEEPALIVE const char* viewer_lua_eval(const char* code) {
	lua_State* L = luaL_newstate();
	luaL_openlibs(L);
	if (luaL_loadstring(L, code) != 0 || lua_pcall(L, 0, 1, 0) != 0) {
		g_result = std::string("error: ") + (lua_tostring(L, -1) ? lua_tostring(L, -1) : "?");
	} else {
		const char* s = lua_tostring(L, -1);
		g_result = s ? s : "nil";
	}
	lua_close(L);
	return g_result.c_str();
}

// sizeof(lua_Number): 4 on the engine's build.
EMSCRIPTEN_KEEPALIVE int viewer_lua_number_size() { return (int)sizeof(lua_Number); }

}  // extern "C"
