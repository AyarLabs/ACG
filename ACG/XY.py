import numbers
import numpy as np
# ACG imports
from ACG.VirtualObj import VirtualObj
from ACG.PrimitiveUtil import Mt


class XY(VirtualObj):
    """
    Primitive class to describe a single coordinate on xy plane and various associated utility functions
    Keeps all coordinates on the grid
    """

    def __init__(self,
                 xy,
                 res=.001  # type: float
                 ):

        VirtualObj.__init__(self)
        # Set the resolution of the grid
        self._res = res
        # Create the internal x and y variable names
        self._x = None
        self._y = None

        # Perform input conditioning before storing data
        if isinstance(xy, XY):
            # Immediately copy the coordinates
            self.xy = xy
        elif len(xy) != 2:
            # If the provided value does not have 1 number for x and 1 for y
            raise ValueError('{}:{} does not have length 2'.format(type(xy), xy))
        elif all([isinstance(xy[0], numbers.Real), isinstance(xy[1], numbers.Real)]):
            # If the provided values contain real numbers, store them in xy
            self.xy = xy
        else:
            raise TypeError('{} type does not represent a valid xy coordinate description'.format(type(xy)))

    """ Magic methods """

    def __repr__(self):
        return 'XY([{}, {}])'.format(self.x, self.y)

    def __str__(self):
        return '[{}, {}]'.format(self.x, self.y)

    def __len__(self):
        return 2

    def __getitem__(self, item):
        """ Treat the xy coordinate as either an indexed array or dictionary when getting values"""
        if item == 0:
            return self.x
        elif item == 1:
            return self.y
        elif item == 'x':
            return self.x
        elif item == 'y':
            return self.y
        else:
            raise ValueError('{} is an invalid coordinate index'.format(item))

    def __setitem__(self, key, value):
        """ Treat the xy coordinate as either an indexed array or dictionary when setting values"""
        if key == 0:
            self.x = value
        elif key == 1:
            self.y = value
        elif key == 'x':
            self.x = value
        elif key == 'y':
            self.y = value
        else:
            raise ValueError('{} is an invalid coordinate index'.format(key))

    def __add__(self, other):
        """ Treats coordinates as vectors, performs vector addition """
        other_temp = XY(other)
        temp_x = self.x + other_temp.x
        temp_y = self.y + other_temp.y
        return XY([temp_x, temp_y])

    def __radd__(self, other):
        """ Just flip the order and add """
        return self.__add__(other)

    def __mul__(self, other):
        """ Performs element-wise product. If a scalar is given, scales coordinate vector """
        if isinstance(other, numbers.Real):
            return XY([self.x * other, self.y * other])
        else:
            temp = XY(other)
            return XY([self.x * temp.x, self.y * temp.y])

    def __rmul__(self, other):
        """ Just flip the order and multiply """
        return self.__mul__(other)

    def __sub__(self, other):
        """ Treats coordinates as vectors, performs subtraction """
        temp = XY(other)
        return self + (temp*-1)

    def __rsub__(self, other):
        """ Just flip the order and subtract """
        return -1*(self.__sub__(XY(other)))

    """ Getters and Setters """

    @property
    def x(self):
        return round(self._x * self._res, 3)

    @x.setter
    def x(self, value):
        temp = round(value / self._res)  # Find location of provided coordinate on grid
        self._x = int(temp)  # Force the coordinate to be an int

    @property
    def y(self):
        return round(self._y * self._res, 3)

    @y.setter
    def y(self, value):
        temp = round(value / self._res)  # Find location of provided coordinate on grid
        self._y = int(temp)  # Force the coordinate to be an int

    @property
    def xy(self):
        return [self.x, self.y]

    @xy.setter
    def xy(self, xy):
        self.x = xy[0]
        self.y = xy[1]

    """ Utility Functions """

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

    def __lt__(self, other):
        """Used to sort XY in min heap"""
        return self.x < other.x
