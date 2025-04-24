from src.spcfile import SPCFile

class NSPCScanner():
    def __init__(self, spc: SPCFile):
        self.spc = spc
        self.instr_table_addr = None
        self.tracker_pointers_addr = None
        self.track_index = 0

    def scan_instr_table(self):
        # scan for a 'mov y,#$06 : mul ya : movw pp,ya : clrc : adc pp,#$ll : adc pp+1,#$hh' where pp is usually $14 and hhll = instr_table_addr
        # there are a few cases where pp != $14
        # for example, KiKi KaiKai: Nazo no Kuro Mantle/Pocky and Rocky has 'adc $1C,#$00 : adc $1D,#$3E'
        scanned_bytes = self.spc.scan('8D 06 CF DA ?? 60 98 ?? ?? 98 ?? ??')
        if scanned_bytes != None:
            self.instr_table_addr = scanned_bytes[7]+scanned_bytes[10]*0x100
        return self.instr_table_addr

    def scan_tracker_pointers(self):
        # scan for a 'mov $04,a : asl a : mov x,a : mov a,pppp-1+x : mov y,a : mov a,pppp-2+x : movw $40,ya : mov $0C,#$02' where pppp = tracker_pointers_addr (most games)
        # again, some games have $04, $40 and $0C repointed
        scanned_bytes = self.spc.scan('C4 ?? 1C 5D F5 ?? ?? FD F5 ?? ?? DA ?? 8F 02 ??')
        if scanned_bytes != None:
            self.tracker_pointers_addr = scanned_bytes[5]+scanned_bytes[6]*0x100+1
        return self.tracker_pointers_addr

    def scan_track_index(self, game='common'):
        saved_addr = self.spc.tell()
        match game:
            case 'common':
                self.spc.seek(0xF4)
                self.track_index = self.spc.read_int(1)
                if self.track_index == 0:
                    self.spc.seek(0x00)
                    self.track_index = self.spc.read_int(1)
                if self.track_index == 0:
                    self.spc.seek(0x04)
                    self.track_index = self.spc.read_int(1)
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

        self.spc.seek(saved_addr)
        return self.track_index
