"""The UI art upscaler as a verb (J36): env check, plan, run, verify, sheets and pack, started in the art_build Python.

purpose: run the UI art upscale pipeline (upscale/napoleon/cli.py) in the GPU environment under <state folder>\\upscale\\art_build (tools/pc_state.py: adapter state_dir, or $NAPOLEON_STATE_DIR), and print that environment (GPU, torch, model sha256)
usage: python3 core/wsc.py upscale env | plan | run | verify | sheets | pack [--play] [--roles a,b] [--sample N] [--limit N] [--model NAME] [--work DIR] [--registry]   (env setup: upscale\\pc\\setup_env.cmd)
when: making the 2.5x master UI art (D19); `plan` and `verify` are read-only, `run` writes under the work folder, `pack` builds ui_art_2x5_<role>.pack there (`pack --play`: ui_art_play_<role>.pack at the vanilla paths in <work>\\packs_play, for upscale/pc/play.py); nothing here writes the game folder
verb: upscale
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pc_state  # noqa: E402

NAME = 'upscale'
HELP = 'UI art upscaler (J36): env, plan, run, verify, sheets, pack'


def add_arguments(p):
    p.add_argument('action', choices=('env', 'plan', 'run', 'verify', 'sheets', 'compare', 'pack'))
    p.add_argument('rest', nargs=argparse.REMAINDER, help='passed to upscale/napoleon/cli.py (--roles, --sample, --limit, --model, --work, --registry, --play)')


def run(args, ctx):
    root = Path(ctx.root)
    WORK = pc_state.upscale_root(root)
    py = pc_state.art_python(root)
    if not py.exists():
        print(f'upscale: no environment at {py}; run upscale\\pc\\setup_env.cmd (it installs nothing system-wide)')
        return 1
    if args.action == 'env':
        cmd = [str(py), str(root / 'upscale' / 'pc' / 'env_check.py'), '--models', str(WORK / 'art_build' / 'models'),
               '--pins', str(root / 'upscale' / 'napoleon' / 'models.json')] + list(args.rest)
    else:
        cmd = [str(py), str(root / 'upscale' / 'napoleon' / 'cli.py'), args.action] + list(args.rest)
    return subprocess.run(cmd, cwd=root).returncode
