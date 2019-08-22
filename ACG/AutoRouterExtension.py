from .AyarLayoutGenerator import AyarLayoutGenerator
from .Rectangle import Rectangle
from .XY import XY
from .tech import tech_info
from typing import Tuple, Union, Optional, List, Dict
from .AutoRouter import EZRouter
import copy


class EZRouterExtension(EZRouter):
    """
    The EZRouterExtension class inherits from the EZRouter class and allows you to create ground-shielded routes.
    """

    # TODO: change tuples to XY to avoid rounding issues. Right now, using XY creates key errors with self.route_point_dict.

    def __init__(self,
                 gen_cls: AyarLayoutGenerator,
                 start_rect: Optional[Rectangle] = None,
                 start_direction: Optional[str] = None,
                 config: Optional[dict] = None
                 ):
        EZRouter.__init__(self, gen_cls, start_rect=start_rect, start_direction=start_direction, config=config)

        # For AStarRouter use only
        self.grids = {}  # Dictionary containing grid 2D array for each layer
        self.dims = {}  # Dictionary of array dimensions for each layer
        self.routing_layers = []  # List of layers to route on

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

    def shield_router(self,
                      start_layer: str,
                      perpendicular_pitch: float,
                      parallel_spacing: float,
                      start_width: float,
                      start_pt: Tuple,
                      shield_layers: list,
                      start_dir: str,
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
        self.cardinal_router(enc_style=enc_style, prim=prim, clear_route=False)
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

        # Clear instance variables for future routes
        self.route_points = []
        self.route_point_dict = {}

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
            self.cardinal_router(enc_style=enc_style, prim=prim, clear_route=False)
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

            router.cardinal_router(enc_style=enc_style, prim=prim, clear_route=False)

            # Switch to opposite side of center
            sign = -sign

        # Clear instance variables for future routes
        self.route_points = []
        self.route_point_dict = {}

        return self

    def bfs_router(self,
                   start : Union[Tuple[float, float], XY],
                   end : Union[Tuple[float, float], XY],
                   start_layer: str,
                   end_layer: str,
                   obstructions : List[Rectangle],
                   layers : list,
                   routing_ll: Tuple[float, float] = None,
                   routing_ur: Tuple[float, float] = None
                   ):
        """
        Given start and end points and a list of obstructions, routes from start to end round the obstructions.

        Notes
        -----
        * Perform breadth-first search to find shortest path around obstructions
        * For a given 2D array grid, coordinate (i, j) is located at grid[j][i].
        * 'O' denotes an obstruction at a grid square, 'S' denotes the start square, and 'E' denotes the end layer

        Parameters
        ----------
        start : Union[Tuple[float, float], XY]
            The point to start routing from
        end : Union[Tuple[float, float], XY]
            The point to end routing on
        start_layer : str
            The layer to start routing on
        end_layer : str
            The layer to end routing on
        obstructions : List[Rectangle]
            List of obstructions that router should avoid
        layers : list
            List of layers to use when routing
        routing_ll : Tuple[float] = None
            If provided, provides lower left coordinate of area permitted to route in
        routing_ur : Tuple[float] = None
            If provided, provides upper right coordinate of area permitted to route in

        Returns
        -------
        self : WgRouter
            returns itself so that route segments can be easily chained together
        """

        # Reset instance variables
        self.grids = {}  # Dictionary containing grid 2D array for each layer
        self.dims = {}  # Dictionary of array dimensions for each layer
        self.routing_layers = layers  # List of layers to route on

        self.route_points = []
        self.route_point_dict = {}

        # Snap all input coordinates to grid
        start_spacing = self.config[start_layer]['spacing']
        start = (round(start[0] / start_spacing) * start_spacing, round(start[1] / start_spacing) * start_spacing)

        end_spacing = self.config[end_layer]['spacing']
        end = (round(end[0] / end_spacing) * end_spacing, round(end[1] / end_spacing) * end_spacing)

        # If routing area not defined, define it using bounds of start and end coordinates
        if not (routing_ll and routing_ur):
            for layer in layers:
                # Determine grid size and initialize grid
                x = round((max([end[0], start[0]]) - min([end[0], start[0]])) / self.config[layer]['spacing']) + 1
                y = round((max([end[1], start[1]]) - min([end[1], start[1]])) / self.config[layer]['spacing']) + 1

                grid = [[None for _ in range(x)] for _ in range(y)]

                self.grids[layer] = grid
                self.dims[layer] = (x, y)

            start_dim = self.dims[start_layer]
            end_dim = self.dims[end_layer]

            # Determine lower left and upper right coordinates based on start and end points
            if end[0] > start[0]:
                if end[1] > start[1]:
                    start_coord = (0, 0)
                    end_coord = (end_dim[0] - 1, end_dim[1] - 1)
                    ll_pos = start
                    ur_pos = end
                else:
                    start_coord = (0, start_dim[1] - 1)
                    end_coord = (end_dim[0] - 1, 0)
                    ll_pos = (start[0], end[1])
                    ur_pos = (end[0], start[1])
            else:
                if end[1] > start[1]:
                    start_coord = (start_dim[0] - 1, 0)
                    end_coord = (0, end_dim[1] - 1)
                    ll_pos = (end[0], start[1])
                    ur_pos = (start[0], end[1])
                else:
                    start_coord = (start_dim[0] - 1, start_dim[1] - 1)
                    end_coord = (0, 0)
                    ll_pos = end
                    ur_pos = start

        # If routing area has been provided
        else:
            for layer in layers:
                layer_spacing = self.config[layer]['spacing']
                ur_temp = (round(routing_ur[0] / layer_spacing) * layer_spacing, round(routing_ur[1] / layer_spacing) * layer_spacing)
                ll_temp = (round(routing_ll[0] / layer_spacing) * layer_spacing, round(routing_ll[1] / layer_spacing) * layer_spacing)

                x = round((ur_temp[0] - ll_temp[0]) / layer_spacing) + 2
                y = round((ur_temp[1] - ll_temp[1]) / layer_spacing) + 2

                grid = [[None for _ in range(x)] for _ in range(y)]

                self.grids[layer] = grid
                self.dims[layer] = (x, y)

            ll_pos = routing_ll
            ur_pos = routing_ur

            # Determine start and end grid coordinates relative to given routing area
            start_coord = (round((start[0] - ll_pos[0]) / self.config[start_layer]['spacing']),
                           round((start[1] - ll_pos[1]) / self.config[start_layer]['spacing']))
            end_coord = (round((end[0] - ll_pos[0]) / self.config[end_layer]['spacing']),
                           round((end[1] - ll_pos[1]) / self.config[end_layer]['spacing']))

        # Mark start coordinate as 'S', end coordinate as 'E'
        self.grids[start_layer][start_coord[1]][start_coord[0]] = 'S'
        self.grids[end_layer][end_coord[1]][end_coord[0]] = 'E'


        obstructions = obstructions + self.loc['rect_list']
        # Initialize obstructions on the grid
        for rect in obstructions:
            # If the obstructions are in the routing area
            if rect and Rectangle.overlap(rect, Rectangle((ll_pos, ur_pos), '')) and rect.layer in layers:
                rel_ll_coord = (rect.ll.x - ll_pos[0], rect.ll.y - ll_pos[1])
                rel_ur_coord = (rect.ur.x - ll_pos[0], rect.ur.y - ll_pos[1])

                # Determine grid coordinates of obstruction, fill in each obstructed grid square with 'O'
                ll = round(rel_ll_coord[0] / self.config[rect.layer]['spacing']), round(rel_ll_coord[1] / self.config[rect.layer]['spacing'])
                ur = round(rel_ur_coord[0] / self.config[rect.layer]['spacing']), round(rel_ur_coord[1] / self.config[rect.layer]['spacing'])

                for j in range(max([ll[1], 0]), min([ur[1] + 1, self.dims[rect.layer][1]])):
                    for i in range(max([ll[0], 0]), min([ur[0] + 1, self.dims[rect.layer][0]])):
                        self.grids[rect.layer][j][i] = 'O'

        # Perform first half of wave propagation algorithm to label each grid square
        self.label_node(start_layer, start_coord[0], start_coord[1])

        curr_node = end_coord + (end_layer,)
        path = [curr_node]
        grid = self.grids[curr_node[2]]

        # for i in self.grids:
        #     print("GRID")
        #     for j in self.grids[i]:
        #         print(j)


        visited = copy.deepcopy(self.grids)

        # Perform second half of wave propagation algorithm
        # Back propagate from end point by finding the minimum-value neighbor at each iteration

        while grid[curr_node[1]][curr_node[0]] != 1:
            neighbors = self.get_neighbors(curr_node[2], curr_node[0], curr_node[1])
            neighbors = [i for i in neighbors if type(self.grids[i[2]][i[1]][i[0]]) == int and visited[i[2]][i[1]][i[0]] != 'V']
            curr_node = min(neighbors, key=lambda x: self.grids[x[2]][x[1]][x[0]])
            visited[curr_node[2]][curr_node[1]][curr_node[0]] = 'V'
            grid = self.grids[curr_node[2]]
            path.append(curr_node)

        # Convert grid coordinates to real coordinates
        real_path = [((round(round(ll_pos[0] / self.config[i[2]]['spacing']) * self.config[i[2]]['spacing'] +
                       self.config[i[2]]['spacing'] * i[0], 3),
                       round(round(ll_pos[1] / self.config[i[2]]['spacing']) * self.config[i[2]]['spacing'] +
                       self.config[i[2]]['spacing'] * i[1], 3)), i[2]) for i in path][::-1]

        next_pt = real_path[0][0]

        # Determine start direction
        if next_pt[0] > start[0]:
            start_dir = '+x'
        elif next_pt[0] < start[0]:
            start_dir = '-x'
        elif next_pt[1] > start[1]:
            start_dir = '+y'
        else:
            start_dir = '-y'

        real_path = self.manhattanize_point_list(start_dir, (start, start_layer), real_path)

        # del_idx = []
        # for i in range(len(real_path) - 1):
        #     if round(real_path[i][0][0], 3) == round(real_path[i + 1][0][0], 3) and round(real_path[i][0][1], 3) == round(real_path[i + 1][0][1], 3):
        #         del_idx.append(i)
        #
        # real_path = [real_path[i] for i in range(len(real_path)) if i not in del_idx]

        for i in range(len(real_path) - 2):
            pt0 = real_path[i]
            pt1 = real_path[i + 1]
            pt2 = real_path[i + 2]

            if pt0[0][0] == pt1[0][0] == pt2[0][0] and (pt0[0][1] < pt1[0][1] > pt2[0][1] or pt0[0][1] > pt1[0][1]
                                                        < pt2[0][1]) and pt0[1] == pt1[1] == pt2[1]:
                pt1 = ((pt1[0][0], pt2[0][1]), pt1[1])
            elif pt0[0][1] == pt1[0][1] == pt2[0][1] and (pt0[0][0] < pt1[0][0] > pt2[0][0] or pt0[0][0] > pt1[0][0]
                                                          < pt2[0][0]) and pt0[1] == pt1[1] == pt2[1]:
                pt1 = ((pt2[0][0], pt1[0][1]), pt1[1])

            real_path[i + 1] = pt1

        for point in real_path:
            add_width = False if point[0] in self.route_point_dict else True
            self.add_route_points([point[0]], point[1], self.config[point[1]]['width'], add_width=add_width)

        # Route points
        self.new_route_from_location(start, start_dir, start_layer, self.config[start_layer]['width'])
        self.cardinal_router(prim=True)

        return self

    def find_adjacent(self, layer1, layer2, i, j):
        """Determine the corresponding grid square to a given grid square on an adjacent layer"""
        spacing1 = self.config[layer1]['spacing']
        spacing2 = self.config[layer2]['spacing']
        return round((i * spacing1) / spacing2), round((j * spacing1) / spacing2)

    def label_node(self, curr_layer, i, j):
        h = [((i, j, curr_layer), 0)]  # FIFO queue for breadth-first search

        # While there are still grid squares to label ('E' hasn't been found)
        while h:
            # Pop front of queue
            # item = ((i, j, layer), idx)
            item = h[0]
            h = h[1:]
            i = item[0][0]
            j = item[0][1]
            curr_layer = item[0][2]
            grid = self.grids[curr_layer]
            elem = grid[j][i]

            if elem == 'E':  # found endpoint (and therefore shortest path), no need to continue searching
                return
            elif elem == 'O' or elem and elem != 'S':  # Cannot label obstructed or already labeled grid squares
                continue
            elif not elem:  # Label unlabeled square
                grid[j][i] = item[1]

            # Add all of this grid square's unlabeled neighbors to queue with an incremented idx
            for neighbor in self.get_neighbors(curr_layer, i, j):
                if not self.grids[neighbor[2]][neighbor[1]][neighbor[0]] or self.grids[neighbor[2]][neighbor[1]][neighbor[0]] == 'E':
                    h.append((neighbor, item[1] + 1))

    def get_neighbors(self, layer, i, j):
        """Find all of a grid square's neighbor grid squares"""
        grid = self.grids[layer]

        all_layers = tech_info['metal_tech']['routing']
        layer_idx = [i for i in range(len(all_layers)) if all_layers[i] == layer][0]
        neighboring_layers = []
        if layer_idx + 1 < len(all_layers):
            neighboring_layers.append(all_layers[layer_idx + 1])
        if layer_idx - 1 >= 0:
            neighboring_layers.append(all_layers[layer_idx - 1])

        neighboring_layers = [l for l in neighboring_layers if l in self.routing_layers]

        neighbors = []
        gridY = len(grid)
        gridX = len(grid[0])

        direction = self.config[layer]['direction']

        # If horizontal layer, there are only horizontal neighbors
        if direction == 'x' or direction == 'xy':
            if i + 1 < gridX:
                neighbors.append((i + 1, j, layer))
            if i - 1 >= 0:
                neighbors.append((i - 1, j, layer))

        # If vertical layer, there are only vertical neighbors
        if direction == 'y' or direction == 'xy':
            if j + 1 < gridY:
                neighbors.append((i, j + 1, layer))
            if j - 1 >= 0:
                neighbors.append((i, j - 1, layer))

        # Find all neighboring grid squares on neighboring layers
        for l in neighboring_layers:
            if l != layer:
                i2, j2 = self.find_adjacent(layer, l, i, j)
                if i2 < self.dims[l][0] and j2 < self.dims[l][1]:
                    neighbors.append((i2, j2, l))

        return neighbors
