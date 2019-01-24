"""
via_test.py

Unit test module for ACG that exercises the creation of metals and vias.
"""
from ACG.AyarLayoutGenerator import AyarLayoutGenerator


class TestViaCreation(AyarLayoutGenerator):
    """
    Class that creates PC and M1 shapes and attempts to place vias
    """
    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        AyarLayoutGenerator.__init__(self, temp_db, lib_name, params, used_names, **kwargs)

    @classmethod
    def get_params_info(cls):
        return dict(
            bot_layer='name of the bottom layer',
            top_layer='name of the top layer',
            bot_x='x size in microns of the bot layer',
            bot_y='y size in microns of the bot layer',
            top_x='x size in microns of the top layer',
            top_y='y size in microns of the top layer'
        )

    def layout_procedure(self):
        print('--- Running via creation test ---')
        bot_layer = self.params['bot_layer']
        top_layer = self.params['top_layer']
        bot_x = self.params['bot_x']
        bot_y = self.params['bot_y']
        top_x = self.params['top_x']
        top_y = self.params['top_y']

        # Create a default rectangle for each layer
        bot = self.add_rect(layer=bot_layer)
        top = self.add_rect(layer=top_layer)

        # Set the size of the PC and M1 rectangles to be the minimum
        bot.set_dim('x', bot_x)
        bot.set_dim('y', bot_y)
        top.set_dim('x', top_x)
        top.set_dim('y', top_y)

        # Attempt to place a via in between them
        via = self.connect_wires(bot, top)
        # via = self.connect_wires(bot, top, extend=(False, False))


if __name__ == '__main__':
    """ Via Unit Test """
    from bag import BagProject
    from ACG.AyarDesignManager import AyarDesignManager

    # The following code checks if there is a bag project already running and uses it
    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()
    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    spec_file = 'ACG/tests/specs/TestViaCreation.yaml'
    ADM = AyarDesignManager(bprj, spec_file)
    ADM.generate_layout()
