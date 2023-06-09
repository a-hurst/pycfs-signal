from collections import OrderedDict


class Frame(object):
    """A frame of data (i.e. data section) from a recording.

    Each Frame represents a window of recording, including signal data for one
    or more channels as well as metadata for the frame (e.g. the trial type, or
    the Magstim power level for a TMS experiment).

    .. note:: According to the CFS spec these are called "data sections", but
       for CFS files generated by Signal these correspond to frames of data.

    Attributes:
        vars (dict): The names/values of the metadata variables for the frame.
        channels (list): The channel names for all signals in the frame.
        sample_rates (dict): The sampling interval (usually in seconds) for each
            channel in the frame.
        data (dict): A dictionary containing the signal data for each channel in
            the frame as a 1D numpy array.

    """
    def __init__(self):
        self.vars = OrderedDict()
        self.channels = []
        self.sample_rates = {}
        self.data = {}

    def __repr__(self):
        s = "Frame(chans={0}, vars={1})"
        return s.format(len(self.data), len(self.vars))

    def _add_variable(self, name, v):
        self.vars[name] = v

    def _add_channel(self, name, rate, data):
        self.channels.append(name)
        self.sample_rates[name] = float(str(rate))
        self.data[name] = data
