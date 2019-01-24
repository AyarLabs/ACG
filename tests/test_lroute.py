from ACG.AyarLayoutGenerator import AyarLayoutGenerator
from ACG.AutoRouter import AutoRouter


class TestLRoute(AyarLayoutGenerator):
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
            bot_loc='center in microns of the bot layer',
            bot_size='xy size in microns of the bot layer',
            top_loc='center in microns of the top layer',
            top_size='xy size in microns of the top layer'
        )

    def layout_procedure(self):
        print('--- Running LRoute test ---')
        bot_layer = self.params['bot_layer']
        top_layer = self.params['top_layer']
        bot_loc = self.params['bot_loc']
        bot_size = self.params['bot_size']
        top_loc = self.params['top_loc']
        top_size = self.params['top_size']

        # Create a default rectangle for each layer
        bot = self.add_rect(layer=bot_layer)
        top = self.add_rect(layer=top_layer)

        # Size up and align the rectangles
        bot.set_dim('x', bot_size[0])
        bot.set_dim('y', bot_size[1])
        bot.align(target_handle='c', offset=bot_loc)
        top.set_dim('x', top_size[0])
        top.set_dim('y', top_size[1])
        top.align(target_handle='c', offset=top_loc)

        # Attempt to place a route in between them
        router = AutoRouter(self)
        router.stretch_l_route(start_rect=bot, start_dir='y', end_rect=top)


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

    spec_file = 'ACG/tests/specs/TestLRoute.yaml'
    ADM = AyarDesignManager(bprj, spec_file)
    ADM.generate_layout()
