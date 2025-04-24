
class SPCFile():
    def __init__(self, filename):
        self.file = open(filename, 'rb')

    def read(self, n):
        return self.file.read(n)

    def read_int(self, n):
        return int.from_bytes(self.read(n), 'little')

    def seek(self, addr):
        return self.file.seek(addr+0x100)

    def tell(self):
        return self.file.tell()-0x100

    def scan(self, bytes_to_scan: str):
        saved_addr = self.tell()
        split = bytes_to_scan.split(' ')
        for addr in range(0x100, 0x10000-len(bytes_to_scan)+1):
            self.seek(addr)
            scanned_bytes = []
            valid = True
            for i in range(len(split)):
                b = self.read_int(1)
                scanned_bytes.append(b)
                if split[i] != '??' and b != int(split[i], 16):
                    valid = False
                    break
            if valid:
                self.seek(saved_addr)
                return scanned_bytes

        self.seek(saved_addr)
        return None
