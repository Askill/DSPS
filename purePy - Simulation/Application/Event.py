class Event:
    def __init__(self, t, type, serviceId, function):
        self.t = t
        # type can be either recalculation or None
        # if type is None, then Event contains function
        self.type = type
        self.serviceId = str(serviceId)
        self.function = function

    # functions for sorting events to keep FIFO even for deferred functions
    def __lt__(self, other):
        if self.function is None:
            return False
        if other.function is None:
            return False

        return self.function.scheduled > other.function.scheduled

    def __eq__(self, other):
        if self.function is None and other.function is None:
            return True
        elif self.function.scheduled == other.function.scheduled:
            return True
        else:
            return False


    def print(self):
        return f"t: {self.t}, type: {self.type}, serviceID: {self.serviceId}, function:{self.function}"