import sys,zlib,struct
def load(p):
    b=open(p,'rb').read();i=8;z=b''
    while i<len(b):
        n,t=struct.unpack('>I4s',b[i:i+8]);d=b[i+8:i+8+n];i+=12+n
        if t==b'IHDR':w,h,bd,ct=struct.unpack('>IIBB',d[:10])
        if t==b'IDAT':z+=d
    bpp={2:3,6:4}[ct];s=w*bpp;raw=zlib.decompress(z);rows=[];prev=bytearray(s);o=0
    for y in range(h):
        f=raw[o];l=bytearray(raw[o+1:o+1+s]);o+=1+s
        for x in range(s):
            a=l[x-bpp] if x>=bpp else 0;b_=prev[x];c=prev[x-bpp] if x>=bpp else 0
            if f==1:l[x]=(l[x]+a)&255
            elif f==2:l[x]=(l[x]+b_)&255
            elif f==3:l[x]=(l[x]+((a+b_)>>1))&255
            elif f==4:
                pa=abs(b_-c);pb=abs(a-c);pc=abs(a+b_-2*c);l[x]=(l[x]+(a if pa<=pb and pa<=pc else b_ if pb<=pc else c))&255
        rows.append(l);prev=l
    return w,h,bpp,rows
for p in sys.argv[1:]:
    w,h,bpp,r=load(p);c=0
    for y in range(280,700):
        row=r[y]
        for x in range(400,820):
            R,G,B=row[x*bpp],row[x*bpp+1],row[x*bpp+2]
            if R>150 and R-B>70 and G>50: c+=1
    print(p,c)
