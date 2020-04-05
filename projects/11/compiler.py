"""
Jack language compiler
"""

import sys
import os
from tokenizer import Tokenizer
from xml.dom.minidom import Document
from pathlib import Path
import logging
from collections import namedtuple, Counter

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

class SymbolTable:
    Symbol = namedtuple('Symbol', ['name', 'type', 'kind', 'index'])

    def __init__(self):
        self.counts = Counter()
        self.table = {}

    def define(self, name, type_, kind):
        self.counts[kind] += 1

        self.table[name] = self.Symbol(
            name, 
            type_, 
            kind, 
            self.counts[kind] - 1 # index starts at 0
        )
        return self.table[name]

    def count(self, kind):
        return self.counts.get(kind, 0)

    def lookup(self, name):
        return self.table[name] if name in self.table else None



class CompilationEngine:

    OPERATORS = {
        '+': 'add',
        '-': 'sub',
        '*': 'call Math.multiply 2',
        '/': 'call Math.divide 2',
        '&': 'and',
        '|': 'or',
        '<': 'gt',
        '>': 'lt',
        '=': 'eq',
    }

    def __init__(self, tokenizer, out):
        self.tokenizer = tokenizer
        self.out = out
        self.current = None
        self.next = None
        self.current = self.tokenizer.get_token()
        self.next = self.tokenizer.get_token()
        self.if_index = 0
        self.while_index = 0
        self.return_type = False

    def advance(self):
        self.current = self.next
        self.next = self.tokenizer.get_token()

    def lookup(self, name):
        return self.symbols.lookup(name) or self.class_symbols.lookup(name)

    def code_write(self, exp):
        if str(exp).isdigit():
            self.write('push constant {}'.format(exp))

        elif self.lookup(exp):
            symbol = self.lookup(exp)
            self.write('push {} {}'.format(symbol.kind, symbol.index))
        elif exp == 'this':
            self.write('push pointer 0')
        elif exp == 'that':
            self.write('push pointer 1')

        # Operators
        elif exp in self.OPERATORS:
            self.write(self.OPERATORS[exp])

        # Constants
        elif exp in ('null', 'false'):
            self.write('push constant 0')
        elif exp == 'true':
            self.write('push constant 0')
            self.write('neg')

        # String?
        elif exp.startswith('"') and exp.endswith('"'):
            string = exp[1:-1]
            self.write("call String.new 1")
            for char in string:
                self.write("push pointer 0")
                self.write('push constant {}'.format(ord(char)))
                self.write('call String.appendChar 2')
        else:
            raise SyntaxError(exp)
        

    def write(self, s):
        print(s, file=self.out)
            
    def eat(self, value=None):
        if value is not None and self.current.value != value:
            raise SyntaxError("{} != {} (next: {})".format(
                self.current.value, 
                value, 
                self.next.value)
            )
        else:
            print("// " + self.current.value, file=self.out)
            tmp = self.current
            self.advance()
            return tmp.value
    
    def compile_class(self):
        # Init symbol table
        self.class_symbols = SymbolTable()

        self.eat('class')
        self.class_name = self.eat()
        self.eat('{')
        while self.current.value in ('static', 'field'):
            self.compile_class_var_dec()
        while self.current.value != '}':
            self.compile_subroutine_dec()
        self.eat('}')

    def compile_class_var_dec(self):
        kind = self.eat() # static | field
        type_ = self.eat() # int | char | boolean | className
        while True:
            self.class_symbols.define(
                type_ = type_,
                kind = 'this' if kind == 'field' else kind,
                name = self.eat(), # varName
            )
            if self.current.value != ',':
                break
            self.eat(',')
        self.eat(';')

    def compile_subroutine_dec(self):
        self.symbols = SymbolTable()

        sub_type = self.eat() # constructor|function|method
        self.return_type = self.eat() # void | (type)
        sub_name = self.eat() # subroutineName

        if sub_type == 'method':
            self.symbols.define('this', self.class_name, 'argument')

        nvars = self.compile_parameter_list()

        self.eat('{')
        while self.current.value == 'var':
            self.compile_var_dec()

        self.write('function {}.{} {}'.format(
            self.class_name, 
            sub_name, 
            self.symbols.count('local')) 
        )

        if sub_type == 'method':
            self.write('push argument 0')  
            self.write('pop pointer 0')  # THIS = argument 0
            self.compile_statements()

        elif sub_type == 'constructor':
            nvars = self.class_symbols.count('this')
            self.write('push constant {}'.format(nvars))
            self.write('call Memory.alloc 1')
            self.write('pop pointer 0') # Anchor THIS at base address
            self.compile_statements()

        elif sub_type == 'function':
            self.compile_statements()

        else:
            raise SyntaxError(sub_type)
        self.eat('}')

    def compile_parameter_list(self):
        nvars = 0
        self.eat('(')
        while self.current.value != ')':
            nvars += 1
            self.symbols.define(
                kind = 'argument',
                type_ = self.eat(),
                name = self.eat(),
            )
            if self.current.value == ',':
                self.eat(',')
        self.eat(')')
        return nvars

    def compile_var_dec(self):
        self.eat('var')
        type_ = self.eat() # type
        while True:
            self.symbols.define(
                kind = 'local', 
                name = self.eat(), # varName
                type_ = type_,
            )
            if self.current.value != ',':
                break
            self.eat(',')
        self.eat(';')

    def compile_let(self):
        self.eat('let')
        var_name = self.eat()
        symbol = self.lookup(var_name)

        if self.current.value == '[': # handle varName[expression]
            self.eat('[')
            self.compile_expression()
            self.eat(']')
        self.eat('=')

        if symbol.type == 'Array':
            self.write('add')
            self.compile_expression() 

            # Store array on temp 0
            self.write('pop temp 0')
            self.write('pop pointer 1')
            self.write('push temp 0')
            self.write('pop that 0')
        else:
            self.compile_expression() 

        self.write('pop {} {}'.format(symbol.kind, symbol.index))
        self.eat(';')

    def compile_do(self):
        self.eat('do')
        self.compile_subroutine_call()
        self.eat(';')

        # Discard the result (void method)
        self.write('pop temp 0')


    def compile_statements(self):
        while self.current.value in ('if', 'while', 'let', 'do', 'return'):
            if self.current.value == 'if':
                self.if_index += 1
                self.compile_if()
            elif self.current.value == 'while':
                self.while_index += 1
                self.compile_while()
            elif self.current.value == 'let':
                self.compile_let()
            elif self.current.value == 'do':
                self.compile_do()
            elif self.current.value == 'return':
                self.compile_return()
                
    def compile_if(self):
        index = self.if_index
        self.eat('if')
        self.eat('(')
        self.compile_expression()
        self.write('not')
        self.eat(')')

        self.eat('{')
        self.write('if-goto {}.endIf.{}'.format(self.class_name, index))
        self.compile_statements()
        self.write('goto {}.endIf.{}'.format(self.class_name, index))
        self.eat('}')

        if self.current.value == 'else':
            self.eat('else')
            self.eat('{')
            self.write('label {}.else.{}'.format(self.class_name, index))
            self.compile_statements()
            self.eat('}')
        self.write('label {}.endIf.{}'.format(self.class_name, index))

    def compile_while(self):
        index = self.while_index
        self.eat('while')
        self.eat('(')
        self.write('label {}.while.{}'.format(self.class_name, index))
        self.compile_expression()
        self.write('not')
        self.write('if-goto {}.endWhile.{}'.format(self.class_name, index))
        self.eat(')')
        self.eat('{')
        self.compile_statements()
        self.write('goto {}.while.{}'.format(self.class_name, index))
        self.write('label {}.endWhile.{}'.format(self.class_name, index))
        self.eat('}')
        
    def compile_return(self):
        self.eat('return')

        # void method must push 0, caller will discard
        if self.return_type == 'void':
            self.write('push constant 0')

        if self.current.value != ';':
            self.compile_expression()

        self.write('return')
        self.eat(';')
        
    def compile_expression_list(self):
        nvars = 0
        while self.current.value != ')':
            nvars += 1
            self.compile_expression()
            if self.current.value == ',':
                self.eat(',')
        return nvars

    def compile_expression(self):
        self.compile_term()

        while self.current.value in self.OPERATORS:
            op = self.eat()
            self.compile_term()
            self.code_write(op)

    def compile_term(self):
        if self.next.value == '[':
            symbol = self.lookup(self.eat()) # varName
            self.write('push {} {}'.format(symbol.kind, symbol.index))
            self.eat('[')
            self.compile_expression()
            self.eat(']')

        # expression 
        elif self.current.value == '(':
            self.eat('(')
            self.compile_expression()
            self.eat(')')

        # unaryOp term
        elif self.current.value in ('-', '~'):
            op = self.eat()
            negate = None
            if op == '-':
                negate = 'neg'
            elif op == '~':
                negate = 'not'
         
            self.compile_term()
            self.write(negate)

        # Handle the following grammars:
        # - subroutineCall ( subroutineName '(' expressionList ')' 
        # - subroutineCall ( className | varNAme ) '.' subroutineName
        elif self.next.value in ('(', '.'):
            self.compile_subroutine_call()

        # varName
        else:
            var_name = self.eat() # varName
            self.code_write(var_name)

    def compile_subroutine_call(self):
        # subroutineName '(' expressionList ')'
        if self.next.value == '(': 
            obj = self.class_name
            sub_name = self.eat() # subroutineName
            self.eat('(')
            self.write('push pointer 0')
            nvars = self.compile_expression_list() + 1
            self.eat(')')

        # ( className | varName ) '.' subroutineName
        elif self.next.value == '.': 
            var_name = self.eat() # className/varName
            self.eat('.')
            sub_name = self.eat() # subroutineName
            self.eat('(')

            # Check if obj.foo() call
            if self.lookup(var_name):
                symbol = self.lookup(var_name)
                self.write('push {} {}'.format(symbol.kind, symbol.index))
                obj = symbol.type
                nvars = 1 # Include "this" in nvars

            # Class.foo() call
            else:
                nvars = 0 # Doesn't pass "this"
                obj = var_name 

            nvars += self.compile_expression_list()
            self.eat(')')

        self.write('call {}.{} {}'.format(obj, sub_name, nvars))

    def compile(self):
        self.compile_class()


def main():
    outdir = '.'
    path = Path(sys.argv[1])

    # If argument is a directory, get all *.jack files
    jackfiles = path.glob('**/*.jack') if path.is_dir() else [path]
    outdir = os.getcwd()

    if path.is_dir():
        # Append .vm to dirname and create it
        path = path.with_suffix('.vm')
        path.mkdir(exist_ok=True)
        outdir = path.name

    for fn in jackfiles:
        with open(str(fn), 'r') as f:
            outfn = str(Path(outdir, fn.with_suffix('.vm').name))
            print('Writing to {}'.format(outfn))
            with open(outfn, 'w') as vmfile:
                comp = CompilationEngine(Tokenizer(f.read()), out=vmfile)
                comp.compile()


if __name__ == '__main__':
    main()
