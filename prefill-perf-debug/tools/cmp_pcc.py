import re,sys
def load(p):
    d={}
    for l in open(p,errors="replace"):
        m=re.search(r"layer=(\d+) layer_minima=(\{.*?\})",l)
        if m:
            vals=[float(x) for x in re.findall(r"[-+]?\d*\.\d+(?:e[-+]?\d+)?",m.group(2))]
            d[int(m.group(1))]=min(vals)
    return d
b=load(sys.argv[1]); a=load(sys.argv[2])
rs=[]
for L in sorted(a):
    if L in b: rs.append((L,b[L],a[L],(1-a[L])/max(1-b[L],1e-7)))
import statistics
e=[r[3] for r in rs if r[0]<=20]
print("L0-20 median err ratio %.2f, L10 %.2f, L20 %.2f; min base %.4f new %.4f"%(statistics.median(e), rs[10][3], rs[20][3], min(b.values()), min(a.values())))
for r in rs:
    if r[0] in (2,5,10,17,23,29,35,39,47,53,59): print("  L%d %.4f -> %.4f (x%.2f)"%r)
