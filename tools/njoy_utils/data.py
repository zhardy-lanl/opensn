import os
import utils


class BaseData:
    """A container class for common NJOY inputs.
    """

    def __init__(self, **kwargs):

        # Get ENDF file
        if 'endf' not in kwargs:
            raise AssertionError('No ENDF path specified.')
        utils.validate_filepath(kwargs.get('endf'))
        self.endf = kwargs.get('endf')

    @staticmethod
    def parse_endf_info(path, element_only=False, thermal=False):
        """
        Returns info from an ENDF file.

        :param str path: Path to an ENDF file
        :param bool element_only: A flag to only return element data.
        :param bool thermal: A flag to return only the thermal scattering material name.
        :return int: Atomic number, if `thermal=False`
        :return str: Elemental symbol, if `thermal=False`
        :return int: Mass number, if `element_only=thermal=False`
        :return str: Metastable state, if `element_only=thermal=False`
        :return str: Material name, if `thermal=True`
        """
        with open(path, 'r') as endf:
            for _ in range(6):
                line = endf.readline()

        if not thermal:
            z, a = int(line[:3]), int(line[7:10])
            sym, meta = line[4:6].strip(), line[10:11].strip()
            return (z, sym) if element_only else (z, a, sym, meta)
        else:
            return line.split()[0]

    @staticmethod
    def parse_complex_options(opt):
        """
        Parses group structure or weight function input options.

        :param int or str opt: A standard NJOY group structure option (int) or a
            custom group structure path (str).
        :return int: The group structure option to use for NJOY.
        :return str: A path to a custom group structure file or empty.
        """
        if not isinstance(opt, (int, str)):
            raise TypeError(
                'Group structure or weight function options must be either an int or a str.')
        if opt == 1:
            raise AssertionError(
                'A value of 1 is for custom group structure or weight function files. Replace the '
                'option with the appropriate custom path.')
        return opt, '' if isinstance(opt, int) else 1, opt

    @staticmethod
    def parse_material_number(path):
        """
        Returns the ENDF material number.

        :param str path: Path to an ENDF file
        :return int: ENDF material number
        """
        with open(path, 'r') as endf:
            for line in endf:
                if 'MATERIAL' in line:
                    return int(line.split()[2])
            raise AssertionError(f'No material number found in {path}.')


class StandardData(BaseData):
    """A container class for standard neutron, gamma, and photo-atomic NJOY inputs.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Get isotope info from ENDF file
        is_isotope = kwargs.get('is_isotope', True)
        info = self.parse_endf_info(self.endf, element_only=not is_isotope)
        if is_isotope:
            self.atomic_number, self.mass_number = info[0], info[1]
            self.symbol, self.metastable = info[2], info[3]
        else:
            self.atomic_number, self.symbol = info[0], info[1]
        self.matnum = self.parse_material_number(self.endf)

        # Group structure options
        if 'num_grps' not in kwargs:
            raise AssertionError('Number of energy groups must be specified with \'num_grps\'')
        self.num_grps = kwargs.get('num_grps')

        self.grps_opt, self.grps_path = None, None
        if 'group_structure' in kwargs:
            opt = self.parse_complex_options(kwargs.get('group_structure'))
            self.grps_opt = opt[0]
            self.grps_path = opt[1] if self.grps_opt == 1 else None
            if self.grps_path:
                utils.validate_filepath(self.grps_path)

        # Weight function options
        self.wgt_opt, self.wgt_path = None, None
        if 'weight_function' in kwargs:
            opt = self.parse_complex_options(kwargs.get('weight_function'))
            self.wgt_opt = opt[0]
            self.wgt_path = opt[1] if self.wgt_opt == 1 else None
            if self.wgt_path:
                utils.validate_filepath(self.wgt_path)


class NeutronData(StandardData):
    """A container class for neutron NJOY inputs.

    This class contains relevant inputs ultimately necessary for the
    GROUPR NJOY module and its predecessors.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Validate group structure, default lanl 30 group
        self.grps_opt = 3 if self.grps_opt is None else self.grps_opt
        if self.grps_opt < 1 or self.grps_opt > 34:
            raise AssertionError('Allowable neutron group structure options are 1-34.')

        # Validate weight function, default (thermal) -- (1/e) -- (fission + fusion)
        self.wgt_opt = 6 if self.wgt_opt is None else self.wgt_opt
        if self.wgt_opt < 0 or self.wgt_opt > 12:
            raise AssertionError('Allowable neutron weight function options are 0-12.')


class GammaData(StandardData):
    """A container class for gamma (photo-nuclear) data.

    This class contains relevant inputs ultimately necessary for the
    GROUPR NJOY module and its predecessors.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Validate group structure, default lanl 12 group
        self.grps_opt = 3 if self.grps_opt is None else self.grps_opt
        if self.grps_opt < 0 or self.grps_opt > 10:
            raise AssertionError('Allowable gamma group structure options are 0-10.')


class PhotoatomicData(StandardData):
    """A container class for photo-atomic data.

    This class contains relevant inputs ultimately necessary for the
    GAMINR NJOY module and its predecessors.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Validate group structure, default lanl 12 group
        self.grps_opt = 3 if self.grps_opt is None else self.grps_opt
        if self.grps_opt < 0 or self.grps_opt > 10:
            raise AssertionError('Allowable gamma group structure options are 1-10.')

        # Validate weight function, default constant
        self.wgt_opt = 2 if self.wgt_opt is None else self.wgt_opt
        if self.wgt_opt < 1 or self.wgt_opt > 3:
            raise AssertionError('Allowable gamma weight function options are 1-3.')


class ThermalScatteringData(BaseData):
    """
    A container class for thermal scattering data.

    This class contains relevant inputs ultimately necessary for the
    THERMR NJOY module and its predecessors.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Get info from ENDF file
        self.mat_name = self.parse_endf_info(self.endf, thermal=True)
        self.matnum = self.parse_material_number(self.endf)

        # Get number of atoms in the molecule
        if 'num_atoms' not in kwargs:
            raise AssertionError('The number of atoms must be specified with \'num_atoms\'.')
        self.num_atoms = kwargs.get('num_atoms')

        # Get the inelastic scattering MT reaction number
        if 'mti' not in kwargs:
            raise AssertionError('The inelastic thermal scattering reaction number must be '
                                 'specified with \'mti\'.')
        self.mti = kwargs.get('mti')

        # Get the coherent scattering MT reaction number
        self.mtc = kwargs.get('mtc')
