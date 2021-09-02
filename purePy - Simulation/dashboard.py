
import pandas as pd

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc

from Application.Simulation import Simulation
import os

import numpy as np
from dash.dependencies import Input, Output, State
from Application.DistributionFactory import *
import base64
import sys
import traceback

import  threading

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import Application.config as config

pd.options.plotting.backend = "plotly"

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.SLATE, {
    'href': 'https://use.fontawesome.com/releases/v5.8.1/css/all.css',
    'rel': 'stylesheet',
    'integrity': 'sha384-50oBUHEmvpQ+1lW4y57PTFmhCaXp0ML5d60M1M7uH2+nqUivzIebhndOJK28anvf',
    'crossorigin': 'anonymous'
}])
sys.setrecursionlimit(10 ** 6)
dfs = dict()
graphs = []

schemaPath = os.path.join(os.path.dirname(__file__), "./Application/files/profile_schema.json")
serviceSchemaPath = os.path.join(os.path.dirname(__file__), "./Application/files/service_schema.json")

schema = DistributionFactory.getContentFromFile(schemaPath)
serviceSchema = DistributionFactory.getContentFromFile(serviceSchemaPath)

profile = None
services = None
mapping = {}

seed = None

lastDropDown = dict()

expectedFig = None
distRequest = None  # [(np.random.triangular(0, 10E9, 60E9, 1), 1)]


@app.callback(
    Output("errors", "children"),
    Input('input_go', 'n_clicks'))
def startSimulation(value):
    global profile
    global services
    global mapping
    global seed
    global distRequest
    
    np.random.seed(1)

    if value > 0:
        if profile is not None and services is not None and mapping is not None:
            try:
                sim = Simulation(schema, serviceSchema)

                mapping2 = DistributionFactory.genMapping(profile, mapping)
                sim.main(profile, mapping2, services, distRequest)
                tmp = readFromQueue(sim)
                saveSimResult(tmp)

                createLayout()



                return html.Div(["Simulation complete"])
            except Exception as e:
                traceback.print_exc()
                print(e)
                return html.Div(str(e)),
        else:
            return html.Div("One or more inputs missing!")
    return html.Div([""])


def saveSimResult(observationDict, savePath="SimResults.json"):
    savePath = os.path.join(os.path.dirname(__file__), savePath)
    print(savePath)
    with open(savePath, 'w') as fp:
        json.dump(observationDict, fp)


def readFromQueue(sim):
    global dfs
    dfs = dict()

    # TODO: auto update the dfs dict properly

    tmp = sim.observationQueueToDict()

    for value, df in tmp.items():#
        x = pd.DataFrame.from_dict(df)
        x["t"] = pd.to_datetime(x["t"], unit='ns')
        x.set_index("t", inplace=True)

        if value in dfs:
            dfs[value].append(x)
        else:
            dfs[value] = x

    return tmp

