"""The UI scale stop-gap as a verb (J66, J67, D40): build the vanilla UI at a factor, classify and check its Lua pixel constants, check a factor against a screen.

purpose: run uiscale/napoleon/cli.py: build and status in the Python under C:\\napoleon_remastered_pc\\upscale\\art_build (numpy, Pillow, freetype-py); lua-consts, lua-patches and check in this Python (standard library only)
usage: python3 core/wsc.py uiscale build [--factor 1.25|1.5|2] [--work DIR] [--no-art] [--no-fonts] [--no-lua] [--limit N] [--jobs N]   |   python3 core/wsc.py uiscale status   |   python3 core/wsc.py uiscale lua-consts [--scripts DIR] [--check]   |   python3 core/wsc.py uiscale lua-patches [--check] [--factor F]   |   python3 core/wsc.py uiscale check --factor F --height H
when: before `python3 upscale/pc/play.py install --scale F` (Liam's play test) and before a PC run of the scaled UI; lua-patches --check after a game update; nothing here writes the game folder
verb: uiscale
"""
import argparse
import subprocess
import sys
from pathlib import Path

NAME = 'uiscale'
HELP = 'UI scale stop-gap (J66, J67): build the vanilla UI at 1.25x, 1.5x or 2x; classify and check the Lua pixel constants; check a factor'
PY = Path(r'C:\napoleon_remastered_pc\upscale\art_build\py\python.exe')
PLAIN = ('lua-consts', 'lua-patches', 'check')


def add_arguments(p):
    p.add_argument('action', choices=('build', 'status') + PLAIN)
    p.add_argument('rest', nargs=argparse.REMAINDER,
                   help='passed to uiscale/napoleon/cli.py (--factor, --work, --no-art, --no-fonts, --no-lua, --limit, --jobs, --scripts, --check, --height, --width)')


def run(args, ctx):
    root = Path(ctx.root)
    py = sys.executable if args.action in PLAIN else str(PY)
    if args.action not in PLAIN and not PY.exists():
        print(f'uiscale: no art_build environment at {PY}; run upscale\\pc\\setup_env.cmd (then pip install -r upscale\\requirements.txt there)')
        return 1
    return subprocess.run([py, str(root / 'uiscale' / 'napoleon' / 'cli.py'), args.action] + list(args.rest), cwd=root).returncode
