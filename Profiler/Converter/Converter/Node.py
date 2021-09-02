class Node:
    def __init__(self, key, value, parent):
        self.value = value
        self.key = key
        self.left = None
        self.right = None
        self.parent = parent