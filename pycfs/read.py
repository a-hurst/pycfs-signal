
import os
import re
from copy import deepcopy
from collections import OrderedDict

import numpy as np

from .structure import CFS_EQUALSPACED, DATA_TYPES, VAR_BYTES, fields, field_sizes
from .frame import Frame


# Name regex for largely-unused CFS variables created by Signal
signal_junk = [
    "User\d+", "RTot", "SysD", "RAcc", "CMemb", "RMemb",
    "FCom", "SysF", "ClF",
]


def from_header(raw, field_size, as_float=False):
    """Convert raw bytes from the CFS header to a useful Python data format.

    For the sake of code simplicity, this function infers the data type of the
    header field from the size in bytes of the header field. This works because,
    apart from int32 and float32, no two types share a byte width.

    Args:
        raw (bytes): The raw bytes of the field to convert.
        field_size (int): The size of the field (in bytes) to be converted.
        as_float (bool, optional): Whether numeric bytes should be cast to an int
            or a float of the specified byte width. Currently only affects 32-bit
            (4 byte) fields. Defaults to False.

    Returns:
        The parsed value from the header.

    """
    if field_size == 1:
        val = np.frombuffer(raw, dtype=np.uint8)[0]
    elif field_size == 2:
        val = np.frombuffer(raw, dtype=np.int16)[0]
    elif field_size == 4:
        if as_float:
            val = np.frombuffer(raw, dtype=np.float32)[0]
        else:
            val = np.frombuffer(raw, dtype=np.int32)[0]
    elif field_size == 8:
        val = raw.decode('utf-8').rstrip('\x00').rstrip()
    else:
        # For strings, first byte is length of string
        strsize = raw[0]
        val = raw[1:(strsize + 1)].decode('utf-8')

    return val


def read_var(f, offset, dtype):
    """Read a file variable or data section variable from the file.

    Args:
        f: The file object containing the target CFS file.
        offset (int): The offset (in bytes) of the variable, relative to
            the start of the file.
        dtype (int): The data type of the variable. See the ``DATA_TYPES``
            list in ``structure.py`` for more information.
    
    Returns:
        The parsed variable, cast to the specified data type.

    """
    current_pos = f.tell()
    f.seek(offset)
    if dtype == 7:
        strsize = int.from_bytes(f.read(1), "little")
        val = f.read(strsize).decode('utf-8')
    else:
        var_type = DATA_TYPES[dtype]
        raw = f.read(np.dtype(var_type).itemsize)
        val = np.frombuffer(raw, dtype=var_type)[0]
    f.seek(current_pos)

    return val


def read_cfs_header(f):
    """Read all fields of a CFS header into a Python dict.

    This function does no postprocessing of the imported fields, which is a role
    left to other functions.

    Returns a dictonary with the keys 'file' (for general file info),
    'chans' (channel info), 'filevars' (file variable info), 'dsvars'
    (data section info), and 'filevars_offset' (the offset in bytes of the
    section containing file variable values).

    Args:
        f: The file object containing the target CFS file.

    Returns:
        dict: A dictonary containing the raw header info.

    """
    # Start at beginning of file, just in case
    f.seek(0)

    # Read in general header
    info = {}
    for field in fields['header']:
        field_size = field_sizes['header'][field]
        info[field] = from_header(f.read(field_size), field_size)

    # Read in channel info
    channels = [{} for _ in range(info['num_channels'])]
    for ch in channels:
        for field in fields['channels']:
            field_size = field_sizes['channels'][field]
            ch[field] = from_header(f.read(field_size), field_size)

    # Read in file variable info
    filevars = [{} for _ in range(info['num_filevars'])]
    for var in filevars:
        for field in fields['vars']:
            field_size = field_sizes['vars'][field]
            var[field] = from_header(f.read(field_size), field_size)
    f.read(VAR_BYTES) # skip empty var at end

    # Read in data section variable info
    dsvars = [{} for _ in range(info['num_dsvars'])]
    for var in dsvars:
        for field in fields['vars']:
            field_size = field_sizes['vars'][field]
            var[field] = from_header(f.read(field_size), field_size)
    f.read(VAR_BYTES) # skip empty var at end

    # Grab the byte offset of the file variables section
    file_vars_offset = f.tell()

    # Return to start of file
    f.seek(0)

    return {
        'file': info, 'chans': channels, 'filevars': filevars, 'dsvars': dsvars,
        'filevars_offset': file_vars_offset
    }


