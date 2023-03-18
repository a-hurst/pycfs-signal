# -*- coding: utf-8 -*-

from collections import OrderedDict
import numpy as np


# Define CFS constants and data types

CFS_EQUALSPACED = 0
CFS_MATRIX = 1
CFS_SUBSIDARY = 2

DATA_TYPES = [
    np.int8,      # INT1
    np.uint8,     # WRD1
    np.int16,     # INT2
    np.uint16,    # WRD2
    np.int32,     # INT4
    np.float32,   # RL4
    np.float64,   # RL8
    np.character, # LSTR
]


# Define the names and sizes (in bytes) of fields in different CFS structures

field_sizes = {}

field_sizes['header'] = OrderedDict([
    ('marker', 8),
    ('filename', 14),
    ('filesize', 4),
    ('starttime', 8),
    ('startdate', 8),
    ('num_channels', 2),
    ('num_filevars', 2),
    ('num_dsvars', 2),
    ('header_bytes', 2),
    ('ds_header_bytes', 2),
    ('last_ds_header_offset', 4),
    ('num_data_sections', 2),
    ('block_size_rounding', 2),
    ('comment', 74),
    ('pointer_table_offset', 4),
    ('reserved', 40)
])

field_sizes['channels'] = OrderedDict([
    ('name', 22),
    ('y_units', 10),
    ('x_units', 10),
    ('dtype', 1),
    ('data_kind', 1),
    ('byte_space', 2),
    ('next_channel', 2)
])

field_sizes['vars'] = OrderedDict([
    ('name', 22),
    ('dtype', 2),
    ('units', 10),
    ('offset', 2)
])
VAR_BYTES = 36

field_sizes['ds_header'] = OrderedDict([
    ('prev_header_p', 4),
    ('ch_dat_p', 4),
    ('ch_dat_size', 4),
    ('flags', 2),
    ('reserved', 16)
])

field_sizes['ch_info'] = OrderedDict([
    ('data_offset', 4),
    ('data_points', 4),
    ('y_scale', 4),
    ('y_offset', 4),
    ('x_increment', 4),
    ('x_offset', 4)
])


fields = {}
for f in field_sizes.keys():
    fields[f] = list(field_sizes[f].keys())
