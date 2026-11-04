"""The PC state folder for the repo's own build verbs (J79, audit G14): one place instead of a path literal in each verb.

purpose: resolve the PC state folder (default: harness/napoleon/adapter.json state_dir, C:\\napoleon_remastered_pc; override: $NAPOLEON_STATE_DIR) and the art_build Python, upscale work and uiscale work folders under it
usage: library: from pc_state import state_dir, art_python, upscale_root, upscale_work, uiscale_work; state_dir(root) -> Path   (root: the repo; environ defaults to os.environ)
when: the uiscale and upscale verbs (tools/verbs) and uiscale/napoleon/cli.py find the art_build Python and their work folders; tests pass their own environ
not-a-verb: a path helper the verbs import, no registry or game state
"""
import json
import os
from pathlib import Path

ENV = 'NAPOLEON_STATE_DIR'
ADAPTER = Path('harness') / 'napoleon' / 'adapter.json'


def state_dir(root, environ=None):
    """$NAPOLEON_STATE_DIR when set and not empty, else the adapter's state_dir (the folder the watcher and pc_deploy.py use)"""
    env = os.environ if environ is None else environ
    if env.get(ENV):
        return Path(env[ENV])
    with open(Path(root) / ADAPTER, encoding='utf-8') as f:
        return Path(json.load(f)['state_dir'])


def upscale_root(root, environ=None):
    """<state>\\upscale: setup_env.cmd's default work folder, holding art_build"""
    return state_dir(root, environ) / 'upscale'


def art_python(root, environ=None):
    """the art_build Python (numpy, Pillow, freetype-py, uharfbuzz, torch): upscale/pc/setup_env.cmd builds it"""
    return upscale_root(root, environ) / 'art_build' / 'py' / 'python.exe'


def upscale_work(root, environ=None):
    """<state>\\upscale\\work: the 2.5x masters (J36, D35) and their manifest.json"""
    return upscale_root(root, environ) / 'work'


def uiscale_work(root, environ=None):
    """<state>\\uiscale\\work: the UI scale stop-gap's build outputs (J66)"""
    return state_dir(root, environ) / 'uiscale' / 'work'
