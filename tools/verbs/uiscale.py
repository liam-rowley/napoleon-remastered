"""The UI scale stop-gap as a verb (J66, J67, D40): build the vanilla UI at a factor, classify and check its Lua pixel constants, check a factor against a screen.

purpose: run uiscale/napoleon/cli.py: build and status in the art_build Python under the PC state folder (tools/pc_state.py: adapter state_dir, or $NAPOLEON_STATE_DIR; numpy, Pillow, freetype-py, uharfbuzz); lua-consts, lua-patches and check in this Python (standard library only)
usage: python3 core/wsc.py uiscale build [--factor 1.25|1.5|2] [--work DIR] [--no-art] [--no-fonts] [--no-lua] [--limit N] [--jobs N]   |   python3 core/wsc.py uiscale status   |   python3 core/wsc.py uiscale lua-consts [--scripts DIR] [--check]   |   python3 core/wsc.py uiscale lua-patches [--check] [--factor F]   |   python3 core/wsc.py uiscale check --factor F --height H   |   ... uiscale check-fonts [--factor F] [--work DIR] (J37 slot check of a built fonts pack)   |   ... uiscale engine-text [--check] | licences [--check]
when: before `python3 upscale/pc/play.py install --scale F` (Liam's play test) and before a PC run of the scaled UI; lua-patches --check after a game update; nothing here writes the game folder
verb: uiscale
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pc_state  # noqa: E402

NAME = 'uiscale'
HELP = 'UI scale stop-gap (J66, J67): build the vanilla UI at 1.25x, 1.5x or 2x into <state folder>\\uiscale\\work; classify and check the Lua pixel constants; check a factor'
PLAIN = ('lua-consts', 'lua-patches', 'check')


def add_arguments(p):
    p.add_argument('action', choices=('build', 'status', 'check-fonts', 'engine-text', 'licences') + PLAIN)
    p.add_argument('rest', nargs=argparse.REMAINDER,
                   help='passed to uiscale/napoleon/cli.py (--factor, --work, --no-art, --no-fonts, --no-lua, --limit, --jobs, --scripts, --check, --height, --width)')


# J37: stdlib-only passes run in this Python (no art_build environment needed)
HOST = {'check-fonts': ('uiscale/napoleon/cli.py', ['check-fonts']), 'engine-text': ('uiscale/napoleon/engine_text.py', []),
        'licences': ('uiscale/core/licences.py', ['check'])}


def run(args, ctx):
    root = Path(ctx.root)
    if args.action in PLAIN:
        return subprocess.run([sys.executable, str(root / 'uiscale' / 'napoleon' / 'cli.py'), args.action] + list(args.rest), cwd=root).returncode
    if args.action in HOST:
        script, pre = HOST[args.action]
        rest = [r for r in args.rest if not (args.action == 'licences' and r == '--check')]
        return subprocess.run([sys.executable, str(root / script)] + pre + rest, cwd=root).returncode
    py = pc_state.art_python(root)
    if not py.exists():
        print(f'uiscale: no art_build environment at {py} (state folder: tools/pc_state.py, ${pc_state.ENV}); run upscale\\pc\\setup_env.cmd (then pip install -r upscale\\requirements.txt there)')
        return 1
    return subprocess.run([str(py), str(root / 'uiscale' / 'napoleon' / 'cli.py'), args.action] + list(args.rest), cwd=root).returncode
