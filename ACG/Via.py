from ACG.VirtualObj import VirtualObj
from ACG.Rectangle import Rectangle
from ACG import tech as tech_info
from typing import Optional, List, Tuple


class ViaStack(VirtualObj):
    """
    A class enabling flexible creation/manipulation of ACG via stacks. There are two main ways that vias
    can be created:

    1. A bbox is created representing the area that a via is allowed to occupy, and then it is sent to bag
    to fill with vias and enclosures

    2. Rectangles are manually created to generate the desired via properties.

    Generally if the user does not call any special properties, the first option will be used to ensure
    DRC compliance. Note that the added options may or may not satisfy DRC constraints.
    """

    def __init__(self,
                 rect1: Rectangle,
                 rect2: Rectangle,
                 size=(None, None),
                 extend=False,
                 ):
        """
        Creates a Via based on the overlap region between the two provided rectangles.

        Parameters
        ----------
        rect1 : Rectangle
            One of the Rectangles to be connected by this via stack
        rect2 : Rectangle
            One of the Rectangles to be connected by this via stack
        size : (int, int)
            Tuple representing the via array size in the (x, y) dimension
        extend : bool
            Tuple representing whether the overlap region can be extended in the (x, y) dimension to meet the
            via enclosure rules
        """

        VirtualObj.__init__(self)

        # Variable initialization
        self.rect1 = rect1
        self.rect2 = rect2
        self.size = size
        self.bot_dir = None  # Direction of the bottom metal layer in the stack. To be deprecated
        self.metal_pairs = []  # List containing all metal layers to be connected by vias
        self.extend = extend  # Flag for top-level bag code to extend enclosure beyond provided overlap
        self.loc = {
            'top': None,
            'bottom': None,
            'overlap': None,
            'rect_list': []
        }

        # Get process specific data
        self.tech_prop = tech_info.tech_info['metal_tech']
        self.routing = self.tech_prop['routing']
        self.metals = self.tech_prop['metals']
        self.vias = self.tech_prop['vias']
        self.dir = self.tech_prop['dir']

        # Generate the actual via stack
        self.compute_via()

    def export_locations(self) -> dict:
        return self.loc

    def shift_origin(self, origin=(0, 0), orient='R0'):
        self.loc['overlap'] = self.loc['overlap'].shift_origin(origin=origin, orient=orient)

    def compute_via(self):
        """
        Takes the stored rectangles and creates the overlap region necessary to meet the user constraints.
        BAG then uses this overlap region to generate the actual vias.

        Via creation algorithm
        ----------------------
        1) Determine all metal layers to be drawn in the via stack
        2) Determine the overlap region to be filled with vias
        3) If a via size is given, adjust the overlap region to meet the constraints
        3) Fill in bottom metal routing direction to satisfy BAG's routing requirements
        """
        self.find_metal_pairs()
        self.find_overlap()
        if self.size != (None, None):
            self.set_via_size()
        self.bot_dir = self.dir[self.routing.index(self.loc['bottom'].layer)]

    def find_metal_pairs(self):
        """
        Creates an ordered list of metal pairs required to generate a via stack between rect1 and rect2

        Metal ordering algorithm
        ------------------------
        1) Map each rectangle's layer to index in the metal stack
        2) Determine which rect is lower/higher in the stack based on the index
        3) Add each metal pair in the stack between rect1 and rect2 to the metal_pair list, starting with the lower
        rectangle and traversing up the metal stack
        """
        # 1) Map each rectangle layer to index in the metal stack
        i1 = self.metals[self.rect1.layer]['index']
        i2 = self.metals[self.rect2.layer]['index']

        # 2) Determine which rect is lower/higher in the stack
        if i2 > i1:
            self.loc['bottom'] = self.rect1
            self.loc['top'] = self.rect2
        else:
            self.loc['bottom'] = self.rect2
            self.loc['top'] = self.rect1

        # 3) Add each metal pair between rect1 and rect2 to the metal_pair list
        bot_layer = self.loc['bottom'].layer
        while True:
            # Try to find the metal layer that the current bot layer connects to
            try:
                top_layer = self.metals[bot_layer]['connect_to']
            except KeyError:
                raise ValueError('Could not complete via stack from {} to {}'.format(self.loc['top'].layer,
                                                                                     self.loc['bottom'].layer))
            self.metal_pairs.append((bot_layer, top_layer))
            if top_layer == self.loc['top'].layer:
                # If we have made it from the bottom to the top of the via stack, break out of the loop
                break
            else:
                # Otherwise continue traversing the via stack
                bot_layer = top_layer

    def find_overlap(self):
        """
        Takes the bottom and top rectangles and stores the rectangle representing their overlapping region. The overlap
        region is used to determine the area to be filled with vias.
        """
        lower_rect = self.loc['bottom']
        upper_rect = self.loc['top']

        self.loc['overlap'] = upper_rect.get_overlap(lower_rect)

    def set_via_size(self):
        """
        If the user provided a via array size, adjust the overlap region to fit the desired number of vias. Enable
        extend to make BAG compute the proper enclosure size

        Overlap adjustment algorithm
        ----------------------------
        1) Determine the highest metal pair in via stack and grab its tech info
        2) For size constraints, set the overlap region to fit the desired number of vias
        """
        # 1) Get tech info for the highest metal pair in the via stack
        bot_layer, top_layer = self.metal_pairs[-1]
        via_prop = self.vias['V' + bot_layer + '_' + top_layer]

        # 2) Compute overlap required to fit via of given size
        self.loc['overlap'].set_dim('x', via_prop['via_size'] + (self.size[0] - 1) * via_prop['via_pitch'])
        self.loc['overlap'].set_dim('y', via_prop['via_size'] + (self.size[1] - 1) * via_prop['via_pitch'])
        self.extend = True

    def remove_enclosure(self) -> 'Via':
        """
        This method removes any metal enclosure on the generated via. Note that this will not be DRC clean
        unless minimum area and minimum enclosure rules are satisfied by other routes you create
        """
        raise NotImplemented('Remove enclosure is currently not supported with via stacks')


