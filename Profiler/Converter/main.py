
import os
import json
import argparse
import plotly.express as px

from Converter.CallTreeBuilder import *
from Converter.ProfileBuilder import *
from Converter.GraphVis import *

def saveJSON(path, data):
    with open(path, 'w') as profileF:
        json.dump(data, profileF)

def gantPlotChild(root):
    lst = []
    for child in sorted(root.children, key=lambda x: x.start):
        lst.append(dict(Task=child.id, Start=pd.to_datetime(child.start), Finish=pd.to_datetime(child.end)))
        for child in sorted(child.children, key=lambda x: x.start):
            lst.append(dict(Task=child.id, Start=pd.to_datetime(child.start), Finish=pd.to_datetime(child.end)))
            for child in sorted(child.children, key=lambda x: x.start):
                lst.append(dict(Task=child.id, Start=pd.to_datetime(child.start), Finish=pd.to_datetime(child.end)))

    df = pd.DataFrame(lst)
    fig = px.timeline(df, x_start="Start", x_end="Finish", y="Task")
    #fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
    fig.show()

def main():


    # handle user input and build paths
    parser = argparse.ArgumentParser(description='program name, path to util log, path to network log')
    parser.add_argument('-cl', type=str, help='name of the programm running exp: java.exe', required=True)
    parser.add_argument('-l', type=str, help='relativ path of input util log', required=True)
    parser.add_argument('-n', type=str, help='relativ path of input network log', required=True)

    parser.add_argument('-op', type=str, help='relativ path to output folder', default="./files")
    parser.add_argument('-d', type=int, help='depth', default=3)
    args = parser.parse_args()

    callLogPath = os.path.join(os.path.dirname(__file__), args.cl)
    utilLogPath = os.path.join(os.path.dirname(__file__),  args.l)
    netLogPath = os.path.join(os.path.dirname(__file__),  args.n)
    depth = args.d

    profilePath = os.path.join(os.path.dirname(__file__), args.op + "/profile.json")
    mappingPath = os.path.join(os.path.dirname(__file__), args.op + "/mapping.json")
    servicePath = os.path.join(os.path.dirname(__file__), args.op + "/services.json")


    # start actual work
    print("Building Call Tree")
    root = convert(callLogPath)
    reduceRoots(root, callLogPath)
    print("Truncating Tree to specified depth")
    truncateTree(root, 0.1 * 1E9, steps=depth)
    print("Merging async interactions")
    mergeAsyncInteractions(root)
    print("Validating Tree")
    validateTree(root)

    print("Creating Profile")
    profile = createProfile(root, "name", utilLogPath, netLogPath)
    print("Creating Default Mapping")
    mapping = genMapping(profile, netLogPath)
    print("Creating Default Service Definition")
    services = genServices(netLogPath)

    # save results
    saveJSON(profilePath, profile)
    saveJSON(mappingPath, mapping)
    saveJSON(servicePath, services)

    print("Interactions: ")
    for i, child1 in enumerate(sorted(root.children, key=lambda x: x.start)):
        print(i, child1.id, "\n ", pd.to_datetime(child1.end - child1.start, unit='ns'))
        if child1.children:
            total = 0
            for child in child1.children:
                total += child.end - child.start
            print(" ",total, "\n", pd.to_datetime(max(child1.children, key=lambda x: x.end).end - min(child1.children, key=lambda x: x.start).start, unit='ns'))
        else:
            print("")

    # plotting
    markAsync(root)
    print("Creating Tree Visualization")
    draw(root)
    gantPlotChild(root)


if __name__ == "__main__":
    main()
