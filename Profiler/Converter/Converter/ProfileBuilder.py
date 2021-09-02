import pandas as pd
from Converter.Function import Function
import json
import copy
import math 

def addUtilFunction(root, util):
    start = root.start
    end = root.end
    if end is not None:
        duration = (end - start)
        if duration < 10*1E6:
            start = start - 10*1E6

        duration = (end - start)

        start = pd.to_datetime(start, unit='ns')
        end = pd.to_datetime(end, unit='ns')

        cpu1 = util.loc[start:end]
        cpu = cpu1["cpu"].mean()
        ram = util.loc[start:end]["mem"].mean()

        if math.isnan(cpu):
            # raise Exception("Function " + root.id + " was too short to attribute any utilization to.")
            cpu = 0
            ram = 0
            io = 0
        else:
            #tmp = util.loc[start:end]["io"]
            #if not tmp.empty:
                #io = tmp[-1] - tmp[0]
            io = 0
    else:
        duration = 0
        cpu = 0
        ram = 0
        io = 0

    root.duration = float(duration)
    root.cpu = float(cpu)
    root.ram = float(ram)
    root.io = float(io)
    root.net = 0

def getFunctionUtilFactor(function, functions):
    if not function.isAsync:
        return 1

    relevantFuncs = [function]
    for f in functions:
        if f == function:
            continue
        if not f.isAsync:
            continue
        if not function.overlaps(f):
            continue
        
        relevantFuncs.append(f)

    relevantFuncs.sort(key=lambda x: x.start)

    vals = {}

    for f in relevantFuncs:
        if f.start < function.start:
            vals[function.start] = "inc"
        else:
            vals[f.start] = "inc"

        if f.end > function.end:
            vals[function.end] = "dec"
        else:
            vals[f.end] = "dec"
    
    val2 = {}
    val2[function.start] = 0

    counter = 0
    for key in sorted(vals.keys()):
        val = vals[key]
        if val == "inc":
            counter += 1
        if val == "dec":
            counter -= 1
        val2[key] = counter
    val2[function.end] = 0

    keys = sorted(val2.keys())
    functionLength = function.end - function.start

    factor = 0

    for i in range(len(keys)-1):
        duration = keys[i+1] - keys[i]
        count = val2[keys[i]]
        factor += (duration / functionLength) * ( 1 / count )
        
    return factor


def addUtil(functions, utilLogPath):

    data = pd.read_csv(utilLogPath, delimiter=",")
    data["time"] = pd.to_datetime(data["time"], unit='s')

    data.set_index("time", inplace=True)
    data = data.resample(rule="1s").mean().resample(rule="10ms").mean().interpolate()
    data["mem"] = data["mem"] - data["mem"][0]
    data["mem"] = data["mem"].clip(lower=0)
    data["cpu"] = data["cpu"].clip(lower=0)

    for child in functions:
        addUtilFunction(child, data)

    return functions


def markAsyncFunction(children):
    children.sort(key=lambda x: x.start)
    for i in range(len(children)):
        child1 = children[i]
        for j in range(i+1 , len(children)):
            child2 = children[j]
            if child1.end is None or child2.end is None:
                continue
            if child1.overlaps(child2):
                child1.isAsync = True
                child2.isAsync = True
    return children


def markAsync(root):
    markAsyncFunction(root.children)
    for child in root.children:
        markAsync(child)


def flattenTree(root, outL):
    if root.children:
        for child in sorted(root.children, key=lambda x: x.start):
            flattenTree(child, outL)
    else:
        outL.append(root)


def getFunctionName(child):
    return child.id + "_" + str(child.start)


def getFunctionDict(child, callbacks, delay):
    return {
        "functionID": getFunctionName(child),
        "cpu": child.cpu,
        "cpu_time": child.duration,
        "ram": child.ram,
        "io": child.io,
        "net": child.net,
        "delay": 0,
        "callbacks": [getFunctionName(callback) if callback != "-1" else "-1" for callback in callbacks]
    }

def getParallelFunctions(function, functions):
    par = []
    dels = []
    for i, f in enumerate(functions):
        if function.overlaps(f):
            par.append(f)
            dels.append(i)

    for i, j in enumerate(dels):
        del functions[j-i]

    return par, functions


def getFunctionsArray(flattened):
    # convert tree structure to linear structure
    #       x
    #      / \
    #     x   x     x - x - x  
    #    /            \ x
    #   x
    # only the longest of n parallel functions may have a callback
    
    lastEnd = flattened[0].start
    syncJoin = False
    i = 0
    functions = []
    while i < len(flattened) - 1:
        child = flattened[i]
        callback1 = flattened[i+1]
        callbacks = []

        fDelay = child.start - lastEnd

        # TODO: multiple async functions after another have negative delay, this is a work around
        if fDelay < 0:
            fDelay = 0
            print("function delay was negativ, function: ", getFunctionName(child), "\n function delay was set to 0")

        # if this is the first sync function after asyncs, add current function to the callbacks
        # -2 because the callbacks are added before the child is and we wqant to add this to the callbacks of the last chiuld not the parent
        if syncJoin:
            syncJoin = False
            functions[-2]["callbacks"] = [getFunctionName(child)]

        if callback1.isAsync:
            syncJoin = True
            parallelFunctions, flattened = getParallelFunctions(callback1, flattened)
            
            # add async functions to callback to last sync function and add functions themselves to the functions array
            for y in parallelFunctions:
                if y == child:
                    continue
                callbacks.append(y)
                functions.append(getFunctionDict(y, ["-1"], y.start - lastEnd))
            lastEnd = max(parallelFunctions, key=lambda x: x.end).end
            i+=1
            
        else:
            lastEnd = child.end
            callbacks.append(callback1)

        functionObj = getFunctionDict(child, callbacks, fDelay)
        functions.append(functionObj)

        i += 1

    if flattened:
        if syncJoin:
            functions[-2]["callbacks"] = ["-1"]
        else:
            functionObj = getFunctionDict(flattened[-1], ["-1"], 0)
            functions.append(functionObj)

    return functions


