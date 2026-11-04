#!/bin/bash
# J28 run driver: order.sh <tag> <ctl order args...>   one ctl.py order call, its JSON kept as raw/<tag>.json, one summary line printed
# (the game is already in the scene: ctl.py scene ... deploy=end first)
cd /c/Users/liamr/repos/napoleon-remastered
TAG=$1; shift
R=harness/runs/20261102_j28pc/raw
core/harness/job.sh touch >/dev/null 2>&1
python3 core/harness/ctl.py --owner j28 order "$@" > $R/$TAG.json 2>&1
echo "$TAG rc $? $(python3 harness/runs/20261102_j28pc/sum.py $R/$TAG.json)"
