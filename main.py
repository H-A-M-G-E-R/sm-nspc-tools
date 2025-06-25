from src.spcfile import SPCFile
from src.instr import SampleTable, InstrTable
from src.scanner import NSPCScanner
from src.asm import PJASMConverter
import argparse, glob, os.path, sys

# Currently supported games
game_list = (
    'common',
    'f_zero',
    'super_mario_all_stars',
    'hal'
)

argparser = argparse.ArgumentParser(description = 'Converts SPC files using the N-SPC engine to ASM')

subparsers = argparser.add_subparsers(dest = 'mode', help = '')
parser_a = subparsers.add_parser('pj', help = 'ASM for PJ\'s optimized sound engine')
parser_a.add_argument('--game', type = str, choices=game_list, default='common', help = 'Game to autodetect instrument table and tracker')
parser_a.add_argument('--p_instr_table', type = lambda n: int(n, 16), default=None, help = 'Address of instrument table')
parser_a.add_argument('--p_track_pointers', type = lambda n: int(n, 16), default=None, help = 'Address of tracker pointers')
parser_a.add_argument('--p_note_length_table', type = lambda n: int(n, 16), default=None, help = 'Address of note length table')
parser_a.add_argument('--i_track', type = lambda n: int(n, 16), default=None, help = 'Tracker index')
parser_a.add_argument('--p_track', type = lambda n: int(n, 16), default=None, help = 'Address of track')
parser_a.add_argument('--defines_fp', type = str, default='defines.asm', help = 'Relative path to defines')
parser_a.add_argument('--export_samples', action='store_true', help = 'Whether to export samples')
parser_a.add_argument('--amplify', type = float, default=1.0, help = 'Amplify volume by a multiplier')
parser_a.add_argument('spc', type = str, help = 'Filepath to input SPC')
parser_a.add_argument('asm', type = str, help = 'Filepath to output ASM')

parser_b = subparsers.add_parser('pj_bulk', help = 'Bulk ASM for PJ\'s optimized sound engine')
parser_b.add_argument('--game', type = str, choices=game_list, default='common', help = 'Game to autodetect instrument table and tracker')
parser_b.add_argument('--defines_fp', type = str, default='defines.asm', help = 'Relative path to defines')
parser_b.add_argument('--export_samples', action='store_true', help = 'Whether to export samples')
parser_b.add_argument('--amplify', type = float, default=1.0, help = 'Amplify volume by a multiplier')
parser_b.add_argument('spc', type = str, help = 'Folder path to input SPCs')
parser_b.add_argument('asm', type = str, help = 'Folder path to output ASMs (and BRRS)')

parser_c = subparsers.add_parser('sample', help = 'Export BRR samples to a folder')
parser_c.add_argument('spc', type = str, help = 'Filepath to input SPC')
parser_c.add_argument('fp', type = str, help = 'Folder path to output BRRs')

args = argparser.parse_args()

if args.mode == 'pj':
    spc = SPCFile(args.spc)
    scanner = NSPCScanner(spc)
    if args.p_instr_table == None:
        args.p_instr_table = scanner.scan_instr_table(args.game)
    if args.p_track == None:
        if args.p_track_pointers == None:
            args.p_track_pointers = scanner.scan_tracker_pointers(args.game)
        if args.i_track == None:
            args.i_track = scanner.scan_track_index(args.game)
        spc.seek(args.p_track_pointers+args.i_track*2-2)
        args.p_track = spc.read_int(2)
    if args.p_note_length_table == None:
        args.p_note_length_table = scanner.scan_note_length_table(args.game)

    asm = open(args.asm, 'w')
    converter = PJASMConverter(spc, game=args.game)
    asm.write(converter.convert(args.p_instr_table, args.p_track, args.p_note_length_table, args.defines_fp, args.export_samples, args.amplify))

    if args.export_samples:
        converter.sample_table.samples_to_files(os.path.split(args.asm)[0], hash_option=True)
elif args.mode == 'pj_bulk':
    for spc_path in glob.glob(os.path.join(args.spc, '*.spc')):
        try:
            spc = SPCFile(spc_path)
            scanner = NSPCScanner(spc)
            spc.seek(scanner.scan_tracker_pointers(args.game)+scanner.scan_track_index(args.game)*2-2)
            p_track = spc.read_int(2)
            p_note_length_table = scanner.scan_note_length_table(args.game)

            spc_filename = os.path.split(spc_path)[1]
            asm = open(os.path.join(args.asm, os.path.splitext(spc_filename)[0] + '.asm'), 'w')
            converter = PJASMConverter(spc, game=args.game)
            asm.write(converter.convert(scanner.scan_instr_table(args.game), p_track, p_note_length_table, args.defines_fp, args.export_samples, args.amplify))

            if args.export_samples:
                converter.sample_table.samples_to_files(args.asm, hash_option=True)
        except:
            print(f'Unable to convert {os.path.split(spc_path)[1]}: {repr(sys.exception())}')
elif args.mode == 'sample':
    spc = SPCFile(args.spc)
    spc.seek(0x1005D)
    sample_table = SampleTable()
    sample_table.extract(spc, spc.read_int(1)*0x100)
    sample_table.samples_to_files(args.fp)
