
from Converter.Function import Function
from Converter.BinaryTree import BinaryTree
import time
import pandas as pd

def validateTree(root):
    '''mostly left over from dev, checks if chidl functions start alter and end earlier than parent'''
    dur = 0
    for child in root.children:
        if child.end is not None:
            dur += child.end - child.start
        if root.end is not None and child.end is not None:
            if(child.start < root.start or child.end > root.end):
                print(child.start - root.start,  root.end - child.end)
                raise Exception("Child starts too soon or ends too late")
        validateTree(child)

    #if root.children:
    #    if root.end is not None and dur != root.end - root.start:
    #        difInS = (root.end - root.start - dur) / 1E9
    #        if difInS > 0.01:
    #            print(pd.to_datetime(difInS * 1E9, unit='ns'))
    #            print(root.id,  "\n", pd.to_datetime(root.start, unit='ns'), "\n", pd.to_datetime(root.end, unit='ns'))
    #            print("")


def indexOfEnd(name, lst):
    return indexOf(name, lst, "end")


def indexOf(name, lst, key):
    tmp = [i for i, x in enumerate(lst) if x[0] == key and x[1] == name]
    if len(tmp) == 0:
        return len(lst) - 1
    return tmp[0]


def indexOfNext(lst, key):
    tmp = [i for i, x in enumerate(lst) if x[0] == key]
    if len(tmp) == 0:
        return len(lst)
    return tmp[0]


def indexOfNextEnd(lst, key, name):
    tmp = [i for i, x in enumerate(lst) if x[0] == key and x[1] == name]
    if len(tmp) == 0:
        return None
    return tmp[0]


def endOfFunction(name, lst, denom="end"):
    tmp = [x[2] for i, x in enumerate(lst) if x[0] == denom and x[1] == name]
    if len(tmp) == 0:
        return None
    return tmp[0]


def getLines(path):
    lines = []
    with open(path, "r") as f:
        root = Function(None, None, None)
        for line in f.readlines():
            try:
                parts = line.split(" ")
                parts = [part.strip() for part in parts]
                parts[2] = int(parts[2])
                lines.append(parts)
            except Exception as e:
                print(e)
                exit(1)

    lines.sort(key=lambda x: x[2])
    return lines


def getEndofExpandedRoot(identifier, lines):
    """return index and ts of end of function, with parallel functions it groups them together returns last end"""
    counter = 1
    dels = []
    for i, line in enumerate(lines):
        if counter == 0:
            return i, lines[i-1][2]
        if line[0] == "startRoot" and line[1] == identifier:
            counter += 1
            dels.append(i)
        if line[0] == "endRoot" and line[1] == identifier:
            counter -= 1
            dels.append(i)
    
    for i, j in enumerate(dels[:-1]):
        del lines[j - i]

    return len(lines)-1, lines[-1][2]

def convert(path):
    start = time.time()
    lines = getLines(path)

    maxTs = lines[-1][2]
    root = Function(None, "root", 0)
    bt = BinaryTree(root)
    lenLines = len(lines)
    i = indexOfNext(lines, "startRoot")

    # see thesis chapter profiler for the biog picture
    while i < lenLines:
        if i % 500 == 0:
            print("                                           ", end="\r")
            print(f"{i/len(lines) * 100}% ", i, end="\r")
            
        line = lines[i]

        keyword = line[0]
        identifier = line[1]
        ts = line[2]

        if keyword == "end":
            i += 1
            continue

        if keyword == "endRoot":
            i += indexOfNext(lines[i+1:], "startRoot") + 1
            continue

        end = None
        if keyword == "startRoot":
            # start new binary tree for new interaction, still uses old root element for easy travering
            bt = BinaryTree(root)
            _, _ = getEndofExpandedRoot(identifier, lines[i+1:])
            end = maxTs
        else:
            end = endOfFunction(identifier, lines[i:])

        parent = bt.getParent(ts, end)

        func = Function(parent, identifier, ts, end)
        parent.addChild(func)

        bt.addNode(func)

        endIndex = indexOf(func.id, lines, "end")
        if endIndex is not None:
            del lines[endIndex]

        i += 1
        lenLines = len(lines)

    while root.parent is not None:
        root = root.parent

    print("Built Calltree in ", time.time() - start, " s \n")

    return root


def truncateTree(root, limit=100000000, steps=5):
    '''traverse tree to given length, if node has length < limit the children are not logged'''
    if steps == 0:
        root.children = []
        return

    if root.end is not None:
        root.duration = (root.end - root.start)

    if root.duration is not None and root.duration < limit:
        root.children = []
        return

    for child in root.children:
        truncateTree(child, limit, steps - 1)



def getEndTimes(lines):
    ends = {}
    for i, line in enumerate(lines):
        if line[0] == "startRoot":
            endIndex = i + indexOf(line[1], lines[i:], "endRoot")
            end = lines[endIndex]
            ends[line[2]] = end[2]

    return ends


def reduceRoots(root, path):
    ''' trims children of root functions to logged length '''
    lines = getLines(path)
    ends = getEndTimes(lines)
    i = 0
    for child in sorted(root.children, key=lambda x: x.start):
        end = ends[child.start]
        # function start and end has only ms acc
        # 1 ms is added to ensure all functions are caught
        child.end = end + 1000000

        deletes = []
        for j, cchild in enumerate(child.children):
            if cchild.end is not None and cchild.end > child.end:
                deletes.append(j)

        for x, j in enumerate(deletes):
            del child.children[j-x]
        i += 1

def overlaps(start, end, fstart, fend):
    if end < fstart or fend < start:
        return False

    r1 = start <= fstart and end >= fstart 
    r3 = start <= fstart and end <= fstart 


    r2 = fstart <= start and fend >= start
    r4 = fstart <= start and fend <= start 


    return r1 or r2 or r3 or r4 

def mergeFunctions(f1, f2):
    for f in f2.children:
        f1.addChild(f)
    return f1

def mergeAsyncInteractions(root):
    toMerge = {}
    # find overlapping interaction ids
    # group the ids in arrays
    for i in range(len(root.children)):
        indexes = set()
        for j in range(i+1, len(root.children)):
            child1 = root.children[i]
            child2 = root.children[j]

            if child1.overlaps(child2):
                indexes.add(i)
                indexes.add(j)

        if indexes:
            toMerge[i] = list(indexes)

    clusters = []
    for key, values in toMerge.items():
        cluster = list(values)
        for value in values:
            if value in toMerge:
                cluster += toMerge[value]

        clusters.append(set(cluster))
    

    # if there are interactions to merge:
    clusters = list(clusters)
    if clusters:
        merged = [list(clusters[0])]
        for c in clusters[1:]:
            if c.issubset(merged[-1]):
                continue
            else:
                merged.append(list(c))

        # merge fountions in one group to single function
        functionsToAdd = []
        for indexes in merged:
            for i in indexes[1:]:
                mergeFunctions(root.children[indexes[0]], root.children[i])
            functionsToAdd.append(root.children[indexes[0]])

        # delete all functions which were merged
        for i, j in enumerate([x for y in merged for x in y]):
            del root.children[j-i]

        # add merged functions
        for f in functionsToAdd:
            if f.children:
                
                fstart = min(f.children, key=lambda x: x.start).start
                maxF = max(f.children, key=lambda x: x.end)
                fend = maxF.end

                if fstart < f.start:
                    f.start = fstart
                if fend > f.end:
                    f.end = fend
            root.addChild(f)



