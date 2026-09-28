import torch, math
def bf(x): return x.to(torch.bfloat16).to(torch.float32)
def h16(x): return x.to(torch.float16).to(torch.float32)
f32=lambda x:x
def run(N=204800,kc=256,d=64,rows=32,splits=1,ls=3.0,o_r=bf,l_r=bf,seed=0):
    torch.manual_seed(seed)
    q=torch.randn(rows,d); k=torch.randn(N,d); v=torch.randn(N,d)
    s=(q@k.T)/math.sqrt(d)*ls; ref=torch.softmax(s,-1)@v
    outs=[]; bounds=[round(i*N/splits) for i in range(splits+1)]
    for b in range(splits):
        m=torch.full((rows,1),-1e30); l=torch.zeros(rows,1); o=torch.zeros(rows,d)
        for c0 in range(bounds[b],bounds[b+1],kc):
            sc=s[:,c0:c0+kc]; m_new=torch.maximum(m, sc.max(-1,keepdim=True).values)
            p=bf(torch.exp(sc-m_new)); pv=bf(p@v[c0:c0+kc]); diff=torch.exp(m-m_new)
            o=o_r(o_r(o*diff)+pv); l=l_r(l_r(l*diff)+bf(p.sum(-1,keepdim=True))); m=m_new
        outs.append((m,l,o))
    M=torch.stack([x[0] for x in outs]).max(0).values
    L=sum(x[1]*torch.exp(x[0]-M) for x in outs); O=sum(x[2]*torch.exp(x[0]-M) for x in outs)
    out=O/L; return ((out-ref).norm()/ref.norm()).item(), L.max().item(), O.abs().max().item()
if __name__=="__main__":
    for N in (4096,20480,49152):
        for sp in (1,3):
            e,_,_=run(N=N,ls=1.0,splits=sp); e2,_,_=run(N=N,ls=1.0,splits=sp,l_r=f32)
            print(f"N={N} splits={sp}: bf16 l err {e:.4f}   fp32 l err {e2:.4f}")