def createLayout():
    uploadStyle = {
        'width': '100%',
        'height': '60px',
        'lineHeight': '60px',
        'borderWidth': '1px',
        'borderStyle': 'dashed',
        'borderRadius': '5px',
        'textAlign': 'center',
        'margin': '10px'
    }
    global app
    app.layout = html.Div(
        [
            html.Div([
                dcc.Interval(
                    id='interval-component',
                    interval=int(config.refreshTime) * 1000,  # in milliseconds
                    n_intervals=0
                ),
                dcc.Interval(
                    id='interval2',
                    interval=int(config.refreshTime/2) * 1000,  # in milliseconds
                    n_intervals=0
                ),
                html.Div([
                    html.Div([
                        dcc.Upload(
                            id='input_profile',
                            children=html.Div([
                                'Select Application Profile'
                            ]),
                            style=uploadStyle,
                            multiple=False
                        )
                    ], className="col-2"),
                    html.Div([
                        dcc.Upload(
                            id='input_services',
                            children=html.Div([
                                'Select Service Definition'
                            ]),
                            style=uploadStyle,
                            multiple=False
                        )
                    ], className="col-2"),
                    html.Div([
                        dcc.Upload(
                            id='input_mapping',
                            children=html.Div([
                                'Select Service Mapping'
                            ]),
                            style=uploadStyle,
                            multiple=False
                        )
                    ], className="col-2"),
                    html.Div([
                        dcc.Upload(
                            id='input_dist',
                            children=html.Div([
                                'Select Distribution Request'
                            ]),
                            style=uploadStyle,
                            multiple=False
                        )
                    ], className="col-2"),
                    html.Div([
                        dcc.Input(id="input_seed", placeholder='seed', style=uploadStyle)
                    ], className="col-1"),
                    html.Div([
                        html.Button(children=html.I(className="far fa-play-circle fa-3x",
                                                    style={"display": "inline-block",
                                                           "margin": "-8px auto auto -8px", "padding": "0"}),
                                    id='input_go',
                                    className="btn btn-outline-success",
                                    style={'lineHeight': '60px', 'margin': '10px',
                                           'width': '60px', 'height': '60px', "display": "inline-block",
                                           },
                                    n_clicks=0
                                    )
                    ], className="col-1"),
                    html.Div([

                    ], className="col-2", id="errors")
                ], className="row g-2 pt-3")
            ]),
            html.Div(getPlots() , className="container-fluid px-2 overflow-hidden", id="plots"),

        ]
    , style={"overflow": "hidden"})



def getPlots():
    plots = [
        html.Div([
            html.Div([
                html.Div([
                    html.Div([
                        getDropdown("dones")
                    ],
                        id="dones-dropdown"
                    ),
                    html.Div([
                        ],
                        id="dones-plot"
                    )
                ], id="done", className="col-6"),
                html.Div([
                    html.Div([
                        getDropdown("service_util")
                    ],
                        id="service_util-dropdown"
                    ),
                    html.Div([
                        ],
                        id="service_util-plot"
                    )
                ], id="service_util", className="col-6")
            ], className="row g-2 pt-3"),
            html.Div([
                html.Div([
                    html.Div([
                        getDropdown("response_time")
                    ],
                        id="response_time-dropdown"
                    ),
                    html.Div([
                        ],
                        id="response_time-plot"
                    )
                ], id="response_time", className="col-6"),

                html.Div([
                    html.Div([
                        getDropdown("sim_events")
                    ],
                        id="sim_events-dropdown"
                    ),
                    html.Div([
                    ],
                        id="sim_events-plot"
                    )
                ], id="sim_events", className="col-6")

            ], className="row g-2 pt-3")
        ])
    ]

    return plots


@app.callback(Output('input_profile', 'children'),
              Input('input_profile', 'contents'))
def setProfileInput(content):
    global profile
    try:
        if content is None and profile is not None:
            return html.Div(['Application Profile ✔'])

        if content is not None:
            content_type, content_string = content.split(',')
            p = json.loads(base64.b64decode(content_string))
            suc, e = DistributionFactory.validateContentvsSchema(p, schema)
            if not suc:
                return html.Div([str(e)])

            profile = p
            return html.Div(['Application Profile ✔'])
        else:
            return html.Div(['Select Application Profile'])
    except Exception as e:
        print(e)
        return html.Div(['Application Profile ❌'])


@app.callback(Output('input_services', 'children'),
              Input('input_services', 'contents'))
def setServicesInput(content):
    try:
        global services
        if content is None and services is not None:
            return html.Div(['Service Definition ✔'])

        if content is not None:
            content_type, content_string = content.split(',')
            p = json.loads(base64.b64decode(content_string))
            suc, e = DistributionFactory.validateContentvsSchema(p, serviceSchema)
            if not suc:
                return html.Div([str(e)])

            services = copy.deepcopy(p)
            return html.Div(['Service Definition ✔'])
        else:
            return html.Div(['Select Service Definition'])
    except Exception as e:
        print(e)
        return html.Div(['Service Definition ❌'])


@app.callback(Output('input_mapping', 'children'),
              Input('input_mapping', 'contents'))
