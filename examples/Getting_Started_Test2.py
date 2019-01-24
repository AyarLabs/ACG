from bag import BagProject
from ACG.AyarDesignManager import AyarDesignManager
from ACG.AyarLayoutGenerator import AyarLayoutGenerator


class RectTest(AyarLayoutGenerator):
    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        # Call ALG's constructor
        AyarLayoutGenerator.__init__(self, temp_db, lib_name, params, used_names, **kwargs)

        # dict for storing important locations
        self.loc = {
            'output': [],
            'input': []
        }

    @classmethod
    def get_params_info(cls):
        """ Return a dictionary of parameter descriptions """
        return dict(
            num_connections='number of input-output connections to be made',
            input_width='width of the input lines',
            input_metal='metal layer of the input lines',
            input_spacing='space between input lines',
            input_start_x='x coordinate location of the first input line',
            output_width='width of the output lines',
            output_metal='metal layer of the output lines',
            output_spacing='space between output lines',
            output_start_y='y coordinate location of the first output line'
        )

    @classmethod
    def get_default_param_values(cls):
        """ Return a dictionary describing default parameter values """
        return dict(
            input_width=.1,
            input_metal='M1',
            input_spacing=.2,
            input_start_x=.7,
            output_width=.15,
            output_metal='M3',
            output_spacing=.15,
            output_start_y=1
        )

    def layout_procedure(self):
        self.setup_output()
        self.setup_input()
        self.draw_connections()

    def setup_output(self):
        """ Prepares the output pin locations """
        for count in range(int(self.params['num_connections'])):
            # Adds a rect of given metal layer, defaults to 100n x 100n size placed at the origin
            output_rect = self.add_rect(layer=self.params['output_metal'])  # self.add_rect returns a rect object
            output_rect.set_dim(dim='y', size=self.params['output_width'])
            if count >= 1:
                # Aligns lower left corner of the rectangle to the upper left corner of the previous rectangle
                # with given output spacing
                output_rect.align('ll', ref_rect=self.loc['output'][-1], ref_handle='ul',
                                  offset=(0, self.params['output_spacing']))
            else:
                # Aligns lower left corner of the first rectangle to (0, 1)
                output_rect.align('ll', offset=(0, self.params['output_start_y']))
            self.loc['output'].append(output_rect)

    def setup_input(self):
        """ Prepares the input pin locations """
        # Creates rect of provided metal layer and default size to origin
        input_rect = self.add_rect(self.params['input_metal'])
        input_rect.set_dim(dim='x', size=self.params['input_width'])
        # Moves first input rectangle to align lower left corner with the start position
        input_rect.align('ll', offset=(self.params['input_start_x'], 0))
        self.loc['input'].append(input_rect)
        # Create consistently spaced reference lines for where the input wires should go
        x_track = self.add_track(dim='x', spacing=self.params['input_spacing'] + self.params['input_width'])
        x_track.align(ref_rect=input_rect, ref_handle='ll')  # Align track 0 to the lower left corner of the input
        for count in range(1, int(self.params['num_connections'])):
            input_temp = self.copy_rect(input_rect)  # Creates a new rectangle with same size and layer as input_rect
            input_temp.align('ll', track=x_track(count))  # Aligns it to appropriate track location
            self.loc['input'].append(input_temp)

    def draw_connections(self):
        """ Connects the input and output wires """
        # Stretch each output wire to the corresponding input wire
        # zip creates a list of input/output rect tuples to loop over
        for in_rect, out_rect in zip(self.loc['input'], self.loc['output']):
            # stretch_opt allows you to disable stretching in a given direction
            out_rect.stretch('ur', ref_rect=in_rect, ref_handle='ur', stretch_opt=(True, False))
            in_rect.stretch('t', ref_rect=out_rect, ref_handle='t')
            self.connect_wires(in_rect, out_rect)


if __name__ == '__main__':
    # The following code checks if there is a bag project already running and uses it
    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()
    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    spec_file = 'ACG/examples/specs/Getting_Started_Test2_specs.yaml'

    ALM = AyarDesignManager(bprj, spec_file=spec_file)
    ALM.generate_layout()
