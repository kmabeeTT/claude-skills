#!/bin/bash
# Sample tt-smi power / AICLK / temperature while a run is going:  smi_sample.sh [seconds=600] [outfile]
OUT=${2:-${PREFILL_RUNS:-$HOME/prefill_runs}/smi_samples.txt}; mkdir -p "$(dirname "$OUT")"; : > "$OUT"
end=$((SECONDS+${1:-600}))
while [ $SECONDS -lt $end ]; do
  timeout 30 tt-smi -s 2>/dev/null | python3 -c "
import json,sys,time
d=json.load(sys.stdin); v=d.get('device_info',[])
a=[float(x['telemetry']['aiclk']) for x in v]; p=[float(x['telemetry']['power']) for x in v]; t=[float(x['telemetry']['asic_temperature']) for x in v]
print(time.strftime('%H:%M:%S'), 'aiclk min/max', min(a), max(a), 'power max', max(p), 'mean', round(sum(p)/len(p),1), 'temp max', max(t))" >> "$OUT" 2>/dev/null
done