class Via(VirtualObj):
    """
    A class that wraps the functionality of adding primitive via types to the layout
    """

    # Get process specific data
    tech_prop = tech_info.tech_info['metal_tech']
    routing = tech_prop['routing']
    metals = tech_prop['metals']
    vias = tech_prop['vias']
    dir = tech_prop['dir']

    def __init__(self,
                 via_id: str,
                 bbox: Rectangle,
                 size: Tuple[int, int] = (1, 1),
                 ):
        """
        Creates a Via based on the overlap region between the two provided rectangles.

        Parameters
        ----------
        via_id: str
            String representing the via type to be drawn.
        size : (int, int)
            Tuple representing the via array size in the (x, y) dimension
        """
        VirtualObj.__init__(self)

        # User variable initialization
        self.bbox = bbox
        self.size = size
        self.loc = {
            'overlap': self.bbox,
        }

        # Via primitive properties
        self.via_id = via_id
        self.location = bbox.center.xy
        self.sp_rows: float = 0
        self.sp_cols: float = 0
        self.enc_bot: List[float] = [0, 0, 0, 0]
        self.enc_top: List[float] = [0, 0, 0, 0]
        self.orient: str = 'R0'

        # Generate the actual via
        self.compute_via()

    @property
    def num_rows(self) -> int:
        return self.size[0]

    @property
    def num_cols(self) -> int:
        return self.size[1]

    @classmethod
    def from_metals(cls,
                    rect1: Rectangle,
                    rect2: Rectangle,
                    size: Tuple[int, int] = (None, None)
                    ) -> "Via":
        """ Generates a via instance from two rectangles """
        via_id0 = 'V' + rect1.layer + '_' + rect2.layer
        via_id1 = 'V' + rect2.layer + '_' + rect1.layer
        if via_id0 in cls.vias:
            return cls(bbox=rect1.get_overlap(rect2),
                       via_id=via_id0,
                       size=size)
        elif via_id1 in cls.vias:
            return cls(bbox=rect2.get_overlap(rect1),
                       via_id=via_id1,
                       size=size)
        else:
            raise ValueError(f"A single via cannot be created between {rect1.layer} and {rect2.layer}")

    def export_locations(self) -> dict:
        return self.loc

    def shift_origin(self, origin=(0, 0), orient='R0'):
        self.loc['overlap'] = self.loc['overlap'].shift_origin(origin=origin, orient=orient)

    def compute_via(self):
        """
        This method extracts the expected via spacing and enclosure based on the provided via id
        """
        tech = self.vias[self.via_id]
        self.sp_cols = tech['via_space']
        self.sp_rows = tech['via_space']
        self.enc_bot = [tech['uniform_enclosure']] * 4
        self.enc_top = [tech['uniform_enclosure']] * 4

    def remove_enclosure(self) -> 'Via':
        """
        This method removes any metal enclosure on the generated via. Note that this will not be DRC clean
        unless minimum area and minimum enclosure rules are satisfied by other routes you create
        """
        tech = self.vias[self.via_id]
        self.enc_bot = [tech['zero_enclosure']] * 4
        self.enc_top = [tech['zero_enclosure']] * 4
        return self

    def set_enclosure(self,
                      enc_bot=None,
                      enc_top=None,
                      type=None
                      ) -> 'Via':
        """
        This method enables you to manually set the enclosure sizing for the top and bottom metal layers

        Parameters
        ----------
        enc_bot : List[float]
            enclosure size of the left, bottom, right, top edges of the bottom layer
        enc_top : List[float]
            enclosure size of the left, bottom, right, top edges of the top layer
        type : str
            TODO: Enables easy selection between asymmetric enclosure styles
        """
        if enc_bot:
            self.enc_bot = enc_bot
        if enc_top:
            self.enc_top = enc_top
        return self
