from src.spcfile import SPCFile

class Track():
    keys = ['!c', '!cs', '!d', '!ds', '!e', '!f', '!fs', '!g', '!gs', '!a', '!as', '!b']

    command_lengths = {
        0xE0: 1, # E0 ii       ; Select instrument i
        0xE1: 1, # E1 pp       ; Panning bias = (p & 1Fh) / 14h. If p & 80h, left side phase inversion is enabled. If p & 40h, right side phase inversion is enabled
        0xE2: 2, # E2 tt bb    ; Dynamic panning over t tics with target panning bias b / 14h
        0xE3: 3, # E3 dd rr ee ; Static vibrato after d tics at rate r with extent e
        0xE4: 0, # E4          ; End vibrato
        0xE5: 1, # E5 vv       ; Music volume multiplier = v / 100h
        0xE6: 2, # E6 tt vv    ; Dynamic music volume over t tics with target volume multiplier v / 100h
        0xE7: 1, # E7 tt       ; Music tempo = t / (0x100 * 0.002) tics per second
        0xE8: 2, # E8 tt TT    ; Dynamic music tempo over t tics with target tempo TT / (0x100 * 0.002) tics per second
        0xE9: 1, # E9 tt       ; Set music transpose of t semitones
        0xEA: 1, # EA tt       ; Set transpose of t semitones
        0xEB: 3, # EB dd rr ee ; Tremolo after d tics at rate r with extent e
        0xEC: 0, # EC          ; End tremolo
        0xED: 1, # ED vv       ; Volume multiplier = v / 100h
        0xEE: 2, # EE tt vv    ; Dynamic volume over t tics with target volume multiplier v / 100h
        0xEF: 3, # EF pppp cc  ; Play subsection p, c times
        0xF0: 1, # F0 ll       ; Dynamic vibrato over l tics with target extent 0
        0xF1: 3, # F1 dd ll ee ; Slide out after d tics for l tics by e semitones
        0xF2: 3, # F2 dd ll ee ; Slide in after d tics for l tics by e semitones
        0xF3: 0, # F3          ; End slide
        0xF4: 1, # F4 ss       ; Set subtranspose of s / 100h semitones
        0xF5: 3, # F5 vv ll rr ; Static echo on voices v with echo volume left = l and echo volume right = r
        0xF6: 0, # F6          ; End echo
        0xF7: 3, # F7 dd ff ii ; Set echo parameters: echo delay = d, echo feedback volume = f, echo FIR filter index = i (range 0..3)
        0xF8: 3, # F8 dd ll rr ; Dynamic echo volume after d tics with target echo volume left = l and target echo volume right = r
        0xF9: 3, # F9 dd ll tt ; Pitch slide after d tics over l tics by t semitones
        0xFA: 1  # FA ii       ; Percussion instruments base index = i
    }

    command_names = {
        0xE0: '!instr',
        0xE1: '!pan',
        0xE2: '!dynamicPan',
        0xE3: '!vibrato',
        0xE4: '!endVibrato',
        0xE5: '!musicVolume',
        0xE6: '!dynamicMusicVolume',
        0xE7: '!tempo',
        0xE8: '!dynamicTempo',
        0xE9: '!musicTranspose',
        0xEA: '!transpose',
        0xEB: '!tremolo',
        0xEC: '!endTremolo',
        0xED: '!volume',
        0xEE: '!dynamicVolume',
        0xEF: '!loop',
        0xF0: '!dynamicVibrato',
        0xF1: '!slideOut',
        0xF2: '!slideIn',
        0xF3: '!endSlide',
        0xF4: '!subtranspose',
        0xF5: '!echo',
        0xF6: '!endEcho',
        0xF7: '!echoParameters',
        0xF8: '!dynamicEcho',
        0xF9: '!pitchSlide',
        0xFA: '!percBase'
    }

    def __init__(self, label=''):
        self.label = label
        self.commands = []
        self.len = 0
        self.note_len = 0
        self.is_subroutine = False

    def extract(self, spc: SPCFile, addr, len_limit=None):
        saved_addr = spc.tell()
        spc.seek(addr)

        while True:
            command = spc.read_int(1)
            if command == 0: # terminator
                break
            elif command < 0x80: # note length
                self.note_len = command
                next_byte = spc.read_int(1)
                if next_byte < 0x80: # volume and ring length
                    self.commands.append([command, next_byte])
                else:
                    spc.seek(spc.tell()-1)
                    self.commands.append([command])
            elif command < 0xE0: # note, tie, rest and percussion note
                self.len += self.note_len
                self.commands.append([command])
                if len_limit != None and self.len >= len_limit:
                    break
            elif command == 0xEF: # play subsection command
                if self.is_subroutine:
                    raise AssertionError('Subroutines cannot be nested')
                subsection_addr = spc.read_int(2)
                repetitions = spc.read_int(1)

                subsection = Track(label=f'.sub{subsection_addr:04X}')
                subsection.is_subroutine = True
                subsection.note_len = self.note_len
                subsection.extract(spc, subsection_addr)

                if repetitions > 0:
                    self.note_len = subsection.note_len
                    self.len += subsection.len*repetitions
                self.commands.append([command, subsection, repetitions])
                if len_limit != None and self.len >= len_limit:
                    break
            else: # track command
                length = Track.command_lengths[command]
                self.commands.append([command] + [spc.read_int(1) for _ in range(length)])

        spc.seek(saved_addr)

    def asm_defines():
        defines = ''
        for note in range(0xC8-0x80):
            defines += f'{Track.keys[note%12]}{note//12+2} = "db ${note+0x80:02X}"\n'
        defines += '\n!end = "db 0"\n!tie = "db $C8"\n!rest = "db $C9"\n\n'
        defines += 'macro percNote(instr)\n'
        defines += '  db <instr>+$CA\n'
        defines += 'endmacro\n\n'
        for command, name in Track.command_names.items():
            defines += f'{name} = "db ${command:02X}"\n'
        defines += '\n'
        return defines

    def to_asm(self, end=True, perc_base=0, first_perc=None, main_vol_l=0x60, main_vol_r=0x60):
        asm = f'{self.label}\n'
        for command in self.commands:
            asm += '  '
            if command[0] < 0x80:
                asm += f'db {command[0]}{''.join(f',${b:02X}' for b in command[1:])}\n'
            elif command[0] < 0xC8:
                asm += f'{Track.keys[(command[0]-0x80)%12]}{(command[0]-0x80)//12+2}\n'
            elif command[0] == 0xC8:
                asm += '!tie\n'
            elif command[0] == 0xC9:
                asm += '!rest\n'
            elif command[0] < 0xE0:
                #asm += f'%percNote(${command[0]-0xCA:02X})\n'
                asm += f'%percNote(!instr{command[0]-0XCA+perc_base:02X}-!instr{first_perc:02X})\n'
            elif command[0] == 0xEF:
                asm += f'{Track.command_names[0xEF]} : dw {command[1].label} : db {command[2]}\n'
            else:
                params = [f',{b}' for b in command[1:]]
                if command[0] == 0xE0:
                    #params[0] = f',${command[1]:02X}'
                    if command[1] >= 0xCA: # select percussion instrument
                        params[0] = f',!instr{command[1]-0xCA+perc_base:02X}'
                    else:
                        params[0] = f',!instr{command[1]:02X}'
                elif command[0] == 0xF5:
                    # Normalize echo volume
                    params[1] = f',{round(command[2]*0x60/main_vol_l)}'
                    params[2] = f',{round(command[3]*0x60/main_vol_r)}'
                elif command[0] == 0xFA:
                    #params[0] = f',${command[1]:02X}'
                    if first_perc == None:
                        asm = asm[:-2]
                        continue
                    params[0] = f',!instr{first_perc:02X}'
                elif command[0] == 0xF5:
                    params[0] = f',%{command[1]:08b}'
                asm += f'{Track.command_names[command[0]]}{''.join(params)}\n'
        if end:
            asm += '  !end\n'
        return asm