def setMappingInput(content):
    try:
        global mapping
        global profile
        if content is None and mapping is not None:
            return html.Div(['Service Mapping ✔'])

        if content is not None:
            content_type, content_string = content.split(',')
            p = json.loads(base64.b64decode(content_string))

            if profile is None:
                return html.Div(['Select Application Profile first'])

            mapping = copy.deepcopy(p)
            return html.Div(['Service Mapping ✔'])
        else:
            return html.Div(['Select Service Mapping'])

    except Exception as e:
        print(e)
        return html.Div(['Service Mapping ❌'])


@app.callback(Output('input_dist', 'children'),
              Input('input_dist', 'contents'))
def setDistInput(content):
    try:
        global distRequest


        if content is None and distRequest is not None:
            return html.Div(['Distributions ✔'])

        if content is not None:
            distRequest = []
            content_type, content_string = content.split(',')
            p = json.loads(base64.b64decode(content_string))

            # TODO: validate that requested scenarioids are present in profile
            for req in p:
                if req["kind"] == "triangle":
                    dist = (np.random.triangular(req["start"]*1E9, req["highpoint"]*1E9, req["end"]*1E9, req["volume"]), req["scenarioID"])
                    distRequest.append(dist)

            return html.Div(['Distributions ✔'])
        else:
            return html.Div(['Select Distribution Request'])

    except Exception as e:
        print(e)
        return html.Div(['Distributions ❌'])

@app.callback(Output('input_seed', 'value'),
              Input('input_seed', 'value'))
def setSeed(value):
    if value is not None:
        global seed
        seed = int(value)
        return value

def getDropdown(keyword):
    if keyword not in dfs:
        return dcc.Dropdown(
            id=keyword + '-dropdown-dd',
            options=[],
            value=[]
        )

    options = []
    for i in sorted(dfs[keyword].identifier.unique()):
        options.append({"label": i, "value": i})

    return dcc.Dropdown(
        id=keyword + '-dropdown-dd',
        options=options,
        value=dfs[keyword].identifier.unique()[0]
    )

@app.callback(
    Output(component_id='dones-dropdown', component_property='children'),
    Output(component_id='response_time-dropdown', component_property='children'),
    Output(component_id='service_util-dropdown', component_property='children'),
    Output(component_id='sim_events-dropdown', component_property='children'),
    Input('interval2', 'n_intervals'))
def getDropdown2(n_intervals):
    returns = []
    global lastDropDown
    titles = ["sim_events","dones", "response_time", "service_util"]

    if not dfs:
        for i in titles:
            returns.append(dcc.Dropdown(
                id=str(i) + '-dropdown-dd',
                options=[],
                value=[])
            )
        return returns

    else:
        for keyword in sorted(list(dfs.keys())):
            options = []
            for i in sorted(dfs[keyword].identifier.unique()):
                options.append({"label": i, "value": i})

            value = lastDropDown[keyword] if lastDropDown[keyword] != [] else dfs[keyword].identifier.unique()[0]

            returns.append( dcc.Dropdown(
                id=keyword + '-dropdown-dd',
                options=options,
                value=value)
                )

        return returns

@app.callback(
    Output(component_id='dones-plot', component_property='children'),
    Input(component_id='dones-dropdown-dd', component_property='value'),
    Input('interval-component', 'n_intervals')
)
def update_output_div(input_value, n_intervals):
    global lastDropDown
    if input_value is not None:
        lastDropDown["dones"] = input_value
    else:
        input_value = lastDropDown["dones"]

    return getPlot("dones", input_value)


@app.callback(
    Output(component_id='response_time-plot', component_property='children'),
    Input(component_id='response_time-dropdown-dd', component_property='value'),
    Input('interval-component', 'n_intervals')
)
def update_output_div(input_value, n_intervals):
    global lastDropDown
    if input_value is not None:
        lastDropDown["response_time"] = input_value
    else:
        input_value = lastDropDown["response_time"]
    return getPlot("response_time", input_value)


