from bag import BagProject
from ACG.AyarDesignManager import AyarDesignManager
from ACG.AyarLayoutGenerator import AyarLayoutGenerator


class CadenceImportTest(AyarLayoutGenerator):
    """ This tests the Cadence Layout import functionality """

    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        AyarLayoutGenerator.__init__(self, temp_db, lib_name, params, used_names, **kwargs)

    @classmethod
    def get_params_info(cls):
        return dict(
            libname='library to import the cell from',
            cellname='name of cell to import'
        )

    def layout_procedure(self):
        master = self.import_cadence_layout(libname=self.params['libname'],
                                            cellname=self.params['cellname'])
        inst = self.add_instance(master=master, loc=(10, 10))
        print(inst.loc)


if __name__ == '__main__':
    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()
    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    spec_file = 'ACG/tests/specs/TestCadenceImport.yaml'
    ADM = AyarDesignManager(bprj, spec_file)
    ADM.generate_layout()
