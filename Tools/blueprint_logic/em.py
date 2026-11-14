import zlib,struct,sys,collections
for f in sys.argv[1:]:
    b=open(f,'rb').read();p=8;idat=[]
    while p<len(b):
        n=struct.unpack('>I',b[p:p+4])[0];t=b[p+4:p+8]
        if t==b'IHDR':w,h=struct.unpack('>II',b[p+8:p+16])
        if t==b'IDAT':idat.append(b[p+8:p+8+n])
        p+=12+n
    raw=zlib.decompress(b''.join(idat));st=w*3+1;c=collections.Counter()
    for y in range(0,h,8):
        r=bytearray(raw[y*st+1:(y+1)*st])
        for i in range(3,len(r)):r[i]=(r[i]+r[i-3])&255
        for x in range(0,w,4):
            c[tuple(v//16*16 for v in r[x*3:x*3+3])]+=1
    t=sum(c.values());print(f,w,h,[(k,round(v/t*100,3)) for k,v in c.most_common(9)])
