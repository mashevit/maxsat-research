"""List the members of a remote zip (name, compressed and uncompressed size, CRC) via HTTP range
requests: only the central directory is downloaded. Usage: remote_zip_list.py URL OUT.tsv"""
import sys, io, zipfile, urllib.request

class HTTPRangeFile(io.RawIOBase):
    def __init__(self, url):
        self.url, self.pos = url, 0
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=60) as r:
            self.size = int(r.headers["Content-Length"])
        self.fetched = 0
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off)
        return self.pos
    def read(self, n=-1):
        if n is None or n < 0: n = self.size - self.pos
        if n == 0 or self.pos >= self.size: return b""
        end = min(self.size, self.pos + n) - 1
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
        self.pos += len(data); self.fetched += len(data)
        return data
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)

url, out = sys.argv[1], sys.argv[2]
f = HTTPRangeFile(url)
z = zipfile.ZipFile(io.BufferedReader(f, buffer_size=1 << 20))
with open(out, "w") as o:
    o.write("name\tcompressed\tuncompressed\tcrc\n")
    for i in z.infolist():
        if not i.is_dir():
            o.write(f"{i.filename}\t{i.compress_size}\t{i.file_size}\t{i.CRC:08x}\n")
print(f"{url.rsplit('/',1)[1]}: {sum(1 for i in z.infolist() if not i.is_dir())} files, zip {f.size/2**30:.2f} GiB, fetched {f.fetched/2**20:.1f} MiB")
