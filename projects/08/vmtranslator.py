#!/bin/env python3
"""
nand2tetris II: translate Hack .vm to .asm

Writes .asm to standard output
"""

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
    'if-goto': 'C_IF',
    'function': 'C_FUNCTION',
    'return': 'C_RETURN',
    'call': 'C_CALL',
}

RE_INVALID_CHARS = re.compile(r'\s+')
RE_COMMENT_PATTERN = re.compile(r'//.*')

MAIN_CLASSNAME = 'Main'


class Command:
    def __init__(self, cmd, arg1=None, arg2=None, debug=''):
        self.cmd = cmd
        self.comment = ''
        self.arg1 = None
        self.arg2 = None
        self.type = COMMANDS[cmd]

        if self.type == 'C_ARITHMETIC':
            self.arg1 = cmd
            self.arg2 = None
        elif self.type == 'C_RETURN': 
            self.arg1 = None
            self.arg2 = arg2
        elif self.type in ('C_CALL', 'C_FUNCTION', 'C_PUSH', 'C_POP'):
            self.arg1 = arg1
            self.arg2 = int(arg2) 
        elif self.type in (
            'C_IF',
            'C_LABEL',
            'C_GOTO'
        ):
            self.arg1 = arg1
            self.arg2 = arg2
        else:
            raise SyntaxError(cmd)
    
        # Build the comment string
        if debug:
            self.comment = debug 

    def __repr__(self):
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

    def __init__(self, classname=None, out=None):
        self.classname = classname
        self.command_index = 0
        self.return_label_index = 0
        self.out = out or sys.stdout

    def write_bootstrap(self):
        """
        Sets stack pointer to 256 and calls Sys.init
        """
        self.write_comment('Bootstrap')
        self.write('@256')
        self.write('D=A')
        self.write('@SP')
        self.write('M=D')
        self.write_call('Sys.init', 0)

    def write_comment(self, s):
        self.write('// {}'.format(s))

    def write_command(self, c):
        self.write_comment(c.comment)
        if c.type == 'C_PUSH':
            if c.arg1 == 'temp':
                self.push_temp(c.arg2)
            elif c.arg1 == 'pointer':
                self.push_pointer(c.arg2)
            elif c.arg1 == 'local':
                self.push_local(c.arg2)
            elif c.arg1 == 'this':
                self.push_this(c.arg2)
            elif c.arg1 == 'that':
                self.push_that(c.arg2)
            elif c.arg1 == 'static':
                self.push_static(c.arg2)
            elif c.arg1 == 'argument':
                self.push_argument(c.arg2)
            elif c.arg1 == 'constant':
                self.push_constant(c.arg2)
            else:
                raise SyntaxError("C_PUSH invalid segment: {}".format(c.arg1))

        elif c.type == 'C_POP':
            if c.arg1 == 'temp':
                self.pop_temp(c.arg2)
            elif c.arg1 == 'pointer':
                self.pop_pointer(c.arg2)
            elif c.arg1 == 'local':
                self.pop_local(c.arg2)
            elif c.arg1 == 'this':
                self.pop_this(c.arg2)
            elif c.arg1 == 'that':
                self.pop_that(c.arg2)
            elif c.arg1 == 'static':
                self.pop_static(c.arg2)
            elif c.arg1 == 'argument':
                self.pop_argument(c.arg2)
            else:
                raise SyntaxError("C_POP invalid segment: {}".format(c.arg1))

        elif c.type == 'C_ARITHMETIC':
            self.arithmetic(c.cmd)
        elif c.type == 'C_CALL':
            self.write_call(c.arg1, c.arg2)
        elif c.type == 'C_FUNCTION':
            self.write_function(c.arg1, c.arg2)
        elif c.type == 'C_RETURN':
            self.write_return(c.arg2)
        elif c.type == 'C_IF':
            self.write_if(c.arg1)
        elif c.type == 'C_LABEL':
            self.write_label(c.arg1)
        elif c.type == 'C_GOTO':
            self.write_goto(c.arg1)
        else:
            raise SyntaxError(c.type)

        self.command_index += 1

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
    
    def push_constant(self, index):
        self.write('@{}'.format(index))
        self.write('D=A')
        self.dreg_to_stack()

    def push_temp(self, index):
        self.push_segment('temp', index)

    def push_pointer(self, index):
        self.write('@THAT' if index else '@THIS')
        self.write('D=M')
        self.dreg_to_stack()

    def push_local(self, index):
        self.push_segment('local', index)

    def push_this(self, index):
        self.push_segment('this', index)

    def push_that(self, index):
        self.push_segment('that', index)

    def push_argument(self, index):
        self.push_segment('argument', index)

    def push_static(self, index):
        self.push_segment('static', index)

    def push_segment(self, segment, index):
        self.segment_to_areg(segment, index)
        self.write('D=M')
        self.dreg_to_stack()

    def pop_local(self, index):
        self.pop_segment('local', index)

    def pop_argument(self, index):
        self.pop_segment('argument', index)

    def pop_this(self, index):
        self.pop_segment('this', index)

    def pop_that(self, index):
        self.pop_segment('that', index)

    def pop_static(self, index):
        self.pop_segment('static', index)

    def pop_temp(self, index):
        self.pop_segment('temp', index)

    def pop_pointer(self, index):
        self.write('@SP')
        self.write('M=M-1')
        self.write('A=M')
        self.write('D=M')
        self.write('@THAT' if index else '@THIS')
        self.write('M=D')

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
            
    def arithmetic(self, cmd):
        if cmd == 'neg':
            self.write('@SP')
            self.write('A=M-1')
            self.write('M=-M')

        elif cmd == 'not':
            self.write('@SP')
            self.write('A=M-1')
            self.write('M=!M')

        else:
            self.write('@SP')
            self.write('M=M-1')
            self.write('A=M')
            self.write('D=M')
            self.write('A=A-1')

            if cmd in ('sub', 'eq', 'lt', 'gt'):
                self.write('D=M-D')
            elif cmd == 'add':
                self.write('D=M+D')
            elif cmd == 'and':
                self.write('D=D&M')
            elif cmd == 'or':
                self.write('D=D|M')

            # Operations that produce boolean values
            # Note: true = -1 and false = 0 here
            if cmd in ('eq', 'lt', 'gt'):
                self.write('@{}$BOOL_TRUE.{}'.format(self.classname, self.command_index))
                if cmd == 'eq':
                    self.write('D;JEQ')
                elif cmd == 'gt':
                    self.write('D;JGT')
                elif cmd == 'lt':
                    self.write('D;JLT')
                elif cmd == 'not':
                    self.write('D;JNE')

                self.write('({}$BOOL_FALSE.{})'.format(self.classname, self.command_index))
                self.write('D=0')
                self.write('@{}$BOOL_END.{}'.format(self.classname, self.command_index))
                self.write('0;JMP')
                self.write('({}$BOOL_TRUE.{})'.format(self.classname, self.command_index))
                self.write('D=-1')
                self.write('({}$BOOL_END.{})'.format(self.classname, self.command_index))

            # Push the D value onto A-1
            self.write('@SP')
            self.write('A=M-1')
            self.write('M=D')

    def init(self):
        self.write('@SP')
        self.write('M=256')

    def write_label(self, label):
        self.write('({}${})'.format(self.classname, label))

    def write_function(self, funcname, nvars):
        # Write function label
        self.write('({})'.format(funcname))

        # Push local nvars 
        self.write('@LCL')
        self.write('A=M')

        for x in range(nvars):
            self.write('M=0')
            self.write('A=A+1')

    def write_return(self, label):
        # Store endFrame in R13
        self.write('@LCL')
        self.write('D=M')

        self.write('@R13')
        self.write('M=D')

        # Store returnAddr = *(endFrame - 5)
        self.write('@5')
        self.write('D=D-A')
        self.write('A=D')
        self.write('D=M')
        self.write('@R14')
        self.write('M=D')

        # *ARG pop()
        self.write('@SP')
        self.write('M=M-1')
        self.write('A=M')
        self.write('D=M')
        self.write('@ARG')
        self.write('A=M')
        self.write('M=D')

        # SP = ARG + 1
        self.write('@ARG')
        self.write('D=M+1')
        self.write('@SP')
        self.write('M=D')

        for ptr in ['@THAT', '@THIS', '@ARG', '@LCL']:
            # Set D = *(--endFrame) 
            self.write('@R13')
            self.write('M=M-1')
            self.write('A=M')
            self.write('D=M')

            # Restore pointer to saved value
            self.write(ptr)
            self.write('M=D')

        # Goto return address in @R14
        self.write('@R14')
        self.write('A=M')
        self.write('0;JMP')
        
    def write_if(self, label):
        self.write('@SP')
        self.write('M=M-1')
        self.write('A=M')
        self.write('D=M')
        self.write('@{}${}'.format(self.classname, label))
        self.write('D;JNE')
        
    def write_goto(self, funcname):
        self.write('@{}${}'.format(self.classname, funcname))
        self.write('0;JMP')

    def write_call(self, funcname, nvars):
        return_label = '{}$RET.{}'.format(funcname, self.return_label_index)

        # Save return address to stack
        self.write('@{}'.format(return_label))
        self.write('D=A')
        self.dreg_to_stack()

        # Backup the caller pointer values to stack
        for ptr in ['@LCL', '@ARG', '@THIS', '@THAT']:
            self.write(ptr)
            self.write('D=M')
            self.dreg_to_stack()
        
        # Reposition @ARG (SP - 5 - nvars))))
        self.write('@SP')
        self.write('D=M')

        self.write('@{}'.format(5 + nvars))
        self.write('D=D-A')

        self.write('@ARG')
        self.write('M=D')

        # Reposition @LCL
        self.write('@SP')
        self.write('D=M')
        self.write('@LCL')
        self.write('M=D')

        # Jump to funcname
        self.write('@{}'.format(funcname))
        self.write('0;JMP')

        # Write the return label
        self.write('({})'.format(return_label))

        # Increment return label index for next time
        self.return_label_index += 1
        
def main():
    path = Path(sys.argv[1])

    # If argument is a directory, get all *.vm files, generate bootstrap code
    if path.is_dir():
        vmfiles = path.glob('**/*.vm') 
        CodeWriter('').write_bootstrap()
    else:
        vmfiles = [path] # Don't generate bootstrap code if there's only one vm file
    for filename in vmfiles:
        classname = Path(filename).name.split('.')[0]
        with open(filename, 'r') as f:
            parser = Parser(f.readlines())
            writer = CodeWriter(classname)
            for command in parser.advance():
                writer.write_command(command)

if __name__ == '__main__':
    main()