def getNet(netLogPath):
    lines = []
    with open(netLogPath, "r") as f:
        for line in f.readlines():
            try:
                parts = line.split(",")
                parts = [part.strip() for part in parts]
                lines.append(parts)
            except Exception as e:
                print(e)
                exit(1)
    lines = lines[1:]
    lines.sort(key=lambda x: x[0])

    return lines


def addNet(functions, netLogPath):
    '''insert network connections into functions'''
    lines = getNet(netLogPath)
    i = 0
    for line in lines:
        start = float(line[0]) 
        end = float(line[2]) 
        host = line[1]
        while i < len(functions):
            f1 = functions[i]
            f2 = copy.deepcopy(functions[i])
            f1.id = f1.id + "_1"
            f2.id = f2.id + "_2"

            if f1.start <= start and f1.end >= end:
                remoteF = Function(f1, host, start, end=end)
                remoteF.setRemoteValues()
                remoteF.children = [f2]

                f1.end = remoteF.start
                f2.start = remoteF.end
                f1.duration = f1.end - f1.start
                f2.duration = f2.end - f2.start
                
                f2.parent = remoteF

                functions.append(remoteF)
                functions.append(f2)
                break

            i += 1

    return functions

def makeInteraction(root, delay, utilLogPath, netLogPath):
    interaction = {"name": root.id, "interactionID": root.id,
                   "delay": delay, "functions": []}

    flattened = []
    flattenTree(root, flattened)
    flattened.sort(key=lambda x: x.end)
    functions = markAsyncFunction(flattened)
    functions = fillGaps(root, functions, True)
    functions = addUtil(functions, utilLogPath)
    functions = addNet(functions, netLogPath)
    functions = getFunctionsArray(functions)

    if not functions:
        return

    interaction["functions"] = functions

    return interaction


def createProfile(root, name, utilLogPath, netLogPath):
    profile = {
        "$id": "/Matz/Patrice/Master-Thesis/Profile.schema.json",
        "name": name,
        "scenarios": []
    }

    # sort interaction nodes by start
    root.children.sort(key=lambda x: x.start)
    interactions = []
    child = root.children[0]
    previousStart = child.start
    for i, child in enumerate(root.children):
        
        # delay is calculated to start of scenario not inbetween interactions, this way async interactions are possible
        delay =  child.start - previousStart 
        interaction = makeInteraction(child, delay, utilLogPath, netLogPath)
        if interaction is not None:
            interaction["interactionID"] = str(i) + " " + interaction["interactionID"]
            interactions.append(interaction)
    

    scenario = {
        "scenarioID": 1,
        "interactions": interactions
    }

    profile["scenarios"] = [scenario]
    return profile


def findGaps(child, children, allowedDiff):
    if not child.children:
        return []
    gaps = []
    children.sort(key=lambda x: x.start)
    firstChild = min(children, key=lambda x: x.start)
    # for gap at the very start
    if firstChild.start - child.start > allowedDiff:
        gaps.append([child.start, firstChild.start])


    # gap at the end
    lastChild = max(children, key=lambda x: x.end)
    if lastChild.end is not None:
       if child.end - lastChild.end > allowedDiff:
           gaps.append([lastChild.end, child.end])

    return gaps


def fillGaps(root, children, validate=False):
    if not children:
        return [root]
    # if difference greater than 0.001 secons / 1 mill sec
    allowedDiff = 0.001 * 1E9

    gaps = findGaps(root, children, allowedDiff)
    for start, end in gaps:
        children.append(
            Function(root, root.id + "_fill_" + str(start), start, end))

    children.sort(key=lambda x: x.end)

    if validate:
        for i in range(len(children)-1):
            if "_fill_" in children[i].id and "_fill_" in children[i+1].id:
                print(gaps)
                raise Exception("Gaps was filled multiple times " + root.id)

        gaps = findGaps(root, children, allowedDiff)
        if len(gaps) != 0:
            print(gaps)
            raise Exception(
                "Could not fill all Gaps in function: " + root.id)

    return sorted(children, key=lambda x: x.end)


def genMapping(profile, netLogPath):
    tmpMapping = {}
    net = getNet(netLogPath)
    net = [x[1] for x in net]
    for scenario in profile["scenarios"]:
        for interaction in scenario["interactions"]:
            for function in interaction["functions"]:
                name = function["functionID"].split("_")[0]
                if name in net:
                    tmpMapping[function["functionID"]] = name    
    return tmpMapping


def getServiceDict(name):
    return  {
            "scaleUpAt": 0.8,
            "scaleDownAt": 0.3,
            "scaleingMetric": "CPU",
            "serviceID": name,
            "scales": False,
            "scale": 1,
            "scalingDelay": 0,
            "defaultServer": {
                "maxCPU": 100,
                "maxRAM": 100,
                "maxIO": 100,
                "maxNET": 100
            }
        }

def genServices(netLogPath):
    services = []

    hosts = set()
    with open(netLogPath, "r") as f:
        line = f.readlines()
        for line in f.readlines():
            
            parts = line.split(" ")
            hosts.add(parts[1])
    
    hosts = list(hosts)
    hosts.append("default")

    servicesList = []
    for host in hosts[::-1]:
        servicesList.append(getServiceDict(host))

    services = {
    "id": "/Matz/Patrice/Master-Thesis/Service.schema.json",
    "name": "Service Definition for Example Application",
    "services": servicesList
    }
    
    return services