from ACG.XY import XY
from typing import Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from bag.layout.routing.grid import RoutingGrid


class TrackManager:
    """
    A class that enables users to create tracks and use them as references for routing
    """
    def __init__(self):
        self.tracks: Dict[Track] = {}

    def __getitem__(self, item) -> 'Track':
        """ Use dictionary syntax to access a specific track instance """
        return self.tracks[item]

    def __str__(self):
        track_str = ""
        for name, track in self.tracks.items():
            track_str += str(name) + ' ' + str(track)
        return track_str

    @classmethod
    def from_routing_grid(cls, grid: 'RoutingGrid'):
        """
        Generates a track manager object from the current grid

        Parameters
        ----------
        grid
            RoutingGrid object used as reference to build all of the desired tracks

        Returns
        -------
        TrackManager
            Generated TrackManager object from the provided RoutingGrid
        """
        track_manager = cls()
        for layer_id in grid.sp_tracks:
            name = grid.tech_info.get_layer_name(layer_id)
            spacing = grid.sp_tracks[layer_id] * grid.resolution
            dim = grid.dir_tracks[layer_id]
            track_manager.add_track(name=name, dim=dim, spacing=spacing)
        return track_manager

    def add_track(self, name, dim, spacing, origin=0):
        """
        Adds a track to the database.

        Parameters
        ----------
        name
            name to associate with the added track
        dim
            'x' or 'y' for the desired routing direction
        spacing
            space between tracks
        origin
            coordinate to place the zero track
        """
        if name in self.tracks:
            raise ValueError(f"Track {name} already exists in the db")
        else:
            self.tracks[name] = Track(dim=dim, spacing=spacing, origin=origin)


class Track:
    """
    A class for creating consistently spaced reference lines
    """
    def __init__(self, dim, spacing, origin=0):
        """
        dim: str
            x or y. Refers to the direction that the tracks span
        spacing: float
            the amount of space between any two tracks
        origin: float
            the single x or y coordinate that determines the location of Track.get_track(0)
        """

        # Init local property variables
        self._dim = None
        self._spacing = None
        self._origin = None
        self._res = .001

        # Store provided params with property setters
        self.dim = dim  # refers to the direction that the tracks span
        self.origin = origin  # coordinate of track 0
        self.spacing = spacing  # distance between tracks

    """ Magic Methods """
    def __call__(self, num):
        return self.get_track(num)

    def __str__(self):
        return f"Track:\n\tdim: {self.dim}\n\tspacing: {self.spacing}\n"

    """ Properties """
    @property
    def dim(self):
        return self._dim

    @dim.setter
    def dim(self, direction):
        if direction is 'x':
            self._dim = 'x'
        elif direction is 'y':
            self._dim = 'y'
        else:
            raise ValueError('Provided direction is invalid, must be x or y')

    @property
    def spacing(self):
        return self._spacing * self._res

    @spacing.setter
    def spacing(self, value):
        temp = round(value / self._res)  # Find location of provided spacing on grid
        self._spacing = int(temp)  # Force the coordinate to be an int

    @property
    def origin(self):
        return self._origin * self._res

    @origin.setter
    def origin(self, value):
        temp = round(value / self._res)  # Find location of provided spacing on grid
        self._origin = int(temp)  # Force the coordinate to be an int

    """ Utility Methods """

    def get_track(self, num) -> XY:
        """ Returns [x, y] coordinates of desired track # """
        distance = self.spacing * num

        if self.dim is 'x':
            return XY([self.origin + distance, 0])
        elif self.dim is 'y':
            return XY([0, self.origin + distance])

    def align(self, ref_rect, ref_handle, num=0, offset=0):
        """ Aligns the provided track number to handle of reference rectangle """
        ref_loc = ref_rect.loc[ref_handle]  # grab coordinates of reference location
        curr_loc = self.get_track(num)  # grab coordinates of track location

        if self.dim is 'x':
            diff_x = curr_loc.x - ref_loc.x - offset  # calculate x dimension difference
            self.origin -= diff_x
        elif self.dim is 'y':
            diff_y = curr_loc.y - ref_loc.x - offset  # calculate y dimension difference
            self.origin -= diff_y

    def stretch(self, track_num, ref_rect, ref_handle, offset=0):
        """ Stretches the track spacing to co-locate track and handle """
        ref_loc = ref_rect[ref_handle]
        curr_loc = self.get_track(track_num)

        if self.dim is 'x':
            diff_x = curr_loc.x - ref_loc.x - offset
            self.spacing -= diff_x
        elif self.dim is 'y':
            diff_y = curr_loc.y - ref_loc.y - offset
            self.spacing -= diff_y
