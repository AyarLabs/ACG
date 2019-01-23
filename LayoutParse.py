from ACG.Rectangle import Rectangle
from ACG.Label import Label
from typing import Dict


class CadenceLayoutParser:
    """
    This class acts as a database that will contain and manipulate layout shapes. Initially the plan
    is to only support Rectangles, Vias, and Instances. Support for other shapes will come as needed
    """

    def __init__(self, raw_content: dict):
        # Initialize dict of lists that will contain the shapes that we generate. These are
        # indexed by their layer
        self._rect_list: Dict[str, list] = {}
        self._via_list: Dict[str, list] = {}
        self._inst_list: Dict[str, list] = {}
        self._label_list: Dict[str, list] = {}

        # Store the raw data for Parsing
        self._raw_content = raw_content
        self._parse_rects()
        self._parse_labels()

    def generate_loc_dict(self) -> dict:
        """
        Takes all of the parsed content and generates a location dictionary that can be used by
        an ACG instance. This method will automatically associate labels with any metal
        rectangles that they overlap with and place them in the location dictionary accessible by
        the name on the label. If multiple labels of the same net exist, a list of associated
        rectangles is created instead. It also automatically creates a boundary based on the
        prBoundary embedded in the design

        Returns
        -------
        loc_dict : dict
            location dictionary that can be used directly by an ACG instance
        """
        loc_dict = {}
        # First generate a boundary from the drawn prBoundary
        if 'prBoundary' in self._rect_list:
            loc_dict['bnd'] = self._rect_list['prBoundary'][0]
        else:
            print(f"WARNING: {self._raw_content['cell_name']} does not contain a prBoundary")

        # Check if the labels overlap with any rectangles on the same layer
        # TODO: This code is dirty... there must be a better way
        for layer, label_list in self._label_list.items():
            for label in label_list:
                for rect in self._rect_list[layer]:
                    if label.contained_by(rect):
                        if label.name not in loc_dict:
                            loc_dict[label.name] = rect
                        else:
                            if isinstance(loc_dict[label.name], list):
                                loc_dict[label.name].append(rect)
                            else:
                                loc_dict[label.name] = [loc_dict[label.name]]
                                loc_dict[label.name].append(rect)
        return loc_dict

    def _parse_labels(self) -> None:
        """
        Tales all of the labels from the raw content and generates new virtual labels from them
        """
        for _, label in self._raw_content['labels'].items():
            # Extract the information from the raw content
            layer = self._parse_layer(label['layer'])
            xy = label['xy']
            # Generate a new virtual label to mirror this cadence label
            new_label = Label(name=label['label'],
                              layer=layer,
                              xy=xy)
            if layer[0] not in self._label_list:
                self._label_list[layer[0]] = [new_label]
            else:
                self._label_list[layer[0]].append(new_label)

    def _parse_rects(self) -> None:
        """
        Takes all of the rectangles from the raw content and generates new virtual rectangles
        from them.
        """
        for _, rect in self._raw_content['rects'].items():
            # Extract the information from the raw content
            layer = self._parse_layer(rect['layer'])
            xy = rect['bBox']
            # Generate a new virtual rect to mirror this cadence rectangle
            new_rect = Rectangle(layer=layer, xy=xy, virtual=True)
            if layer[0] not in self._rect_list:
                self._rect_list[layer[0]] = [new_rect]
            else:
                self._rect_list[layer[0]].append(new_rect)

    def _parse_layer(self, layer_str: str):
        """
        The SKILL interface returns the layer in a single string containing both the layer and
        purpose. This method takes in that string and returns the appropriate tuple layer type

        Parameters
        ----------
        layer_str : str
            Raw layer string provided by SKILL interface

        Returns
        -------
        layer : tuple[str, str]
            Layer purpose pair
        """
        return tuple(layer_str.split())
