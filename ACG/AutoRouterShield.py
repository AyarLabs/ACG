from .AyarLayoutGenerator import AyarLayoutGenerator
from .Rectangle import Rectangle
from .XY import XY
from typing import Tuple, Union, Optional, List, Dict
from .AutoRouter import EZRouter
import heapq


class EZRouterShield(EZRouter):
    """
    The EZRouterShield class inherits from the EZRouter class and allows you to create ground-shielded routes.
    """

    # TODO: change tuples to XY to avoid rounding issues. Using XY creates key errors with self.route_point_dict.

    def __init__(self,
                 gen_cls: AyarLayoutGenerator,
                 start_rect: Optional[Rectangle] = None,
                 start_direction: Optional[str] = None,
                 config: Optional[dict] = None
                 ):
        EZRouter.__init__(self, gen_cls, start_rect=start_rect, start_direction=start_direction, config=config)


    def draw_straight_route_shield(self,
                                   loc: Union[Tuple[float, float], XY],
                                   perpendicular_pitch: float,
                                   parallel_spacing: float,
                                   shield_layers: list,
                                   width: Optional[float] = None
                                   ) -> 'EZRouter':
        """
        Routes a straight, shielded metal line from the current location of specified
        length. This method does not change the current routing direction.

        Note: This method relies on the fact that stretching a rectangle with an offset
        but without a reference rectangle uses the offset as an absolute reference loc

        Parameters
        ----------
        loc : Optional[Tuple[float, float]]
            XY location to route to. This method will only route in the current direction
        perpendicular_pitch : float
            The pitch between the perpendicular shielding stripes
        parallel_spacing : float
            The pitch between the parallel shields
        shield_layers : list
            A list of layers to route perpendicular shields on
        width : Optional[float]
            Draws the new route segment with this width if provided

        Returns
        -------
        self : EZRouter
            Return self to make it easy to cascade connections
        """
        if not self.current_rect or not self.current_handle or not self.current_dir:
            raise ValueError('Router has not been initialized, please call new_route()')

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
        self.loc['rect_list'].append(new_rect)
        self.current_rect = new_rect
        self.current_rect.stretch(target_handle=self.current_handle,
                                  offset=loc,
                                  stretch_opt=stretch_opt)

        # Create parallel shields
        rect_1 = self.gen.add_rect(layer=self.current_rect.layer)
        rect_2 = self.gen.add_rect(layer=self.current_rect.layer)

        # If horizontal route
        if self.current_handle[1] in ['r', 'l']:
            rect_1.align('ll', new_rect, 'ul', offset=(0, parallel_spacing))
            rect_2.align('ul', new_rect, 'll', offset=(0, -parallel_spacing))
            rect_1.set_dim('y', width)
            rect_2.set_dim('y', width)
            dir = 'r'
            length = new_rect.ur.x - new_rect.ll.x
        # If vertical route
        else:
            rect_1.align('lr', new_rect, 'll', offset=(-parallel_spacing, 0))
            rect_2.align('ll', new_rect, 'lr', offset=(parallel_spacing, 0))
            rect_1.set_dim('x', width)
            rect_2.set_dim('x', width)
            dir = 't'
            length = new_rect.ur.y - new_rect.ll.y

        rect_1.stretch(dir, new_rect, dir)
        rect_2.stretch(dir, new_rect, dir)

        # Create perpendicular shields

        for layer in shield_layers:
            perpendicular_stripes = []
            i = 0

            while (i + 1) * width + i * perpendicular_pitch < length:
                g_temp = self.gen.add_rect(layer)
                if dir == 'r':
                    g_temp.set_dim('x', width)
                    g_temp.align('ul', rect_1, 'ul', offset=((width + perpendicular_pitch) * i, 0))
                    g_temp.stretch('b', rect_2, 'b')
                else:
                    g_temp.set_dim('y', width)
                    g_temp.align('ll', rect_1, 'll', offset=(0, (width + perpendicular_pitch) * i))
                    g_temp.stretch('r', rect_2, 'r')
                self.gen.connect_wires(g_temp, rect_1)
                self.gen.connect_wires(g_temp, rect_2)
                perpendicular_stripes.append(g_temp)
                i += 1

        return self

    def cardinal_router_shield(self,
                               start_layer: str,
                               perpendicular_pitch: float,
                               parallel_spacing: float,
                               start_width: float,
                               start_pt: Tuple,
                               shield_layers: list,
                               start_dir: str = '+x',
                               enc_style: str = 'uniform',
                               prim: bool = False
                               ):
        """
        Creates a shielded route network that contains all the points added by add_route_points.

        Notes
        -----
        * Calls new_route_from_location for the user -- no need to call it beforehand.

        Parameters
        ----------
        start_layer : str
            The layer to start routing on
        perpendicular_pitch : float
            The pitch between the perpendicular shielding stripes
        parallel_spacing : float
            The pitch between the parallel shields
        start_width : float
            The width to start routing with
        start_pt : Tuple
            The point to start routing from
        shield_layers : list
            A list of layers to route perpendicular shields on
        start_dir : str = '+x'
            The direction to start routing in
        enc_style : str
            Via enclosure style to use
        prim ; bool
            True to use primitive vias, False not to

        Returns
        -------
        self : WgRouter
            returns itself so that route segments can be easily chained together
        """
        points = self.route_points
        self.new_route_from_location(start_pt, start_dir, start_layer, start_width)
        self.route_point_dict[start_pt] = start_width

        # Route the signal
        self.cardinal_router(enc_style=enc_style, prim=prim)
        manh = self.manhattanize_point_list(start_dir, (start_pt, start_layer), points)

        # Create and route routing networks for shields
        router1, _, _ = self.cardinal_helper(self, manh, start_pt, start_dir, start_layer, parallel_spacing)
        router2, _, _ = self.cardinal_helper(self, manh, start_pt, start_dir, start_layer, -parallel_spacing)

        router1.cardinal_router(enc_style=enc_style, prim=prim)
        router2.cardinal_router(enc_style=enc_style, prim=prim)

        # Find all parallel shield pairs to be connected by perpendicular shields ignoring rectangles created for vias
        max_w = max(self.route_point_dict.values())

        router1_rects = [i for i in router1.loc['rect_list'][1:] if
             round(i.ur.x - i.ll.x, 3) > max_w or round(i.ur.y - i.ll.y, 3) > max_w]
        router2_rects = [i for i in router2.loc['rect_list'][1:] if
             round(i.ur.x - i.ll.x, 3) > max_w or round(i.ur.y - i.ll.y, 3) > max_w]

        shield_pairs = list(zip(router1_rects, router2_rects))

        # Iterate over each pair of shields
        for i in range(len(shield_pairs)):
            rect_1 = shield_pairs[i][0]
            rect_2 = shield_pairs[i][1]
            rects = [rect_1, rect_2]

            # If horizontal trace
            if rect_1.ur.x - rect_1.ll.x > rect_1.ur.y - rect_1.ll.y:
                top = max(rects, key=lambda x: x.ur.y)
                bottom = min(rects, key=lambda x: x.ll.y)
                right = min(rects, key=lambda x: x.ur.x)
                start = top.ll.x

                # Iterate over length of shield traces to add perpendicular traces at the given pitch
                j = 0
                width = self.route_point_dict[tuple(manh[i + 1][0])]
                while start + (j + 1) * width + j * perpendicular_pitch + 1 < right.ur.x:
                    g_temp = self.gen.add_rect(shield_layers[0], virtual=True)

                    # Align trace with top shield and stretch to bottom shield if it overlaps with both shields
                    g_temp.set_dim('x', width)
                    g_temp.align('ul', top, 'ul', offset=((width + perpendicular_pitch) * j + .5, 0))
                    g_temp.stretch('b', bottom, 'b')

                    if Rectangle.overlap(g_temp, top) and Rectangle.overlap(g_temp, bottom):
                        for layer in shield_layers:
                            g_temp = self.gen.copy_rect(g_temp, virtual=False, layer=layer)
                            self.gen.connect_wires(g_temp, rect_1)
                            self.gen.connect_wires(g_temp, rect_2)

                    j += 1

            # If vertical trace
            else:
                top = min(rects, key=lambda x: x.ur.y)
                left = min(rects, key=lambda x: x.ll.x)
                right = max(rects, key=lambda x: x.ur.x)

                start = left.ll.y

                # Iterate over length of shield traces to add perpendicular traces at the given pitch
                j = 0
                width = self.route_point_dict[tuple(manh[i + 1][0])]
                while start + (j + 1) * width + j * perpendicular_pitch + 1 < top.ur.y:
                    g_temp = self.gen.add_rect(shield_layers[0], virtual=True)

                    # Align trace with left shield and stretch to right shield if it overlaps with both shields
                    g_temp.set_dim('y', width)
                    g_temp.align('ll', left, 'll', offset=(0, (width + perpendicular_pitch) * j + .5))
                    g_temp.stretch('r', right, 'r')

                    if Rectangle.overlap(g_temp, left) and Rectangle.overlap(g_temp, right):
                        for layer in shield_layers:
                            g_temp = self.gen.copy_rect(g_temp, virtual=False, layer=layer)
                            self.gen.connect_wires(g_temp, rect_1)
                            self.gen.connect_wires(g_temp, rect_2)

                    j += 1

        return self

    def diff_pair_router(self,
                         start_layer: str,
                         parallel_spacing: float,
                         start_width: float,
                         start_pt: Tuple,
                         start_dir: str = '+x',
                         enc_style: str = 'uniform',
                         prim: bool = False
                         ):
        """
        Creates a differential pair route network, assuming the points added by
        add_route_points correspond to the center of the differential pair.

        Parameters
        ----------
        start_layer : str
            The layer to start routing on
        parallel_spacing : float
            The pitch between the parallel shields
        start_width : float
            The width to start routing with
        start_pt : Tuple
            The point to start routing from
        start_dir : str = '+x'
            The direction to start routing in
        enc_style : str
            Via enclosure style to use
        prim : bool
            True to use primitive vias

        Returns
        -------
        self : WgRouter
            returns itself so that route segments can be easily chained together
        """
        points = self.route_points
        manh = self.manhattanize_point_list(start_dir, (start_pt, start_layer), points)
        self.route_point_dict[start_pt] = start_width

        # Include new route points created by manhattanize_point_list in route_point_dict
        for i in range(len(manh)):
            point = manh[i]
            if tuple(point[0]) not in self.route_point_dict:
                if i != 0:
                    self.route_point_dict[tuple(point[0])] = self.route_point_dict[tuple(manh[i - 1][0])]

        # Create and route routing networks for diff pair
        router1, _, _ = self.cardinal_helper(self, manh, start_pt, start_dir, start_layer, parallel_spacing / 2)
        router2, _, _ = self.cardinal_helper(self, manh, start_pt, start_dir, start_layer, -parallel_spacing / 2)

        router1.cardinal_router(enc_style=enc_style, prim=prim)
        router2.cardinal_router(enc_style=enc_style, prim=prim)

        return self

    def bus_router(self,
                   start_layer: str,
                   parallel_spacing: float,
                   bus_size: int,
                   start_width: float,
                   start_pt: Tuple,
                   start_dir: str = '+x',
                   enc_style: str = 'uniform',
                   prim: bool = False
                   ):
        """
        Creates a bus route network, assuming the points added by add_route_points correspond
        to the center of the bus route.

        Parameters
        ----------
        start_layer : str
            The layer to start routing on
        parallel_spacing : float
            The pitch between the parallel shields
        bus_size : int
            Size of bus (number of routes)
        start_width : float
            The width to start routing with
        start_pt : Tuple
            The point to start routing from
        start_dir : str = '+x'
            The direction to start routing in
        enc_style : str
            Via enclosure style to use
        prim : bool
            True to use primitive vias

        Returns
        -------
        self : WgRouter
            returns itself so that route segments can be easily chained together
        """
        # Manhattanize center path
        points = self.route_points
        manh = self.manhattanize_point_list(start_dir, (start_pt, start_layer), points)
        self.route_point_dict[start_pt] = start_width

        # Include new route points created by manhattanize_point_list in route_point_dict
        for i in range(len(manh)):
            point = manh[i]
            if tuple(point[0]) not in self.route_point_dict:
                if i != 0:
                    self.route_point_dict[tuple(point[0])] = self.route_point_dict[tuple(manh[i - 1][0])]

        # Calculate sequence of routing directions
        dirs = []

        for i in range(len(manh) - 1):
            pt0 = manh[i]
            pt1 = manh[i + 1]

            if pt0[0][0] > pt1[0][0]:
                dirs.append('-x')
            elif pt0[0][0] < pt1[0][0]:
                dirs.append('+x')
            elif pt0[0][1] > pt1[0][1]:
                dirs.append('-y')
            else:
                dirs.append('+y')

        top = (manh, self, start_pt)  # Current "topmost" shield
        bottom = (manh, self, start_pt)  # Current "bottommost" shield
        sign = 1  # Used to determine which side of center

        # If the bus width is odd, add a route in the center
        if bus_size % 2 == 1:
            self.new_route_from_location(start_pt, start_dir, start_layer, 0.5)
            self.cardinal_router(enc_style=enc_style, prim=prim)
            num_iters = bus_size - 1
        # If even bus width, the center is between two routes
        else:
            num_iters = bus_size

        # Determine initial offset direction of routes from center
        if start_pt[0] > manh[1][0][0]:
            start = (0, -1)
        elif start_pt[0] < manh[1][0][0]:
            start = (0, 1)
        elif start_pt[1] > manh[1][0][1]:
            start = (1, 0)
        else:
            start = (-1, 0)

        for j in range(num_iters):
            manh = top[0] if sign == 1 else bottom[0]
            router_temp = top[1] if sign == 1 else bottom[1]
            temp_start = top[2] if sign == 1 else bottom[2]

            # If the bus width is even, the distance from the first two routes from center is half the spacing
            if bus_size % 2 == 0 and (j == 0 or j == 1):
                spacing = parallel_spacing / 2
            # If odd bus width, the distance from the center route is the full spacing amount
            else:
                spacing = parallel_spacing

            # Create and route routing network for this signal
            router, manh, shield_start = self.cardinal_helper(router_temp, manh, temp_start, start_dir, start_layer, sign * spacing, dirs=dirs, start=start)

            # Update "topmost" and "bottommost" routes
            if sign == 1:
                top = (manh, router, shield_start[0])
            else:
                bottom = (manh, router, shield_start[0])

            router.cardinal_router(enc_style=enc_style, prim=prim)

            # Switch to opposite side of center
            sign = -sign

        return self

    def AStarRouter(self,
                    start : Union[Tuple[float, float], XY],
                    end : Union[Tuple[float, float], XY],
                    obstructions : List[Rectangle],
                    layer : str,
                    width : float
                    ):

        all_points = [start, end]

        for rectangle in obstructions:
            all_points.append(rectangle.ll)
            all_points.append(rectangle.ur)
            all_points.append(XY((rectangle.ll.x, rectangle.ur.y)))
            all_points.append(XY((rectangle.ur.x, rectangle.ll.y)))

        all_points = set(all_points)

        adj_mtx = {point: [] for point in all_points}

        for pointA in all_points:
            for pointB in all_points:
                if pointA != pointB and self.visible(pointA, pointB, obstructions) and pointA not in adj_mtx[pointB]:
                    adj_mtx[pointA].append(pointB)
                    adj_mtx[pointB].append(pointA)

        h = []

        curr_point = start

        edgeTo = {start: None}
        distTo = {start: 0}

        i = 0

        while curr_point != end:
            i += 1
            for adj_point in adj_mtx[curr_point]:
                heuristic = self.L1_dist(adj_point, end) + distTo[curr_point] + self.L1_dist(adj_point, curr_point)
                if adj_point not in distTo and adj_point != curr_point:
                    heapq.heappush(h, (float(heuristic), adj_point))
                    distTo[adj_point] = distTo[curr_point] + self.L1_dist(adj_point, curr_point)
                    edgeTo[adj_point] = curr_point

            if not h:
                raise RuntimeError("The provided endpoint is unreachable with the given obstructions")
            curr_point = heapq.heappop(h)[1]

        path = [curr_point]

        while curr_point != start:
            curr_point = edgeTo[curr_point]
            path.append(curr_point)

        path = path[::-1]

        offs = (path[1].x - path[0].x, path[1].y - path[0].y)

        if offs[0] > 0:
            start_dir = '+x'
        elif offs[0] < 0:
            start_dir = '-x'
        elif offs[1] > 0:
            start_dir = '+y'
        else:
            start_dir = '-y'

        self.new_route_from_location(start, start_dir, layer, width)
        self.route_point_dict[(start.x, start.y)] = width

        self.add_route_points(path[1:], layer)
        self.cardinal_router()

    def visible(self,
                A : XY,
                B : XY,
                rects : List[Rectangle]
                ):
        if A.x >= B.x and A.y >= B.y:
            ur = A
            ll = B
        elif A.x <= B.x and A.y <= B.y:
            ur = B
            ll = A
        elif A.x <= B.x and A.y >= B.y:
            ur = XY((B.x, A.y))
            ll = XY((A.x, B.y))
        else:
            ll = XY((B.x, A.y))
            ur = XY((A.x, B.y))
        for rect in rects:
            if Rectangle.overlap(rect, Rectangle((ll, ur), '')):
                return False
        return True

    def L1_dist(self,
                pt1 : XY,
                pt2 : XY
                ):
        return abs(pt2.y - pt1.y) + abs(pt2.x - pt1.x)
