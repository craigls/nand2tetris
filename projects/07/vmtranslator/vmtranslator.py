#!/bin/env python3
"""
nand2tetris II: translate Hack .vm to .asm
"""
# Most difficult part was getting all of the memory segments working correctly.
# Had to look at code on github to get it right.


from pathlib import Path
import sys
import re 

COMMANDS = {
    'add': 'C_ARITHMETIC',
    'sub': 'C_ARITHMETIC',
    'neg': 'C_ARITHMETIC',
    'eq': 'C_ARITHMETIC',
    'gt': 'C_ARITHMETIC',
    'lt': 'C_ARITHMETIC',
    'and': 'C_ARITHMETIC',
    'or': 'C_ARITHMETIC',
    'not': 'C_ARITHMETIC',
    'push': 'C_PUSH',
    'pop': 'C_POP',
    'label': 'C_LABEL',
    'goto': 'C_GOTO',
    'if': 'C_IF',
    'function': 'C_FUNCTION',
    'return': 'C_RETURN',
    'call': 'C_CALL',
}

RE_INVALID_CHARS = re.compile(r'\s+')
RE_COMMENT_PATTERN = re.compile(r'//.*')


class Command:
    def __init__(self, cmd, arg1=None, arg2=None, debug=''):
        self.comment = ''
        self.arg1 = None
        self.arg2 = None
        self.cmd = cmd
        self.type = COMMANDS[cmd]

        if self.type == 'C_ARITHMETIC':
            self.arg1 = cmd
        elif self.type == 'C_RETURN': 
            self.arg1 = None
        else:
            self.arg1 = arg1

        if self.type in ('C_PUSH', 'C_POP', 'C_FUNCTION', 'C_CALL'):
            self.arg2 = arg2
        else:
            self.arg2 = None
    
        # Build the comment string
        self.comment = '// ' + debug 

    def __unicode__(self):
        return "Command({}, arg1={}, arg2={}, type={}, comment={})".format(
            self.cmd, 
            self.arg1, 
            self.arg2, 
            self.type,
            self.comment,
        )

class Parser:
    def __init__(self, lines):
        self.lines = lines
        
    def clean(self, line):
        return RE_COMMENT_PATTERN.sub('', line).strip()

    def tokenize(self, line):
        return [
            x.strip() 
            for x in self.clean(line).split() 
            if x.strip()
        ]

    def advance(self):
        for line in self.lines:
            cleaned = self.clean(line)
            tokens = self.tokenize(line)
            if tokens:
                yield Command(*tokens, debug=cleaned)

