from numpy import rad2deg


class Function:
    def __init__(self, parent, id, start, end=None):
        self.parent = parent
        self.id = id
        self.start = start
        self.end = end
        self.children = []
        self.duration = None
        self.cpu = None
        self.ram = None
        self.net = None
        self.io = None
        self.isAsync = False

    def addChild(self, child):
        self.children.append(child)

    def __eq__(self, other):
        if other == "-1":
            return False
        return self.id == other.id and self.start == other.start and self.end == other.end 

    def overlaps(self, f):
        if self.end < f.start or f.end < self.start:
            return False

        r1 = self.start <= f.start and self.end > f.start 
        r3 = self.start <= f.start and self.end < f.start 

        r2 = f.start <= self.start and f.end > self.start
        r4 = f.start <= self.start and f.end < self.start 

        return r1 or r2 or r3 or r4 

    def getOverlap(self, f):
        if self.start < f.start:
            if self.end < f.start:
                return (None, None)
            else:
                return (f.start, self.end)
        else:
            if f.end < self.start:
                return (None, None)
            else:
                return (f.end, self.start)

    def setRemoteValues(self):
        self.cpu = 1
        self.ram = 1
        self.io = 0
        self.net = 0
        self.duration = self.end - self.start
        
            