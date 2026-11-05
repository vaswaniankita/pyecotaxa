"""Convert each 2D numeric variable in a .mat file to CSV: python mat2csv.py file.mat"""
import sys

import numpy as np
import scipy.io

path = sys.argv[1]
for name, value in scipy.io.loadmat(path).items():
    if not name.startswith("__"):
        out = f"{path.rsplit('.', 1)[0]}_{name}.csv"
        np.savetxt(out, np.atleast_2d(value), delimiter=",", fmt="%.10g")
        print(f"{name} {value.shape} -> {out}")