class CodeWriter:
    BASE_ADDRESSES = {
        'pointer': 3,
        'temp': 5,
        'static': 16, # For reference
        'local': 'LCL',
        'argument': 'ARG',
        'this' : 'THIS',
        'that': 'THAT',
    }

    def __init__(self, classname, out=None):
        self.index = 0
        self.classname = classname
        self.out = out or sys.stdout
        
    def write_comment(self, s):
        self.write('// {}'.format(s))

    def write_command(self, c):
        self.write_comment(c.comment)
        if c.type == 'C_PUSH':
            if c.arg1 == 'temp':
                self.push_temp(c)
            elif c.arg1 == 'pointer':
                self.push_pointer(c)
            elif c.arg1 == 'local':
                self.push_local(c)
            elif c.arg1 == 'this':
                self.push_this(c)
            elif c.arg1 == 'that':
                self.push_that(c)
            elif c.arg1 == 'static':
                self.push_static(c)
            elif c.arg1 == 'argument':
                self.push_argument(c)
            elif c.arg1 == 'constant':
                self.push_constant(c)
            else:
                raise SyntaxError("C_PUSH invalid segment: {}".format(c.arg1))

        elif c.type == 'C_POP':
            if c.arg1 == 'temp':
                self.pop_temp(c)
            elif c.arg1 == 'pointer':
                self.pop_pointer(c)
            elif c.arg1 == 'local':
                self.pop_local(c)
            elif c.arg1 == 'this':
                self.pop_this(c)
            elif c.arg1 == 'that':
                self.pop_that(c)
            elif c.arg1 == 'static':
                self.pop_static(c)
            elif c.arg1 == 'argument':
                self.pop_argument(c)
            else:
                raise SyntaxError("C_POP invalid segment: {}".format(c.arg1))

        elif c.type == 'C_ARITHMETIC':
            self.arithmetic(c)
        self.index += 1

    def write(self, s):
        print(s, file=self.out)

    def dreg_to_stack(self):
        """
        Push contents of D-register onto stack, advance stack pointer
        """
        self.write('@SP')
        self.write('A=M')
        self.write('M=D')
        self.write('@SP')
        self.write('M=M+1')

    def segment_to_areg(self, segment, index):
        if segment == 'static':
            self.write('@{}.{}'.format(self.classname, index))
        else:
            address = self.BASE_ADDRESSES[segment]
            self.write('@{}'.format(address))
            self.write('D=A' if isinstance(address, int) else 'D=M')
            self.write('@{}'.format(index))
            self.write('A=A+D') 
    
    def push_constant(self, c):
        self.write('@' + c.arg2)
        self.write('D=A')
        self.dreg_to_stack()

    def push_temp(self, c):
        self.push_segment('temp', c.arg2)

    def push_pointer(self, c):
        if c.arg2:
            self.write('@THAT')
        else:
            self.write('@THIS')
        self.write('D=M')
        self.dreg_to_stack()
    
    def push_local(self, c):
        self.push_segment('local', c.arg2)

    def push_this(self, c):
        self.push_segment('this', c.arg2)

    def push_that(self, c):
        self.push_segment('that', c.arg2)

    def push_argument(self, c):
        self.push_segment('argument', c.arg2)

    def push_static(self, c):
        self.push_segment('static', c.arg2)

    def push_segment(self, segment, index):
        self.segment_to_areg(segment, index)
        self.write('D=M')
        self.dreg_to_stack()

    def pop_local(self, c):
        self.pop_segment('local', c.arg2)

    def pop_argument(self, c):
        self.pop_segment('argument', c.arg2)

    def pop_this(self, c):
        self.pop_segment('this', c.arg2)

    def pop_that(self, c):
        self.pop_segment('that', c.arg2)

    def pop_static(self, c):
        self.pop_segment('static', c.arg2)

    def pop_temp(self, c):
        self.pop_segment('temp', c.arg2)

    def pop_pointer(self, c):
        self.pop_segment('pointer', c.arg2)

    def pop_segment(self, segment, index):
        self.segment_to_areg(segment, index)
        self.write('D=A')
        self.write('@R15')
        self.write('M=D')
        self.write('@SP')
        self.write('M=M-1')
        self.write('A=M')
        self.write('D=M')
        self.write('@R15')
        self.write('A=M')
        self.write('M=D')
            
    def arithmetic(self, c):
        if c.cmd == 'neg':
            self.write('@SP')
            self.write('A=M-1')
            self.write('M=-M')

        elif c.cmd == 'not':
            self.write('@SP')
            self.write('A=M-1')
            self.write('M=!M')

        else:
            self.write('@SP')
            self.write('M=M-1')
            self.write('A=M')
            self.write('D=M')
            self.write('A=A-1')

            if c.cmd in ('sub', 'eq', 'lt', 'gt'):
                self.write('D=M-D')
            elif c.cmd == 'add':
                self.write('D=M+D')
            elif c.cmd == 'and':
                self.write('D=D&M')
            elif c.cmd == 'or':
                self.write('D=D|M')

            # Operations that produce boolean values
            # Note: true = -1 and false = 0 here
            if c.cmd in ('eq', 'lt', 'gt'):
                self.write('@BOOL_TRUE_{}'.format(self.index))
                if c.cmd == 'eq':
                    self.write('D;JEQ')
                elif c.cmd == 'gt':
                    self.write('D;JGT')
                elif c.cmd == 'lt':
                    self.write('D;JLT')
                elif c.cmd == 'not':
                    self.write('D;JNE')

                self.write('(BOOL_FALSE_{})'.format(self.index))
                self.write('D=0')
                self.write('@BOOL_UPDATE_STACK_{}'.format(self.index))
                self.write('0;JMP')
                self.write('(BOOL_TRUE_{})'.format(self.index))
                self.write('D=-1')
                self.write('(BOOL_UPDATE_STACK_{})'.format(self.index))

            # Push the D value onto A-1
            self.write('@SP')
            self.write('A=M-1')
            self.write('M=D')

def main():
    filename = sys.argv[1]
    classname = Path(filename).name.split('.')[0]

    with open(filename, 'r') as f:
        parser = Parser(f.readlines())
        writer = CodeWriter(classname)
        for tokens in parser.advance():
            writer.write_command(tokens)

if __name__ == '__main__':
    main()
