#!/bin/bash
# Run-queue helpers for prefill perf work. Source it from a queue script:
#   source <skill>/tools/lib.sh
#   perf <label> <chunk> [ENV=VAL ...]      traced long-context demo: first chunk, 106k, 256k
#   pcc  <label> <chunk> [ENV=VAL ...]      256k KV-cache PCC run; saves <label>.runner.log for cmp_pcc.py
#   lp   <label> <chunk> <idx> <type> [ENV=VAL ...]   isolated-layer benchmark
#   t    <label> <pytest args ...>          any pytest, one line of result
#   mkb  <branch>   detached checkout + build + JIT purge;   sw <branch>   Python-only switch + JIT purge
#   waitchips       block until the chips are free; resets and clears locks left by a dead process
# Settings (env, with defaults):
#   TT_METAL_HOME   tree under test (required)
#   PY              python   (default: $TT_METAL_HOME/python_env/bin/python3)
#   PREFILL_RUNS    where logs go (default: ~/prefill_runs)
#   PREFILL_ENV     optional file sourced first (model weight / cache paths, HF_MODEL, ...)
#   PURGE_KERNELS   JIT kernel dirs that `purge` removes (default: the ring joint SDPA + ring gather kernels)
# The perf/pcc/lp test ids are the Gemma4 ones (models/demos/gemma4_d_p); edit them for another model.

TOOLS=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
W=${TT_METAL_HOME:?set TT_METAL_HOME to the tree under test}
PY=${PY:-$W/python_env/bin/python3}
O=${PREFILL_RUNS:-$HOME/prefill_runs}; mkdir -p "$O"
[ -n "$PREFILL_ENV" ] && source "$PREFILL_ENV"
RING=/tt_prefill_layer_completion_ring_${USER}
export PYTEST_TIMEOUT=3600 PREFILL_LAYER_COMPLETION_RING=$RING
export PATH=$(dirname "$PY"):$PATH
PURGE_KERNELS=${PURGE_KERNELS:-"ring_joint_reader ring_joint_writer ring_joint_sdpa ring_attention_all_gather_reader ring_attention_all_gather_writer"}

purge () { for k in $PURGE_KERNELS; do rm -rf ~/.cache/tt-metal-cache/*/kernels/$k; done; }

# PIDs named by the UMD chip locks (a lock with no live owner is left by a killed run).
lock_pids () { python3 -c "
import glob,struct
for f in glob.glob('/dev/shm/TT_UMD_LOCK.CHIP_IN_USE_*'):
    d=open(f,'rb').read()
    if len(d)>=56 and struct.unpack_from('<i',d,52)[0]: print(struct.unpack_from('<i',d,52)[0])
" | sort -u; }
# Free when no chip is claimed. When every lock names a dead PID, reset first (another user's live process
# shows as EPERM under hidepid and counts as live).
waitchips () {
  while true; do
    local pids; pids=$(lock_pids)
    [ -z "$pids" ] && return
    local live=0
    for p in $pids; do
      kill -0 $p 2>/dev/null && live=1; [ -d /proc/$p ] && live=1
      kill -0 $p 2>&1 | grep -q "not permitted" && live=1
    done
    if [ $live = 0 ]; then
      echo "stale locks $(echo $pids | tr '\n' ' ')-> reset $(date +%T)"
      tt-smi -glx_reset > $O/glx_reset_auto.log 2>&1; rm -f /dev/shm/TT_UMD_LOCK.CHIP_IN_USE_*_PCIe
    fi
    sleep 20
  done; }

perf () { local L=perf_$1_c$2; local C=$2; shift 2
  waitchips; echo "=== $L start $(date +%T) sha=$(git -C $W rev-parse --short HEAD) env=$*"
  (cd $W && env "$@" TT_METAL_HOME=$W PYTHONPATH=$W/ttnn:$W timeout 2400 $PY -m pytest "models/demos/gemma4_d_p/demo/text_demo_prefill.py::test_prefill_long_context_traced[blackhole-readback_final-ctx_256k-chunk${C}-text-8x4]" -sv -p no:cacheprovider < /dev/null > $O/$L.log 2>&1)
  echo "$L rc=$? $(grep -o 'first=[0-9.]*ms' $O/$L.log | head -1) $(grep -o 'TOTAL 262144 tokens in [0-9.]*s' $O/$L.log) 106k=$(python3 - $O/$L.log <<'PY'
import re,sys
t=0.0
for l in open(sys.argv[1],errors='replace'):
    m=re.search(r"\[traced_perf\] chunk (\d+)/(\d+) \[(\d+), (\d+)\) device=([0-9.]+)ms",l)
    if m and int(m.group(4))<=106496: t+=float(m.group(5))
print(f"{t/1000:.3f}s")
PY
)"; }

pcc () { local L=pcc_$1_c$2; local C=$2; shift 2; local BT=$O/$L.tmp; rm -rf $BT
  rm -f /dev/shm${RING}_0; waitchips; echo "=== $L start $(date +%T) env=$*"
  (cd $W && { env "$@" TT_METAL_HOME=$W PYTHONPATH=$W/ttnn:$W GEMMA4_PCC_CHUNK_SIZE=$C timeout 3600 $PY -m pytest "models/demos/gemma4_d_p/tests/test_prefill_migration.py::test_prefill_migration[mock-256k]" -svv --basetemp=$BT -p no:cacheprovider < /dev/null; echo "### rc=$?"; } > $O/$L.log 2>&1)
  cp "$(find $BT -name runner.log | head -1)" $O/$L.runner.log 2>/dev/null
  echo "$L $(grep '^### rc' $O/$L.log) $(grep -E '^ *Overall' $O/$L.log | tr -s ' ') minpcc=$($PY $TOOLS/minpcc.py $O/$L.runner.log 2>/dev/null | awk '{print $2,$3}')"; }

lp () { local L=lp_$1_c$2_i$3_$4; local C=$2 I=$3 T=$4; shift 4; waitchips; echo "=== $L start $(date +%T) env=$*"
  (cd $W && env "$@" TT_METAL_HOME=$W PYTHONPATH=$W/ttnn:$W timeout 2400 $PY -m pytest "models/demos/gemma4_d_p/demo/text_demo_prefill.py::test_prefill_layer_perf_chunk_n[blackhole-chunk$I-$T-sz$C-ctx_256k-8x4]" -sv -p no:cacheprovider < /dev/null > $O/$L.log 2>&1)
  echo "$L rc=$? $(grep -o 'RESULT type=[a-z]* chunk=[0-9]* .*measured_ms=[0-9.]*' $O/$L.log | sed 's/ring_depth.*measured/measured/' | tr '\n' ' ')"; }

t () { local n=$1; shift; waitchips
  (cd $W && env TT_METAL_HOME=$W PYTHONPATH=$W/ttnn:$W timeout 3000 $PY -m pytest "$@" -p no:cacheprovider -q < /dev/null > $O/t_$n.log 2>&1)
  echo "$n rc=$? $(grep -E '[0-9]+ (passed|failed)' $O/t_$n.log | tail -1)"; }

mkb () { cd $W && git checkout -q --detach $1 || return 1; echo "== $1 $(git rev-parse --short HEAD) $(date +%T)"
  local log=$O/build_$(echo $1 | tr / _).log
  (cmake build_Release > /dev/null 2>&1 && cmake --build build_Release --target install -j 64 > $log 2>&1) && echo "build ok" || { echo "build FAIL"; grep -m5 error: $log; return 1; }
  purge; }

sw () { cd $W && git checkout -q --detach $1 && echo "== sw $1 $(git rev-parse --short HEAD) $(date +%T)"; purge; }
