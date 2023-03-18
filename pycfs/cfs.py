# -*- coding: utf-8 -*-

import re
from datetime import datetime
import numpy as np

from .read import read_cfs



def _fmt_creator(name, version):
    # Formats the name/version of the program that created the file
    name = re.sub(" Program", "", name).strip()
    release = str(version)[0]
    patch = str(version)[1:]
    return "{0} {1}.{2}".format(name, release, patch)



class CFSInfo(object):
    """Basic metadata for a CFS file.

    """
    def __init__(self, header, creator):
        self.header = header
        self._creator = creator

    def __repr__(self):
        name = ""
        if 'filename' in self.header.keys():
            name = "'{0}'".format(self.header['filename'])
        return "CFSInfo({0})".format(name)

    @property
    def filename(self):
        """str: The internal filename of the CFS file.
        
        Limited to 12 characters, may not match the actual file name.

        """
        return self.header['filename']

    @property
    def created(self):
        """:obj:`datetime.datetime`: The date and time when the file was created.

        """
        timestamp = self.header['startdate'] + "_" + self.header['starttime']
        return datetime.strptime(timestamp, "%d/%m/%y_%H:%M:%S")

    @property
    def creator(self):
        """str: Name and version of the software that created the file.

        """
        return self._creator

    @property
    def size(self):
        """int: The size of the CFS file (in bytes).
        
        """
        return self.header['filesize']

    @property
    def version(self):
        """int: The version of the CFS format used by the file (1 or 2).

        """
        version_char = self.header['marker'][-1]
        return (ord(version_char) - ord('!')) + 1

    @property
    def comment(self):
        """str: The comment field for the CFS file.

        """
        return self.header['comment']



class CFS(object):
    """An object containing the data and metadata from a CED CFS file.

    CFS files store data in separate frames (i.e. trials, windows of data), each
    of which contains both signal data and metadata for a given recording. For
    CFS files generated from CED Signal, one frame typically responds to one
    trial or sweep of data.

    In addition to frames of data, CFS files also contain file-level metadata in
    the form of file variables, which can store values as well as their units.
    These are stored in a ``{name: data}`` dictionary, with ``name`` being the
    name of each variable, and ``data`` being a dict containing its value and
    unit (e.g. ``{'age': {'value': 25, 'units': 'years'}}``).

    Args:
        filepath (str): The path of the CFS file to open.

    Attributes:
        info (:obj:`CFSInfo`): An object containing basic CFS metadata for the
            file (e.g. date created, creator program, size).
        filevars (dict): The names, values, and units of the file's file-level
            variables.
        channels (dict): The names and x/y-axis units of the channels present
            in the file.
        framevars (dict): The names and units of the frame-level variables
            present in the file.
        frames (list): A sequential list containing each :obj:`Frame` of data in
            the file.

    """
    def __init__(self, filepath):

        self._raw = None
        self.info = None

        self.channels = {}
        self.filevars = {}
        self.framevars = {}
        self.frames = []

        self._load_cfs(filepath)

    def __repr__(self):
        s = "CFS({0} channels, {1} frames)"
        return s.format(self.n_channels, self.n_frames)

    def _load_cfs(self, filepath):
        # Actually parse the raw data into Python
        dat = read_cfs(filepath)
        self._raw = dat

        # Gather basic file metadata
        creator_name = dat['header']['filevars'][0]['name']
        creator_version = dat['filevars'][creator_name]
        creator_str = _fmt_creator(creator_name, creator_version)
        self.info = CFSInfo(dat['header']['file'], creator_str)

        # Get channels and their x/y units
        for ch, ch_info in dat['header']['chans'].items():
            self.channels[ch] = {
                'x_units': ch_info['x_units'],
                'y_units': ch_info['y_units'],
            }

        # Get file variables and their values/units
        for v in dat['header']['filevars']:
            self.filevars[v['name']] = {
                'value': dat['filevars'][v['name']],
                'units': v['units'],
            }

        # Get frame variables and their units
        self.framevars = {
            v['name']: v['units'] for v in dat['header']['dsvars']
        }

        self.frames = dat['frames']

    @property
    def n_channels(self):
        """int: The number of channels present in the file."""
        return len(self.channels)

    @property
    def n_frames(self):
        """int: The number of frames of data present in the file."""
        return len(self.frames)

    @property
    def n_filevars(self):
        """int: The number of file-level metadata variables the file."""
        return len(self.filevars)
    
    @property
    def n_framevars(self):
        """int: The number of frame-level metadata variables the file."""
        return len(self.framevars)
