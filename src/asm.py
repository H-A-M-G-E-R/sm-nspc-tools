from src.spcfile import SPCFile
from src.instr import BRRSample, SampleTable, InstrTable
from src.track import Track, Pattern, Tracker

class PJASMConverter():
    def __init__(self, spc, game='common'):
        self.spc = spc
        self.asm = ''
        self.game = game

    def convert(self, p_instr_table, p_track, p_note_length_table, defines_fp='defines.asm', hash_option=False, vol_multiplier=1.0):
        self.spc.seek(0x1000C)
        main_vol_l = self.spc.read_int(1)
        self.spc.seek(0x1001C)
        main_vol_r = self.spc.read_int(1)

        self.asm += 'asar 1.91\n'
        self.asm += 'norom : org 0\n'
        self.asm += f'incsrc "{defines_fp}"\n\n'

        tracker = Tracker(label=f'Tracker{p_track:04X}', game=self.game)
        tracker.extract(self.spc, p_track)
        for track in tracker.tracks_and_subsections():
            track.amplify(vol_multiplier)
            track.normalize_echo_volume(main_vol_l=0x60, main_vol_r=0x60)

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
        self.sample_table = SampleTable()
        self.sample_table.extract(self.spc, self.spc.read_int(1)*0x100, used_sample_ids=used_instrs[0] | used_instrs[1])
        self.asm += 'spcblock 4*$16+!p_sampleTable nspc ; sample table\n'
        self.asm += self.sample_table.sample_table_to_asm()
        self.asm += 'endspcblock\n\n'

        self.asm += 'spcblock $B210-$6E00+!p_sampleData nspc ; sample data\n'
        self.asm += self.sample_table.samples_to_asm('', hash_option) + '\n'

        self.spc.seek(p_note_length_table)
        note_length_table = [self.spc.read_int(1) for _ in range(0x18)]

        if note_length_table != Track.standard_note_length_table:
            self.asm += 'NoteLengthTable: ; note length table\n'
            self.asm += f'  db ${',$'.join(f'{b:02X}' for b in note_length_table[:8])}\n'
            self.asm += f'  db ${',$'.join(f'{b:02X}' for b in note_length_table[8:])}\n\n'

        self.asm += 'dw 0,0,0,0 ; padding for shared trackers\n'
        self.asm += 'Trackers:\n'
        self.asm += f'  dw {tracker.label}\n\n'

        self.asm += tracker.to_asm() + '\n'
        for pattern in tracker.patterns.values():
            self.asm += pattern.to_asm() + '\n'
        self.asm += '\n'
        used_tracks = set()
        for pattern in tracker.patterns.values():
            end = True
            for track in pattern.tracks:
                if track != None and not track.label in used_tracks:
                    self.asm += track.to_asm(end=end, perc_base=perc_base, first_perc=first_perc, use_custom_note_length_table=note_length_table != Track.standard_note_length_table) + '\n'
                    used_tracks.add(track.label)
                    #end = False

        for subsection in tracker.subsections().values():
            self.asm += subsection.to_asm(perc_base=perc_base, first_perc=first_perc) + '\n'

        self.asm = self.asm[:-1] # delete newline
        self.asm += 'endspcblock\n\n'
        self.asm += 'spcblock !p_extra nspc\n'
        self.asm += '  dw Trackers-8 : db 0\n'
        self.asm += 'endspcblock execute !p_spcEngine\n'

        return self.asm
