import bag
from ACG.VirtualObj import VirtualObj
from ACG.Rectangle import Rectangle


class Via(VirtualObj):
    """
    A class enabling flexible creation/manipulation of ACG via stacks
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
        self.tech_prop = bag.core._parse_yaml_file(pathname)
        self.routing = self.tech_prop['routing']
        self.metals = self.tech_prop['metals']
        self.vias = self.tech_prop['vias']
        self.dir = self.tech_prop['dir']

        # Generate the actual via stack
        self.compute_via()

    def export_locations(self) -> dict:
        return self.loc

    def shift_origin(self, origin=(0, 0), orient='R0'):
        pass

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
        via_prop = self.vias[bot_layer + '_' + top_layer]

        # 2) Compute overlap required to fit via of given size
        self.loc['overlap'].set_dim('x', via_prop['via_size'] + (self.size[0] - 1) * via_prop['via_pitch'])
        self.loc['overlap'].set_dim('y', via_prop['via_size'] + (self.size[1] - 1) * via_prop['via_pitch'])
        self.extend = True
