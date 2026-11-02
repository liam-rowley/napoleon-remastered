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
#include <cstring>
#include <string>
#include <vector>
#include "RmlUi_Renderer_GL3.h"
#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#define STBI_ONLY_JPEG
#define STBI_NO_STDIO
#include "stb_image.h"

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

// The GL3 backend loads only TGA; review art is PNG or JPEG (the artifact serves web image types only), decoded by stb_image.
class Render : public RenderInterface_GL3 {
public:
	Rml::TextureHandle LoadTexture(Rml::Vector2i& dimensions, const Rml::String& source) override {
		if (source.size() > 4 && source.compare(source.size() - 4, 4, ".tga") == 0)
			return RenderInterface_GL3::LoadTexture(dimensions, source);
		Rml::FileInterface* files = Rml::GetFileInterface();
		Rml::FileHandle f = files->Open(source);
		if (!f)
			return 0;
		std::vector<unsigned char> data(files->Length(f));
		files->Read(data.data(), data.size(), f);
		files->Close(f);
		int w = 0, h = 0, n = 0;
		unsigned char* px = stbi_load_from_memory(data.data(), (int)data.size(), &w, &h, &n, 4);
		if (!px) {
			Rml::Log::Message(Rml::Log::LT_ERROR, "stb_image could not decode %s: %s", source.c_str(), stbi_failure_reason());
			return 0;
		}
		for (int i = 0; i < w * h * 4; i += 4)   // RmlUi 6 textures are premultiplied
			for (int j = 0; j < 3; j++)
				px[i + j] = (unsigned char)((px[i + j] * px[i + 3]) / 255);
		dimensions = Rml::Vector2i(w, h);
		Rml::TextureHandle t = GenerateTexture({px, (size_t)w * h * 4}, dimensions);
		stbi_image_free(px);
		return t;
	}
};

System g_system;
Render* g_render = nullptr;
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
	g_render = new Render();
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

// Keyboard: a named key (Tab, Enter, Space, Escape, Up, Down, Left, Right, Home, End) goes down or up; mods as the mouse calls. Tab moves
// the focus between tab-index elements and sets :focus-visible (J34). Returns 1 if the name is known.
EMSCRIPTEN_KEEPALIVE int viewer_key(const char* name, int down, int mods) {
	static const struct { const char* n; Rml::Input::KeyIdentifier k; } keys[] = {
		{"Tab", Rml::Input::KI_TAB}, {"Enter", Rml::Input::KI_RETURN}, {"Space", Rml::Input::KI_SPACE}, {"Escape", Rml::Input::KI_ESCAPE},
		{"Up", Rml::Input::KI_UP}, {"Down", Rml::Input::KI_DOWN}, {"Left", Rml::Input::KI_LEFT}, {"Right", Rml::Input::KI_RIGHT},
		{"Home", Rml::Input::KI_HOME}, {"End", Rml::Input::KI_END}};
	for (const auto& e : keys) {
		if (std::strcmp(e.n, name) == 0) {
			if (down)
				g_context->ProcessKeyDown(e.k, mods);
			else
				g_context->ProcessKeyUp(e.k, mods);
			return 1;
		}
	}
	return 0;
}

// Touch drag: scroll the nearest scrollable element under (x, y) by dy backbuffer pixels (a phone has no wheel). Returns 1 if it moved.
EMSCRIPTEN_KEEPALIVE int viewer_scroll_at(int x, int y, float dy) {
	for (Rml::Element* e = g_context->GetElementAtPoint(Rml::Vector2f((float)x, (float)y)); e; e = e->GetParentNode()) {
		if (e->GetScrollHeight() > e->GetClientHeight() + 0.5f) {
			const float before = e->GetScrollTop();
			e->SetScrollTop(before + dy);
			return e->GetScrollTop() != before ? 1 : 0;
		}
	}
	return 0;
}

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

// The element's state for checks, as JSON: {"x","y","w","h","scroll_top","hover","active","rml"} (or "null").
EMSCRIPTEN_KEEPALIVE const char* viewer_element_json(const char* id) {
	Rml::Element* e = g_document ? g_document->GetElementById(id) : nullptr;
	if (!e) {
		g_result = "null";
		return g_result.c_str();
	}
	float* b = viewer_element_box(id);
	Rml::String rml = e->GetInnerRML(), esc;
	for (char c : rml) {
		if (c == '"' || c == '\\')
			esc += '\\';
		if ((unsigned char)c >= 0x20)
			esc += c;
	}
	char head[256];
	std::snprintf(head, sizeof head, "{\"x\":%g,\"y\":%g,\"w\":%g,\"h\":%g,\"scroll_top\":%g,\"hover\":%s,\"active\":%s,\"rml\":\"", b[0], b[1],
		b[2], b[3], e->GetScrollTop(), e->IsPseudoClassSet("hover") ? "true" : "false", e->IsPseudoClassSet("active") ? "true" : "false");
	g_result = head + esc + "\"}";
	return g_result.c_str();
}

