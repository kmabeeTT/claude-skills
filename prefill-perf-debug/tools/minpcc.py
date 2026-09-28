import re,sys
# min per-head PCC and layer from a runner.log (layer_minima dict per layer)
for p in sys.argv[1:]:
    best=(9,None)
    for l in open(p,errors="replace"):
        m=re.search(r"layer=(\d+) layer_minima=(\{.*?\})",l)
        if m:
            vals=[float(x) for x in re.findall(r"[-+]?\d*\.\d+(?:e[-+]?\d+)?",m.group(2))]
            if vals and min(vals)<best[0]: best=(min(vals),int(m.group(1)))
    print(p.split('/')[-1], "min=%.4f @L%s"%best)
