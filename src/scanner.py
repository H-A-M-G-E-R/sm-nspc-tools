from src.spcfile import SPCFile

class NSPCScanner():
    def __init__(self, spc: SPCFile):
        self.spc = spc
        self.instr_table_addr = None
        self.tracker_pointers_addr = None
        self.track_index = 0
        self.note_length_table_addr = None

    def scan_instr_table(self, game='common'):
        # scan for a 'mov y,#$06 : mul ya : movw pp,ya : clrc : adc pp,#$ll : adc pp+1,#$hh' where pp is usually $14 and hhll = instr_table_addr
        # there are a few cases where pp != $14
        # for example, KiKi KaiKai: Nazo no Kuro Mantle/Pocky and Rocky has 'adc $1C,#$00 : adc $1D,#$3E'
        scanned_bytes = self.spc.scan('8D 06 CF DA ?? 60 98 ?? ?? 98 ?? ??')
        if scanned_bytes != None:
            self.instr_table_addr = scanned_bytes[7]+scanned_bytes[10]*0x100
        return self.instr_table_addr

    def scan_tracker_pointers(self, game='common'):
        # scan for a 'asl a : mov x,a : mov a,pppp-1+x : mov y,a : mov a,pppp-2+x : movw $40,ya : mov $0C,#$02' where pppp = tracker_pointers_addr (most games)
        # again, some games have $04, $40 and $0C repointed, and
        # Kirby Super Star has a beq $0E instead of a mov $04,a before the asl for some reason
        scanned_bytes = self.spc.scan('1C 5D F5 ?? ?? FD F5 ?? ?? DA ?? 8F 02 ??')
        if scanned_bytes != None:
            self.tracker_pointers_addr = scanned_bytes[3]+scanned_bytes[4]*0x100+1
        else:
            # Yoshi's Island
            scanned_bytes = self.spc.scan('1C 5D F5 ?? ?? FD D0 03 C4 ?? 6F F5 ?? ?? DA ?? 8F 02 ??')
            if scanned_bytes != None:
                self.tracker_pointers_addr = scanned_bytes[3]+scanned_bytes[4]*0x100+1
        return self.tracker_pointers_addr

    def scan_track_index(self, game='common'):
        saved_addr = self.spc.tell()
        match game:
            case 'f_zero':
                self.spc.seek(0x04)
                self.track_index = self.spc.read_int(1)
            case 'super_mario_all_stars':
                self.spc.seek(0xF6)
                self.track_index = self.spc.read_int(1)
                if self.track_index == 0:
                    self.spc.seek(0x02)
                    self.track_index = self.spc.read_int(1)
                if self.track_index == 0:
                    self.spc.seek(0x06)
                    self.track_index = self.spc.read_int(1)
            case _:
                self.spc.seek(0xF4)
                self.track_index = self.spc.read_int(1)
                if self.track_index == 0:
                    self.spc.seek(0x00)
                    self.track_index = self.spc.read_int(1)
                if self.track_index == 0:
                    self.spc.seek(0x04)
                    self.track_index = self.spc.read_int(1)

        self.spc.seek(saved_addr)
        self.track_index &= 0x7F # needed for Tetris & Dr. Mario
        return self.track_index

    def scan_note_length_table(self, game='common'):
        #$1842: 2D        push  a            ;\
        #$1843: 9F        xcn   a            ;|
        #$1844: 28 07     and   a,#$07       ;|
        #$1846: FD        mov   y,a          ;} Track note ring length multiplier * 100h = [$5800 + ([A] >> 4 & 7)]
        #$1847: F6 00 58  mov   a,$5800+y    ;|
        #$184A: D5 01 02  mov   $0201+x,a    ;|
        #$184D: AE        pop   a            ;/
        #$184E: 28 0F     and   a,#$0F       ;\
        #$1850: FD        mov   y,a          ;|
        #$1851: F6 08 58  mov   a,$5808+y    ;} Track note volume multiplier * 100h = [$5808 + ([A] & Fh)]
        #$1854: D5 10 02  mov   $0210+x,a    ;/
        scanned_bytes = self.spc.scan('2D 9F 28 07 FD F6 ?? ?? D5 ?? ?? AE 28 0F FD F6 ?? ?? D5 ?? ??')
        if scanned_bytes != None:
            self.note_length_table_addr = scanned_bytes[6]+scanned_bytes[7]*0x100
        return self.note_length_table_addr
