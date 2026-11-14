import re,sys,zlib
b=open(sys.argv[1],'rb').read()
objs={}
for m in re.finditer(rb'(?:^|[\r\n ])(\d+) (\d+) obj\b(.*?)endobj',b,re.S):
    objs[int(m[1])]=m[3]
def stream(body):
    i=body.find(b'stream')
    if i<0:return None
    s=body[i+6:].lstrip(b'\r\n') if False else body[i+6:]
    if s[:2]==b'\r\n':s=s[2:]
    elif s[:1]==b'\n':s=s[1:]
    j=s.rfind(b'endstream'); s=s[:j]
    if b'FlateDecode' in body[:i]:
        try:return zlib.decompressobj().decompress(s)
        except Exception:return None
    return s
def cmap(data):
    m={}
    t=data.decode('latin1')
    def u(h):
        return bytes.fromhex(h).decode('utf-16-be','replace')
    for blk in re.findall(r'beginbfchar(.*?)endbfchar',t,re.S):
        for a,c in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>',blk):m[int(a,16)]=u(c)
    for blk in re.findall(r'beginbfrange(.*?)endbfrange',t,re.S):
        for a,e,c in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>',blk):
            a,e=int(a,16),int(e,16);base=int(c,16);n=len(c)
            for k in range(a,e+1):m[k]=u(format(base+k-a,'0%dx'%n))
        for a,e,arr in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]',blk,re.S):
            a=int(a,16)
            for k,c in enumerate(re.findall(r'<([0-9A-Fa-f]+)>',arr)):m[a+k]=u(c)
    w=max((len(x) for x in re.findall(r'<([0-9A-Fa-f]+)>',t.split('endcodespacerange')[0].split('begincodespacerange')[-1])),default=4)//2
    return m,w
def ref(body,key):
    m=re.search(key+rb'\s+(\d+) 0 R',body);return int(m[1]) if m else None
def pages():
    root=next(k for k,v in objs.items() if re.search(rb'/Type\s*/Catalog',v))
    out=[]
    def walk(n):
        v=objs[n]
        if re.search(rb'/Type\s*/Pages',v):
            for k in re.findall(rb'(\d+) 0 R',re.search(rb'/Kids\s*\[(.*?)\]',v,re.S)[1]):walk(int(k))
        else:out.append(n)
    walk(ref(objs[root],rb'/Pages'));return out
def fonts(body):
    r=ref(body,rb'/Resources')
    res=objs[r] if r else body
    m=re.search(rb'/Font\s*(\d+) 0 R',res)
    d=objs[int(m[1])] if m else (re.search(rb'/Font\s*<<(.*?)>>',res,re.S) or [None,b''])[1]
    f={}
    for name,n in re.findall(rb'/([\w.+-]+)\s+(\d+) 0 R',d):
        tu=ref(objs.get(int(n),b''),rb'/ToUnicode')
        f[name]=cmap(stream(objs[tu])) if tu else ({},1)
    return f
def lit(s):
    o=bytearray();i=0
    while i<len(s):
        c=s[i]
        if c==92:
            i+=1;c=s[i]
            if c in b'nrtbf':o.append({110:10,114:13,116:9,98:8,102:12}[c])
            elif 48<=c<=55:
                k=i
                while k<i+3 and k<len(s) and 48<=s[k]<=55:k+=1
                o.append(int(s[i:k],8)&255);i=k-1
            elif c in b'\r\n':pass
            else:o.append(c)
        else:o.append(c)
        i+=1
    return bytes(o)
def dec(raw,fnt):
    m,w=fnt
    return ''.join(m.get(int.from_bytes(raw[i:i+w],'big'),'') for i in range(0,len(raw),w))
tok=re.compile(rb'\((?:\\.|[^\\()]|\((?:\\.|[^\\()])*\))*\)|<[0-9A-Fa-f\s]*>|\[|\]|/[\w.+-]+|-?\d*\.?\d+|[A-Za-z\'"*]+',re.S)
def text(n):
    body=objs[n];fs=fonts(body);cur=({},1)
    c=re.search(rb'/Contents\s*\[(.*?)\]',body,re.S)
    ids=[int(x) for x in re.findall(rb'(\d+) 0 R',c[1])] if c else [ref(body,rb'/Contents')]
    data=b'\n'.join(stream(objs[i]) or b'' for i in ids if i)
    out=[];st=[];inarr=False;lasty=None;pend=[]
    for t in tok.findall(data):
        if t[:1]==b'(':
            pend.append(dec(lit(t[1:-1]),cur))
        elif t[:1]==b'<':
            pend.append(dec(bytes.fromhex(re.sub(rb'\s',b'',t[1:-1]).decode()),cur))
        elif t==b'[':inarr=True
        elif t==b']':inarr=False
        elif re.fullmatch(rb'-?\d*\.?\d+',t):
            if inarr and float(t)<-180:pend.append(' ')
            st.append(float(t));st=st[-6:]
        elif t[:1]==b'/':st=[t]
        elif t==b'Tf':
            nm=next((x for x in st if isinstance(x,bytes)),None)
            if nm:cur=fs.get(nm[1:],cur)
        elif t in (b'Tj',b'TJ',b"'",b'"'):
            out.append(''.join(pend));pend=[]
        elif t in (b'Td',b'TD',b'T*'):
            if t==b'T*' or (len(st)>=1 and st[-1]!=0):out.append('\n')
            else:out.append(' ')
        elif t==b'Tm':
            if lasty is not None and st and st[-1]!=lasty:out.append('\n')
            elif lasty is not None:out.append(' ')
            lasty=st[-1] if st else None
    return ''.join(out)
ps=pages();print(len(ps),file=sys.stderr)
with open(sys.argv[2],'w') as f:
    for i,p in enumerate(ps,1):
        f.write(f'\n=====PDFPAGE {i}=====\n'+text(p)+'\n')
