// purpose: the review viewer's page glue: load viewer.wasm, write a screen's files into its file system, run frames, route input, expose a capture API
// usage: <script src="viewer.js"></script><script src="viewer_host.js"></script> in viewer/core/web/index.html; URL ?w=&h=&slider=&ratio=&headless=1
// when: every review page and every headless render (viewer/core/render.py drives window.viewer); game-agnostic (core candidate)
// not-a-verb: browser glue served with the viewer, not a command
'use strict';

(function () {
  const params = new URLSearchParams(location.search);
  const statusEl = document.getElementById('status');
  const log = (msg) => {
    console.log('[host] ' + msg);
    if (statusEl) statusEl.textContent += msg + '\n';
  };

  // D19: dp ratio = backbuffer height / 1080 x slider; an explicit ?ratio= wins (render.py passes the final ratio)
  function ratioFor(h, slider, explicit) {
    return explicit > 0 ? explicit : (h / 1080) * slider;
  }

  async function fetchBytes(path) {
    const r = await fetch(path);
    if (!r.ok) throw new Error(`fetch ${path}: HTTP ${r.status}`);
    return new Uint8Array(await r.arrayBuffer());
  }

  async function start() {
    const canvas = document.getElementById('canvas');
    const t0 = performance.now();
    const m = await createViewer({
      canvas,
      print: (s) => console.log(s),
      printErr: (s) => console.error(s),
    });
    log(`wasm instantiated in ${Math.round(performance.now() - t0)} ms`);

    const screen = JSON.parse(new TextDecoder().decode(await fetchBytes('screen/screen.json')));
    m.FS.mkdirTree('/screen');
    m.FS.mkdirTree('/fonts');
    for (const f of screen.files) m.FS.writeFile('/screen/' + f, await fetchBytes('screen/' + f));
    for (const f of screen.fonts) m.FS.writeFile('/fonts/' + f, await fetchBytes('fonts/' + f));
    log(`${screen.files.length} screen files and ${screen.fonts.length} font(s) loaded`);

    let w = +params.get('w') || 1280, h = +params.get('h') || 720;
    let slider = +params.get('slider') || 1.0, explicit = +params.get('ratio') || 0;
    const headless = params.get('headless') === '1';
    canvas.width = w;
    canvas.height = h;
    if (!m.ccall('viewer_init', 'number', ['number', 'number', 'number'], [w, h, ratioFor(h, slider, explicit)]))
      throw new Error('viewer_init failed (see the console)');
    if (headless) m.ccall('viewer_set_time', null, ['number'], [0]);
    for (const f of screen.fonts)
      if (!m.ccall('viewer_load_font', 'number', ['string', 'number'], ['/fonts/' + f, 1])) throw new Error('font failed: ' + f);
    if (!m.ccall('viewer_load_document', 'number', ['string'], ['/screen/' + screen.document]))
      throw new Error('document failed: ' + screen.document);
    log(`${screen.title}: ${w}x${h}, dp ratio ${ratioFor(h, slider, explicit).toFixed(4)}`);

    const frame = () => m.ccall('viewer_frame', null, [], []);
    const resize = (nw, nh, r) => {
      w = nw; h = nh;
      canvas.width = w;
      canvas.height = h;
      m.ccall('viewer_resize', null, ['number', 'number', 'number'], [w, h, r]);
    };
    const box = (id) => {
      const p = m.ccall('viewer_element_box', 'number', ['string'], [id]);
      return p ? Array.from(m.HEAPF32.subarray(p >> 2, (p >> 2) + 4)) : null;
    };
    const capture = () => {   // RGBA, top row first, base64 (Playwright moves strings cheaply)
      frame();
      const p = m.ccall('viewer_read_pixels', 'number', [], []);
      const bytes = m.HEAPU8.subarray(p, p + w * h * 4);
      let s = '';
      for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
      return { w, h, rgba: btoa(s) };
    };

    // Input: CSS pixels -> backbuffer pixels (the canvas may be shown scaled)
    const toPx = (e) => {
      const r = canvas.getBoundingClientRect();
      return [Math.round((e.clientX - r.left) * w / r.width), Math.round((e.clientY - r.top) * h / r.height)];
    };
    const mods = (e) => (e.ctrlKey ? 1 : 0) | (e.shiftKey ? 2 : 0) | (e.altKey ? 4 : 0);
    // Mouse (and pen): hover, press, release. Touch has no hover and no wheel: a tap is move + press + release at the end, and a
    // drag scrolls the scrollable element under the finger (viewer_scroll_at); `touch-action: none` keeps the page from scrolling.
    canvas.style.touchAction = 'none';
    const move = (x, y, md) => m.ccall('viewer_mouse_move', null, ['number', 'number', 'number'], [x, y, md]);
    const down = (b, md) => m.ccall('viewer_mouse_down', null, ['number', 'number'], [b, md]);
    const up = (b, md) => m.ccall('viewer_mouse_up', null, ['number', 'number'], [b, md]);
    const scrollAt = (x, y, dy) => m.ccall('viewer_scroll_at', 'number', ['number', 'number', 'number'], [x, y, dy]);
    const touch = { id: null, x: 0, y: 0, lastY: 0, moved: false };
    canvas.addEventListener('pointermove', (e) => {
      const [x, y] = toPx(e);
      if (e.pointerType !== 'touch') return move(x, y, mods(e));
      if (e.pointerId !== touch.id) return;
      if (!touch.moved && Math.abs(y - touch.y) + Math.abs(x - touch.x) > 10 * h / canvas.getBoundingClientRect().height) touch.moved = true;
      if (touch.moved) { scrollAt(touch.x, touch.y, touch.lastY - y); touch.lastY = y; }
    });
    canvas.addEventListener('pointerdown', (e) => {
      const [x, y] = toPx(e);
      if (e.pointerType !== 'touch') return down(e.button, mods(e));
      Object.assign(touch, { id: e.pointerId, x, y, lastY: y, moved: false });
      canvas.setPointerCapture(e.pointerId);
    });
    canvas.addEventListener('pointerup', (e) => {
      if (e.pointerType !== 'touch') return up(e.button, mods(e));
      if (e.pointerId !== touch.id) return;
      if (!touch.moved) { move(touch.x, touch.y, 0); down(0, 0); frame(); up(0, 0); }
      touch.id = null;
    });
    canvas.addEventListener('pointercancel', () => { touch.id = null; });
    canvas.addEventListener('pointerleave', (e) => { if (e.pointerType !== 'touch') m.ccall('viewer_mouse_leave', null, [], []); });
    canvas.addEventListener('wheel', (e) => { e.preventDefault(); m.ccall('viewer_mouse_wheel', null, ['number', 'number'], [Math.sign(e.deltaY), mods(e)]); }, { passive: false });
    canvas.addEventListener('contextmenu', (e) => e.preventDefault());

    // The scale picker (plain inputs: size and slider, or an explicit ratio)
    const picker = document.getElementById('picker');
    if (picker) {
      const set = (id, v) => { const el = document.getElementById(id); if (el) el.value = v; };
      set('pk_w', w); set('pk_h', h); set('pk_slider', Math.round(slider * 100)); set('pk_ratio', explicit || '');
      const show = () => { document.getElementById('pk_out').textContent = 'dp ratio ' + ratioFor(h, slider, explicit).toFixed(4); };
      picker.addEventListener('change', () => {
        slider = (+document.getElementById('pk_slider').value || 100) / 100;
        explicit = +document.getElementById('pk_ratio').value || 0;
        resize(+document.getElementById('pk_w').value || w, +document.getElementById('pk_h').value || h, ratioFor(
          +document.getElementById('pk_h').value || h, slider, explicit));
        show();
      });
      show();
    }

    window.viewer = { module: m, frame, resize, box, capture, ratioFor,
      mouseMove: (x, y) => m.ccall('viewer_mouse_move', null, ['number', 'number', 'number'], [x, y, 0]),
      mouseDown: (b) => m.ccall('viewer_mouse_down', null, ['number', 'number'], [b, 0]),
      mouseUp: (b) => m.ccall('viewer_mouse_up', null, ['number', 'number'], [b, 0]),
      scrollAt,
      wheel: (dy) => m.ccall('viewer_mouse_wheel', null, ['number', 'number'], [dy, 0]),
      element: (id) => JSON.parse(m.ccall('viewer_element_json', 'string', ['string'], [id])),
      lua: (code) => m.ccall('viewer_lua_eval', 'string', ['string'], [code]) };
    frame();
    if (!headless) {
      const loop = () => { frame(); requestAnimationFrame(loop); };
      requestAnimationFrame(loop);
    }
    log('ready');
    window.viewerReady = true;
  }

  start().catch((e) => { log('ERROR ' + (e && e.message ? e.message : e)); console.error(e); window.viewerError = String(e); });
})();
