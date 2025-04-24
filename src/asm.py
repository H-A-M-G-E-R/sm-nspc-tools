from src.spcfile import SPCFile
from src.instr import BRRSample, SampleTable, InstrTable
from src.track import Track, Pattern, Tracker

class PJASMConverter():
    def __init__(self, spc):
        self.spc = spc
        self.asm = ''

    def convert(self, p_instr_table, p_track, fp):
        self.asm += 'asar 1.91\n'
        self.asm += 'norom : org 0\n'
        self.asm += 'incsrc "defines.asm"\n\n'

        tracker = Tracker(f'Tracker{p_track:04X}')
        tracker.extract(self.spc, p_track)

        perc_base = tracker.perc_base()
        used_instrs = tracker.used_instrs(perc_base=perc_base)
        first_perc = None if len(used_instrs[1]) == 0 else min(used_instrs[1])

        instr_map = {}
        i = 0x16
        for instr in sorted(used_instrs[0] | used_instrs[1]):
            instr_map[instr] = i
            i += 1
        self.asm += InstrTable.instr_defines(instr_map) + '\n'

        instr_table = InstrTable()
        instr_table.extract(self.spc, p_instr_table, used_instrs=used_instrs[0] | used_instrs[1])
        self.asm += 'spcblock 6*$16+!p_instrumentTable nspc ; instruments\n'
        self.asm += instr_table.to_asm()
        self.asm += 'endspcblock\n\n'

        self.spc.seek(0x1005D)
        sample_table = SampleTable()
        sample_table.extract(self.spc, self.spc.read_int(1)*0x100, used_sample_ids=used_instrs[0] | used_instrs[1])
        self.asm += 'spcblock 4*$16+!p_sampleTable nspc ; sample table\n'
        self.asm += sample_table.sample_table_to_asm()
        self.asm += 'endspcblock\n\n'

        self.asm += 'spcblock $B210-($6E00-!p_sampleData) nspc ; sample data\n'
        self.asm += sample_table.samples_to_asm(fp) + '\n'

        self.asm += 'dw 0,0,0,0 ; padding for shared trackers\n'
        self.asm += 'Trackers:\n'
        self.asm += f'  dw {tracker.label}\n\n'

        self.asm += tracker.to_asm() + '\n'
        for pattern in tracker.patterns.values():
            self.asm += pattern.to_asm() + '\n'
        self.asm += '\n'
        for pattern in tracker.patterns.values():
            end = True
            for track in pattern.tracks:
                if track != None:
                    self.asm += track.to_asm(end=end, perc_base=perc_base, first_perc=first_perc) + '\n'
                    end = False

        for subsection in tracker.subsections().values():
            self.asm += subsection.to_asm(perc_base=perc_base, first_perc=first_perc) + '\n'

        self.asm = self.asm[:-1] # delete newline
        self.asm += 'endspcblock\n\n'
        self.asm += 'spcblock !p_extra nspc\n'
        self.asm += '  dw Trackers-8 : db 0\n'
        self.asm += 'endspcblock execute !p_spcEngine\n'

        return self.asm