class Pattern():
    def __init__(self, label=''):
        self.label = label
        self.tracks = [None]*8

    def extract(self, spc: SPCFile, addr):
        saved_addr = spc.tell()
        spc.seek(addr)

        len_limit = None
        for i in range(8):
            track_addr = spc.read_int(2)
            if track_addr != 0:
                track = Track(label=f'{self.label}_{i}')
                track.extract(spc, track_addr, len_limit)

                self.tracks[i] = track
                if len_limit == None:
                    len_limit = self.tracks[i].len

        spc.seek(saved_addr)

    def to_asm(self):
        return f'{self.label}: dw {', '.join('0' if track == None else track.label for track in self.tracks)}'

class Tracker():
    def __init__(self, label=''):
        self.label = label
        self.commands = []
        self.patterns = {}

    def extract(self, spc: SPCFile, addr):
        saved_addr = spc.tell()
        spc.seek(addr)

        command_addrs = []
        pattern_i = 0
        while True:
            command_addrs.append(spc.tell())
            command = spc.read_int(2)
            if command == 0 or spc.tell() in command_addrs: # terminator
                break
            elif command < 0x100: # jump
                goto_addr = spc.read_int(2)
                self.commands.append([command, command_addrs.index(goto_addr)])
                if command >= 0x81:
                    break
            else: # play pattern
                if not f'{command:04X}' in self.patterns:
                    label = f'.pattern{pattern_i}'
                    pattern_i += 1
                    pattern = Pattern(label)
                    pattern.extract(spc, command)
                    self.patterns[label] = pattern
                self.commands.append([label])

        spc.seek(saved_addr)

    def to_asm(self):
        asm = f'{self.label}:\n'
        loop_indices = set()
        for command in self.commands:
            if type(command[0]) != str:
                loop_indices.add(command[1])

        i = 0
        for command in self.commands:
            if i in loop_indices:
                asm += '-\n'
            if type(command[0]) == str:
                asm += f'  dw {command[0]}\n'
            else:
                asm += f'  dw ${command[0]:04X},-\n'
            i += 1
        if type(self.commands[-1][0]) == str or self.commands[-1][0] < 0x82: # track doesn't loop
            asm += f'  dw $0000\n'
        return asm

    def subsections(self):
        subsections = {}
        for pattern in self.patterns.values():
            for track in pattern.tracks:
                if track != None:
                    for command in track.commands:
                        if command[0] == 0xEF:
                            subsections[command[1].label] = command[1]

        return subsections

    def tracks_and_subsections(self):
        for pattern in self.patterns.values():
            for track in pattern.tracks:
                if track != None:
                    yield track
        for subsection in self.subsections().values():
            yield subsection

    def used_instrs(self, perc_base=0):
        used_instrs = set()
        used_perc_instrs = set()
        for track in self.tracks_and_subsections():
            for command in track.commands:
                if command[0] == 0xE0:
                    if command[1] >= 0xCA:
                        used_instrs.add(command[1]-0xCA+perc_base)
                    else:
                        used_instrs.add(command[1])
                elif command[0] >= 0xCA and command[0] < 0xE0:
                    used_perc_instrs.add(command[0]-0xCA+perc_base)

        return (used_instrs, used_perc_instrs)

    def perc_base(self):
        perc_base = 0
        for track in self.tracks_and_subsections():
            for command in track.commands:
                if command[0] == 0xFA:
                    perc_base = command[1]
        return perc_base
