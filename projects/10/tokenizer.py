"""
Jack language tokenizer
"""
from xml.dom.minidom import Document
from node import Node

import sys
import string

KEYWORDS = [
    'class', 
    'constructor', 
    'function',
    'method',
    'field', 
    'static', 
    'var', 
    'int', 
    'char', 
    'boolean', 
    'void',
    'true', 
    'false', 
    'null', 
    'this', 
    'let', 
    'do', 
    'if',
    'else', 
    'while', 
    'return'
]

SYMBOLS = '{}()\[\].,;+-*/&|<>=~'
MAXINTEGER = 32767
IDENTIFIERS = string.ascii_letters + string.digits + '_'


class Tokenizer:
    def __init__(self, data):
        self.pos = 0
        self.data = self.strip_comments(data)
        self.endpos = len(self.data) - 1
        self.line = 1
        self.current = None
        self.next = None

    def strip_comments(self, data):
        """
        Remove comments prior to parsing
        """
        out = ''
        end = len(data) - 1
        pos = 0
        
        while pos <= end:
            # Line comment
            if data[pos:].startswith('//'):
                while pos <= end and data[pos] != '\n':
                    pos += 1
                pos += 1
                #import pdb;pdb.set_trace()

            # Block comment
            elif data[pos:].startswith('/*'):
                while pos <= end and data[pos:pos + 2] != '*/':
                    pos += 1
                pos += 2
            else:
                char = data[pos]
                out += char
                pos += 1
        return out

    def get_token(self):
        token = None
        chunk = ''

        while self.pos <= self.endpos:
            if self.data[self.pos].isspace():
                self.pos += 1
                continue

            peek = self.data[self.pos+1:self.pos+2]
            char = self.data[self.pos]

            # Symbol handling
            if char in SYMBOLS:
                self.pos += 1
                return Node('symbol', char)
            
            # String literal handling
            elif char == '"':
                self.pos += 1
                while self.data[self.pos] != '"':
                    char += self.data[self.pos]
                    self.pos += 1
                char += self.data[self.pos]
                self.pos += 1
                return Node('stringConstant', char[1:-1])

            # Other token handling
            else:
                # Consume remaining characters
                chunk = ''
                while self.data[self.pos] in IDENTIFIERS:
                    chunk += self.data[self.pos]
                    self.pos += 1

                # Integer token handling
                if chunk.isdigit():
                    value = int(chunk)
                    if value >= 0 and value < MAXINTEGER:
                        return Node('integerConstant', chunk)

                # Keyword token handling
                elif chunk in KEYWORDS:
                    return Node('keyword', chunk)

                # Identifier token handling
                else:
                    if chunk[0].isdigit():
                        raise SyntaxError("Identifiers can't start with a number: {}".format(chunk))
                    for char in chunk:
                        if char not in IDENTIFIERS:
                            break
                    else:
                        return Node('identifier', chunk)
        
    def get_tokens(self):
        self.pos = 0
        while True:
            token = self.get_token()
            if not token:
                raise StopIteration
            yield token
            
    def to_xml(self):
        doc = Document()
        root = doc.createElement('tokens')
        doc.appendChild(root)
        
        for token in self.get_tokens():
            elem = doc.createElement(token.name)
            text = doc.createTextNode(' {} '.format(token.value))
            elem.appendChild(text)
            root.appendChild(elem)
        return root.toprettyxml(indent='')

if __name__ == '__main__':
    with open(sys.argv[1]) as f:
        data = f.read()
    tokenizer = Tokenizer(data)
    print(tokenizer.to_xml(), end='')
    