namespace {

bool ClipsX(Rml::Element* e) { return e->GetComputedValues().overflow_x() != Rml::Style::Overflow::Visible; }
bool ClipsY(Rml::Element* e) { return e->GetComputedValues().overflow_y() != Rml::Style::Overflow::Visible; }

std::string Describe(Rml::Element* e) {
	std::string s = e->GetTagName();
	if (!e->GetId().empty())
		s += "#" + e->GetId();
	std::string cls = e->GetClassNames();
	for (char& c : cls)
		if (c == ' ')
			c = '.';
	if (!cls.empty())
		s += "." + cls;
	for (char& c : s)
		if (c == '"' || c == '\\')
			c = '\'';
	return s;
}

void CheckOverflow(Rml::Element* e, Rml::Element* parent, bool clip_x, bool clip_y, std::string& out, int& count) {
	const float tol = 1.0f;   // sub-pixel layout at dp ratios like 0.85
	if (!e->IsVisible())
		return;
	const std::string tag = e->GetTagName();
	if (tag.compare(0, 6, "scroll") == 0 || tag.compare(0, 6, "slider") == 0 || tag[0] == '#')
		return;
	const Rml::Vector2f at = e->GetAbsoluteOffset(Rml::BoxArea::Border), size = e->GetBox().GetSize(Rml::BoxArea::Border);
	const Rml::ComputedValues& cv = e->GetComputedValues();
	const bool floating = cv.position() == Rml::Style::Position::Absolute || cv.position() == Rml::Style::Position::Fixed;
	auto add = [&](const char* kind, const char* detail) {
		char buf[512];
		std::snprintf(buf, sizeof buf, "%s{\"kind\":\"%s\",\"element\":\"%s\",\"box\":[%g,%g,%g,%g],\"detail\":\"%s\"}", count ? "," : "", kind,
			Describe(e).c_str(), at.x, at.y, size.x, size.y, detail);
		out += buf;
		count++;
	};
	if (size.x > 0 && size.y > 0) {
		if ((!clip_x && (at.x < -tol || at.x + size.x > g_width + tol)) || (!clip_y && (at.y < -tol || at.y + size.y > g_height + tol)))
			add("outside_viewport", "border box leaves the viewport");
		if (parent && !floating) {
			const Rml::Vector2f pat = parent->GetAbsoluteOffset(Rml::BoxArea::Content), psz = parent->GetBox().GetSize(Rml::BoxArea::Content);
			if (psz.x > 0 && psz.y > 0 &&
				((!ClipsX(parent) && (at.x < pat.x - tol || at.x + size.x > pat.x + psz.x + tol)) ||
					(!ClipsY(parent) && (at.y < pat.y - tol || at.y + size.y > pat.y + psz.y + tol)))) {
				char d[160];
				std::snprintf(d, sizeof d, "outside parent content box %g,%g %gx%g", pat.x, pat.y, psz.x, psz.y);
				add("outside_parent", d);
			}
		}
		const auto& c = cv;
		if (c.overflow_x() == Rml::Style::Overflow::Visible && e->GetScrollWidth() > e->GetClientWidth() + tol && e->GetNumChildren() > 0) {
			char d[96];
			std::snprintf(d, sizeof d, "content %g wide in a %g box", e->GetScrollWidth(), e->GetClientWidth());
			add("text_wider_than_box", d);
		}
		if (c.overflow_y() == Rml::Style::Overflow::Visible && e->GetScrollHeight() > e->GetClientHeight() + tol && e->GetNumChildren() > 0 &&
			c.height().type != Rml::Style::Height::Auto) {
			char d[96];
			std::snprintf(d, sizeof d, "content %g high in a %g box", e->GetScrollHeight(), e->GetClientHeight());
			add("content_taller_than_box", d);
		}
	}
	for (int i = 0; i < e->GetNumChildren(); i++)
		CheckOverflow(e->GetChild(i), e, clip_x || ClipsX(e), clip_y || ClipsY(e), out, count);
}

}  // namespace

// Layout problems of the shown document found by the renderer (J34 corner gate), as a JSON array: border boxes outside the viewport or
// outside a non-clipping parent's content box (absolute and fixed elements are checked against the viewport only), and content wider or
// taller than its own box. Per axis, an ancestor that scrolls or clips (overflow other than visible) exempts what is inside it on that axis.
EMSCRIPTEN_KEEPALIVE const char* viewer_overflow_json() {
	std::string out = "[";
	int count = 0;
	if (g_document)
		CheckOverflow(g_document, nullptr, false, false, out, count);
	g_result = out + "]";
	return g_result.c_str();
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
