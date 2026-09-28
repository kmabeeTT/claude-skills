import torch, math
torch.manual_seed(0)
def bf(x): return x.to(torch.bfloat16).to(torch.float32)
def run(N=204800, kc=256, d=64, rows=32, splits=1, logit_scale=3.0, store_bf16=True, fixed_max=False):
    q=torch.randn(rows,d); k=torch.randn(N,d); v=torch.randn(N,d)
    s=(q@k.T)/math.sqrt(d)*logit_scale
    ref=torch.softmax(s,-1)@v
    outs=[]
    bounds=[round(i*N/splits) for i in range(splits+1)]
    for b in range(splits):
        m=torch.full((rows,1),-1e30); l=torch.zeros(rows,1); o=torch.zeros(rows,d)
        for c0 in range(bounds[b],bounds[b+1],kc):
            sc=s[:,c0:c0+kc]
            m_new=torch.maximum(m, sc.max(-1,keepdim=True).values) if not (fixed_max and c0>bounds[b]) else m
            p=bf(torch.exp(sc-m_new))  # P in bf16
            pv=bf(p@v[c0:c0+kc])       # PV result through 16-bit DST
            diff=torch.exp(m-m_new)
            if store_bf16:
                o=bf(bf(o*diff)+pv); l=bf(bf(l*diff)+bf(p.sum(-1,keepdim=True)))
            else:
                o=o*diff+pv; l=l*diff+bf(p.sum(-1,keepdim=True))
            m=m_new
        outs.append((m,l,o))
    # merge splits in fp32
    M=torch.stack([x[0] for x in outs]).max(0).values
    L=sum(x[1]*torch.exp(x[0]-M) for x in outs); O=sum(x[2]*torch.exp(x[0]-M) for x in outs)
    out=O/L
    err=(out-ref).norm()/ref.norm()
    pcc=torch.corrcoef(torch.stack([out.flatten(),ref.flatten()]))[0,1].item()
    return err.item(), pcc
for name,kw in [][:0] and [("bf16 k256",{}),("bf16 k128",dict(kc=128)),("bf16 k512",dict(kc=512)),("bf16 k256 3 splits",dict(splits=3)),("fp32 store k256",dict(store_bf16=False)),("bf16 fixed-max",dict(fixed_max=True))]:
    print(name, "rel err %.4f pcc %.6f"%run(**kw))

def run_seg(N=204800,kc=256,d=64,rows=32,segs=8,logit_scale=3.0,merge_bf16=True):
    torch.manual_seed(0)
    q=torch.randn(rows,d); k=torch.randn(N,d); v=torch.randn(N,d)
    s=(q@k.T)/math.sqrt(d)*logit_scale
    ref=torch.softmax(s,-1)@v
    M=torch.full((rows,1),-1e30); L=torch.zeros(rows,1); O=torch.zeros(rows,d)
    bounds=[round(i*N/segs) for i in range(segs+1)]
    for b in range(segs):
        m=torch.full((rows,1),-1e30); l=torch.zeros(rows,1); o=torch.zeros(rows,d)
        for c0 in range(bounds[b],bounds[b+1],kc):
            sc=s[:,c0:c0+kc]; m_new=torch.maximum(m, sc.max(-1,keepdim=True).values)
            p=bf(torch.exp(sc-m_new)); pv=bf(p@v[c0:c0+kc]); diff=torch.exp(m-m_new)
            o=bf(bf(o*diff)+pv); l=bf(bf(l*diff)+bf(p.sum(-1,keepdim=True))); m=m_new
        Mn=torch.maximum(M,m)
        if merge_bf16:
            O=bf(bf(O*torch.exp(M-Mn))+bf(o*torch.exp(m-Mn))); L=bf(bf(L*torch.exp(M-Mn))+bf(l*torch.exp(m-Mn)))
        else:
            O=O*torch.exp(M-Mn)+o*torch.exp(m-Mn); L=L*torch.exp(M-Mn)+l*torch.exp(m-Mn)
        M=Mn
    out=O/L; return ((out-ref).norm()/ref.norm()).item()
for segs in (1,8,16,32):
    print("segments",segs,"bf16 merge err %.4f"%run_seg(segs=segs), "fp32 merge err %.4f"%run_seg(segs=segs,merge_bf16=False))
