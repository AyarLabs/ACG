from .AyarLayoutGenerator import AyarLayoutGenerator
from .Rectangle import Rectangle
from .Via import Via
from .XY import XY

from typing import Tuple


class AutoRouter:
    """
    The Autorouter class provides a number of methods to automatically generate simple wire routes in ACG
    """

    def __init__(self, gen_cls: AyarLayoutGenerator):
        """
        Expects an ACG layout generator as input. This generator class has its shape creation methods called after the
        route is completed

        Parameters
        ----------
        gen_cls : AyarLayoutGenerator
            Layout generator class that this Autorouter will be drawing in
        """
        self.gen = gen_cls
        self.tech = self.gen.tech

    def stretch_l_route(self,
                        start_rect: Rectangle,
                        start_dir: str,
                        end_rect: Rectangle,
                        via_size: Tuple[int, int] = (None, None)
                        ):
        """
        This method takes a starting rectangle and an ending rectangle and automatically routes an L between them

        Parameters
        ----------
        start_rect : Rectangle
            The location where the route will be started
        start_dir : str
            'x' or 'y' for the direction the first segment in the l route will traverse
        end_rect : Rectangle
            The location where the route will be ended
        via_size : Tuple[int, int]
            Overrides the array size of the via to be placed.

        Returns
        -------
        route : Route
            The created route object containing all of the rects and vias
        """
        if via_size != (None, None):
            print('WARNING, explicit via size is not yet supported')

        rect1 = self.gen.copy_rect(start_rect)
        rect2 = self.gen.copy_rect(end_rect)
        if start_dir == 'y':
            if rect2['t'] > rect1['t']:
                rect1.stretch('t', ref_rect=rect2, ref_handle='t')
                if rect2['c'].x > rect1['c'].x:
                    rect2.stretch('l', ref_rect=rect1, ref_handle='l')
                else:
                    rect2.stretch('r', ref_rect=rect1, ref_handle='r')
            else:
                rect1.stretch('b', ref_rect=rect2, ref_handle='b')
                if rect2['c'].x > rect1['c'].x:
                    rect2.stretch('l', ref_rect=rect1, ref_handle='l')
                else:
                    rect2.stretch('r', ref_rect=rect1, ref_handle='r')
        else:
            if rect2['r'] > rect1['r']:
                rect1.stretch('r', ref_rect=rect2, ref_handle='r')
                if rect2['c'].y > rect1['c'].y:
                    rect2.stretch('b', ref_rect=rect1, ref_handle='b')
                else:
                    rect2.stretch('t', ref_rect=rect1, ref_handle='t')
            else:
                rect1.stretch('l', ref_rect=rect2, ref_handle='l')
                if rect2['c'].y > rect1['c'].y:
                    rect2.stretch('b', ref_rect=rect1, ref_handle='b')
                else:
                    rect2.stretch('t', ref_rect=rect1, ref_handle='t')
        self.gen.connect_wires(rect1=rect1, rect2=rect2, size=via_size)


class Route:
    """
    This class contains a list of rectangles and vias which describe a continuous route from one location to another.
    Also contains convenience methods to modify the shape of the route
    """

    def __init__(self,
                 gen_cls: AyarLayoutGenerator,
                 start_loc: XY,
                 start_dir: str,
                 start_rect: Rectangle = None,
                 ):
        self.gen = gen_cls  # Class where we will be drawing the route
        self.route_list = []  # Contains the full list of rects and vias

        # Pointers to route in progress
        self.current_rect = start_rect  # Contains the current rectangle being routed
        self.current_dir = start_dir  # direction that the current rectangle is routing in
        self.current_loc = start_loc  # pointer to the center location of the current route

    def add_via(self, target_layer: str):
        """
        Places a via at the current location from the current rect's layer to the target_layer

        Parameters
        ----------
        target_layer: str
            the ending metal layer of the via stack
        """
        pass

    def straight_route(self,
                       location: XY,
                       width: float = None,
                       direction: str = None
                       ) -> None:
        """
        Stretches the current route to move the provided location in a single direction

        Parameters
        ----------
        location : XY
            Location that the new route will be routed to
        width : float
            Width of the metal in microns. If None, defaults to the current rectangles width
        direction : str
            'x' or 'y' for which direction the current rectangle will be stretched. If None, defaults to the current
            direction
        """
        if direction is None:
            direction = self.current_dir
        if width is None:
            if direction == 'x':
                width = self.current_rect.get_dim('y')
            if direction == 'y':
                width = self.current_rect.get_dim('x')

        seg, end = self.draw_path_segment(start=self.current_loc,
                                          layer=self.current_rect.layer,
                                          width=width,
                                          direction=direction,
                                          end=location)
        print(seg, end)
        self.update_route_pointer(seg, end)

    def update_route_pointer(self, rect: Rectangle, loc: XY) -> None:
        self.route_list.append(rect)
        self.current_rect = rect
        self.current_loc = loc

    def draw_path_segment(self,
                          start: XY,
                          layer: str,
                          width: float,
                          direction: str,
                          end: XY
                          ) -> Tuple[Rectangle, XY]:
        """
        This method manually draws the specified rectangle. This method does not place vias. If the end and start coords
        do not share an x or y coordinate, the path is only drawn in the provided direction.

        Parameters
        ----------
        start : XY
            starting location of the path segment
        layer : str
            layer for the rectangle to be drawn
        width : float
            width of the route perpendicular to its direction
        direction : str
            direction in which the route will be drawn
        end : XY
            ending location of the path segment
        """
        seg = self.gen.add_rect(layer=layer)  # Create a new rectangle

        # Set the size of the rectangle and align it to the starting point
        if direction == 'x':
            seg.set_dim(dim='x', size=abs(end.x - start.x))
            seg.set_dim(dim='y', size=width)
            if end.x > start.x:
                seg.align(target_handle='cl', offset=start)
                end_loc = seg['cr']
            else:
                seg.align(target_handle='cr', offset=start)
                end_loc = seg['cl']
        else:
            seg.set_dim(dim='x', size=width)
            seg.set_dim(dim='y', size=abs(end.y - start.y))
            if end.y > start.y:
                seg.align(target_handle='cb', offset=start)
                end_loc = seg['ct']
            else:
                seg.align(target_handle='ct', offset=start)
                end_loc = seg['cb']
        return seg, end_loc
