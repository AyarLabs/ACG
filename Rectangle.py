from ACG.VirtualObj import VirtualObj
from ACG.XY import XY
import bag
from bag.layout.util import BBox
from typing import Tuple, Union
coord_type = Union[Tuple[float, float], XY]


class Rectangle(VirtualObj):
    """
    Creates a better rectangle object with stretch and align capabilities
    """

    """ Constructor Methods """

    def __init__(self, xy, layer, virtual=False):
        """
        xy: [[x0, y0], [x1, y1]]
            xy coordinates for ll and ur locations
        layer: str
            layer name
        virtual: Bool
            If True, do not draw the rectangle
        """

        VirtualObj.__init__(self)

        # Init internal properties
        self._ll = None
        self._ur = None
        self._res = .001

        # Init local variables
        self.xy = xy  # property setter creates ll and ur coordinates
        self.layer: str = layer
        self.virtual: bool = virtual
        self.loc = {
            'll': 0,
            'ur': 0,
            'ul': 0,
            'lr': 0,
            'l': 0,
            'r': 0,
            't': 0,
            'b': 0,
            'cl': 0,
            'cr': 0,
            'ct': 0,
            'cb': 0,
            'c': 0
        }
        self.edges = ['l', 'r', 'b', 't']
        self.v_edges = ['t', 'b']
        self.h_edges = ['l', 'r']

        # Init rect locations
        self.update_dict()

    # Describes all the required keys to define a Rect2 object with a dict
    dict_compatability = ('handle0', 'handle1', 'xy0', 'xy1', 'layer')

    @classmethod
    def from_dict(cls, params: dict) -> 'Rectangle':
        """ Enable the creation of a rectangle from a dictionary of parameters """
        # Check that all parameters required to create keys exist
        if not all(keys in params.keys() for keys in cls.dict_compatability):
            raise ValueError('Provided dict does not contain all parameters required to specify Rect2 obj')
        else:
            handles = [params['handle0'], params['handle1']]
            coordinates = [params['xy0'], params['xy1']]

            # Calculate ll and ur coordinates based on provided handle locations
            if ('ll' in handles) and ('ur' in handles):
                ll_loc = coordinates[handles.index('ll')]
                ur_loc = coordinates[handles.index('ur')]
                xy = [ll_loc, ur_loc]
            elif ('ul' in handles) and ('lr' in handles):
                ul_loc = coordinates[handles.index('ul')]
                lr_loc = coordinates[handles.index('lr')]
                ll_loc = [ul_loc[0], lr_loc[1]]
                ur_loc = [lr_loc[0], ul_loc[1]]
                xy = [ll_loc, ur_loc]
            else:
                raise ValueError('Provided handles do not adequately constrain rectangle dimensions')

            if 'virtual' in params.keys():
                virtual = params['virtual']
            else:
                virtual = False

            # construct class based on cleaned up xy coordinates
            rect = cls(xy, params['layer'], virtual)
            return rect

    """ Properties """

    @property
    def ll(self) -> XY:
        return self._ll

    @ll.setter
    def ll(self, xy):
        self._ll = XY(xy)

    @property
    def ur(self) -> XY:
        return self._ur

    @ur.setter
    def ur(self, xy):
        self._ur = XY(xy)

    @property
    def xy(self):
        return [self.ll, self.ur]

    @xy.setter
    def xy(self, coordinates):
        self.ll = coordinates[0]
        self.ur = coordinates[1]

    @property
    def width(self) -> float:
        return self.get_dim('x')

    @property
    def height(self) -> float:
        return self.get_dim('y')

    @property
    def center(self) -> XY:
        return self.loc['c']

    """ Magic Methods """

    def __repr__(self):
        return 'Rectangle(xy={!s}, layer={}, virtual={})'.format(self.xy, self.layer, self.virtual)

    def __str__(self):
        return '\tloc: {} \n\tlayer: {} \n\tvirtual: {}'.format(self.xy, self.layer, self.virtual)

    """ Utility Methods """

    def export_locations(self):
        return self.loc

    def update_dict(self):
        """ Updates the location dictionary based on the current ll and ur coordinates """
        self.loc = {
            'll': self.ll,
            'ur': self.ur,
            'ul': XY([self.ll.x, self.ur.y]),
            'lr': XY([self.ur.x, self.ll.y]),
            'l': self.ll.x,
            'r': self.ur.x,
            't': self.ur.y,
            'b': self.ll.y,
            'cl': XY([self.ll.x, .5 * (self.ur.y + self.ll.y)]),
            'cr': XY([self.ur.x, .5 * (self.ur.y + self.ll.y)]),
            'ct': XY([.5 * (self.ll.x + self.ur.x), self.ur.y]),
            'cb': XY([.5 * (self.ll.x + self.ur.x), self.ll.y]),
            'c': XY([.5 * (self.ll.x + self.ur.x), .5 * (self.ur.y + self.ll.y)])
        }

    def set_dim(self, dim: str, size: float) -> 'Rectangle':
        """ Sets either the width or height of the rect to desired value. Maintains center location of rect """
        if dim == 'x':
            self.ll.x = self.loc['cb'].x - (.5 * size)
            self.ur.x = self.loc['ct'].x + (.5 * size)
        elif dim == 'y':
            self.ll.y = self.loc['cl'].y - (.5 * size)
            self.ur.y = self.loc['cr'].y + (.5 * size)
        elif dim == 'xy':
            self.ll.x = self.loc['cb'].x - (.5 * size)
            self.ur.x = self.loc['ct'].x + (.5 * size)
            self.ll.y = self.loc['cl'].y - (.5 * size)
            self.ur.y = self.loc['cr'].y + (.5 * size)
        else:
            raise ValueError('target_dim must be either x or y')
        # Update rectangle locations
        self.update_dict()
        return self

    def get_dim(self, dim):
        """ Returns measurement of the dimension of the rectangle """
        if dim == 'x':
            return abs(self.loc['l'] - self.loc['r'])
        elif dim == 'y':
            return abs(self.loc['t'] - self.loc['b'])
        else:
            raise ValueError('Provided dimension is not valid')

    def scale(self, size, dim=None) -> 'Rectangle':
        """ Additvely resizes the rectangle by the provided size """
        if dim == 'x':
            self.set_dim('x', self.get_dim('x') + size)
        elif dim == 'y':
            self.set_dim('y', self.get_dim('y') + size)
        else:
            self.set_dim('x', self.get_dim('x') + size)
            self.set_dim('y', self.get_dim('y') + size)
        return self

    def align(self,
              target_handle: str,
              ref_rect: 'Rectangle' = None,
              ref_handle: str = None,
              track=None,
              align_opt: Tuple[bool, bool] = (True, True),
              offset: coord_type = (0, 0)
              ) -> 'Rectangle':
        """ Moves the rectangle to co-locate the target and ref handles """
        if track is not None:
            # If a track is provided, calculate difference in dimension of track
            if track.x != 0:
                diffx = self.loc[target_handle].x - (track.x - offset[0])
            else:
                diffx = 0
            if track.y != 0:
                diffy = self.loc[target_handle].y - (track.y - offset[1])
            else:
                diffy = 0

        elif (ref_rect is None) and (ref_handle is None):
            # If no reference rectangle/handle is given
            if target_handle in self.loc:
                diffx = self.loc[target_handle].x - offset[0]
                diffy = self.loc[target_handle].y - offset[1]

        elif (target_handle in self.loc) and (ref_handle in ref_rect.loc):
            # If a reference rectangle and handles are given
            if (target_handle in self.edges) and (ref_handle in self.edges):
                # If we're provided with edges instead of vertices
                if (target_handle in self.v_edges) and (ref_handle in self.v_edges):
                    # If both handles are vertical edges
                    diffx = 0
                    diffy = self.loc[target_handle] - (ref_rect.loc[ref_handle] + offset[1])
                elif (target_handle in self.h_edges) and (ref_handle in self.h_edges):
                    # If both handles are horizontal edges
                    diffx = self.loc[target_handle] - (ref_rect.loc[ref_handle] + offset[0])
                    diffy = 0
                else:
                    raise ValueError('{} and {} must both be edge handles to support edge alignment'.
                                     format(target_handle, ref_handle))
            else:
                # Compute difference in location
                diffx = self.loc[target_handle].x - (ref_rect.loc[ref_handle].x + offset[0])
                diffy = self.loc[target_handle].y - (ref_rect.loc[ref_handle].y + offset[1])
        else:
            raise ValueError('Arguments do not specify a valid align operation')

        # Shift ll and ur locations to co-locate handles, unless align_opt is false
        if align_opt[0] or (align_opt is None):
            self.ll.x -= diffx
            self.ur.x -= diffx
        if align_opt[1] or (align_opt is None):
            self.ll.y -= diffy
            self.ur.y -= diffy
        # Update rectangle locations
        self.update_dict()
        return self

    def stretch(self,
                target_handle,  # type: str
                ref_rect=None,
                ref_handle=None,  # type: str
                track=None,
                stretch_opt=(True, True),  # type: Tuple[bool, bool]
                offset=(0, 0)  # type: Tuple[float, float]
                ) -> 'Rectangle':
        """
        Stretches rectangle to co-locate the target and ref handles. If ref handles are not provided,
        stretch by given offset
        """

        if track is not None:
            # If a track is provided, calculate difference only in dimension of track
            if track.x != 0:
                diff_width = self.loc[target_handle].x - (track.x - offset[0])
            else:
                diff_width = 0
            if track.y != 0:
                diff_height = self.loc[target_handle].y - (track.y - offset[1])
            else:
                diff_height = 0

        elif (ref_rect is None) and (ref_handle is None):
            # If no reference rect/handle is provided, stretch the target rect by provided offset
            if target_handle in self.loc:
                # Check that the handle is valid
                diff_width = self.loc[target_handle].x - offset[0]
                diff_height = self.loc[target_handle].y - offset[1]
                # First align the two points
                self.align(target_handle, align_opt=stretch_opt, offset=offset)
            else:
                raise ValueError('target handle is invalid')

        elif (target_handle in self.loc) and (ref_handle in ref_rect.loc):
            # If a reference rect and handles are given
            if (target_handle in self.edges) and (ref_handle in self.edges):
                # If we're provided with edges instead of vertices
                if (target_handle in self.v_edges) and (ref_handle in self.v_edges):
                    # If both handles are vertical edges
                    diff_width = 0
                    diff_height = self.loc[target_handle] - (ref_rect.loc[ref_handle] + offset[1])
                elif (target_handle in self.h_edges) and (ref_handle in self.h_edges):
                    # If both handles are horizontal edges
                    diff_width = self.loc[target_handle] - (ref_rect.loc[ref_handle] + offset[0])
                    diff_height = 0
                else:
                    raise ValueError('{} and {} must both be edge handles of same dimension to support edge alignment'.
                                     format(target_handle, ref_handle))
                self.align(target_handle, ref_rect, ref_handle, align_opt=stretch_opt, offset=offset)
            else:
                diff_width = self.loc[target_handle].x - (ref_rect.loc[ref_handle].x + offset[0])
                diff_height = self.loc[target_handle].y - (ref_rect.loc[ref_handle].y + offset[1])
                # First align the two points
                self.align(target_handle, ref_rect, ref_handle, align_opt=stretch_opt, offset=offset)
        else:
            raise ValueError('Arguments do not specify a valid stretch operation')

        # Shift ll and ur locations to co-locate handles, unless stretch_opt is false
        # Stretch width of rectangle
        if target_handle == 'll' or target_handle == 'ul' or target_handle == 'cl' or target_handle == 'l':
            if stretch_opt[0]:
                self.ur.x += diff_width
        elif target_handle == 'lr' or target_handle == 'ur' or target_handle == 'cr' or target_handle == 'r':
            if stretch_opt[0]:
                self.ll.x += diff_width
        elif target_handle == 'c' or target_handle == 'ct' or target_handle == 'cb':
            if stretch_opt[0]:
                self.ll.x += .5 * diff_width
                self.ur.x += .5 * diff_width

        # Stretch height of rectangle
        if target_handle == 'll' or target_handle == 'lr' or target_handle == 'cb' or target_handle == 'b':
            if stretch_opt[1]:
                self.ur.y += diff_height
        elif target_handle == 'ul' or target_handle == 'ur' or target_handle == 'ct' or target_handle == 't':
            if stretch_opt[1]:
                self.ll.y += diff_height
        elif target_handle == 'c' or target_handle == 'cl' or target_handle == 'cr':
            if stretch_opt[1]:
                self.ll.y += .5 * diff_height
                self.ur.y += .5 * diff_height

        # Update rectangle locations
        self.update_dict()
        return self

    def shift_origin(self, origin=(0, 0), orient='R0', virtual=True) -> 'Rectangle':
        """
        Takes xy coordinates and rotation, returns a virtual Rect2 that is re-referenced to the new origin
        Assumes that the origin of the rectangle is (0, 0)
        """
        # Apply the transformation to the xy coordinates that describe the rectangle
        new_xy = [0, 0]
        new_xy[0] = self.ll.shift_origin(origin, orient)
        new_xy[1] = self.ur.shift_origin(origin, orient)

        # Depending on the transformation, ll and ur may describe different rect corner
        if orient is 'MX':
            handle0 = 'ul'
            handle1 = 'lr'
        elif orient is 'MY':
            handle0 = 'lr'
            handle1 = 'ul'
        elif orient is 'R180':
            handle0 = 'ur'
            handle1 = 'll'
        else:
            handle0 = 'll'
            handle1 = 'ur'

        # Return the new shifted rectangle created from dictionary
        rect_dict = {
            'handle0': handle0,
            'handle1': handle1,
            'xy0': new_xy[0],
            'xy1': new_xy[1],
            'virtual': virtual,
            'layer': self.layer
        }
        return Rectangle.from_dict(rect_dict)

    def to_bbox(self) -> BBox:
        return BBox(self.ll.x, self.ll.y, self.ur.x, self.ur.y, self._res)

    def copy(self, virtual=False, layer=None) -> 'Rectangle':
        if layer is None:
            layer = self.layer
        return Rectangle(self.xy, layer, virtual=virtual)

    def get_overlap(self,
                    rect: 'Rectangle',
                    virtual: bool = True
                    ) -> 'Rectangle':
        """ Returns a rectangle corresponding to the overlapped region between two rectangles """

        # Determine bounds of the intersection in x dimension
        x_min = max(self.ll.x, rect.ll.x)
        x_max = min(self.ur.x, rect.ur.x)

        # Determine bounds of the intersection in y dimension
        y_min = max(self.ll.y, rect.ll.y)
        y_max = min(self.ur.y, rect.ur.y)

        # Throw exception if the rectangles don't overlap
        if x_min > x_max:
            print(self)
            print(rect)
            print('x_min: {}'.format(x_min))
            print('x_max: {}'.format(x_max))
            raise ValueError('Given rectangles do not overlap in x direction')
        if y_min > y_max:
            print(self)
            print(rect)
            print('y_min: {}'.format(y_min))
            print('y_max: {}'.format(y_max))
            raise ValueError('Given rectangles do not overlap in y direction')

        return Rectangle([[x_min, y_min],
                          [x_max, y_max]],
                         layer=self.layer,
                         virtual=virtual)

    def get_enclosure(self,
                      rect: 'Rectangle',
                      virtual: bool = True
                      ) -> 'Rectangle':
        """  Returns a rectangle that encloses all provided rectangles """

        ll = [min(self.ll.x, rect.ll.x), min(self.ll.y, rect.ll.y)]
        ur = [max(self.ur.x, rect.ur.x), max(self.ur.y, rect.ur.y)]
        return Rectangle(xy=[ll, ur], layer=self.get_highest_layer(rect), virtual=virtual)

    def get_highest_layer(self,
                          rect: 'Rectangle'
                          ) -> str:
        """ Returns the highest layer used by provided rectangles """

        pathname = 'ACG_GF45RFSOI/tech/GF45RFSOI_metal.yaml'  # TODO: Remove absolute file reference
        layerstack = bag.core._parse_yaml_file(pathname)['layerstack']  # TODO: Access layerstack from bag tech

        # Check for non-routing layers and return the highest routing layer
        # TODO: Clean up this logic to deal with non-routing layers
        if (self.layer not in layerstack) and (rect.layer not in layerstack):
            raise ValueError('both {} and {} are not valid routing layers, and cannot be ordered')
        elif self.layer not in layerstack:
            return rect.layer
        elif rect.layer not in layerstack:
            return self.layer

        i1 = layerstack.index(self.layer)
        i2 = layerstack.index(rect.layer)
        if i2 > i1:
            return rect.layer
        else:
            return self.layer
