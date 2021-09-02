import networkx as nx
from pyvis.network import Network
import matplotlib.pyplot as plt
import os


def makeGraph(g, root):
    color_map = {}
    root_name = str(root.id) + "_" + str(root.start)[8:]
    for child in root.children:
        child_name = child.id + "_" + str(child.start)[8:]
        if child_name not in color_map and child.isAsync:
            color_map[child_name] = 1
        else:
            color_map[child_name] = 0

        g.add_node(child_name)
        g.add_edge(root_name,
                   child_name)
        cm2 = makeGraph(g, child)
        color_map = {**color_map, **cm2}

    return color_map

def draw(root):
    net = Network(notebook=True)
    G = nx.DiGraph()
    color_map = makeGraph(G, root)
    pos = nx.spring_layout(G)
    nx.draw_networkx_edges(G, pos, edge_color='r', arrows=True)
    net.from_nx(G)
    net.height = "100%"
    net.width = "100%"
    for node in net.nodes:
        if node["id"] in color_map and color_map[node["id"]] == 1:
            node["color"] = "red"
        elif node["id"] in color_map and color_map[node["id"]] == 0:
            node["color"] = "blue"
        else:
            node["color"] = "green"
    
    net.show(os.path.join(os.path.dirname(__file__), '../files/mygraph.html'))

