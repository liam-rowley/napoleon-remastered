// purpose: prove the built viewer's Lua uses the engine's float32 numbers, by running Lua through the built viewer.wasm under Node
// usage: node viewer/core/tests/lua_numbers.mjs build/viewer/out/viewer.js   (exit 1 on any mismatch; build.sh test runs it)
// when: every viewer build (local --docker and CI); a double-number Lua fails the first two cases
// not-a-verb: a build test, run by viewer/core/build.sh
import { createRequire } from 'node:module';
import path from 'node:path';

const require = createRequire(import.meta.url);
const createViewer = require(path.resolve(process.argv[2]));
const m = await createViewer();

// [Lua chunk, expected on float32, what a double build returns]
const CASES = [
  // Empire's example (LEARNINGS_ENGINE "The repo's Lua 5.1 is float32 like the engine"): 2550 x 0.319999992 is 816 in float32
  ['return math.floor(2550 * 0.319999992)', '816', '815'],
  // 2^24 + 1 is not representable in float32
  ['return 16777217 - 16777216', '0', '1'],
  ['return string.format("%d", 2550 * 0.319999992)', '816', '815'],
  // LUA_NUMBER_FMT "%.7g"
  ['return tostring(1/3)', '0.3333333', '0.33333333333333'],
  ['return tostring(16777216)', '1.677722e+07', '16777216'],
  // lua_str2number goes through float
  ['return tostring(tonumber("0.1") == 0.1)', 'true', 'true'],
];

let fail = 0;
const size = m.ccall('viewer_lua_number_size', 'number', [], []);
console.log(`sizeof(lua_Number) = ${size}`);
if (size !== 4) fail++;
for (const [code, want, dbl] of CASES) {
  const got = m.ccall('viewer_lua_eval', 'string', ['string'], [code]);
  const ok = got === want;
  if (!ok) fail++;
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${code}  ->  ${got}  (float32 ${want}, double ${dbl})`);
}
console.log(fail ? `lua_numbers: ${fail} failed` : 'lua_numbers: all float32');
process.exit(fail ? 1 : 0);
