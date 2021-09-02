from Converter.Node import Node

class BinaryTree:
    def __init__(self, function):
        self.root = Node(function.start, function, None)
        return

    def addNode(self, function):
        root = self.root
        while True:
            if function.start <= root.key:
                if root.left is None:
                    root.left = Node(function.start, function, root)
                    break
                else:
                    root = root.left
            else:
                if root.right is None:
                    root.right = Node(function.start, function, root)
                    break
                else:
                    root = root.right

    def getParent(self, start, end, root=None):
        if root is None:
            root = self.root

        node = None
        while True:
            if start <= root.key:
                if root.left is None:
                    node = root
                    break
                root = root.left
            else:
                if root.right is None:
                    node = root
                    break
                root = root.right

        if end is None:
            return node.value

        while True:
            if node.parent is None:
                break

            if node.value.end is None:
                node = node.parent
                continue

            if node.value.start < start and node.value.end > end:
                break

            node = node.parent

        return node.value
