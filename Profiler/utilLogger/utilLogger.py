# coding:utf-8
from threading import current_thread
from time import sleep
import psutil
import numpy as np
import os
import time
import datetime
import atexit
import argparse
import multiprocessing

class processMoniter:
    def __init__(self, name):
        self.name = name
        self.cpu_nums = psutil.cpu_count()
        self.max_mem = psutil.virtual_memory().total
        self.plist = [proc for proc in psutil.process_iter()
                      if proc.name() == self.name]
        
        self.get_system_info()
        self.get_processes_info()

    def get_system_info(self):
        cpu_percent = psutil.cpu_percent(interval=None, percpu=False)
        mem_percent = psutil.virtual_memory().used
        return cpu_percent, mem_percent

    def get_process_info(self, p):
        try:
            if p.is_running:
                cpu_percent = p.cpu_percent(interval=None)
                mem_percent = p.memory_percent()
            else:
                cpu_percent = 0.0
                mem_percent = 0.0
            return cpu_percent, mem_percent
        except:
            return 0.0, 0.0

    def get_processes_info(self):
        infodic = []
        try:
            cpuG = 0
            memG = 0
            l = len(infodic)
            for p in self.plist:
                res = self.get_process_info(p)
                if res is not None:
                    cpu, mem = res
                    cpuG += cpu
                    memG += mem
                else:
                    l -= 1

            return cpuG, memG
        except:
            self.plist = [proc for proc in psutil.process_iter()
                          if proc.name() == self.name]
            return self.get_processes_info()


class Logger:
    def __init__(self, name):
        self.taskmgr = processMoniter(name)
        self.name = name
        self.connections = {}
        self.netpath = ""
        self.pids = []
   

    def getFuncIdentifier(self, connection):
        return connection.laddr.ip + ":" + str(connection.laddr.port) + "-" + connection.raddr.ip + ":" + str(connection.raddr.port)

    def logConnnections(self):
        connections = psutil.net_connections()
        returns = []
        current_time = time.time()
        connectionsList = []
        for connection in connections:
            if connection.status == "LISTEN" or connection.status == "NONE":
                continue
            if connection.raddr.ip == "127.0.0.1":
                continue
            if connection.status in ["CLOSE_WAIT", "FIN_WAIT1"] :
                continue
            #if connection.pid not in self.pids:
            #    continue

            
            identifier = self.getFuncIdentifier(connection)
            if identifier in self.connections:
                connectionsList.append(identifier)
                continue
            else: 
                self.connections[identifier] = [current_time, connection.raddr.ip + ":" + str(connection.raddr.port), None]   
                connectionsList.append(identifier)

        dels = []
        for i, ident in enumerate(self.connections):
            if ident not in connectionsList:
                res = self.connections[ident]
                res[-1] = current_time
                returns.append(res)
                dels.append(i)

        for i, j in enumerate(dels):
            del self.connections[list(self.connections.keys())[j-i]]

        return returns

    def log(self, utilPath, netPath):
        self.netpath = netPath
        cycles = 0
        self.pids = [p.pid for p in self.taskmgr.plist]
        with open(utilPath, "w") as f:
            f.write("{},{},{}\n".format("time", "cpu", "mem"))
            with open(netPath, "w") as fn:
                fn.write("{},{},{}\n". format("start", "target", "end"))
                while True:
                   
                    if cycles == 10:
                        cycles = 0
                        #cpu, mem = self.taskmgr.get_processes_info()
                        io = 0
                        current_time = time.time()
                        cpu, mem = self.taskmgr.get_system_info()
                        cpu *= multiprocessing.cpu_count()
                        fn.flush()
                        f.write("{},{},{}\n".format(
                            current_time, cpu, mem))

                    
#                    if cycles > 100:
#                        cycles = 0
#                        self.taskmgr.plist = [
#                            proc for proc in psutil.process_iter() if proc.name() == self.name]
#                        self.pids = [p.pid for p in self.taskmgr.plist]

                    net = self.logConnnections()
                    for entry in net:
                        fn.write("{},{},{}\n". format(entry[0], entry[1], entry[2]))

                    # interval schould be 0.1 seconds at least
                    time.sleep(.01)
                    cycles += 1

    
    def cleanup(self, netPath):
        # write all cached connections to disk with the current time as end time
        with open(netPath, "a") as fn:
            current_time = time.time()
            for ident in self.connections:
                res = self.connections[ident]
                res[-1] = current_time
                fn.write("{},{},{}\n". format(res[0], res[1], res[2]))

# https://psutil.readthedocs.io/en/latest/

def main():
    parser = argparse.ArgumentParser(description='program name, path to util log, path to network log')
    parser.add_argument('-p', type=str, help='name of the programm running exp: java.exe', required=True)
    parser.add_argument('-l', type=str, help='relativ path of output util log', default="./utilLog.csv")
    parser.add_argument('-n', type=str, help='relativ path of output network log', default="./networkLog.csv")
    args = parser.parse_args()

    utilPath = os.path.join(os.path.dirname(__file__), args.l)
    netPath = os.path.join(os.path.dirname(__file__), args.n)

    l = Logger(args.p)
    atexit.register(l.cleanup, netPath)
    l.log(utilPath, netPath)

if __name__ == "__main__":
    main()