@app.callback(
    Output(component_id='service_util-plot', component_property='children'),
    Input(component_id='service_util-dropdown-dd', component_property='value'),
    Input('interval-component', 'n_intervals')
)
def update_output_div(input_value, n_intervals):
    global lastDropDown
    if input_value is not None:
        lastDropDown["service_util"] = input_value
    else:
        input_value = lastDropDown["service_util"]
    return getPlot("service_util", input_value)


@app.callback(
    Output(component_id='sim_events-plot', component_property='children'),
    Input(component_id='sim_events-dropdown-dd', component_property='value'),
    Input('interval-component', 'n_intervals')
)
def update_output_div(input_value, n_intervals):
    global lastDropDown
    if input_value is not None:
        lastDropDown["sim_events"] = input_value
    else:
        input_value = lastDropDown["sim_events"]
    return getPlot("sim_events", input_value)


def loadSimResult(savePath="SimResults.json"):
    global dfs

    savePath = os.path.join(os.path.dirname(__file__), savePath)
    if not os.path.isfile(savePath):
        print(savePath)
        return dfs

    with open(savePath, "r") as fp:
        dfDicts = json.load(fp)

    for value, df in dfDicts.items():
        dfs[value] = pd.DataFrame.from_dict(df)
        dfs[value]["t"] = pd.to_datetime(dfs[value]["t"], unit='ns')
        dfs[value].set_index("t", inplace=True)

    return dfs

def getHistPlot(fig, title, changes):
    global distRequest
    fig2 = make_subplots()

    hist = pd.DataFrame()

    if distRequest is not None:
        dists = sorted([pd.to_datetime(y/1E9, unit="s") for x,_ in distRequest for y in x])
        integratedCurve =  [i for i in range(len(dists))]

        expectedFig =go.Scatter(
            x=dists,
            y=integratedCurve,
            mode="lines",
            line=go.scatter.Line(color="black"),
            name="expected"
            )
        fig2.add_trace(expectedFig)
        hist["t"] = dists
        hist["t2"] = integratedCurve
        hist.set_index("t", inplace=True)
        hist = hist.resample(rule=config.bucketSize).last().interpolate()
        fig2.add_trace(go.Bar(x=hist.index, y=hist["t2"].diff(), name="input"))

    fig2.add_trace(fig)

    #hist = go.Histogram(x=dists, name="input")

    changes = changes.resample(rule=config.bucketSize).last().interpolate()

    fig2.add_trace(go.Bar(x=changes.index, y=changes["completed"].diff(), name="output"))

    fig2.update_layout({"title": title})

    return fig2


def getPlot(keyword, identifier=None):
    global dfs
    if keyword not in dfs:
        return html.P(keyword + ' graph')

    titles = {
        "sim_events": "events in queue",
        "dones": "completed interactions",
        "response_time": "response time",
        "service_util": "service utilization",
    }

    df = dfs[keyword]

    if identifier is None:
        identifier = df.identifier.unique()[0]

    if keyword == "sim_events":
        fig = df.loc[df["identifier"] == identifier].resample(rule=config.average).sum().interpolate().plot(kind='bar', title=f"{titles[keyword]}: {identifier}")

        return dcc.Graph(id=f"{keyword} {identifier}",
                         figure=fig,
                         style={"height": "24rem"}, animate=True)
    else:

        if keyword == "dones":
            data = df.loc[df["identifier"] == identifier].resample(rule = config.average).last().interpolate("pad")
            fig = go.Scatter(
                x=data.index,
                y=data["completed"],
                mode="lines",
                line=go.scatter.Line(color="blue"),
                name="completed"
            )

            fig = getHistPlot(fig, f"{titles[keyword]}: {identifier}", data)

        else:
            data = df.loc[df["identifier"] == identifier].resample(rule=config.average).mean().interpolate("pad")
            fig = data.plot(kind='line', title=f"{titles[keyword]}: {identifier}")

        return dcc.Graph(id=f"{keyword} {identifier}",
                         figure=fig,
                         style={"height": "24rem"}, animate=True)


if __name__ == '__main__':
    dfs = loadSimResult()

    createLayout()
    app.run_server(debug=True)