def read_cfs(filename, filter_vars=True):

    if not os.path.exists(filename):
        raise RuntimeError("File '{0}' does not exist.".format(filename))
    
    # Read in raw data without parsing
    with open(filename, 'rb') as cfs:

        # Read in header
        header = read_cfs_header(cfs)
        
        # By default, filter out rarely-used internal Signal vars
        if filter_vars:
            junk = "^(" + "|".join(signal_junk) + ")"
            header['filevars'] = [
                v for v in header['filevars'] if not re.match(junk, v['name'])
            ]
            header['dsvars'] = [
                v for v in header['dsvars'] if not re.match(junk, v['name'])
            ]

        # Read in file variables
        file_vars = {}
        file_vars_offset = header['filevars_offset']
        for var in header['filevars']:
            v = read_var(cfs, file_vars_offset + var['offset'], var['dtype'])
            file_vars[var['name']] = v

        # Get channel names and wrangle channels into a dict
        ch_names = [ch['name'] for ch in header['chans']]
        channels = OrderedDict()
        for ch in header['chans']:
            name = ch.pop('name')
            channels[name] = ch
        header['chans'] = channels

        # Get byte offsets for each data section from end of file
        table_bytes = 4 * header['file']['num_data_sections']
        cfs.seek(header['file']['pointer_table_offset'])
        ds_offsets = np.frombuffer(cfs.read(table_bytes), dtype=np.int32)

        data_sections = []
        for offset in ds_offsets:

            # Jump to start of data section & create frame template
            cfs.seek(offset)
            frame = Frame()

            # Read in general header for data section
            ds_header = {}
            for field in fields['ds_header']:
                field_size = field_sizes['ds_header'][field]
                ds_header[field] = from_header(cfs.read(field_size), field_size)
            
            # Read in channel info for each channel in data section
            ch_info = {}
            for ch in ch_names:
                tmp = {}
                for field in fields['ch_info']:
                    if field[0] in ['x', 'y']:
                        tmp[field] = from_header(cfs.read(4), 4, as_float=True)
                    else:
                        tmp[field] = from_header(cfs.read(4), 4)
                ch_info[ch] = tmp

            # Read in variables for data section
            ds_vars_offset = cfs.tell()
            for var in header['dsvars']:
                v = read_var(cfs, ds_vars_offset + var['offset'], var['dtype'])
                frame._add_variable(var['name'], v)

            # Read in actual data for each channel in section
            data_offset = ds_header['ch_dat_p']
            for ch in ch_names:
                ch_dtype = DATA_TYPES[channels[ch]['dtype']]
                ch_byte_space = channels[ch]['byte_space']
                ch_byte_size = np.dtype(ch_dtype).itemsize
                ch_offset = ch_info[ch]['data_offset']
                ch_sample_rate = ch_info[ch]['x_increment']
                ch_samples = ch_info[ch]['data_points']
                ch_bytes = ch_info[ch]['data_points'] * ch_byte_space
                if ch_bytes == 0:
                    frame._add_channel(ch, ch_sample_rate, None)
                    continue
                elif ch_byte_space > ch_byte_size:
                    # If bytes from multiple channels are interleaved, read in all
                    # bytes for all interleaved channels and then discard
                    # irrelevant bytes
                    byte_pos = int((ch_offset % ch_byte_space) / ch_byte_size)
                    ch_offset = ch_offset - (ch_offset % ch_byte_space)
                    cfs.seek(data_offset + ch_offset)
                    raw = np.frombuffer(cfs.read(ch_bytes), dtype=ch_dtype)
                    raw = np.reshape(raw, (ch_samples, -1))[:, byte_pos]
                else:
                    cfs.seek(data_offset + ch_offset)
                    raw = np.frombuffer(cfs.read(ch_bytes), dtype=ch_dtype)
                data = (raw * ch_info[ch]['y_scale']) + ch_info[ch]['y_offset']
                frame._add_channel(ch, ch_sample_rate, data)

            data_sections.append(frame)

    return {
        'header': header,
        'filevars': file_vars,
        'frames': data_sections
    }
