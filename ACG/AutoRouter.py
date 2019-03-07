from .AyarLayoutGenerator import AyarLayoutGenerator
from .Rectangle import Rectangle
from .XY import XY
from .tech import tech_info
from typing import Tuple, Union, Optional, List


class AutoRouter:
    """
    The Autorouter class provides a number of methods to automatically generate simple wire routes in ACG
    """

    def __init__(self,
                 gen_cls: AyarLayoutGenerator,
                 start_rect: Rectangle,
                 start_direction: str,
                 config: Optional[dict] = None
                 ):
        """
        Expects an ACG layout generator as input. This generator class has its shape creation methods called after the
        route is completed

        Parameters
        ----------
        gen_cls : AyarLayoutGenerator
            Layout generator class that this Autorouter will be drawing in
        start_rect : Rectangle
            The rectangle we will be starting the route from
        start_direction : str
            '+x', '-x', '+y', '-y' for the direction the route will start from
        config : dict
            dictionary of configuration variables that will set router defaults
        """
        # Init generator and tech information
        self.gen: AyarLayoutGenerator = gen_cls
        self.tech = self.gen.tech
        self.config = tech_info['metal_tech']['router']
        if config:
            self.config.update(config)  # Update the default settings with your own

        # State variables for where the route will be going
        self.current_rect = self.gen.copy_rect(start_rect, virtual=False)
        self.current_dir = start_direction
        self.current_handle: str = ''
        self.layer = start_rect.layer

        # Set the current rectangle handle based on the starting direction
        self._set_handle_from_dir(direction=start_direction)

        # Location dictionary to store the running components in the route
        self.loc = dict(
            route_list=[self.current_rect],
            rect_list=[self.current_rect],
            via_list=[],
        )

    def draw_straight_route(self,
                            loc: Union[Tuple[float, float], XY],
                            width: Optional[float] = None
                            ) -> 'AutoRouter':
        """
        Routes a straight metal line from the current location of specified length. This
        method does not change the current routing direction.

        Note: This method relies on the fact that stretching a rectangle with an offset
        but without a reference rectangle uses the offset as an absolute reference loc

        Parameters
        ----------
        loc : Optional[Tuple[float, float]]
            XY location to route to. This method will only route in the current direction
        width : Optional[float]
            Draws the new route segment with this width if provided

        Returns
        -------
        self : AutoRouter
            Return self to make it easy to cascade connections
        """
        # Make a new rectangle and align it to the current route location
        new_rect = self.gen.add_rect(layer=self.current_rect.layer)

        # Size the new rectangle to match the current route width
        if self.current_dir == '+x' or self.current_dir == '-x':
            if width:
                new_rect.set_dim('y', width)
            else:
                new_rect.set_dim('y', self.current_rect.get_dim('y'))
            stretch_opt = (True, False)
            if self.current_dir == '+x':
                new_rect.align('cl', ref_rect=self.current_rect, ref_handle=self.current_handle)
            else:
                new_rect.align('cr', ref_rect=self.current_rect, ref_handle=self.current_handle)
        else:
            if width:
                new_rect.set_dim('x', width)
            else:
                new_rect.set_dim('x', self.current_rect.get_dim('x'))
            stretch_opt = (False, True)
            if self.current_dir == '+y':
                new_rect.align('cb', ref_rect=self.current_rect, ref_handle=self.current_handle)
            else:
                new_rect.align('ct', ref_rect=self.current_rect, ref_handle=self.current_handle)

        # Update the current rectangle pointer and stretch it to the desired location
        self.current_rect = new_rect
        self.current_rect.stretch(target_handle=self.current_handle,
                                  offset=loc,
                                  stretch_opt=stretch_opt)
        return self

    def draw_via(self,
                 layer: Union[str, Tuple[str, str]],
                 direction: str,
                 out_width: float,
                 enc_style: str = 'uniform',
                 size: Optional[Tuple[int, int]] = None,
                 enc_bot: Optional[List[float]] = None,
                 enc_top: Optional[List[float]] = None,
                 ) -> 'AutoRouter':
        """
        This method adds a via at the current location to the user provided layer. Cannot
        move by more than one layer at a time

        This method will change the current rectangle and can change the current routing
        direction

        Parameters
        ----------
        layer : Union[str, Tuple[str, str]]
            layer or lpp of the metal to via up/down to
        direction : str
            '+x', '-x', '+y', '-y' for the direction the new route segment will start from
        out_width : Optional[float]
            width of the output wire to be drawn on the new metal layer
        enc_style : str
            'uniform' to draw uniform enclosures, 'asymm' to draw min size asymmetric enclosures
        size : Optional[Tuple[int, int]]
            number of vias to place in the array
        enc_bot : List[float]
            enclosure size of the left, right, top, bot edges of the bottom layer of the via
        enc_top : List[float]
            enclosure size of the left, right, top, bot edges of the top layer of the via

        Returns
        -------
        self : AutoRouter
            Return self to make it easy to cascade connections
        """
        # Create the new rectangle and align it to the end of the route
        new_rect = self.gen.add_rect(layer=layer)
        new_rect.align(target_handle='c',
                       ref_rect=self.current_rect,
                       ref_handle=self.current_handle)

        # Match the route width of the current route
        if self.current_dir == '+x' or self.current_dir == '-x':
            new_rect.set_dim('y', size=self.current_rect.get_dim('y'))
        else:
            new_rect.set_dim('x', size=self.current_rect.get_dim('x'))

        # Size the new rectangle to match the output width
        if direction == '+x' or direction == '-x':
            new_rect.set_dim('y', out_width)
        else:
            new_rect.set_dim('x', out_width)

        # If the provided layer is the same as the current layer, turn the route
        # Otherwise add a new via with the calculated enclosure rules
        if layer != self.current_rect.layer:
            # Add a new primitive via at the current location
            if self.current_rect.get_highest_layer(layer=layer) == self.current_rect.layer:
                via_id = 'V' + layer + '_' + self.current_rect.layer
            else:
                via_id = 'V' + self.current_rect.layer + '_' + layer
            via = self.gen.add_prim_via(via_id=via_id, rect=new_rect)

            # If we use asymmetric via enclosures, figure out which directions should
            # have what enclosure size
            if enc_style == 'asymm':
                # Determine whether the current route segment is on bottom or top
                # Allocate the default enc params to the corresponding layer
                if self.current_rect.get_highest_layer(layer=layer) == self.current_rect.layer:
                    default_enc = self.config['V' + layer + '_' + self.current_rect.layer]

                    # Set the enclosure for the current route segment
                    enc_large = default_enc['asymm_enclosure_large']
                    enc_small = default_enc['asymm_enclosure_small']
                    if self.current_dir == '+x' or self.current_dir == '-x':
                        via.set_enclosure(enc_top=[enc_large, enc_large, enc_small, enc_small])
                    else:
                        via.set_enclosure(enc_top=[enc_small, enc_small, enc_large, enc_large])

                    # Set the enclosure for the next route segment
                    enc_large = default_enc['asymm_enclosure_large']
                    enc_small = default_enc['asymm_enclosure_small']
                    if direction == '+x' or direction == '-x':
                        via.set_enclosure(enc_bot=[enc_large, enc_large, enc_small, enc_small])
                    else:
                        via.set_enclosure(enc_bot=[enc_small, enc_small, enc_large, enc_large])
                else:
                    default_enc = self.config['V' + self.current_rect.layer + '_' + layer]

                    # Set the enclosure for the current route segment
                    enc_large = default_enc['asymm_enclosure_large']
                    enc_small = default_enc['asymm_enclosure_small']
                    if self.current_dir == '+x' or self.current_dir == '-x':
                        via.set_enclosure(enc_bot=[enc_large, enc_large, enc_small, enc_small])
                    else:
                        via.set_enclosure(enc_bot=[enc_small, enc_small, enc_large, enc_large])

                    # Set the enclosure for the next route segment
                    enc_large = default_enc['asymm_enclosure_large']
                    enc_small = default_enc['asymm_enclosure_small']
                    if direction == '+x' or direction == '-x':
                        via.set_enclosure(enc_top=[enc_large, enc_large, enc_small, enc_small])
                    else:
                        via.set_enclosure(enc_top=[enc_small, enc_small, enc_large, enc_large])

            # Set via parameters
            if size is not None:
                via.size = size
            else:
                via.size = self.config[via_id]['size']
            if enc_bot is not None:
                via.set_enclosure(enc_bot=enc_bot)
            if enc_top is not None:
                via.set_enclosure(enc_top=enc_top)

        # Update the pointers for the current rect, handle, and direction
        self.current_rect = new_rect
        self.current_dir = direction
        self._set_handle_from_dir(direction)

        return self

    def draw_l_route(self,
                     loc: Union[Tuple[float, float], XY],
                     enc_style: str = 'uniform',
                     in_width: Optional[float] = None,
                     out_width: Optional[float] = None,
                     layer: Optional[Union[str, Tuple[str, str]]] = None,
                     enc_bot: Optional[List[float]] = None,
                     enc_top: Optional[List[float]] = None,
                     omit_final_segment: bool = False
                     ) -> 'AutoRouter':
        """
        Draws an L-route from the current location to the provided location while minimizing
        the number of turns.

        Parameters
        ----------
        loc : Union[Tuple[float, float], XY]
            Final location of the route
        enc_style : str
            'uniform' to draw uniform enclosures, 'asymm' to draw min size asymmetric enclosures
        in_width : Optional[float]
            If provided, will change the first route segment to the desired width
        out_width : Optional[float]
            If provided, will set the second segment of the l-route to match this width, otherwise
            will maintain the same width
        layer : Optional[Union[str, Tuple[str, str]]]
            If provided will draw the second segment of the l-route on this metal layer, otherwise
            will stay on the same layer
        enc_bot : Optional[List[float]]
            If provided, will use these enclosure settings for the bottom layer of the via
        enc_top : Optional[List[float]]
            If provided, will use these enclosure settings for the top layer of the via
        omit_final_segment : bool
            If true, will not draw the final straight route. This is useful when cascading l-routes

        Returns
        -------
        self : AutoRouter
            Return self to make it easy to cascade connections
        """
        # Draw the first straight route segment
        self.draw_straight_route(loc=loc, width=in_width)

        # Draw the via to turn the l-route
        # If layer is None, stay on the same layer
        if not layer:
            layer = self.current_rect.layer
        # If an output width is not provided, use the same as the current width
        if not out_width:
            if self.current_dir == '+x' or self.current_dir == '-x':
                out_width = self.current_rect.get_dim('y')
            else:
                out_width = self.current_rect.get_dim('x')
        # Determine the output direction
        if self.current_dir == '+x' or self.current_dir == '-x':
            if self.current_rect[self.current_handle].y < XY(loc).y:
                direction = '+y'
            else:
                direction = '-y'
        else:
            if self.current_rect[self.current_handle].x < XY(loc).x:
                direction = '+x'
            else:
                direction = '-x'
        self.draw_via(layer=layer,
                      direction=direction,
                      enc_style=enc_style,
                      out_width=out_width,
                      enc_top=enc_top,
                      enc_bot=enc_bot)

        # Draw the final straight route segment
        if not omit_final_segment:
            self.draw_straight_route(loc=loc)

        return self

    ''' Automatic routing methods '''

    def cardinal_router(self,
                        points: List[Tuple],
                        relative_coords: bool = False,
                        ):
        """
        Creates a route network that contains all provided points. Any required vias use the user provided

        Notes
        -----
        * This method forces the use of width and via parameters from the configuration dictionary
        * This method attempts to generate a manhattanized list of points that contains all of the user
        provided points while minimizing the number of times the direction of the route changes
        * Then a set of cascaded L-routes is created to connect all of the coordinates in the mahattanized point list

        Parameters
        ----------
        points : List[Tuple]
            List of (x, y, layer) points that the route will contain
        relative_coords : bool
            True if the list of coordinates are relative to the starting port's coordinate.
            False if the list of coordinates are absolute relative to the current Template's origin

        Returns
        -------
        self : WgRouter
            returns itself so that route segments can be easily chained together
        """
        current_dir = self.current_dir
        current_point = self.current_rect[self.current_handle]

        if relative_coords:
            # If passed coordinates are relative, need to add WgRouter's port location to convert to absolute coords
            x0, y0 = current_point
            points = [(x + x0, y + y0) for x, y in points]

        # Generate a manhattanized list of waypoints on the route while minimizing the number of required bends
        manh_point_list = self.manhattanize_point_list(initial_direction=current_dir,
                                                       initial_point=current_point,
                                                       points=points)
        # Simplify the point list so that each point corresponds with a bend of the route, i.e. no co-linear points
        final_point_list = self.reduce_point_list(manh_point_list)
        print(final_point_list)
        final_point_list = final_point_list[1:]  # Ignore the first pt, since it is co-incident with the starting port

        # Draw a series of L-routes to follow the final simplified point list
        for end_point in final_point_list[1:]:
            # Draw the L-route while omitting the final straight route so that another L-route can be appended to
            # it in the next for loop iteration
            self.draw_l_route(loc=end_point[0:2],
                              layer=end_point[2],
                              in_width=self.config[self.current_rect.layer]['width'],
                              out_width=self.config[self.current_rect.layer]['width'],
                              enc_style='asymm',
                              omit_final_segment=True)

        # The loop does not draw the final straight waveguide segment, so add it here
        self.draw_straight_route(manh_point_list[-1])

    @staticmethod
    def manhattanize_point_list(initial_direction, initial_point, points):
        """
        Manhattanizes a provided list of (x, y) points while minimizing the number of times the direction changes.
        Manhattanization ensures that every segment of the route only traverses either the x or y direction.

        Notes
        -----
        * Turn minimization is achieved in the following way: If the current direction is x, then the next point in
        the list will have dy = 0. If the current direction is y, then the next point in the list will have dx = 0
        * TODO: Fix layer allocation bugs

        Parameters
        ----------
        initial_direction : str
            The current routing direction which must be maintained in the first segment
        initial_point : Tuple
            (x, y) coordinate location where the route will begin
        points : List[Tuple[float, float]]
            List of coordinates which must also exist in the final manhattanized list

        Returns
        -------
        manh_point_list : List[Tuple[float, float]]
            A manhattanized point list
        """
        if initial_direction == '+x' or initial_direction == '-x':
            current_dir = 'x'
        else:
            current_dir = 'y'
        current_point = initial_point
        manh_point_list = [current_point]
        # Iteratively generate a manhattan point list from the user provided point list
        for next_point in points:
            dx, dy = (next_point[0] - current_point[0]), (next_point[1] - current_point[1])
            # If the upcoming point has a relative offset in both dimensions
            if dx != 0 and dy != 0:
                # Add an intermediate point
                if current_dir == 'x':
                    # First move in x direction then y
                    manh_point_list.append((current_point[0] + dx, current_point[1], next_point[2]))
                    manh_point_list.append((current_point[0] + dx, current_point[1] + dy, next_point[2]))
                    current_point = manh_point_list[-1]
                    current_dir = 'y'
                else:
                    # First move in y direction then x
                    manh_point_list.append((current_point[0], current_point[1] + dy, next_point[2]))
                    manh_point_list.append((current_point[0] + dx, current_point[1] + dy, next_point[2]))
                    current_point = manh_point_list[-1]
                    current_dir = 'x'
            # If the point does not move ignore it to avoid adding co-linear points
            elif dx == 0 and dy == 0:
                continue
            # If the next point only changes in one direction and it is not co-linear
            else:
                manh_point_list.append((current_point[0] + dx, current_point[1] + dy, current_point[2]))
                current_point = manh_point_list[-1]
                if dx == 0:
                    current_dir = 'y'
                else:
                    current_dir = 'x'
        return manh_point_list

    @staticmethod
    def reduce_point_list(points: List[Union[Tuple[float, float], XY]]):
        """
        Returns a new list with all co-linear points removed. This algorithm requires that the point list has already
        been manhattanized so that only dx or dy is 0 for any set of adjacent points. Redundant points must also have
        been removed.

        Notes
        -----
        * Create 3 pointers to locations on the point list: start, middle, end. Place them at the first three points
        in the list
        * Detect whether middle is co-linear with start and end by measuring the derivatives between the three points
        * If the derivatives are such that the points are not co-linear, add the middle point to the reduced point list
        * If the derivatives are such that the points are co-linear, do not add the middle point to the list
        * Increment all 3 pointers

        Parameters
        ----------
        points : List[coord_type]
            Input list of points outlining the route to be drawn

        Returns
        -------
        reduced_point_list : List[coord_type]
            Point list without co-linear or redundant points
        """
        reduced_point_list = list()
        reduced_point_list.append(points[0])  # Always start with the first point in the list

        # Initialize pointers to the first three elements in the list
        tot_length = len(points)
        start_pt = 0
        middle_pt = 1
        end_pt = 2

        while end_pt < tot_length:
            start = points[start_pt]
            middle = points[middle_pt]
            end = points[end_pt]

            # Compute start-middle and middle-end derivatives
            dx0, dy0 = (middle[0] - start[0]), (middle[1] - start[1])
            dx1, dy1 = (end[0] - middle[0]), (end[1] - middle[1])

            # Since the manhattanization routine ensures that either dx or dy is 0, but not both for all pairs of
            # adjacent points, co-linearity between 3 points can determined simply by checking if either dx is non-zero
            # for both pairs or dy is non-zero for both pairs
            if dx0 != 0 and dx1 != 0:
                colinear = True
            elif dy0 != 0 and dy1 != 0:
                colinear = True
            else:
                colinear = False

            # If not co-linear, add the middle point to the list
            if colinear is False:
                reduced_point_list.append(middle)

            # Increment pointers
            start_pt += 1
            middle_pt += 1
            end_pt += 1

        reduced_point_list.append(points[-1])  # Always finish with the last point in the list
        return reduced_point_list

    ''' Old Routing Methods to be Deprecated '''

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

    def _set_handle_from_dir(self, direction: str) -> None:
        """ Determines the current rectangle handle based on the provided routing direction """
        if direction == '+x':
            self.current_handle = 'cr'
        elif direction == '-x':
            self.current_handle = 'cl'
        elif direction == '+y':
            self.current_handle = 'ct'
        elif direction == '-y':
            self.current_handle = 'cb'
