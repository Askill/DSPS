class Server:
    def __init__(self, maxCPU, maxRAM, maxIO, maxNET):
        self.functions = []
        self.maxcpu = maxCPU  # 100 per core
        self.maxram = maxRAM  # mb
        self.maxio = maxIO
        self.maxnet = maxNET
        self.io = self.maxio  # mb/s
        self.net = self.maxnet  # mb/s
        self.cpu = self.maxcpu
        self.ram = self.maxram
        self.perf = self.cpu

    def fits(self, function):
        if len(self.functions) == 0:
            return True

        net = self.maxnet / (max(sum(f.net / f.cput for f in self.functions) + function.net, 1) / function.cput)
        io = self.maxio / (max(sum(f.io / f.cput for f in self.functions) + function.io, 1) / function.cput)
        ram = self.maxram / max(sum(f.ram for f in self.functions) + function.ram, 1)
        cpu = self.cpu / max(sum(f.cpu for f in self.functions) + function.cpu, 1)

        if min(net, io, ram, cpu) >= 1:
            return True
        else:
            return False

    def push(self, function, t):
        # assign function to servers array of active functions
        if function.cpu > self.maxcpu or function.ram > self.maxram:
            raise Exception("Function has higher requirements than server can satisfy")

        ets = set()

        self.functions.append(function)
        tpf = self.calcEffPerf()
        for function in self.functions:
            et = function.calcEndTime(tpf, t, self.io, self.net)
            ets.add(et)

        return list(ets), None

    def pop(self, time):
        # remove old functions from array of active ones and return callbacks
        ets = []
        delete = []
        callbacks = []
        returns = []
        done = 0
        for i, function in enumerate(self.functions):
            if function.end <= time:

                for callback in function.callbacks:
                    if callback != "-1":
                        callbacks.append(callback)

                delete.append(i)
                returns.append(function)
                done += 1

            # function is dropped after 30sec timeout
            # no callbacks will be called
            # elif function.end - function.scheduled > 30:
            #    print("dropped ", function.functionID)
            #    delete.append(i)
            #    done += 1

        for i, j in enumerate(delete):
            try:
                x = self.functions[j - i]
                del self.functions[j - i]
            except:
                print("")
        tpf = self.calcEffPerf()
        for function in self.functions:
            et = function.calcEndTime(tpf, time, self.io, self.net)
            ets.append(et)

        return returns, list(set(ets)), callbacks

    def getResUtil(self):
        '''Ressource Utilization between 0 and 1 cpu, ram, io, net'''
        if len(self.functions) > 0:
            net = sum(f.net for f in self.functions) / self.maxnet
            io = sum(f.io for f in self.functions) / self.maxio
            ram = sum(f.ram for f in self.functions) / self.maxram
            cpu = sum(f.cpu for f in self.functions) / self.cpu

            return cpu, ram, net, io
        else:
            return 0, 0, 0, 0

    def calcEffPerf(self):

        # simulate slow down caused by swap
        # can make model unstable and increase function cpu time to inf
        # ram = sum(f.ram for f in self.functions)
        # self.swap = 0
        # if ram > self.ram:
        #    swap = ram - self.ram
        #    swap = (swap /  ram)
        #    self.perf = ((1-swap) + swap*self.swapSlowdown)*self.cpu
        #    self.swap = swap*10

        # self.net = self.maxnet - sum(f.net for f in self.functions)
        # self.io = self.maxio - sum(f.io for f in self.functions)
        # self.ram = self.maxram - sum(f.ram for f in self.functions)
        # self.cpu = self.maxcpu - sum(f.cpu for f in self.functions)

        self.perf = self.cpu
        tpf = ((self.perf) / (max(1, len(self.functions))))
        return tpf

    def getFreeBy(self):
        return min(f.end for f in self.functions)

    # servers can be sorted and minimum can be calculated, used to determine earliest time by which sevrer is available again

    def __lt__(self, other):
        return self.getFreeBy() < other.getFreeBy()

    def __eq__(self, other):
        return self.getFreeBy() == other.getFreeBy()
