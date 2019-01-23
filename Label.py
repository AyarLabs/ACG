# Python imports
import numpy as np
# ACG imports
from ACG.VirtualObj import VirtualObj
from ACG.PrimitiveUtil import Mt
from ACG.XY import XY
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ACG.Rectangle import Rectangle


class Label(VirtualObj):
    """
    Primitive class to describe a label on xy plane and various associated utility functions
    Keeps all coordinates on the grid
    """

    def __init__(self,
                 name,
                 layer,
                 xy,
                 res=.001  # type: float
                 ):

        VirtualObj.__init__(self)
        # Set the resolution of the grid
        self._res = res
        self._xy = XY(xy)
        self._name = name
        self._layer = layer

    @property
    def xy(self):
        return self._xy

    @property
    def x(self):
        return self._xy.x

    @property
    def y(self):
        return self._xy.y

    @property
    def name(self):
        return self._name

    @property
    def layer(self):
        return self._layer

    """ Utility Functions """

    def contained_by(self, rect: "Rectangle") -> bool:
        """
        Determines whether or not this label is contained by the provided rectangle. This is useful
        when trying to associate labels with drawn metals

        Parameters
        ----------
        rect : Rectangle
            Rectangle to check for enclosure

        Returns
        -------
        contained : bool
            True if the label and rectangle overlap
        """
        # Check that we are in between the left and right edges
        if self.x > rect.loc['l'] and self.x < rect.loc['r']:
            # Then check that we are in between the top and bottom edges
            if self.y > rect.loc['b'] and self.y < rect.loc['t']:
                return True
        else:
            return False

    def export_locations(self):
        """ For now just returns a dict of the coordinates """
        return {
            'x': [self.x],
            'y': [self.y]
        }

    def shift_origin(self, origin=(0, 0), orient='R0'):
        transform = Mt(orient)  # Convert the rotation string to a matrix transformation
        # Apply the transformation to the coordinate
        new_xy = np.transpose(np.matmul(transform, np.transpose(np.asarray(self.xy))))
        # Convert to XY coordinates and return shifted coordinate
        return XY(new_xy) + XY(origin)
