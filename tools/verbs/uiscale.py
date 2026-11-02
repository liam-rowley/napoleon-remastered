"""The UI scale stop-gap as a verb (J66, D40): build the vanilla UI at 2x (layouts, uied.templates, slot fonts, UI art) in the art_build Python.

purpose: run uiscale/napoleon/cli.py (build, status) in the Python under C:\\napoleon_remastered_pc\\upscale\\art_build (numpy, Pillow, freetype-py)
usage: python3 core/wsc.py uiscale build [--factor 2] [--work DIR] [--no-art] [--no-fonts] [--limit N] [--jobs N]   |   python3 core/wsc.py uiscale status
when: before `python3 upscale/pc/play.py install --scale 2` (Liam's 4K play test) and before a PC run of the scaled UI; nothing here writes the game folder
verb: uiscale
"""
import argparse
import subprocess
from pathlib import Path

NAME = 'uiscale'
HELP = 'UI scale stop-gap (J66): build the vanilla UI at 2x into C:\\napoleon_remastered_pc\\uiscale\\work'
PY = Path(r'C:\napoleon_remastered_pc\upscale\art_build\py\python.exe')


def add_arguments(p):
    p.add_argument('action', choices=('build', 'status'))
    p.add_argument('rest', nargs=argparse.REMAINDER, help='passed to uiscale/napoleon/cli.py (--factor, --work, --no-art, --no-fonts, --limit, --jobs)')


def run(args, ctx):
    root = Path(ctx.root)
    if not PY.exists():
        print(f'uiscale: no art_build environment at {PY}; run upscale\\pc\\setup_env.cmd (then pip install -r upscale\\requirements.txt there)')
        return 1
    return subprocess.run([str(PY), str(root / 'uiscale' / 'napoleon' / 'cli.py'), args.action] + list(args.rest), cwd=root).returncode
