from .AyarLayoutGenerator import AyarLayoutGenerator
from .Rectangle import Rectangle
from .XY import XY
from typing import Tuple, Union, Optional, List, Dict
from .AutoRouter import EZRouter


class EZRouterShield(EZRouter):
    """
    The EZRouterShield class inherits from the EZRouter class and allows you to create ground-shielded routes.
    """

    def __init__(self,
                 gen_cls: AyarLayoutGenerator,
                 start_rect: Optional[Rectangle] = None,
                 start_direction: Optional[str] = None,
                 config: Optional[dict] = None
                 ):
        EZRouter.__init__(self, gen_cls, start_rect=start_rect, start_direction=start_direction, config=config)

        self.route_points = []
        self.route_point_dict = {}

        # to determine offset of shield_1 from center
        self.shield_dict = {
            '+x': {
                '+x': (0, 1),
                '-x': (0, 1),
                '+y': (-1, 1),
                '-y': (1, 1)
            },
            '-x': {
                '+x': (0, -1),
                '-x': (0, -1),
                '+y': (-1, -1),
                '-y': (1, -1)
            },
            '+y': {
                '+x': (-1, 1),
                '-x': (-1, -1),
                '+y': (-1, 0),
                '-y': (-1, 0)
            },
            '-y': {
                '+x': (1, 1),
                '-x': (1, -1),
                '+y': (1, 0),
                '-y': (1, 0)
            }
        }

    def add_route_points(self,
                         points: List[Tuple],
                         metal_layer: str,
                         width: Optional[float] = None
                         ):
        """
        Adds provided points to route network.

        Notes
        -----
        * Stores width for each point in self.route_point_dict
        * No need to add start point of route network

        Parameters
        ----------
        points : str
            A list of Tuple[float, float] or XY
        metal_layer : str
            The metal layer on which to route the given points
        width : float
            The width of the route at the given points
        """
        for point in points:
            p = (round(point[0], 3), round(point[1], 3))
            self.route_points.append((p, metal_layer))
            self.route_point_dict[p] = width

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
            A list of metal layers to route perpendicular shields on
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

        if self.current_handle[1] in ['r', 'l']:
            rect_1.align('ll', new_rect, 'ul', offset=(0, parallel_spacing))
            rect_2.align('ul', new_rect, 'll', offset=(0, -parallel_spacing))
            rect_1.set_dim('y', width)
            rect_2.set_dim('y', width)
            dir = 'r'
            length = new_rect.ur.x - new_rect.ll.x
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
                               start_met: str,
                               perpendicular_pitch: float,
                               parallel_spacing: float,
                               start_width: float,
                               start_pt: Tuple,
                               shield_layers: list,
                               start_dir: str = '+x',
                               ):
        """
        Creates a shielded route network that contains all the points added by add_route_points.

        Notes
        -----
        * Calls new_route_from_location for the user -- no need to call it beforehand.

        Parameters
        ----------
        start_met : str
            The metal layer to start routing on
        perpendicular_pitch : float
            The pitch between the perpendicular shielding stripes
        parallel_spacing : float
            The pitch between the parallel shields
        start_width : float
            The width to start routing with
        start_pt : Tuple
            The point to start routing from
        shield_layers : list
            A list of metal layers to route perpendicular shields on
        start_dir : str = '+x'
            The direction to start routing in

        Returns
        -------
        self : WgRouter
            returns itself so that route segments can be easily chained together
        """
        points = self.route_points
        self.new_route_from_location(start_pt, start_dir, start_met, start_width)

        self.route_point_dict[start_pt] = start_width

        self.cardinal_router_variant()
        manh = self.manhattanize_point_list(start_dir, (start_pt, start_met), points)
        manh = self.process_manh(manh)

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

        router1 = None
        router2 = None

        for i in range(len(dirs)):
            if i == 0:
                if start_pt[0] > manh[1][0][0]:
                    start = (0, -1)
                elif start_pt[0] < manh[1][0][0]:
                    start = (0, 1)
                elif start_pt[1] > manh[1][0][1]:
                    start = (1, 0)
                else:
                    start = (-1, 0)
                shield1_start = ((start_pt[0] + start[0] * parallel_spacing,
                                  start_pt[1] + start[1] * parallel_spacing),
                                 start_met)
                shield2_start = ((start_pt[0] - start[0] * parallel_spacing,
                                  start_pt[1] - start[1] * parallel_spacing),
                                 start_met)
                router1 = EZRouterShield(self.gen)
                router2 = EZRouterShield(self.gen)
                router1.new_route_from_location(shield1_start[0], start_dir, start_met, 0.5)
                router2.new_route_from_location(shield2_start[0], start_dir, start_met, 0.5)
            else:
                pt0 = manh[i]

                direc = self.shield_dict[dirs[i - 1]][dirs[i]]
                router1.add_route_points([(pt0[0][0] + direc[0] * (parallel_spacing),
                                           pt0[0][1] + direc[1] * (parallel_spacing))],
                                         pt0[1], width=self.route_point_dict[pt0[0]])
                router2.add_route_points([(pt0[0][0] - direc[0] * (parallel_spacing),
                                           pt0[0][1] - direc[1] * (parallel_spacing))],
                                         pt0[1], width=self.route_point_dict[pt0[0]])

        if manh[-2][0][0] > manh[-1][0][0]:
            end = (0, -1)
        elif manh[-2][0][0] < manh[-1][0][0]:
            end = (0, 1)
        elif manh[-2][0][1] > manh[-1][0][1]:
            end = (1, 0)
        else:
            end = (-1, 0)

        router1.add_route_points([(manh[-1][0][0] + end[0] * parallel_spacing,
                                   manh[-1][0][1] + end[1] * parallel_spacing)],
                                 manh[-1][1], width=self.route_point_dict[manh[-1][0]])
        router2.add_route_points([(manh[-1][0][0] - end[0] * parallel_spacing,
                                   manh[-1][0][1] - end[1] * parallel_spacing)],
                                 manh[-1][1], width=self.route_point_dict[manh[-1][0]])

        router1.cardinal_router_variant()
        router2.cardinal_router_variant()

        max_w = max(self.route_point_dict.values())

        router1_rects = [i for i in router1.loc['rect_list'][1:] if
             round(i.ur.x - i.ll.x, 3) > max_w or round(i.ur.y - i.ll.y, 3) > max_w]

        router2_rects = [i for i in router2.loc['rect_list'][1:] if
             round(i.ur.x - i.ll.x, 3) > max_w or round(i.ur.y - i.ll.y, 3) > max_w]

        shield_pairs = list(zip(router1_rects, router2_rects))

        for i in range(len(shield_pairs)):
            rect_1 = shield_pairs[i][0]
            rect_2 = shield_pairs[i][1]
            rects = [rect_1, rect_2]

            if rect_1.ur.x - rect_1.ll.x > rect_1.ur.y - rect_1.ll.y:
                top = max(rects, key=lambda x: x.ur.y)
                bottom = min(rects, key=lambda x: x.ll.y)
                right = min(rects, key=lambda x: x.ur.x)

                start = top.ll.x

                j = 0
                width = self.route_point_dict[tuple(manh[i + 1][0])]
                while start + (j + 1) * width + j * perpendicular_pitch + 1 < right.ur.x:
                    g_temp = self.gen.add_rect(shield_layers[0], virtual=True)

                    g_temp.set_dim('x', width)
                    g_temp.align('ul', top, 'ul', offset=((width + perpendicular_pitch) * j + .5, 0))
                    g_temp.stretch('b', bottom, 'b')

                    if self.overlap(g_temp, top) and self.overlap(g_temp, bottom):
                        for layer in shield_layers:
                            g_temp = self.gen.copy_rect(g_temp, virtual=False, layer=layer)
                            self.gen.connect_wires(g_temp, rect_1)
                            self.gen.connect_wires(g_temp, rect_2)

                    j += 1

            else:
                top = min(rects, key=lambda x: x.ur.y)
                left = min(rects, key=lambda x: x.ll.x)
                right = max(rects, key=lambda x: x.ur.x)

                start = left.ll.y

                j = 0
                width = self.route_point_dict[tuple(manh[i + 1][0])]
                while start + (j + 1) * width + j * perpendicular_pitch + 1 < top.ur.y:
                    g_temp = self.gen.add_rect(shield_layers[0], virtual=True)

                    g_temp.set_dim('y', width)
                    g_temp.align('ll', left, 'll', offset=(0, (width + perpendicular_pitch) * j + .5))
                    g_temp.stretch('r', right, 'r')

                    if self.overlap(g_temp, left) and self.overlap(g_temp, right):
                        for layer in shield_layers:
                            g_temp = self.gen.copy_rect(g_temp, virtual=False, layer=layer)
                            self.gen.connect_wires(g_temp, rect_1)
                            self.gen.connect_wires(g_temp, rect_2)

                    j += 1

        return self

    def diff_pair_router(self,
                         start_met: str,
                         parallel_spacing: float,
                         start_width: float,
                         start_pt: Tuple,
                         start_dir: str = '+x',
                         ):
        """
        Creates a differential pair route network, assuming the points added by
        add_route_points correspond to the center of the differential pair.

        Parameters
        ----------
        start_met : str
            The metal layer to start routing on
        parallel_spacing : float
            The pitch between the parallel shields
        start_width : float
            The width to start routing with
        start_pt : Tuple
            The point to start routing from
        start_dir : str = '+x'
            The direction to start routing in

        Returns
        -------
        self : WgRouter
            returns itself so that route segments can be easily chained together
        """
        points = self.route_points
        manh = self.manhattanize_point_list(start_dir, (start_pt, start_met), points)

        self.route_point_dict[start_pt] = start_width

        for i in range(len(manh)):
            point = manh[i]
            if tuple(point[0]) not in self.route_point_dict:
                if i != 0:
                    self.route_point_dict[tuple(point[0])] = self.route_point_dict[tuple(manh[i - 1][0])]

        manh = self.process_manh(manh)

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

        router1 = None
        router2 = None

        for i in range(len(dirs)):
            if i == 0:
                if start_pt[0] > manh[1][0][0]:
                    start = (0, -1)
                elif start_pt[0] < manh[1][0][0]:
                    start = (0, 1)
                elif start_pt[1] > manh[1][0][1]:
                    start = (1, 0)
                else:
                    start = (-1, 0)
                shield1_start = ((start_pt[0] + start[0] * parallel_spacing / 2,
                                  start_pt[1] + start[1] * parallel_spacing / 2), start_met)
                shield2_start = ((start_pt[0] - start[0] * parallel_spacing / 2,
                                  start_pt[1] - start[1] * parallel_spacing / 2), start_met)
                router1 = EZRouterShield(self.gen)
                router2 = EZRouterShield(self.gen)
                router1.new_route_from_location(shield1_start[0], start_dir, start_met, 0.5)
                router2.new_route_from_location(shield2_start[0], start_dir, start_met, 0.5)
            else:
                pt0 = manh[i]

                direc = self.shield_dict[dirs[i - 1]][dirs[i]]
                router1.add_route_points(
                    [(pt0[0][0] + direc[0] * parallel_spacing / 2,
                      pt0[0][1] + direc[1] * parallel_spacing / 2)], pt0[1],
                    width=self.route_point_dict[pt0[0]])
                router2.add_route_points(
                    [(pt0[0][0] - direc[0] * parallel_spacing / 2,
                      pt0[0][1] - direc[1] * parallel_spacing / 2)], pt0[1],
                    width=self.route_point_dict[pt0[0]])

        if manh[-2][0][0] > manh[-1][0][0]:
            end = (0, -1)
        elif manh[-2][0][0] < manh[-1][0][0]:
            end = (0, 1)
        elif manh[-2][0][1] > manh[-1][0][1]:
            end = (1, 0)
        else:
            end = (-1, 0)

        router1.add_route_points(
            [(manh[-1][0][0] + end[0] * parallel_spacing / 2,
              manh[-1][0][1] + end[1] * parallel_spacing / 2)], manh[-1][1],
            width=self.route_point_dict[manh[-1][0]])
        router2.add_route_points(
            [(manh[-1][0][0] - end[0] * parallel_spacing / 2,
              manh[-1][0][1] - end[1] * parallel_spacing / 2)], manh[-1][1],
            width=self.route_point_dict[manh[-1][0]])

        router1.cardinal_router_variant()
        router2.cardinal_router_variant()

        return self

    @staticmethod
    def process_manh(manh):
        """
        Helper method to clean up point list returned by manhattanize_point_list
        """
        del_idx = []
        for i in range(len(manh) - 2):
            pt0 = manh[i]
            pt1 = manh[i + 1]
            pt2 = manh[i + 2]

            if pt0[0][0] == pt1[0][0] == pt2[0][0] and (pt0[0][1] <= pt1[0][1] <= pt2[0][1] or pt0[0][1] >= pt1[0][1]
                                                        >= pt2[0][1]) and pt0[1] == pt1[1] == pt2[1]:
                del_idx.append(i + 1)
            elif pt0[0][1] == pt1[0][1] == pt2[0][1] and (pt0[0][0] <= pt1[0][0] <= pt2[0][0] or pt0[0][0] >= pt1[0][0]
                                                          >= pt2[0][0]) and pt0[1] == pt1[1] == pt2[1]:
                del_idx.append(i + 1)

        return [manh[i] for i in range(len(manh)) if i not in del_idx]

    def bus_router(self,
                   start_met: str,
                   parallel_spacing: float,
                   bus_size: int,
                   start_width: float,
                   start_pt: Tuple,
                   start_dir: str = '+x',
                   ):
        """
        Creates a bus route network, assuming the points added by add_route_points correspond
        to the center of the bus route.

        Parameters
        ----------
        start_met : str
            The metal layer to start routing on
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

        Returns
        -------
        self : WgRouter
            returns itself so that route segments can be easily chained together
        """
        # pre-process points
        points = self.route_points
        manh = self.manhattanize_point_list(start_dir, (start_pt, start_met), points)

        self.route_point_dict[start_pt] = start_width

        for i in range(len(manh)):
            point = manh[i]
            if tuple(point[0]) not in self.route_point_dict:
                if i != 0:
                    self.route_point_dict[tuple(point[0])] = self.route_point_dict[tuple(manh[i - 1][0])]

        manh = self.process_manh(manh)

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

        routers = []
        top = (manh, self, start_pt)
        bottom = (manh, self, start_pt)
        sign = 1

        if bus_size % 2 == 1:
            self.new_route_from_location(start_pt, start_dir, start_met, 0.5)
            self.cardinal_router_variant()
            num_iters = bus_size - 1
        else:
            num_iters = bus_size

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

            if bus_size % 2 == 0 and (j == 0 or j == 1):
                spacing = parallel_spacing / 2
            else:
                spacing = parallel_spacing

            for i in range(len(dirs)):
                if i == 0:
                    shield_start = ((temp_start[0] + sign * start[0] * spacing,
                                     temp_start[1] + sign * start[1] * spacing), start_met)

                    router = EZRouterShield(self.gen)
                    router.new_route_from_location(shield_start[0], start_dir, start_met, 0.5)
                else:
                    pt0 = manh[i]

                    direc = self.shield_dict[dirs[i - 1]][dirs[i]]
                    point = (pt0[0][0] + sign * direc[0] * spacing,
                             pt0[0][1] + sign * direc[1] * spacing)
                    router.add_route_points([point], pt0[1], width=router_temp.route_point_dict[pt0[0]])

            if manh[-2][0][0] > manh[-1][0][0]:
                end = (0, -1)
            elif manh[-2][0][0] < manh[-1][0][0]:
                end = (0, 1)
            elif manh[-2][0][1] > manh[-1][0][1]:
                end = (1, 0)
            else:
                end = (-1, 0)

            router.add_route_points(
                [(manh[-1][0][0] + sign * end[0] * spacing,
                  manh[-1][0][1] + sign * end[1] * spacing)], manh[-1][1],
                width=router_temp.route_point_dict[manh[-1][0]])

            manh = router.manhattanize_point_list(start_dir, (shield_start[0], start_met), router.route_points)
            manh = self.process_manh(manh)

            if sign == 1:
                top = (manh, router, shield_start[0])
            else:
                bottom = (manh, router, shield_start[0])

            router.cardinal_router_variant()
            sign = -sign

        return self

    def cardinal_router_variant(self,
                                relative_coords: bool = False,
                                ):
        """
        Creates a route network that contains all points stored by add_route_points

        Notes
        -----
        * This method attempts to generate a manhattanized list of points that contains all of the user
        provided points while minimizing the number of times the direction of the route changes
        * Then a set of cascaded L-routes is created to connect all of the coordinates in the mahattanized point list

        Parameters
        ----------
        relative_coords : bool
            True if the list of coordinates are relative to the starting port's coordinate.
            False if the list of coordinates are absolute relative to the current Template's origin

        Returns
        -------
        self : WgRouter
            returns itself so that route segments can be easily chained together
        """
        if not self.current_rect or not self.current_handle or not self.current_dir:
            raise ValueError('Router has not been initialized, please call new_route()')

        points = self.route_points

        current_dir = self.current_dir
        current_point = (self.current_rect[self.current_handle].xy, self.current_rect.layer)

        if relative_coords:
            # If passed coordinates are relative, need to add WgRouter's port location to convert to absolute coords
            x0, y0 = current_point[0]
            points = [((pt[0] + x0, pt[1] + y0), layer) for pt, layer in points]

        # Generate a manhattanized list of waypoints on the route while minimizing the number of required bends
        manh_point_list = self.manhattanize_point_list(initial_direction=current_dir,
                                                       initial_point=current_point,
                                                       points=points)

        for i in range(len(manh_point_list)):
            point = manh_point_list[i]
            if tuple(point[0]) not in self.route_point_dict:
                if i != 0:
                    self.route_point_dict[tuple(point[0])] = self.route_point_dict[tuple(manh_point_list[i - 1][0])]

        final_point_list = self.process_manh(manh_point_list)

        # Simplify the point list so that each point corresponds with a bend of the route, i.e. no co-linear points
        final_point_list = final_point_list[1:]  # Ignore the first pt, since it is co-incident with the starting port

        # Draw a series of L-routes to follow the final simplified point list
        for pt0, pt1 in zip(final_point_list, final_point_list[1:]):
            # print(f'drawing route {pt0[0]} -> {pt1[0]} on layer {pt0[1]}')
            self._draw_route_segment(pt0=pt0,
                                     pt1=pt1,
                                     in_width=self.route_point_dict[tuple(pt0[0])],
                                     out_width=self.route_point_dict[tuple(pt1[0])],
                                     enc_style='asymm')

        # The loop does not draw the final straight segment, so add it here
        self._draw_route_segment(pt0=final_point_list[-1],
                                 pt1=None,
                                 in_width=self.route_point_dict[tuple(final_point_list[-1][0])],
                                 out_width=self.route_point_dict[final_point_list[-1][0]],
                                 enc_style='uniform')

    @staticmethod
    def overlap(A, B):
        x_min = max(A.ll.x, B.ll.x)
        x_max = min(A.ur.x, B.ur.x)
        y_min = max(A.ll.y, B.ll.y)
        y_max = min(A.ur.y, B.ur.y)

        return x_min < x_max and y_min < y_max
