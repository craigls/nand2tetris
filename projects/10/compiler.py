"""
Jack language compiler
"""

import sys
from node import Node
from tokenizer import Tokenizer
from xml.dom.minidom import Document
from pathlib import Path
import logging

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

class CompilationEngine:
    # Parsing logic:
    # - follow the right hand side of the rule and parse the input accordingly
    # - if the right-hand side specifies a non-terminal rule, call compileXXX
    # - Do this recursively

    # No corresponding compile method for:
    # - type
    # - className
    # - subroutineName
    # - variableName
    # - statement
    # - subroutineCall

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.current = None
        self.next = None
        self.current = self.tokenizer.get_token()
        self.next = self.tokenizer.get_token()

    def advance(self):
        self.current = self.next
        self.next = self.tokenizer.get_token()

    def eat(self, value=None):
        if value is not None and self.current.value != value:
            raise SyntaxError("{} != {} (next: {})".format(self.current.value, value, self.next.value))
        else:
            tmp = self.current
            self.advance()
            return tmp
            
    def compile_class(self):
        node = Node('class')
        node.add(self.eat('class'))
        node.add(self.eat())
        node.add(self.eat('{'))
        while self.current.value in ('static', 'field'):
            node.add(self.compile_class_var_dec())
        while self.current.value != '}':
            node.add(self.compile_subroutine_dec())
        node.add(self.eat('}'))
        return node

    def compile_class_var_dec(self):
        node = Node('classVarDec')
        node.add(self.eat()) # static | field
        while True:
            node.add(self.eat()) # int | char | boolean | className
            node.add(self.eat()) # varName
            if self.current.value != ',':
                break
        node.add(self.eat(';'))
        return node

    def compile_subroutine_dec(self):
        node = Node('subroutineDec')
        node.add(self.eat()) # constructor|function|method
        node.add(self.eat()) # void|type
        node.add(self.eat()) # subroutineName
        node.add(self.eat('('))
        node.add(self.compile_parameter_list())
        node.add(self.eat(')'))
        node.add(self.compile_subroutine_body())
        return node
        
    def compile_subroutine_body(self):
        node = Node('subroutineBody')
        node.add(self.eat('{'))
        while self.current.value == 'var':
            node.add(self.compile_var_dec())
        node.add(self.compile_statements())
        node.add(self.eat('}'))
        return node

    def compile_parameter_list(self):
        node = Node('parameterList')
        while self.current.value != ')':
            node.add(self.eat()) # type
            node.add(self.eat()) # varName
            if self.current.value == ',':
                node.add(self.eat(','))
        return node
            
    def compile_var_dec(self):
        node = Node('varDec')
        node.add(self.eat('var'))
        node.add(self.eat()) # type
        node.add(self.eat()) # varNAme
        while self.current.value != ';':
            node.add(self.eat(','))
            node.add(self.eat()) # varName
        node.add(self.eat(';'))
        return node

    def compile_let(self):
        node = Node('letStatement')
        node.add(self.eat('let'))
        node.add(self.eat()) # varName
        if self.current.value == '[': # check for varName[expression]
            node.add(self.eat('['))
            node.add(self.compile_expression())
            node.add(self.eat(']'))
        node.add(self.eat('='))
        node.add(self.compile_expression())
        node.add(self.eat(';'))
        return node

    def compile_do(self):
        node = Node('doStatement')
        node.add(self.eat('do'))
        node = self.compile_subroutine_call(node)
        node.add(self.eat(';'))
        return node

    def compile_statements(self):
        node = Node('statements')
        while self.current.value in ('if', 'while', 'let', 'do', 'return'):
            if self.current.value == 'if':
                node.add(self.compile_if())
            elif self.current.value == 'while':
                node.add(self.compile_while())
            elif self.current.value == 'let':
                node.add(self.compile_let())
            elif self.current.value == 'do':
                node.add(self.compile_do())
            elif self.current.value == 'return':
                node.add(self.compile_return())
        return node
                
    def compile_if(self):
        node = Node('ifStatement')
        node.add(self.eat('if'))
        node.add(self.eat('('))
        node.add(self.compile_expression())
        node.add(self.eat(')'))
        node.add(self.eat('{'))
        node.add(self.compile_statements())
        node.add(self.eat('}'))
        if self.current.value == 'else':
            node.add(self.eat('else'))
            node.add(self.eat('{'))
            node.add(self.compile_statements())
            node.add(self.eat('}'))
        return node 

    def compile_while(self):
        node = Node('whileStatement')
        node.add(self.eat('while'))
        node.add(self.eat('('))
        node.add(self.compile_expression())
        node.add(self.eat(')'))
        node.add(self.eat('{'))
        node.add(self.compile_statements())
        node.add(self.eat('}'))
        return node
        
    def compile_return(self):
        node = Node('returnStatement')
        node.add(self.eat('return'))
        if self.current.value != ';':
            node.add(self.compile_expression())
        node.add(self.eat(';'))
        return node
        
    def compile_expression_list(self):
        node = Node('expressionList')
        while self.current.value != ')':
            node.add(self.compile_expression())
            if self.current.value == ',':
                node.add(self.eat(','))
        return node

    def compile_expression(self):
        node = Node('expression')
        node.add(self.compile_term())
        while self.current.value in ('+', '-', '*', '/', '&', '|', '<', '>', '='):
            node.add(self.eat())
            node.add(self.compile_term())
        return node
    
    def compile_term(self):
        #'Single look ahead required. Must be one of "[", "(" or "."'
        node = Node('term')

        # varName[expression]
        if self.next.value == '[':
            node.add(self.eat()) # varName
            node.add(self.eat('['))
            node.add(self.compile_expression())
            node.add(self.eat(']'))
            return node

        # expression 
        elif self.current.value == '(':
            node.add(self.eat('('))
            node.add(self.compile_expression())
            node.add(self.eat(')'))
            return node

        # Handle the following grammars:
        # - subroutineCall ( subroutineName '(' expressionList ')' 
        # - subroutineCall ( className | varNAme ) '.' subroutineName
        elif self.next.value in ('(', '.'):
            return self.compile_subroutine_call(node)

        # unaryOp term
        elif self.current.value in ('-', '~'):
            node.add(self.eat())
            node.add(self.compile_term())
            return node

        # varName
        else:
            node.add(self.eat())
            return node

    def compile_subroutine_call(self, node):
        # subroutineCall ( subroutineName '(' expressionList ')'
        if self.next.value == '(': 
            node.add(self.eat()) # subroutineName
            node.add(self.eat('('))
            node.add(self.compile_expression_list())
            node.add(self.eat(')'))
            return node

        # subroutineCall ( className | varName ) '.' subroutineName
        elif self.next.value == '.': 
            node.add(self.eat()) # className/varName
            node.add(self.eat('.'))
            node.add(self.eat()) # subroutineName
            node.add(self.eat('('))
            node.add(self.compile_expression_list())
            node.add(self.eat(')'))
            return node

        
    def get_xml(self, root):
        doc = Document()
        doc.appendChild(self.to_xml(doc, doc, root))
        return doc.toprettyxml(indent='  ')

    def to_xml(self, doc, parent, node, indent=0):
        elem = doc.createElement(node.name)
        if node.value:
            text = doc.createTextNode(' {} '.format(node.value))
            elem.appendChild(text)
        
        for node in node.nodes:
            elem.appendChild(self.to_xml(doc, elem, node))
            
        return elem

    def compile(self):
        root = self.compile_class()
        return self.get_xml(root)


def main():
    path = Path(sys.argv[1])

    # If argument is a directory, get all *.jack files
    jackfiles = path.glob('**/*.jack') if path.is_dir() else [path]
    for fn in jackfiles:
        with open(str(fn), 'r') as f:
            comp = CompilationEngine(Tokenizer(f.read()))
            xml = comp.compile()
            outfn = fn.with_suffix('.xml').name
            print('Writing to {}'.format(outfn))
            with open(outfn, 'w') as out:
                out.write(xml)


if __name__ == '__main__':
    main()

