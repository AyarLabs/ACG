from bag import BagProject
from ACG.AyarDesignManager import AyarDesignManager
from ACG.AyarLayoutGenerator import AyarLayoutGenerator


class FillMeIn(AyarLayoutGenerator):
    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        # Call ALG's constructor
        AyarLayoutGenerator.__init__(self, temp_db, lib_name, params, used_names, **kwargs)

        # dict for storing important locations
        self.loc = {
            'example1': [],
            'example2': []
        }

    @classmethod
    def get_params_info(cls):
        """ Return a dictionary of parameter descriptions """
        return dict(
            ex1='text description of param',
            ex2='text description of param',
            ex3='text description of param'
        )

    @classmethod
    def get_default_param_values(cls):
        """ Return a dictionary describing default parameter values """
        return dict(
            ex3=.07  # any subset of the parameters can be provided with defaults
        )

    def export_locations(self):
        """
        Returns a dictionary of shapes/inst in the layout. If you would like to use a different variable than
        self.loc, override export_locations() here.
        """
        return self.loc

    def layout_procedure(self):
        """ Implement this method to describe how the layout is drawn """
        # It is recommended to break up the procedure into multiple functions that can be called
        # independently. This makes it easy to subclass and override in future implementations
        # Example procedure:
        self.create_master()
        self.place_instance()
        self.connect_nets()
        self.draw_pins()

    def create_master(self):
        pass

    def place_instance(self):
        pass

    def connect_nets(self):
        pass

    def draw_pins(self):
        pass


if __name__ == '__main__':
    # The following code checks if there is a bag project already running and uses it
    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()
    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    spec_file = 'Path/to/spec/file.yaml'
    ALM = AyarDesignManager(bprj, spec_file=spec_file)
    ALM.generate_layout()
