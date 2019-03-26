import os
import importlib
from bag.io import read_yaml
from bag.layout.routing import RoutingGrid
from bag.layout.template import TemplateDB
# TB imports
from bag.data import load_sim_results, save_sim_results, load_sim_file


class AyarDesignManager:
    """
    Class that oversees the creation of layouts, schematics, testbenches, and simulations. Overrides DesignMaster for
    more intuitive yaml file organization and handles the RoutingGrid in grid-free layouts
    """

    def __init__(self, bprj, spec_file, gds_layermap=''):
        self.prj = bprj
        self.tdb = None  # templateDB instance for layout creation
        self.impl_lib = None  # Virtuoso library where generated cells are stored
        self.cell_name_list = None  # list of names for each created cell
        self.specs = read_yaml(spec_file)

        # Initialize self.tdb with appropriate templateDB instance
        self.make_tdb(gds_layermap)

    """
    GENERATION METHODS - call these methods to generate and simulate your designs
    """

    def run_flow(self):
        """
        Override and call this method to specify your design procedure when subclassing
        """
        pass

    def generate_layout(self, layout_params_list=None, cell_name_list=None):
        """
        Generates a batch of layouts with the layout package/class in the spec file with parameters set by
        layout_params_list and names them according to cell_name_list. Each dict in the layout_params_list creates a
        new layout

        layout_params_list : :obj:'list' of :obj:'dict'
            list of parameter dicts to be applied to the specified layout class
        cell_name_list : :obj:'list' of :obj:'str'
            list of names to be applied to each implementation of the layout class
        """
        # If no list is provided, extract parameters from the provided spec file
        if layout_params_list is None:
            if 'layout_params' in self.specs:
                layout_params_list = [self.specs['layout_params']]
            else:
                layout_params_list = [self.specs['dsn_params']]
        if cell_name_list is None:
            cell_name_list = [self.specs['impl_cell']]
        # Reformat provided lists
        if type(layout_params_list) is not list:
            layout_params_list = [layout_params_list]
        if type(cell_name_list) is not list:
            cell_name_list = [cell_name_list]

        print('Generating Layout')
        cls_package = self.specs['layout_package']
        cls_name = self.specs['layout_class']

        lay_module = importlib.import_module(cls_package)
        temp_cls = getattr(lay_module, cls_name)

        temp_list = []
        for lay_params in layout_params_list:
            template = self.tdb.new_template(params=lay_params, temp_cls=temp_cls, debug=False)
            temp_list.append(template)

        self.tdb.batch_layout(self.prj, temp_list, cell_name_list)

    def generate_schematic(self, sch_params_list=None, cell_name_list=None):
        """
        Generates a batch of schematics specified by sch_params_list and names them according to cell_name_list.
        Each dict in the sch_params_list creates a new schematic

        Parameters
        ----------
        sch_params_list : :obj:'list' of :obj:'dict'
            parameter dicts to be applied to the specified layout class
        cell_name_list : :obj:'list' of :obj:'str'
            list of names to be applied to each implementation of the layout class
        """
        # If no list is provided, extract parameters from the provided spec file
        if sch_params_list is None:
            if 'sch_params' in self.specs:
                sch_params_list = [self.specs['sch_params']]
            else:
                sch_params_list = [self.specs['dsn_params']]
        if cell_name_list is None:
            cell_name_list = [self.specs['impl_cell']]
        if type(sch_params_list) is not list:
            sch_params_list = [sch_params_list]
        if type(cell_name_list) is not list:
            cell_name_list = [cell_name_list]

        print('Generating Schematic')
        sch_temp_lib = self.specs['sch_temp_lib']
        sch_temp_cell = self.specs['sch_temp_cell']
        impl_lib = self.specs['impl_lib']

        inst_list, name_list = [], []
        for sch_params, cur_name in zip(sch_params_list, cell_name_list):
            dsn = self.prj.create_design_module(sch_temp_lib, sch_temp_cell)
            dsn.design(**sch_params)
            inst_list.append(dsn)
            name_list.append(cur_name)

        self.prj.batch_schematic(impl_lib, inst_list, name_list=name_list)

    def generate_tb(self, tb_params_list=None, tb_name_list=None):
        """
        Generates a batch of testbenches specified by tb_params_list and names them according to tb_name_list.
        Each dict in tb_params_list creates a new set of tb's

        Parameters
        ----------
        tb_params_list : :obj:'list' of :obj:'dict'
            list of parameter dicts to be applied to the testbench generator class
        tb_name_list : :obj:'list' of :obj:'str'
            list of names to be applied to each implementation of the tb class
        """
        # If no info is provided, extract parameters from the provided spec file
        if tb_params_list is None or tb_name_list is None:
            tb_name_list = self.specs['tb_params'].keys()
            tb_params_list = self.specs['tb_params'].values()

        print('Generating Testbench')
        impl_lib = self.specs['impl_lib']
        impl_cell = self.specs['impl_cell']

        for info, name in zip(tb_params_list, tb_name_list):
            tb_lib = info['tb_lib']
            tb_cell = info['tb_cell']
            tb_sch_params = info['tb_sch_params']
            # If dut lib/cell is provided, override the impl lib/cell
            if 'dut_lib' in info and 'dut_cell' in info:
                impl_lib = info['dut_lib']
                impl_cell = info['dut_cell']

            tb_dsn = self.prj.create_design_module(tb_lib, tb_cell)
            tb_dsn.design(dut_lib=impl_lib, dut_cell=impl_cell, **tb_sch_params)
            tb_dsn.implement_design(impl_lib, top_cell_name=name)

    def simulate(self):
        """
        Runs a batch of simulations on the generated TB's. All parameters for simulation are set within the spec file
        """
        print('Running Simulation')
        impl_lib = self.specs['impl_lib']
        impl_cell = self.specs['impl_cell']

        results_dict = {}
        for tb_impl_cell, info in self.specs['tb_params'].items():
            tb_params = info['tb_sim_params']
            view_name = info['view_name']
            sim_envs = info['sim_envs']
            data_dir = info['data_dir']

            # setup testbench ADEXL state
            print('setting up %s' % tb_impl_cell)
            tb = self.prj.configure_testbench(impl_lib, tb_impl_cell)
            # set testbench parameters values
            for key, val in tb_params.items():
                tb.set_parameter(key, val)
            # set config view, i.e. schematic vs extracted
            tb.set_simulation_view(impl_lib, impl_cell, view_name)
            # set process corners
            tb.set_simulation_environments(sim_envs)
            # commit changes to ADEXL state back to database
            tb.update_testbench()
            print('running simulation')
            tb.run_simulation()
            print('simulation done, load results')
            results = load_sim_results(tb.save_dir)
            save_sim_results(results, os.path.join(data_dir, '%s.hdf5' % tb_impl_cell))
            results_dict[tb_impl_cell] = results

        print('all simulation done')
        return results_dict

    def run_LVS(self, cell_name_list=None):
        """
        Runs LVS on a batch of cells contained within the implementation library

        Parameters
        ----------
        cell_name_list : :obj:'list' of :obj:'str'
            list of strings containing the names of the cells we should run LVS on
        """
        if not cell_name_list:
            cell_name_list = [self.specs['impl_cell']]

        for cell_name in cell_name_list:
            print('Running LVS on {}'.format(cell_name))
            lvs_passed, lvs_log = self.prj.run_lvs(self.impl_lib, cell_name)
            if lvs_passed:
                print('\n' + 'LVS Clean :)')
            else:
                print('\n' + 'LVS Incorrect :(')
                print('LVS log path: {}'.format(lvs_log))

    def run_PEX(self, cell_name_list):
        """
        Runs PEX on a batch of cells contained within the implementation library

        Parameters
        ----------
        cell_name_list : :obj:'list' of :obj:'str'
            list of strings containing the names of the cells we should run PEX on
        """
        for cell_name in cell_name_list:
            print('Running PEX on {}'.format(cell_name))
            pex_passed, pex_log = self.prj.run_rcx(self.impl_lib, cell_name, create_schematic=True)
            if pex_passed:
                print('\n' + 'PEX Passed :)')
            else:
                print('\n' + 'PEX Failed :(')
                print('PEX log path: {}'.format(pex_log))

    def load_sim_data(self):
        """
        Returns simulation data for all TBs in spec file
        """
        results_dict = {}
        for name, info in self.specs['tb_params'].items():
            data_dir = info['data_dir']
            fname = os.path.join(data_dir, '%s.hdf5' % name)
            print('loading simulation data for %s' % name)
            results_dict[name] = load_sim_file(fname)

        print('finish loading data')
        return results_dict

    def import_schematic_library(self, lib_name):
        """
        Imports a Cadence library containing schematic templates for use in BAG, this must be called if
        changes to the schematic were made since the last run

        Parameters
        ----------
        lib_name : str
            string containing name of the library to be imported
        """
        self.prj.import_design_library(lib_name)

    """
    HELPER METHODS - These should not need to be called by any subclass or external routine
    """

    def make_tdb(self, layermap=''):
        """
        Makes a new TemplateDB object. If no routing grid parameters are sent in, dummy parameters are used.
        """
        self.impl_lib = self.specs['impl_lib']

        # Default routing grid settings
        layers = [1, 2, 3, 4, 5]
        spaces = [0.1, 0.1, 0.1, 0.1, 0.2]
        widths = [0.1, 0.1, 0.1, 0.1, 0.2]
        bot_dir = 'y'
        routing_grid = RoutingGrid(self.prj.tech_info, layers, spaces, widths, bot_dir)
        self.tdb = TemplateDB('template_libs.def',
                              routing_grid,
                              self.impl_lib,
                              use_cybagoa=True,
                              prj=self.prj,
                              gds_lay_file=layermap)
