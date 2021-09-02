class Function:
    def __init__(self, cpu, ram, cpu_time, io, net, start=None, callbacks=None, functionID=None,
                 interactionID=None, scenarioID=None, runtimeID=None, delay=0):
        self.cpu = cpu
        self.cput = cpu_time
        self.remainT = cpu_time
        self.ram = ram
        self.end = None
        self.start = start
        self.scheduled = start
        self.io = io
        self.net = net
        self.perfMod = 1
        self.callbacks = callbacks
        self.functionID = functionID
        self.interactionID = interactionID
        self.scenarioID = scenarioID
        self.delay = delay
        self.runtimeID = runtimeID

    def calcEndTime(self, sCpu, time, io, net):
        self.effCpu(io, net)

        if self.start is None:
            self.start = time

        if sCpu <= 0:
            raise Exception("Server seems to have no resources for this function or in general")

        perfMod = self.cpu / sCpu
        perfMod = max(self.perfMod, perfMod)
        if perfMod < 1:
            perfMod = 1

        if self.end is None:
            self.end = self.start + perfMod * self.cput
            return self.end

        self.remainT = self.cput * perfMod - (time - self.start)
        self.end = time + self.remainT
        if self.end == float("inf"):
            raise Exception("Function duration is infinite")
        return self.end

    def effCpu(self, io, net):
        # to simulate wating for data IO and NET usage of the server are taken into consideration
        perfModIo = 1
        perfModNet = 1

        if io < self.io / self.cput:
            perfModIo = io / (self.io / self.cput)

        if net < self.net / self.cput:
            perfModNet = net / (self.net / self.cput)

        perfMod = 1 / min(perfModIo, perfModNet)
        self.perfMod = perfMod
        return self.cpu * perfMod

    def setCallbackStart(self, t):
        self.start = self.delay + t
        self.scheduled = self.start


    # just list events functions can be ordered to keep FIFO for deferred functions
    def __gt__(self, f2):
        return self.start < f2.start

    def __lt__(self, f2):
        return self.start > f2.start