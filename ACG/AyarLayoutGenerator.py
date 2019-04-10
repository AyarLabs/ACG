"""
The AyarLayoutGenerator module implements classes to generate full-custom layout without a grid. It allows designers
to describe layout generation scripts in the Python language and automate the layout process.
"""

# General imports
import abc
from typing import Union, Tuple, List
import re
import yaml
import os

# BAG imports
import bag
from bag.layout.template import TemplateBase

# ACG imports
from ACG.Rectangle import Rectangle
from ACG.Track import Track, TrackManager
from ACG.VirtualInst import VirtualInst
from ACG.Via import ViaStack, Via
from ACG import tech as tech_info
from ACG.LayoutParse import CadenceLayoutParser


class AyarLayoutGenerator(TemplateBase, metaclass=abc.ABCMeta):
    """
    The AyarLayoutGenerator class implements functions and variables for full-custom layout generations on physical
    grids
    """

    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        # Call TemplateBase's constructor
        TemplateBase.__init__(self, temp_db, lib_name, params, used_names, **kwargs)
        self.tech = self.grid.tech_info
        self._res = .001  # set basic grid size to be 1nm
        # Create a dictionary that holds all objects required to construct the layout
        self._db = {
            'rect': [],
            'via': [],
            'prim_via': [],
            'instance': [],
            'template': []
        }

        # Create an empty database that will store only the relevant layout objects
        self.loc = {}

        # Manage the tracks in a track manager
        self.tracks = TrackManager.from_routing_grid(self.grid)

        # Pull default layout parameters
        self.params = self.__class__.get_default_param_values()
        # Override defaults and add provided parameters
        for key in params:
            self.params[key] = params[key]

        # Set up properties for BAG black-boxing
        self.temp_boundary = Rectangle(xy=[[0, 0], [.1, .1]], layer='M1', virtual=True)  # TODO: Make process agnostic
        self.prim_bound_box = None
        self.prim_top_layer = None

    """ REQUIRED METHODS """
    """ You must implement these methods for BAG to work """

    @classmethod
    @abc.abstractmethod
    def get_params_info(cls) -> dict:
        """ Return a dictionary describing all parameters in the layout generator """
        return dict()

    @classmethod
    def get_default_param_values(cls) -> dict:
        """ Return a dictionary of all default parameter values """
        return dict()

    def export_locations(self) -> dict:
        """
        Returns a dictionary of shapes/inst in the layout. It is recommended to override this method and only return
        relevant shapes in a dict() with easily interpretable key names
        """
        return self.loc

    @abc.abstractmethod
    def layout_procedure(self):
        """ Implement this method to describe how the layout is drawn """
        pass

    """ DRAWING TOOLS """
    """ Call these methods to craft your layout """
    """ DO NOT OVERRIDE """

    def add_rect(self,
                 layer: Union[str, Tuple[str, str], List[str]],
                 xy=None,
                 virtual: bool = False
                 ) -> Rectangle:
        """
        Instantiates a rectangle, adds the Rectangle object to local db, and returns it for further user manipulation

        Args:
            layer (str):
                layer that the rectangle should be drawn on
            xy (Tuple[[float, float], [float, float]]):
                list of xy coordinates representing the lower left and upper right corner of the rectangle. If None,
                select default size of 100nm by 100nm at origin
            virtual (bool):
                 If true, the rectangle object will be created but will not be drawn in the final layout. If false, the
                 rectangle will be drawn as normal in the final layout
        Returns:
            (Rectangle):
                the created rectangle object
        """
        if xy is None:
            xy = [[0, 0], [.1, .1]]
        temp = Rectangle(xy, layer, virtual=virtual)
        self._db['rect'].append(temp)
        return self._db['rect'][-1]

    def copy_rect(self, rect,  # type: Rectangle
                  layer=None,  # type: Union[str, Tuple[str, str]]
                  virtual=False  # type: bool
                  ) -> Rectangle:
        """
        Creates a copy of the given rectangle and adds it to the local db

        Args:
            rect (Rectangle):
                rectangle object to be copied
            layer (str):
                layer that the copied rectangle should be drawn on. If None, the copied rectangle will use the same
                layer as the provided rectangle
            virtual (bool):
                 If true, the rectangle object will be created but will not be drawn in the final layout. If false, the
                 rectangle will be drawn as normal in the final layout

        Returns:
            (Rectangle):
                a new rectangle object copied from provided rectangle
        """
        temp = rect.copy(layer=layer, virtual=virtual)
        self._db['rect'].append(temp)
        return self._db['rect'][-1]

    def add_track(self, name: str, dim: str, spacing: float, origin: float = 0) -> Track:
        """
        Creates and returns a track object for alignment use

        Parameters
        ----------
        name
            Name to use for the added track
        dim:
            'x' for a horizontal track and 'y' for a vertical track
        spacing:
            number representing the space between tracks
        origin:
            coordinate for the 0th track

        Returns
        -------
        Track:
            track object for user manipulation
        """
        self.tracks.add_track(name=name, dim=dim, spacing=spacing, origin=origin)
        return self.tracks[name]

    def new_template(self,
                     params: dict = None,
                     temp_cls=None,
                     debug: bool = False,
                     **kwargs):
        """
        Generates a layout master of specified class and parameter set

        Args:
            params (dict):
                dictionary of parameters to specify the layout to be created
            temp_cls:
                the layout generator class to be used
            debug (bool):
                True to print debug messages
        """
        return TemplateBase.new_template(self,
                                         params=params,
                                         temp_cls=temp_cls,
                                         debug=debug, **kwargs)

    def add_instance(self,
                     master,
                     inst_name=None,
                     loc=(0, 0),
                     orient="R0",
                     nx=1,
                     ny=1,
                     spx=0,
                     spy=0,
                     unit_mode=False
                     ) -> VirtualInst:
        """ Adds a single instance from a provided template master """
        temp = VirtualInst(master, inst_name=inst_name)
        temp.shift_origin(loc, orient=orient)  # Move virtual instance to desired location/orientation
        self._db['instance'].append(temp)  # Add the instance to the list
        return temp

    def import_layout(self,
                      libname: str,
                      cellname: str,
                      yaml_root: str = None,
                      export_pins: bool = True
                      ) -> 'LayoutAbstract':
        """
        Creates an abstract layout master from the provided virtuoso libname and cellname. Adds pin shapes
        from the yaml root to the location dictionary for easy access.

        Parameters
        ----------
        libname : str
            virtuoso design library name
        cellname : str
            virtuoso cell name; must be contained within the provided virtuoso design library
        yaml_root : str
            path to yaml file containing pin shapes. These shapes will be added to the location dictionary
        export_pins : bool
            if True, will draw all pin shapes provided in yaml root

        Returns
        -------
        abstract_temp : LayoutAbstract
            A design master containing the generated layout_abstract
        """
        params = {
            'libname': libname,
            'cellname': cellname,
            'yaml_root': yaml_root,
            'export_pins': export_pins
        }
        abstract_temp = self.new_template(params=params, temp_cls=LayoutAbstract)
        return abstract_temp

    def import_cadence_layout(self,
                              libname: str,
                              cellname: str
                              ) -> 'AyarLayoutGenerator':
        """
        This method will extract the layout specified by libname, cellname from Cadence, and return a new
        LayoutAbstract master that can be placed in the current db. This method will also analyze the layout for
        its pins and automatically add them to the location dictionary.

        Parameters
        ----------
        libname : str
            Cadence library name where the cell will be located
        cellname : str
            Cadence cell name of the layout to be imported

        Returns
        -------
        master : LayoutAbstract
            Newly created master that will contain the imported layout and pin information
        """
        # Grab layout information from Cadence through SKILL interface
        temp_file_name = 'test.yaml'
        expr = 'parse_cad_layout( "%s" "%s" "%s" )' % (libname, cellname, temp_file_name)
        self.template_db._prj.impl_db._eval_skill(expr)

        # Grab the raw layout data, then delete the temp file afterward
        with open(temp_file_name, 'r') as f:
            data = yaml.load(f)
        os.remove(temp_file_name)

        # Create the new master
        return self.new_template(params={'libname': libname,
                                         'cellname': cellname,
                                         'data': data},
                                 temp_cls=CadenceLayout)

    def connect_wires(self,
                      rect1: Rectangle,
                      rect2: Rectangle,
                      size: Tuple[int, int] = (None, None),
                      extend: bool = False,
                      prim: bool = False
                      ) -> Union[ViaStack, Via]:
        """
        Creates a via stack between the two provided rectangles. This method requires that the provided rectangles
        overlap. No knowledge of which rectangle is higher/lower in the metal stack is needed.

        Parameters
        ----------
        rect1: Rectangle
            first rectangle to be connected
        rect2: Rectangle
            second rectangle to be connected
        size: Tuple[int, int]
            number of vias to be placed in the x and y dimension respectively. If (None, None), vias will be placed to
            fill the enclosure
        extend: bool
            Represents whether the enclosure will be extended in the x or y direction to meet drc rules
        prim: bool
            if True, will attempt to create a single primitive via instead of a via stack
        """
        if rect1.layer != rect2.layer:
            if prim:
                temp = Via.from_metals(rect1, rect2, size=size)
                self._db['prim_via'].append(temp)
            else:
                temp = ViaStack(rect1, rect2, size=size, extend=extend)
                self._db['via'].append(temp)
            return temp

    def add_prim_via(self,
                     via_id: str,
                     rect: Rectangle,
                     size: Tuple[int, int] = (None, None),
                     ) -> Via:
        """
        Creates a via stack between the two provided rectangles. This method requires that the provided rectangles
        overlap. No knowledge of which rectangle is higher/lower in the metal stack is needed.

        Parameters
        ----------
        via_id: str
            id for the via to be drawn
        rect: Rectangle
            the rectangle bounding the region to draw the via
        size: Tuple[int, int]
            number of vias to be placed in the x and y dimension respectively. If (None, None), vias will be placed to
            fill the enclosure
        """
        temp = Via(via_id, bbox=rect, size=size)
        self._db['prim_via'].append(temp)
        return temp

    def create_label(self, label, rect, purpose=None, show=True):
        if purpose is not None:
            self.add_rect([rect.layer, purpose], rect.xy)
        if show is True:
            TemplateBase.add_label(self, label, rect.layer, rect.to_bbox())
        TemplateBase.add_pin_primitive(self, net_name=label, layer=rect.layer, bbox=rect.to_bbox(), show=False)

    """ INTERNAL METHODS """
    """ DO NOT CALL OR OVERRIDE """

    def draw_layout(self) -> None:
        """ Called by higher level BAG functions to create layout """
        self.layout_procedure()  # Perform the user determined layout process
        self._commit_shapes()  # Take all of the created shapes and actually push them to the bag db

    def parse_yaml(self, pathname) -> dict:
        """ returns the parsed yaml file TODO: change the reference function to something not in bag.core """
        return bag.core._parse_yaml_file(pathname)

    def _commit_shapes(self) -> None:
        """ Takes all shapes in local db and creates standard BAG equivalents """
        self._commit_rect()
        self._commit_inst()
        self._commit_via()

        # Set the properties required for BAG primitive black boxing
        self.prim_bound_box = self.temp_boundary.to_bbox()
        self.prim_top_layer = self.grid.tech_info.get_layer_id(self.temp_boundary.layer)

        # for layer_num in range(1, self.prim_top_layer + 1):
        #     self.mark_bbox_used(layer_num, self.prim_bound_box)

    def _commit_rect(self) -> None:
        """ Takes in all rectangles in the db and creates standard BAG equivalents """
        for shape in self._db['rect']:
            self.temp_boundary = self.temp_boundary.get_enclosure(shape)
            if shape.virtual is False:
                TemplateBase.add_rect(self, shape.lpp, shape.to_bbox())

    def _commit_inst(self) -> None:
        """ Takes in all inst in the db and creates standard BAG equivalents """
        for inst in self._db['instance']:
            # Get the boundary of the instance
            try:
                bound = inst.master.temp_boundary.shift_origin(origin=inst.origin, orient=inst.orient)
            except AttributeError:
                # TODO: Get the size properly
                bound = Rectangle(xy=[[0, 0], [.1, .1]], layer='M1', virtual=True)
            self.temp_boundary = self.temp_boundary.get_enclosure(bound)
            TemplateBase.add_instance(self,
                                      inst.master,
                                      inst_name=inst.inst_name,
                                      loc=inst.origin,
                                      orient=inst.orient)

    def _commit_via(self) -> None:
        """ Takes in all vias in the db and creates standard BAG equivalents """
        for via in self._db['via']:
            for connection in via.metal_pairs:
                TemplateBase.add_via(self,
                                     bbox=via.loc['overlap'].to_bbox(),
                                     bot_layer=connection[0],
                                     top_layer=connection[1],
                                     bot_dir=connection[2],
                                     extend=via.extend)
        for via in self._db['prim_via']:
            TemplateBase.add_via_primitive(self,
                                           via_type=via.via_id,
                                           loc=via.location,
                                           num_rows=via.num_rows,
                                           num_cols=via.num_cols,
                                           sp_rows=via.sp_rows,
                                           sp_cols=via.sp_cols,
                                           enc1=via.enc_bot,
                                           enc2=via.enc_top,
                                           orient=via.orient)


