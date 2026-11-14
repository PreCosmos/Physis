import re,sys,zlib
b=open(sys.argv[1],'rb').read()
print(len(b), b[:8], 'pages~',len(re.findall(rb'/Type\s*/Page[^s]',b)), 'objstm',b.count(b'/ObjStm'), 'tounicode',b.count(b'/ToUnicode'), 'encrypt',b.count(b'/Encrypt'))
print(re.findall(rb'/Producer\s*\(([^)]*)',b)[:2], re.findall(rb'/Subtype\s*/(\w+)',b)[:0])
print(set(re.findall(rb'/Filter\s*/(\w+)',b)))
