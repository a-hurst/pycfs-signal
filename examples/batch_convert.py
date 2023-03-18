# -*- coding: utf-8 -*-
"""An example script showing how to batch-convert CFS files to other formats.

This script is written to export the frame metadata and signal data for each
file separately, with metadata getting saved as CSV files in the '_Data/trial'
subfolder and signal data getting saved as Apache Feather (.arrow) files in the
'_Data/signals' subfolder.

To use this script for your own project, you will need to:
  a) Create a folder named 'Raw' and put your CFS data inside it,
  b) Save a copy of this script into the same folder as 'Raw',
  c) Modify 'trial_framevars' and 'signal_channels' to match the names of the
     frame metadata variables and channels in your dataset.

"""

import os
import re
import csv
import shutil
from pathlib import Path

from pycfs import CFS

import numpy as np
import pyarrow as pa
from pyarrow.feather import write_feather


### Paths & Settings ###

rawdir = "Raw" # Folder containing all CFS files to convert
outdir = "_Data" # Output folder for the converted data 

trial_data_dir = os.path.join(outdir, "trial") # Output subfolder for metadata
signal_data_dir = os.path.join(outdir, "signals") # Output subfolder for signals

# Names of the frame metadata and channels to include in the exported data
trial_framevars = ['StateL', 'Interval', 'Power A', 'Power B']
signal_channels = ["Force", "FDS", "Target"]

# Map of raw CFS frame variable and channel names to R-friendly ones
rename_map = {
    "StateL": "state",
    "Interval": "pulse_interval",
    "Power A": "pwr_a",
    "Power B": "pwr_b",
    "Force": "force",
    "FDS": "fds",
    "Target": "target",
}

# If a CFS file's name contains any of these strings, ignore it
exclude = ["DONTUSE", "error"]



### Export Helper Functions ###

def get_frame_dt(frame, chans):
    """Gets the x-axis increment (i.e. sample rate) for a given set of channels.

    Raises an exception if the channels don't all have the same sample rate.

    """
    # Ensure sample rates are consistent for all requested channels
    sample_rates = [frame.sample_rates[ch] for ch in chans]
    if len(set(sample_rates)) > 1:
        raise RuntimeError("Inconsistent sample rates across channels")

    # Ensure requested channels have equal numbers of samples
    sample_counts = [len(frame.data[ch]) for ch in chans]
    if len(set(sample_counts)) > 1:
        raise RuntimeError("Inconsistent sample counts across channels")
    
    # Once we've verified equal sample rates/counts, return the dt
    dt = sample_rates[0]
    return dt


def write_metadata(cfs, outpath, framevars = [], name_map = {}):
    """Writes out the metadata for each frame in a CFS to a .csv file.

    Args:
        cfs (:obj:`pycfs.CFS`): The CFS object containing the metadata to write.
        outpath (str): The output path for the CSV file.
        framevars (list): A list of the frame variables to include in the output
            file (e.g. ['StateL', 'Power A']).
        name_map (dict, optional): A dictionary in ``{name: outname}`` format
            allowing frame variables to be renamed in the header during export
            (e.g. ``{'Power A': 'pwr_a'}).

    """
    frame_num = 0
    header = ['frame']
    for var in framevars:
        if var in name_map.keys():
            var = name_map[var]
        header.append(var)

    rows = []
    for i in range(cfs.n_frames):
        row = [i + 1]
        for var in framevars:
            row.append(cfs.frames[i].vars[var])
        rows.append(row)

    with open(outpath, 'w+', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)


def write_signals(cfs, outpath, chans = [], name_map = {}):
    """Writes out the signal for each frame in a CFS to an Apache Feather file.

    This example uses the Feather format (``.arrow``) because of its speed,
    small file sizes, and ease of use with both R and Python.

    Args:
        cfs (:obj:`pycfs.CFS`): The CFS object containing the data to export.
        outpath (str): The output path for the Feather file.
        chans (list): A list of the channels to include in the output file
            (e.g. ['EMG', 'Force Grip']).
        name_map (dict, optional): A dictionary in ``{name: outname}`` format
            allowing channels to be renamed in the file during export
            (e.g. ``{'Force Grip': 'force'}).

    """
    # Build output file header
    header = ['frame', 'time']
    cols = ['frame', 'time']
    data = {'frame': [], 'time': []}
    for ch in chans:
        data[ch] = []
        cols.append(ch)
        if ch in name_map.keys():
            ch = name_map[ch]
        header.append(ch)

    # Gather arrays of data for each frame in the file
    for i in range(cfs.n_frames):
        frame = cfs.frames[i]
        nsamples = len(frame.data[chans[0]])
        data['frame'].append(np.full(nsamples, i + 1, dtype=np.int16))

        # Generate the time array for the frame based on the sample rates of the
        # requested channels
        dt = get_frame_dt(frame, chans)
        time_sigfigs = len(str(dt).split('.')[-1])
        data['time'].append(np.arange(0, nsamples, dtype=np.float64) * dt)

        # Grab the frame data for each requested channel
        for ch in chans:
            data[ch].append(frame.data[ch])

    # Merge the data from all frames together and export it to Feather
    table = pa.Table.from_arrays(
        [pa.array(np.concatenate(data[col])) for col in cols],
        names=header
    )
    write_feather(table, outpath, compression="zstd")



### Actual Export Script ###

# If the output folder already exists, remove it
if os.path.exists(outdir):
    shutil.rmtree(outdir)

# Create all the output directories
for d in [outdir, trial_data_dir, signal_data_dir]:
    os.mkdir(d)


for f in Path(rawdir).rglob("*.cfs"):

    # Skip files with names matching exclusion criteria
    skip = False
    for s in exclude:
        if s in f.name:
            skip = True
            msg = " - {0} matches exclusion criteria, skipping..."
            print(msg.format(f.name))
            continue
    if skip:
        continue

    # Create the output file names/paths
    print(" - Parsing {0}...".format(f.name))
    basename = f.stem
    trial_outpath = os.path.join(trial_data_dir, basename + "_trial.csv")
    signal_outpath = os.path.join(signal_data_dir, basename + "_signals.arrow")

    # Actually read in the CFS and write out the data
    cfs = CFS(f)
    write_metadata(cfs, trial_outpath, trial_framevars, rename_map)
    write_signals(cfs, signal_outpath, signal_channels, rename_map)
