# Hack assembler! 

import sys
import re
import pprint

RE_VALID_CHARS = re.compile(r'\s+')

SYMBOLS = {
    'R0': 0,
    'R1': 1,
    'R2': 2,
    'R3': 3,
    'R4': 4,
    'R5': 5,
    'R6': 6,
    'R7': 7,
    'R8': 8,
    'R9': 9,
    'R10': 10,
    'R11': 11,
    'R12': 12,
    'R13': 13,
    'R14': 14,
    'R15': 15,
    'SCREEN': 16384,
    'KBD': 24576,
    'SP': 0,
    'LCL': 1,
    'ARG': 2,
    'THIS': 3,
    'THAT': 4,
}

COMP = {
    '0':   '0101010',
    '1':   '0111111',
    '-1':  '0111010',
    'D':   '0001100',
    'A':   '0110000',
    '!D':  '0001101',
    '!A':  '0110001',
    '-D':  '0001111',
    '-A':  '0110011',
    'D+1': '0011111',
    'A+1': '0110111',
    'D-1': '0001110',
    'A-1': '0110010',
    'D+A': '0000010',
    'D-A': '0010011',
    'A-D': '0000111',
    'D&A': '0000000',
    'D|A': '0010101',
    'M':   '1110000',
    '!M':  '1110001',
    '-M':  '1110011',
    'M+1': '1110111',
    'M-1': '1110010',
    'D+M': '1000010',
    'D-M': '1010011',
    'M-D': '1000111',
    'D&M': '1000000',
    'D|M': '1010101',
}
    
DEST = {
    'M': '001',
    'D': '010',
    'MD': '011',
    'A': '100',
    'AM': '101',
    'AD': '110',
    'AMD': '111',
}

JUMP = {
    'JGT': '001',
    'JEQ': '010',
    'JGE': '011',
    'JLT': '100',
    'JNE': '101',
    'JLE': '110',
    'JMP': '111',
}

def prepare(filedata):
    # Strip whitespace, remove comments, etc
    lines = []
    for line in filedata:
        s = RE_VALID_CHARS.sub('', line.split('//')[0]).strip()
        if s:
            lines.append(s)
    return lines
        

def parse_labels(lines):
    # Add goto labels to symbol table
    n = 0
    out = []
    for line in lines:
        if line.startswith('(') and line.endswith(')'):
            SYMBOLS[line[1:-1]] = n
        else:
            out.append(line)
            n += 1
        
    return out
        
def parse_code(lines):
    out = []
    n = 16
    for line in lines:
        if line.startswith('@'):
            (n, ins) = handle_a(n, line)
            out.append(ins)
        else:
            (n, ins) = handle_c(n, line)
            out.append(ins)
    return out
             
        
def handle_a(n, s):
    # A-Instruction
    if s[1:].isdigit():
        value = s[1:]
    elif s[1:] not in SYMBOLS:
        value = SYMBOLS[s[1:]] = n 
        n += 1
    else: 
        value = SYMBOLS[s[1:]]
    return (n, '0{0:015b}'.format(int(value)))

def handle_c(n, line):
    # C-Instruction
    dest = comp = jump = ''

    if '=' in line:
        dest = line.split('=')[0].split(';')[0]
        comp = line.split('=')[1].split(';')[0]
    else:
        comp = line.split(';')[0]
    if ';' in line:
        jump = line.split(';')[1]

    dest_b = DEST.get(dest, '000')
    comp_b = COMP.get(comp, '0000000')
    jump_b = JUMP.get(jump, '000')

    out = '111' 
    out += comp_b
    out += dest_b
    out += jump_b
    return (n, out)

def assemble(data):
    return '\n'.join(parse_code(parse_labels(prepare(data))))

if __name__ == '__main__':
    with open(sys.argv[1], 'r') as f:
        print assemble(f.readlines())
