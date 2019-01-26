import abc


class VirtualObj(metaclass=abc.ABCMeta):
    """
    Abstract class for creation of primitive objects
    """
    def __init__(self):
        self.loc = {}

    def __getitem__(self, item):
        """
        Allows for access of items inside the location dictionary without typing .loc[item]
        """
        return self.export_locations()[str(item)]

    def export_locations(self):
        """ This method should return a dict of relevant locations for the virtual obj"""
        return self.loc

    @abc.abstractmethod
    def shift_origin(self, origin=(0, 0), orient='R0'):
        """
        This method should shift the coordinates of relevant locations according to provided
        origin/transformation, and return a new shifted object. This is important to allow for deep manipulation in the
        hierarchy
        """
        pass
