import os
import time
from pprint import pprint

import matplotlib.pyplot as plt
from Application.Server import *
from Application.Service import *
from Application.DistributionFactory import *
from queue import Queue
import pandas as pd
import numpy as np


class Simulation:

    def __init__(self, schema, serviceSchema):
        self.schema = schema
        self.serviceSchema = serviceSchema
        self.observationQueue = Queue()
        self.dfDicts = {}

    def main(self, profile, mapping, serviceDict, distRequest):

        distributionFactory = DistributionFactory()

        # https://www.jsonschemavalidator.net/
        suc, e = distributionFactory.validateContentvsSchema(profile, self.schema)
        if not suc:
            raise Exception(e)
        suc, e = distributionFactory.validateContentvsSchema(serviceDict, self.serviceSchema)
        if not suc:
            raise Exception(e)

        self.profile = distributionFactory.getProfileAsDict(profile)
        print("Generating input distribution")
        eventSeries = distributionFactory.getScenarioDist(distRequest, profile, mapping)

        services = self.getServices(serviceDict)
        print("starting simulation")
        self.simLoop(eventSeries, services, mapping)

    def saveOberservations(self, dfs):
        observationDict = self.observationQueueToDict()
        self.observations = observationDict
        self.saveSimResult(observationDict, savePath="../SimResults.json")
        return observationDict

        
    def addEvent(self, eventDict, event, ts):
        if ts in eventDict:
            eventDict[ts].append(event)
        else:
            eventDict[ts] = [event]

    def simLoop(self, eventSeries, services, mapping):

        done = 0
        t = 0
        t3 = time.time_ns()
        times = set()
        lastT = 0
        doneInteractions = dict()
        awaitedFunctions = dict()

        ids = []

        # primary loop see thesis chapter "simulation engine"
        while len(eventSeries.keys()) > 0:

            # get next timestamp and events
            t = min(eventSeries.keys())
            events = eventSeries.pop(t)
            if t < lastT:
                lastT = t
                #print(len(events), events[0])
                self.observationQueue.put(("sim_events", t, "error", len(events)))
                continue
            lastT = t

            # print progression
            if done % 1000 == 0:
                print("simulation time: " + str(t /1E9), end="\r")
            self.observationQueue.put(("sim_events", t, "total", len(events)))

            # secondary loop see thesis chapter "simulation engine"
            # iterate over all events
            while events:
                events = sorted(events)
                event = events.pop()

                # monitor for simulation internal error
                if event.type is None:
                    if event.function.runtimeID in ids and event.function.start == event.function.scheduled :
                        raise Exception(str(event.function.runtimeID) + " Runtime ID was not unique")
                    else:
                        ids.append(event.function.runtimeID)

                # monitor for simulation internal error
                if t != event.t or (event.function is not None and t != event.function.start):
                    self.observationQueue.put(("sim_events", t, "t_not_start", 1))
                    print(event.function.functionID, "\n", t, "\n", event.t, "\n", event.function.start, "\n")

                    event.function.start = t


                # retrieve completed functions and callbacks
                d, ets, callbacks = services[event.serviceId].pop(t)
                done += len(d)

                # track completed functions for visualization
                for doneFunction in d:
                    self.trackPop(doneInteractions, awaitedFunctions, self.observationQueue, doneFunction, t)

                # create events for callbacks
                for callback in callbacks:
                    callback.setCallbackStart(t)

                    serviceID = mapping[callback.functionID]
                    self.addEvent(eventSeries, Event(callback.start, None, serviceID, callback), callback.start)


                if event.type == "recalc":
                    # track number of recalc events
                    self.observationQueue.put(("sim_events", t, "recalculations", 1))
                else:
                    # push function if function is in event
                    # event has function if tape is None
                    # if service is busy function is returned to be referred
                    ets, function = services[event.serviceId].push(event.function, t)

                    # function is not None if the function was deferred, because the service didn't have ressources
                    if function is not None:
                        function = copy.deepcopy(function)
                        serviceID = mapping[function.functionID]
                        self.addEvent(eventSeries, Event(function.start, None, serviceID, function), function.start)
                        self.observationQueue.put(("sim_events", t, "rescheduled", 1))
                    else:
                        self.trackPush(awaitedFunctions, event.function)

                for et in ets:
                    if et not in eventSeries.keys():
                        # recalculation events occour when a function should be finished and a server should have free ressources
                        # that function might have already finished and there might be multiple recalc events for a single function
                        self.addEvent(eventSeries, Event(et, "recalc", services[event.serviceId].serviceId, None), et)
                        times.add(et)
            # monitor services for visualization
            self.monitorServices(self.observationQueue, services, t)

            # track completed interactions
            for key, value in doneInteractions.items():
                self.observationQueue.put(("dones", t, key, value))

        #self.observationQueue.put(("dones", t, "total", 0))
        self.observationQueue.put("done")
        print("time: ", t/ 1E9, "completed functions: ", done, " in ", (time.time_ns() - t3) / 1E9, "s")

    def saveSimResult(self, observationDict, savePath="SimResults.json"):
        savePath = os.path.join(os.path.dirname(__file__), savePath)
        print(savePath)
        with open(savePath, 'w') as fp:
            json.dump(observationDict, fp)

    def getServices(self, serviceDict):
        '''create service objects from service definition'''
        services = dict()

        for service in serviceDict["services"]:
            tmpService = copy.deepcopy(service)
            tmpService["defaultServer"] = copy.deepcopy(Server(**service["defaultServer"]))
            services[service["serviceID"]] = Service(**tmpService)

        return services

    def observationQueueToDict(self, chunks=None):
        columnNames = {
            "sim_events": ["active"],
            "dones": ["completed"],
            "response_time": ["delay", "response time"],
            "service_util": ["CPU", "RAM", "NET", "IO"],
        }
        i = 0
        while True:
            if chunks is not None and i >= chunks:
                break

            content = self.observationQueue.get()
            if content == "done":
                break

            Simulation.transfromQueue(columnNames, content, self.dfDicts)

            i += 1

        return self.dfDicts

    @staticmethod
    def transfromQueue(columnNames, content, dfDicts):
        '''transform Queue into Dicts'''
        key, t, identifier, value = content
        # this is bad
        # I am not sure why it happens
        if isinstance(value, np.ndarray):
            value = value
        else:
            if not isinstance(value, list):
                value = [value]
            else:
                value = value
        if key not in dfDicts:
            dfDicts[key] = {"t": [], "identifier": []}

        dfDicts[key]["t"].append(t)
        dfDicts[key]["identifier"].append(identifier)

        for i, val in enumerate(value):
            if i >= len(columnNames[key]):
                newKey = "value_" + str(i)
            else:
                newKey = columnNames[key][i]
            if newKey not in dfDicts[key]:
                dfDicts[key][newKey] = []
            dfDicts[key][newKey].append(val)


    def plotResults(self, dfDicts):

        dfs = dict()
        for value, df in dfDicts.items():
            dfs[value] = pd.DataFrame.from_dict(df)
            dfs[value]["t"] = pd.to_datetime(dfs[value]["t"], unit='ns')
            dfs[value].set_index("t", inplace=True)

        for key, df in dfs.items():
            for i in df.identifier.unique():
                if key == "sim_events":
                    df.loc[df["identifier"] == i].resample(rule="1s").sum().interpolate().plot(kind='line', title=f"{key} {i}")
                else:
                    df.loc[df["identifier"] == i].resample(rule="1s").mean().interpolate().plot(kind='line', title=f"{key} {i}")

        plt.show()



    def monitorServices(self, observationQueue, services, t):
        avgUtil = [0, 0, 0, 0]
        for service in services.values():
            observationQueue.put(("service_util", t, "service " + service.serviceId, service.getAvgUtil()))
            avgUtil = np.add(avgUtil, service.getAvgUtil())

        avgUtil /= len(services)
        observationQueue.put(("service_util", t, "average", avgUtil))

    def trackPush(self, awaitedFunctions, function):
        '''if function was first in interaction put the last functionID in the awaited functions, used to track interaction delay and time'''
        interactions = self.profile["scenarios"][function.scenarioID]["interactions"]

        # get first function in interaction
        firstF = None
        interactionFunctions = list(interactions[function.interactionID]["functions"].values())
        if len(interactionFunctions) == 1:
            firstF = interactionFunctions[0]["functionID"]

        for f in interactionFunctions:
            if f["callbacks"] != ["-1"]:
                firstF = f["functionID"]
                break

        if function.functionID == firstF:
            callbacks = function.callbacks
            if callbacks == ["-1"]:
                awaitedFunctions[function.runtimeID] = [function.start, function.scheduled]
                return
            cb2 = None
            while True:
                if callbacks == ["-1"]:
                    break
                for callback in callbacks:
                    if callback != "-1":
                        cb2 = callback
                        callbacks = callback.callbacks
                        continue

            awaitedRunTimeID = cb2.runtimeID
            awaitedFunctions[awaitedRunTimeID] = [function.start, function.scheduled]

    def trackPop(self, doneInteractions, awaitedFunctions, observationQueue, function, t):
        '''remove function from awaited functions if interaction is completed'''
        key = f"scenario {str(function.scenarioID)} interaction {str(function.interactionID)}"

        if function.runtimeID in awaitedFunctions:
            if key not in doneInteractions:
                doneInteractions[key] = 0
            doneInteractions[key] += 1

            fStart, fScheduled = awaitedFunctions.pop(function.runtimeID)
            tmp = [(fStart - fScheduled) / 1E9, (function.end - fScheduled)/ 1E9]
            observationQueue.put(("response_time", t, key, tmp))
