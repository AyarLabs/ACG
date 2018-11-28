from ACG.VirtualObj import VirtualObj
from ACG.XY import XY

from typing import Optional, Tuple, Union
point_type = Union[float, int]
coord_type = Union[Tuple[point_type, point_type], XY]


class VirtualInst(VirtualObj):
    """
    A class to enable movement/access of low level instances without directly accessing the master
    class
    """
    edges = ('l', 'b', 'r', 't')
    vertices = ('ll', 'lr', 'ur', 'ul', 'c', 'cl', 'cb', 'cr', 'ct')
    valid_orientation = ('R0', 'MX', 'MY', 'R180')

    def __init__(self, master, origin=(0, 0), orient='R0', inst_name=None):
        VirtualObj.__init__(self)

        # Init internal properties
        self._origin = None
        self._orient = None

        # Init local variables
        self.master = master
        self.origin = origin
        self.orient = orient
        self.inst_name = inst_name
        self.loc = {}

        # Init locations
        self.export_locations()

    def __repr__(self):
        temp = 'VirtualInst(master={}, origin={}, orient={})'
        return temp.format(self.master.__class__.__name__, self.origin, self.orient)

    def __str__(self):
        temp = '{}:\n\torigin: {} \n\torient: {}'
        return temp.format(self.master.__class__.__name__, self.origin, self.orient)

    """ Properties """

    @property
    def origin(self) -> XY:
        return self._origin

    @origin.setter
    def origin(self, xy: coord_type) -> None:
        self._origin = XY(xy)  # feed it into XY class to check/condition input

    @property
    def orient(self) -> str:
        return self._orient

    @orient.setter
    def orient(self, value: str):
        if value in VirtualInst.valid_orientation:
            self._orient = value
        else:
            raise ValueError('{} is not a valid orientation'.format(value))

    """ Utility Methods """

    def export_locations(self) -> dict:
        """ Recursively shift all of the elements in the location dictionary """
        self.loc = {}
        old_db = self.master.export_locations()
        for key in old_db:
            # Iterate over all relevant locations in master
            if isinstance(old_db[key], list):
                # If its a list, init an empty list and iterate
                self.loc[key] = []
                for elem in old_db[key]:
                    self.loc[key].append(elem.shift_origin(origin=self.origin, orient=self.orient))
            elif old_db[key] is None:
                print('{} is not a valid location object'.format(key))
                print(old_db[key])
            else:
                # If its not a list
                self.loc[key] = old_db[key].shift_origin(origin=self.origin, orient=self.orient)
        return self.loc

    def move(self, origin=None, orient=None) -> 'VirtualInst':
        """ Set the origin and orientation to new values """
        if origin is not None:
            self.origin = origin
        if orient is not None:
            self.orient = orient
        # Update locations
        self.export_locations()
        return self

    def shift_origin(self, origin=None, orient=None) -> 'VirtualInst':
        """ Moves the instance origin to the provided coordinates and performs transformation"""
        if origin is not None:
            new_origin = self.origin + XY(origin)
            self.move(new_origin, orient)  # Move the block
        else:
            self.move(origin)
        return self

    def align(self,
              target_handle: str,
              target_rect: VirtualObj = None,
              ref_rect: VirtualObj = None,
              ref_handle: str = None,
              align_opt: Tuple[bool, bool] = (True, True),
              offset: coord_type = (0, 0)
              ) -> 'VirtualInst':
        """ Moves the instance to co-locate target rect handle and reference rect handle """
        if target_rect is None:
            # If an explicit target is not provided, assume that the boundary should be used
            target_rect = self.loc['bnd']

        if (target_handle in VirtualInst.edges) or (ref_handle in VirtualInst.edges):
            # If you provided an edge handle instead of a corner handle throw an error
            ValueError('Please use the align_edge method to align edges')

        if (ref_rect is not None) and (ref_handle in ref_rect.loc):
            # if a reference rectangle and handle are provided
            diff = target_rect.loc[target_handle] - ref_rect.loc[ref_handle]
            diff -= XY(offset)
        else:
            # otherwise align only to offset coordinates
            diff = target_rect.loc[target_handle] - XY(offset)

        # if the corresponding align opt is true, shift the origin appropriately
        if align_opt[0]:
            self.origin.x -= diff.x
        if align_opt[1]:
            self.origin.y -= diff.y
        # Update locations
        self.export_locations()
        return self
