import os
import pandas as pd
import matplotlib.pyplot as plt
from pandas.core.frame import DataFrame

path = "C:/projects/Master/Projekt/validationTestProgram/utilLog.csv"
data = pd.read_csv(path, delimiter=",")
data["time"] = pd.to_datetime(data["time"], unit='s')
data.set_index("time", inplace=True)

data.cpu[pd.to_datetime(1627321487, unit='s'):pd.to_datetime(1627321488 + 17.5, unit='s')].plot()
plt.show()

path = "C:/projects/Master/Projekt/validationTestProgram/delay.csv"
data2 = pd.read_csv(path, delimiter=",")

data2["time"] = pd.to_datetime(data2["time"], unit='s')
data2.set_index("time", inplace=True)
data2.plot()
plt.show()