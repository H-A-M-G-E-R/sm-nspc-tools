from src.spcfile import SPCFile
import os.path

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
                loop = header & 2 == 2
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
            if p_start in label_map:
                label_map[p_start] += f'_{i:02X}'
            else:
                label_map[p_start] = f'Sample{i:02X}'

        for i in range(count):
            if used_sample_ids == None or i in used_sample_ids:
                spc.seek(addr+i*4)
                p_start = spc.read_int(2)
                p_end = spc.read_int(2)
                if p_start == 0xFFFF and p_end == 0xFFFF:
                    break

                self.sample_labels.append(label_map[p_start])
                sample = BRRSample(label_map[p_start])
                sample.extract_from_header(spc, addr+i*4)
                self.samples[label_map[p_start]] = sample

        spc.seek(saved_addr)

    def sample_table_to_asm(self):
        asm = ''
        for i in range(len(self.sample_labels)):
            label = self.sample_labels[i]
            asm += f'  dw {label},{label}+{self.samples[label].loop_point}\n'
        return asm

    def samples_to_asm(self, fp):
        asm = ''
        for label, sample in self.samples.items():
            asm += f'  {label}: incbin "{os.path.join(fp, label) + '.brr'}"\n'
        return asm

    def samples_to_files(self, fp):
        for label, sample in self.samples.items():
            file = open(os.path.join(fp, label) + '.brr', 'wb')
            file.write(sample.data)

class InstrTable():
    def __init__(self, label=''):
        self.label = label
        self.instrs = []

    def extract(self, spc: SPCFile, addr, used_instrs=None):
        saved_addr = spc.tell()
        for i in sorted(used_instrs):
            spc.seek(addr+i*6)
            self.instrs.append([spc.read_int(1) for _ in range(6)])
        spc.seek(saved_addr)

    def to_asm(self):
        asm = ''
        for instr in self.instrs:
            asm += f'  db !instr{instr[0]:02X},{','.join(f'${b:02X}' for b in instr[1:])}\n'
        return asm

    def instr_defines(instr_map: dict):
        asm = ''
        for instr in instr_map.keys():
            asm += f'!instr{instr:02X} = ${instr_map[instr]:02X}\n'
        return asm
