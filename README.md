# pyCFS

pyCFS is a pure-Python library for reading CED File System (`.cfs`) files. It is designed to make it easy to extract signal data and metadata from CFS files and convert them to different formats (or analyze them directly in Python).

This package has been primarily tested with CFS files created by CED Signal 6, but should be compatible with CFS files from other software. If you encounter a file that doesn't work properly, please open an issue!


## Usage

```python
from pycfs import CFS
import numpy as np

dat = CFS("p001_session1.cfs")

# List all channels in the file along with their units
print("Channels:")
for name, units in dat.channels.items():
	tmp = " - {0}: (x-axis = '{1}', y-axis = '{2}'"
	print(tmp.format(name, units['x_units'], units['y_units']))

# Print the mean EMG amplitude for each frame in the file
i = 1
for f in dat.frames:
	mean_emg = np.mean(f.data['EMG'])
	print("Mean EMG for frame {0}: {1}".format(i, mean_emg))
	i += 1

```