class LayoutAbstract(AyarLayoutGenerator):
    """
    Generator class that instantiates an existing layout with LEF equivalent pins/obs(optional)
    """

    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        # Call super class' constructor
        AyarLayoutGenerator.__init__(self, temp_db, lib_name, params, used_names, **kwargs)

        self.loc = {}
        self.cell_dict = None
        self.yaml_root = self.params['yaml_root']
        self.cell_yaml = self.yaml_root + self.params['libname'] + '/' + self.params['cellname'] + '.yaml'
        self.tech_layers = []
        self.pin_list = []

    @classmethod
    def get_params_info(cls):
        return dict(
            libname='Name of the library to instantiate the cell from',
            cellname='Name of the cell to instantiate',
            yaml_root='Root directory path for yaml files'
        )

    def get_pins(self):
        return self.pin_list

    def layout_procedure(self):
        """Draws the layout and caculates the coordinates based on LEF"""
        self.get_tech_params()
        self.get_cell_params()
        self.calculate_pins()
        # self.calculate_obs() # Can be enabled later if needed!!!
        self.calculate_boundary()
        self.instantiate_layout()

    def instantiate_layout(self):
        """We instantiate the layout as a primitive here based on the cell_name read"""
        """Adding mapping since the stupid lef layout library name is different than the cds.lib name"""

        self.add_instance_primitive(lib_name=self.params['libname'], cell_name=self.params['cellname'], loc=(0, 0))

    def get_cell_params(self):
        """Read cell parameters from specific Yaml"""
        pathname = open(self.cell_yaml, mode='r')
        self.cell_dict = yaml.load(pathname)
        print("{} instantiated".format(self.params['cellname']))

    def get_tech_params(self):
        """Get tech information to ensure that information of metal stacks is passed through yaml and not hardcoded"""
        self.tech_layers = tech_info.tech_info['metal_tech']['routing']

    def calculate_pins(self):
        """Calculates the pins on the stdcell/macro and pushes them to loc dict"""
        for keys in self.cell_dict:
            if re.match('pins', keys):
                for pins in self.cell_dict['pins']:
                    pins_dict = {pins: []}
                    for layers in self.cell_dict['pins'][pins]:
                        if layers.upper() in self.tech_layers:
                            for rects in self.cell_dict['pins'][pins][layers]:
                                shape = self.add_rect(layers.upper(), rects, virtual=True)
                                pins_dict[pins].append(shape)
                    self.loc.update(pins_dict)
                    self.pin_list.append(pins)

    #                    self.copy_rect(shape,layer=(layers.upper(), 'label'))
    #                    self.create_label(pins,shape)

    def calculate_boundary(self):
        """Calulates the boundary from lef file"""
        for keys in self.cell_dict:
            if re.match('size', keys):
                bnd = self.add_rect('OUTLINE', self.cell_dict['size'], virtual=True)
                bnd_dict = {'bnd': bnd}
                self.loc.update(bnd_dict)

    def calculate_obs(self):
        """Calulates obstructions in the lef (Can be pushed to ACG/BAG ), cant see a reason for it yet"""
        for keys in self.cell_dict:
            if re.match('obs', keys):
                for layers in self.cell_dict['obs']:
                    pass


class CadenceLayout(AyarLayoutGenerator):
    """
    Generator class that instantiates an existing layout from Cadence and fills the location dict
    """

    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        AyarLayoutGenerator.__init__(self, temp_db, lib_name, params, used_names, **kwargs)
        self.loc = {}

    @classmethod
    def get_params_info(cls):
        return dict(
            libname='Name of the library to instantiate the cell from',
            cellname='Name of the cell to instantiate',
            data='data for location dict to attach to this master'
        )

    def layout_procedure(self):
        parser = CadenceLayoutParser(raw_content=self.params['data'])
        self.loc = parser.generate_loc_dict()
        self.instantiate_layout()

    def instantiate_layout(self):
        """We instantiate the layout as a primitive here based on the cell_name read"""
        self.add_instance_primitive(lib_name=self.params['libname'], cell_name=self.params['cellname'], loc=(0, 0))
