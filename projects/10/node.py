

class Node:
    def __init__(self, name, value=''):
        self.name = name or ''
        self.value = value or ''
        self.nodes = []

    def add(self, node):
        self.nodes.append(node)
        return self

    def __str__(self):
        return 'Node(name="{}", value="{}")'.format(self.name, self.value)
