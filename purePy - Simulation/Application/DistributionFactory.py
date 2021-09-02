import json
from jsonschema import validate
from Application.Function import *
from Application.Event import *
import copy


class DistributionFactory:

    def __init__(self):
        self.profilePath = None
        self.servicePath = None
        self.mapping = None
        self.profile = None

    @staticmethod
    def getContentFromFile(path):
        with open(path) as profileF:
            content = json.load(profileF)
        return content

    @staticmethod
    def validateContentvsSchema(profile, schema):
        try:
            validate(instance=profile, schema=schema)
            return True, None
        except Exception as e:
            return False, e

    def validateByPath(self, contentPath, schemaPath):
        content = self.getContentFromFile(contentPath)
        schema = self.getContentFromFile(schemaPath)
        return self.validateContentvsSchema(content, schema)

    @staticmethod
    def getFuncDist(times, functionDict):
        ''' deprecated
        times according to a distribution, Dictionary from which Function Objects can be generated'''
        funcDist = dict()
        for t in times:
            functionDict["start"] = t
            funcDist[t] = [Event(None, 1, Function(**functionDict))]
        return funcDist

    def resolvCallback(self, functionDict, functions):
        '''recursiv function to create a callback Function object from the callback ID of each function dict, 
        the resolved function is then added to the function dict and converted to a function object'''
        callbacks = []
        for i in range(len(functionDict["callbacks"])):
            if isinstance(functionDict["callbacks"][i], Function):
                return copy.deepcopy(Function(**functionDict))
            if functionDict["callbacks"][i] == "-1":
                return copy.deepcopy(Function(**functionDict))
            else:
                for callbackFunction in [x for x in functions if x["functionID"] == functionDict["callbacks"][i]]:
                    callbackFunction["scenarioID"] = functionDict["scenarioID"]
                    callbackFunction["interactionID"] = functionDict["interactionID"]
                    functionDict["callbacks"][i] = self.resolvCallback(callbackFunction, functions)
        function = copy.deepcopy(Function(**functionDict))
        return function

    def getFirstFunction(self, functions):
        # get first function in interaction
        # the first function in the list might be callback, so we have toi find the first function wihch is never called as a callback
        if len(functions) == 1:
            return functions[0]
        firstF = None
        for f in functions:
            if f["callbacks"] != ["-1"]:
                firstF = f
                break
        return firstF

    def getScenarioDist(self, inputs, profile, mapping):
        '''returns dictionary with timestamp as key and array of events as value
            {
            0:[event1, event2],
            1:[event4],
            ...
            }
        '''
        try:
            if not self.validateMapping(profile, mapping):
                raise Exception("Function not mapped to Service")

            funcDist = dict()

            functions = {}

            # for every distribution and every moment in the distribution all interactions of the scenario are created each intaeraction has a delay added,
            # so the actual start point is t_start = t_current + delay  for every interaction
            # this way parallel interactions are possible

            # inputs is an array of tupels [([moment1, moment2, moment3...], scenarioID), ...]
            for i in inputs:
                times, scenarioID = i
                scenario = [x for x in profile["scenarios"] if x["scenarioID"] == scenarioID][0]

                for t in times:
                    for interaction in scenario["interactions"]:

                        ts = t + interaction["delay"]
                        functionDict = copy.deepcopy(self.getFirstFunction(interaction["functions"]))
                        functionDict["start"] = ts
                        functionDict["scenarioID"] = scenarioID
                        functionDict["interactionID"] = interaction["interactionID"]

                        if functionDict["functionID"] in functions:
                            function = functions[functionDict["functionID"]]
                        else:
                            function = self.resolvCallback(functionDict, interaction["functions"])
                            functions[function.functionID] = function

                        function.start = ts
                        function.scheduled = ts

                        serviceID = mapping[function.functionID]
                        self.addEvent(funcDist, Event(ts, None, serviceID, copy.deepcopy(function)))


            # set runtime ID for every function
            runtimeID = 0
            for val in funcDist.values():
                for v in val:
                    v.function.runtimeID = runtimeID
                    runtimeID += 1
                    callbacks = [cb for cb in v.function.callbacks]

                    i = 0
                    while i < len(callbacks):
                        callback = callbacks[i]
                        i+=1
                        if callback != "-1":
                            callback.runtimeID = runtimeID
                            runtimeID += 1
                            for cb in callback.callbacks:
                                if not isinstance(cb, Function) and cb != "-1":
                                    raise Exception("Function was not resolved during callback resolving")
                                callbacks.append(cb)
                        if callback == "-1" and not callbacks:
                            break


            return funcDist

        except Exception as e:
            print(e)

    @staticmethod
    def addEvent(eventDict, event):
        ts = event.t
        if ts in eventDict:
            eventDict[ts].append(event)
        else:
            eventDict[ts] = [event]

    @staticmethod
    def validateMapping(profile, mapping):
        for scenario in profile["scenarios"]:
            for interaction in scenario["interactions"]:
                for function in interaction["functions"]:
                    if function["functionID"] not in mapping:
                        raise Exception(function["functionID"] + " not mapped to Service")
                        return False
        return True

    @staticmethod
    def getProfileAsDict(profileIn):
        '''Converts input JSON to a usable nested Dict()'''

        # Yeah... so this is ugly...
        # this function converts the inpuput nested object structure which has arrays of objects and converts them to dictionaries of objects with the objectID as the key
        # this was done to avoid redundancy in the input file, since this way a potential user doesn't have to make sure the key of the object and the ID match and can work with a simpler input

        profile = dict()
        profile["scenarios"] = {}

        for si, scenario in enumerate(profileIn["scenarios"]):
            profile["scenarios"][scenario["scenarioID"]] = copy.deepcopy(scenario)
            profile["scenarios"][scenario["scenarioID"]]["interactions"] = {}
            for ii, interaction in enumerate(profileIn["scenarios"][si]["interactions"]):
                profile["scenarios"][scenario["scenarioID"]]["interactions"][
                    interaction["interactionID"]] = copy.deepcopy(interaction)
                profile["scenarios"][scenario["scenarioID"]]["interactions"][interaction["interactionID"]][
                    "functions"] = {}
                for function in profileIn["scenarios"][si]["interactions"][ii]["functions"]:
                    profile["scenarios"][scenario["scenarioID"]]["interactions"][interaction["interactionID"]][
                        "functions"][function["functionID"]] = function

        return profile

    @staticmethod
    def createNetworkGraph(profile, mapping):
        # creates a JS definition for a graph of the application
        inclNodes = []
        nodes = []
        edges = []

        for scenario in profile["scenarios"]:
            for interaction in scenario["interactions"]:
                for function in interaction["functions"]:
                    serviceID = mapping[function["functionID"]]
                    if serviceID not in inclNodes:
                        inclNodes.append(serviceID)
                        nodes.append({"data": {"id": serviceID, "label": serviceID}})

                    if function["callbacks"][0] != "-1":
                        callbackServiceID = mapping[function["callbacks"][0].functionID]
                        if mapping[callbackServiceID] != serviceID:
                            if callbackServiceID not in inclNodes:
                                inclNodes.append(callbackServiceID)
                                nodes.append({"data": {"id": callbackServiceID, "label": callbackServiceID}})
                            edges.append({"data": {"source": serviceID, "target": callbackServiceID}})

        graph = nodes + edges
        return graph

    @staticmethod
    def genMapping(profile, mapping):
        # this function could be made redundant
        # as of right now all functions that are not on the default server
        # have a mapping for a simple lookup all function not in the mapping are mapped to the default server
        # default server needs to have the ID "default"
        tmpMapping = {}

        for scenario in profile["scenarios"]:
            for interaction in scenario["interactions"]:
                for function in interaction["functions"]:
                    className = function["functionID"].split(".")[0]
                    service = mapping[className] if className in mapping else "default"
                    service = mapping[function["functionID"]] if function["functionID"] in mapping else service

                    tmpMapping[function["functionID"]] = service

        return tmpMapping