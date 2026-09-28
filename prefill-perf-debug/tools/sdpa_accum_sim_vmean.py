import torch, math
from sdpa_accum_sim2 import bf
f32=lambda x:x
def run(N=204800,kc=256,d=64,rows=32,ls=1.0,vmean=0.0,o_mode="bf16",l_mode="bf16",splits=1,seed=0):
    torch.manual_seed(seed)
    q=torch.randn(rows,d); k=torch.randn(N,d); v=torch.randn(N,d)+vmean*torch.randn(1,d).abs()
    s=(q@k.T)/math.sqrt(d)*ls; ref=torch.softmax(s,-1)@v
    per=N//splits; outs=[]
    for b in range(splits):
        m=torch.full((rows,1),-1e30); l=torch.zeros(rows,1); o=torch.zeros(rows,d); cl=torch.zeros(rows,1); co=torch.zeros(rows,d)
        for c0 in range(b*per,(b+1)*per,kc):
            sc=s[:,c0:c0+kc]; m_new=torch.maximum(m, sc.max(-1,keepdim=True).values)
            p=bf(torch.exp(sc-m_new)); pv=bf(p@v[c0:c0+kc]); diff=bf(torch.exp(m-m_new)); rs=bf(p.sum(-1,keepdim=True))
            if o_mode=="bf16": o=bf(bf(o*diff)+pv)
            else: t=bf(o*diff)+bf(co*diff)+pv; o=bf(t); co=bf(t-o)
            if l_mode=="bf16": l=bf(bf(l*diff)+rs)
            else: t=bf(l*diff)+bf(cl*diff)+rs; l=bf(t); cl=bf(t-l)
            m=m_new
        outs.append((m,l+cl,o+co))
    M=torch.stack([x[0] for x in outs]).max(0).values
    L=sum(x[1]*torch.exp(x[0]-M) for x in outs); O=sum(x[2]*torch.exp(x[0]-M) for x in outs)
    out=O/L; e=out-ref
    # remove per-row scale (post-norm), report residual
    a=(out*ref).sum(-1,keepdim=True)/(out*out).sum(-1,keepdim=True)
    return (e.norm()/ref.norm()).item(), ((out*a-ref).norm()/ref.norm()).item()
for vmean in (0.0,1.0,3.0):
    for name,kw in [("both bf16",{}),("l comp",dict(l_mode="c")),("o+l comp",dict(l_mode="c",o_mode="c")),("3 splits",dict(splits=3))]:
        e,er=run(N=98304,vmean=vmean,**kw); print(f"vmean {vmean} {name:10s} err {e:.4f}  after row-scale {er:.4f}")
