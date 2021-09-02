from Application.Simulation import *
from Application.DistributionFactory import *
import os
from queue import Queue
import sys
import argparse

if __name__ == '__main__':

    # function callbacks are resolved recursively
    # there can be thousands of function in one interaction
    sys.setrecursionlimit(10**6)

    # these path should be changed
    schemaPath = os.path.join(os.path.dirname(__file__), "./Application/files/profile_schema.json")
    serviceSchemaPath = os.path.join(os.path.dirname(__file__), "./Application/files/service_schema.json")

    # parse user input
    parser = argparse.ArgumentParser(description='program name, path to util log, path to network log')
    parser.add_argument('-p', type=str, help='relativ path to app profile', required=True)
    parser.add_argument('-s', type=str, help='relativ path to service definition', required=True)
    parser.add_argument('-m', type=str, help='relativ path to mapping', required=True)
    parser.add_argument('-d', type=str, help='relativ path to distribution request', required=True)

    args = parser.parse_args()

    servicePath = os.path.join(os.path.dirname(__file__), args.s)
    profilePath = os.path.join(os.path.dirname(__file__), args.p)
    mappingPath = os.path.join(os.path.dirname(__file__), args.m)

    # the standard seed, so simulations are reproducible
    # seed is used by Distribution factory
    seed = 435234

    # resolve distribution requests
    # only triangle distributions are supported right now
    # can be expanded analog to triangle
    p = DistributionFactory.getContentFromFile(os.path.join(os.path.dirname(__file__), args.d))
    distRequest = []
    for req in p:
        if req["kind"] == "triangle":
            dist = (np.random.triangular(req["start"] * 1E9, req["highpoint"] * 1E9, req["end"] * 1E9, req["volume"]),
                    req["scenarioID"])
            distRequest.append(dist)


    schema = DistributionFactory.getContentFromFile(schemaPath)
    serviceSchema = DistributionFactory.getContentFromFile(serviceSchemaPath)

    profile = DistributionFactory.getContentFromFile(profilePath)
    specialMapping = DistributionFactory.getContentFromFile(mappingPath)
    mapping = DistributionFactory.genMapping(profile, specialMapping)
    service = DistributionFactory.getContentFromFile(servicePath)

    sim = Simulation(schema, serviceSchema)
    # https://json-schema-validator.herokuapp.com/
    sim.main(profile, mapping, service, distRequest)
    #DistributionFactory.createNetworkGraph(profile, mapping)
    # save observation queue as json to be visualized in dashboard
    res = sim.saveOberservations()
    # plot observation results with matplotlib.pyplot
    sim.plotResults(res)
