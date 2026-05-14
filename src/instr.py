from src.spcfile import SPCFile
import hashlib, os.path

class BRRSample():
    def __init__(self, label=''):
        self.label = label
        self.data = bytearray()
        self.loop_point = 0
        self.loop = False

    def extract_from_header(self, spc: SPCFile, addr):
        saved_addr = spc.tell()
        spc.seek(addr)

        p_start = spc.read_int(2)
        p_loop = spc.read_int(2)
        self.loop_point = p_loop-p_start

        spc.seek(p_start)
        while True:
            header = spc.read_int(1)
            self.data.append(header)
            self.data.extend(spc.read(8))

            if header & 1: # end of sample
                self.loop = header & 2 == 2
                break

        spc.seek(saved_addr)

class SampleTable():
    def __init__(self, label=''):
        self.label = label
        self.sample_labels = []
        self.samples = {}

    def extract(self, spc: SPCFile, addr, count=0x100, used_sample_ids=None):
        saved_addr = spc.tell()

        label_map = {}
        for i in range(count):
            spc.seek(addr+i*4)
            p_start = spc.read_int(2)
            p_end = spc.read_int(2)
            if (p_start, p_end) in label_map:
                label_map[(p_start, p_end)] += f'_{i:02X}'
            else:
                label_map[(p_start, p_end)] = f'Sample{i:02X}'

        for i in range(count):
            if used_sample_ids == None or i in used_sample_ids:
                spc.seek(addr+i*4)
                p_start = spc.read_int(2)
                p_end = spc.read_int(2)
                if used_sample_ids == None and p_start == 0xFFFF and p_end == 0xFFFF:
                    break

                self.sample_labels.append(label_map[(p_start, p_end)])
                sample = BRRSample(label_map[(p_start, p_end)])
                sample.extract_from_header(spc, addr+i*4)
                self.samples[label_map[(p_start, p_end)]] = sample

        spc.seek(saved_addr)

    def sample_table_to_asm(self):
        asm = ''
        for i in range(len(self.sample_labels)):
            label = self.sample_labels[i]
            asm += f'  dw {label},{label}+{self.samples[label].loop_point}\n'
        return asm

    def samples_to_asm(self, fp, hash_option=False):
        asm = ''
        for label, sample in self.samples.items():
            if hash_option:
                fn = f'Sample_{hashlib.md5(self.samples[label].data).hexdigest()}'
            else:
                fn = label
            asm += f'  {label}: incbin "{os.path.join(fp, fn) + '.brr'}"\n'
        return asm

    def samples_to_files(self, fp, hash_option=False):
        for label, sample in self.samples.items():
            if hash_option:
                label = f'Sample_{hashlib.md5(self.samples[label].data).hexdigest()}'
            file = open(os.path.join(fp, label) + '.brr', 'wb')
            file.write(sample.data)

    def sample_map(used_samples, base=0x16):
        sample_map = {}
        i = base
        for sample_i in sorted(used_samples):
            sample_map[sample_i] = i
            i += 1
        return sample_map

    def sample_defines(sample_map: dict):
        asm = ''
        for sample_i in sample_map.keys():
            asm += f'!sample{sample_i:02X} = ${sample_map[sample_i]:02X}\n'
        return asm

class InstrTable():
    def __init__(self, label=''):
        self.label = label
        self.instrs = []

    def extract(self, spc: SPCFile, addr, used_instrs=None):
        used_sample_ids = set()
        saved_addr = spc.tell()
        for i in sorted(used_instrs):
            spc.seek(addr+i*6)
            instr = [spc.read_int(1) for _ in range(6)]
            self.instrs.append(instr)
            used_sample_ids.add(instr[0])
        spc.seek(saved_addr)

        return sorted(used_sample_ids)

    def to_asm(self):
        asm = ''
        for instr in self.instrs:
            asm += f'  db !sample{instr[0]:02X},{','.join(f'${b:02X}' for b in instr[1:])}\n'
        return asm

    def instr_map(used_instrs, base=0x16):
        instr_map = {}
        i = base
        for instr in sorted(used_instrs):
            instr_map[instr] = i
            i += 1
        return instr_map

    def instr_defines(instr_map: dict):
        asm = ''
        for instr in instr_map.keys():
            asm += f'!instr{instr:02X} = ${instr_map[instr]:02X}\n'
        return asm
