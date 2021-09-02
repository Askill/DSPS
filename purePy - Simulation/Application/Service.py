import copy
import numpy as np

class Service:
    def __init__(self, defaultServer, serviceID, scaleUpAt, scaleDownAt, scaleingMetric, scales, scale, scalingDelay):
        # TODO scaling, also get load average over x seconds for scaling needed
        self.scaleUpAt = scaleUpAt
        self.scaleDownAt = scaleDownAt
        self.scaleable = scales
        self.scaleingDown = False
        self.defaultServer = copy.deepcopy(defaultServer)
        self.scale = scale
        self.servers = [copy.deepcopy(defaultServer) for i in range(scale)]
        self.serviceId = str(serviceID)
        self.avgUtil = None
        self.scalingDelay = scalingDelay

    def calcAverageUtil(self):
        avgcpu, avgram, avgnet, avgio = 0, 0, 0, 0
        for server in self.servers:
            tcpu, tram, tnet, tio = server.getResUtil()
            avgcpu += tcpu
            avgram += tram
            avgnet += tnet
            avgio += tio

        self.avgUtil = np.divide([avgcpu, avgram, avgnet, avgio], len(self.servers))

    def getAvgUtil(self):
        self.calcAverageUtil()
        return self.avgUtil

    def push(self, function, t):
        # assign function to server with lowest util
        ets = set()
        returns = None
        scaleingDownBy = None
        if self.scaleingDown and len(self.servers) > 1:
            scaleingDownBy = -1

        serverAssigned = False

        for sc, server in enumerate(self.servers[:scaleingDownBy]):
            if server.fits(function):
                et, x = server.push(function, t)
                if x is not None:
                    raise Exception("Service wanted to push function to Server without capacity")
                ets.update(et)
                serverAssigned = True
                break

        if not serverAssigned:
            function.start = sorted(self.servers)[0].getFreeBy()
            returns = function

        self.calcAverageUtil()

        return list(ets), returns

    def pop(self, ts):
        done = []
        ets = []
        callbacks = []
        for server in self.servers:
            d, et, callbackstTemp = server.pop(ts)
            done += d
            ets += et
            callbacks += callbackstTemp
        # self.scaleDown()

        self.calcAverageUtil()
        return done, ets, callbacks

    def scaleServiceUp(self):
        self.servers.append(copy.deepcopy(self.defaultServer))

    def scaleDown(self):
        self.scaleingDown = True
        try:
            if len(self.servers) > 1 and len(self.servers[-1].functions) == 0:
                self.servers.pop(-1)
                self.scaleingDown = False
                return True
        except Exception as e:
            print(e)
            return False
