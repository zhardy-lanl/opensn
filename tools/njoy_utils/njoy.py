import os
from data import StandardData
from data import NeutronData
from data import GammaData
from data import PhotoatomicData
from data import ThermalScatteringData


class NJOY:
    _neutron_tape = 20
    _gamma_tape = 60
    _photoat_tape = 70
    _thermal_tape = 50

    def __init__(self, neutron_data=None, gamma_data=None, photoat_data=None,
                 thermal_data=None, with_thermal=True, is_fissionable=False,
                 temperature=296.0):
        """
        :param neutron_data: Data structure for neutron data.
        :type neutron_data: NeutronData, optional
        :param gamma_data: Data structure for gamma data.
        :type gamma_data: GammaData, optional
        :param photoat_data: Data structure for photo-atomic data.
        :type photoat_data: PhotoatomicData, optional
        :param thermal_data: Data structure for S(alpha, beta) thermal scattering data.
        :type thermal_data: ThermalScatteringData, optional
        :param with_thermal: Flag to include thermal scattering treatment. If no S(alpha,beta)
            data is provided, free gas thermal scattering will be used.
        :type with_thermal: bool
        :param is_fissionable: Flag for whether isotope is fissionable.
        :type is_fissionable: bool
        :param temperature: The temperature to evaluate cross-sections.
        :type temperature: float
        """

        self._neutron: NeutronData = neutron_data
        self._gamma: GammaData = gamma_data
        self._photoat: PhotoatomicData = photoat_data
        self._thermal: ThermalScatteringData = thermal_data
        self._temperature = temperature

        self._with_thermal = with_thermal
        self._is_fissionable = is_fissionable

        if self._neutron:
            os.system(f'ln -sf {self._neutron.endf} tape{self._neutron_tape}')
        if self._gamma:
            os.system(f'ln -sf {self._gamma.endf} tape{self._gamma_tape}')
        if self._photoat:
            os.system(f'ln -sf {self._photoat.endf} tape{self._photoat_tape}')
        if self._with_thermal and self._thermal:
            os.system(f'ln -sf {self._thermal.endf} tape{self._thermal_tape}')

    def write(self, filepath='NJOY_INPUT.txt'):
        """Write the NJOY input file.

        :param filepath: Path to write an NJOY input file to.
        :type filepath: str
        """
        lines = ['-- NJOY input ']

        # MODER
        lines.extend(self._moder(20, 21) if self._neutron else [])
        lines.extend(self._moder(60, 61) if self._gamma else [])
        lines.extend(self._moder(70, 71) if self._photoat else [])

        # RECONR
        lines.extend(self._reconr('neutron') if self._neutron else [])
        lines.extend(self._reconr('gamma') if self._gamma else [])
        lines.extend(self._reconr('photoat') if self._photoat else [])

        # BROADR
        lines.extend(self._broadr('neutron') if self._neutron else [])
        lines.extend(self._broadr('gamma') if self._gamma else [])

        # UNRESR
        lines.extend(self._unresr() if self._neutron else [])

        # HEATR
        lines.extend(self._heatr() if self._neutron else [])

        # THERMR
        lines.extend(self._thermr() if self._neutron and self._with_thermal else [])

        # GROUPR
        lines.extend(self._groupr('neutron') if self._neutron else [])
        lines.extend(self._groupr('gamma') if self._gamma else [])

        # GAMINR
        lines.extend(self._gaminr() if self._photoat else [])

        lines.append('stop')

        # Write the input file
        print(f'Writing NJOY input to {filepath}.')
        with open(filepath, 'w') as njoy:
            njoy.write('\n'.join(lines))

    @staticmethod
    def run(input_path, output_path):
        if not os.path.isfile(f'{output_path}.njoy'):
            print(f'Running NJOY input {input_path}')
            os.system(f'njoy < {input_path}')
            print(f'Moving input file to {output_path}.njoy.in')
            os.system(f'mv {input_path} {output_path}.njoy.in')
            print(f'Moving output file to {output_path}.njoy')
            os.system(f'mv output {output_path}.njoy')
            print('Cleaning up NJOY run.')
            os.system('rm tape*')
        else:
            print(f'The output file {output_path}.njoy already exists.')
            if os.path.isfile('NJOY_INPUT.txt'):
                os.system('rm NJOY_INPUT.txt tape*')

    @staticmethod
    def _moder(input_tape, output_tape):
        """Returns a MODER input.

        :param input_tape: The input tape.
        :type input_tape: int
        :param output_tape: The output tape.
        :type output_tape: int
        :return: The MODER input lines.
        :rtype: list of str
        """
        return ['moder', f'{input_tape} -{output_tape}/']

    def _reconr(self, particle):
        """Returns a RECONDR input for the given reaction type.

        :param particle: The incident particle type for this RECONR input.
        :type particle:  str, {'neutron', 'gamma', 'photoat'}
        :return: The RECONR input lines.
        :rtype: list of str
        """
        data = self._get_data(particle)

        lines = ['reconr']
        lines += ['-21 -22/' if particle == 'neutron' else
                  '-61 -62/' if particle == 'gamma' else
                  '-71 -72/']
        lines += [f'\'pendf {particle} tape\'']
        lines += [f'{data.matnum} 0/']
        lines += ['0.001/']
        lines += ['0/']
        return lines

    def _broadr(self, particle):
        """Returns a BROADR input for the given reaction type.

        :param particle: The incident particle type for this BROADR input.
        :type particle:  str, {'neutron', 'gamma'}
        :return: The BROADR input lines.
        :rtype: list of str
        """
        data = self._get_data(particle, ['neutron', 'gamma'])

        lines = ['broadr']
        lines += ['-21 -22 -23/' if particle == 'neutron' else '-61 -62 -63/']
        lines += [f'{data.matnum} 1 0 0 0/']
        lines += ['0.001/']
        lines += [f'{self._temperature}/']
        lines += ['0/']
        return lines

    def _unresr(self):
        """Returns an UNRESR input for neutron reactions.

        :return: The UNRESER input lines.
        :rtype: list of str
        """
        lines = ['unresr']
        lines += ['-21 -23 -24/']
        lines += [f'{self._neutron.matnum} 1 1 0/']
        lines += [f'{self._temperature}/']
        lines += ['0.0/']
        lines += ['0/']
        return lines

    def _heatr(self):
        """Returns a HEATR input for neutron reactions.

        :return: The HEATR input lines.
        :rtype: list of str
        """
        return ['heatr', '-21 -24 -25/', f'{self._neutron.matnum} 0/']

    def _thermr(self):
        """Returns the THERMR input for neutron reactions.

        If thermal scattering data is provided, this routine returns both the free-gas and
        S(alpha, beta) inputs.

        :return: The THERMR input lines.
        :rtype: list of str
        """
        lines = ['thermr']
        lines += ['0 -25 -26/']
        lines += [f'0 {self._neutron.matnum} 16 1 1 0 0 1 221 1/']
        lines += [f'{self._temperature}/']
        lines += ['0.005 5.0/']

        if self._thermal:
            lines += ['thermr']
            lines += ['60 -26 -27/']
            lines += [f'{self._thermal.matnum} {self._neutron.matnum} 16 1 2 0 0 '
                      f'{self._thermal.num_atoms} {self._thermal.mti} 1/']
            lines += [f'{self._temperature}/']
            lines += ['0.005 5.0/']
        return lines

    def _groupr(self, particle):
        """Returns a GROUP input for the given reaction type.

        :param particle: The incident particle type for this GROUP input.
        :type particle:  str, {'neutron', 'gamma'}
        :return: The GROUPR input lines.
        :rtype: list of str
        """
        data = self._get_data(particle, ['neutron', 'gamma'])

        lines = ['groupr']
        if particle == 'neutron':
            lines += ['-21 -27 0 -28/' if self._with_thermal and self._thermal else
                      '-21 -26 0 -28/' if self._with_thermal else
                      '-21 -25 0 -28/']
        else:
            lines += ['-61 -63 0 -64/']

        lines += [f'{data.matnum} {self._neutron.grps_opt} '
                  f'{self._gamma.grps_opt if self._gamma else 0} '
                  f'{self._neutron.wgt_opt} 7 1 1 1 1/']

        lines += [f'\'{data.atomic_number}{data.symbol}{data.mass_number}{data.metastable}\'/']
        lines += [f'{self._temperature}/']
        lines += ['0.0/']

        if self._neutron.grps_opt == 1:
            lines.extend(self._parse_custom_file(self._neutron.grps_path))
        if self._gamma and self._gamma.grps_opt == 1:
            lines.extend(self._parse_custom_file(self._gamma.grps_path))
        if self._neutron.wgt_opt == 1:
            lines.extend(self._parse_custom_file(self._neutron.wgt_path))

        # MF3 cross-sections
        lines += ['3/']

        # Thermal treatments for neutron cross-sections
        if particle == 'neutron' and self._with_thermal:
            lines += ['3 221 \'free gas neutron\'/']
            if self._thermal:
                lines += [f'3 {self._thermal.mti} \'inelastic s(a,b) neutron\'/']
                if self._thermal.mtc:
                    lines += [f'3 {self._thermal.mtc} \'elastic s(a,b) neutron\'/']

        # Fission cross-sections
        if self._is_fissionable:
            lines += [f'3 452 \'total nubar {particle}\'/']
            lines += [f'3 456 \'prompt nubar {particle}\'/']
            lines += [f'5 18 \'prompt chi {particle}\'/']
            lines += [f'3 455 \'delayed nubar {particle}\'/']
            lines += [f'5 455 \'delayed chi {particle}\'/']

        # Energy/speed data
        lines += [f'3 257 \'average energy {particle}\'/']
        if particle == 'neutron':
            lines += [f'3 259 \'inverse velocity neutron\'/']

        # MF6 transfer matrices
        lines += ['6/']

        # Thermal treatments for neutron transfer matrices
        if particle == 'neutron' and self._with_thermal:
            lines += ['6 221 \'free gas neutron matrix\'/']
            if self._thermal:
                lines += [f'6 {self._thermal.mti} \'inelastic s(a,b) neutron matrix\'/']
                if self._thermal.mtc:
                    lines += [f'6 {self._thermal.mtc} \'elastic s(a,b) neutron matrix\'/']

        # Fission transfer matrices
        if self._is_fissionable:
            lines += [f'6 18 \'({particle[0]},fission) neutron matrix\'/']

        # Neutron-to-gamma transfer matrices
        if particle == 'neutron' and self._gamma:
            lines += ['13/']  # MF13 photon production cross-sections
            lines += ['16/']  # MF16 neutron-gamma transfer matrices

        lines += ['0/']  # stop reaction specifications
        lines += ['0/']  # stop groupr

        # Run moder on the groupr output
        # lines += ['moder']
        # lines += ['-28 90/' if particle == 'neutron' else '-64 91/']
        return lines

    def _gaminr(self):
        """Returns the GAMINR input for photo-atomic reactions.

        :return: The GAMINR input lines.
        :rtype: list of str
        """
        lines = ['gaminr']
        lines += ['-71 -72 0 -73']
        lines += [f'{self._photoat.matnum} {self._photoat.grps_opt} {self._photoat.wgt_opt} 7 1/']
        lines += ['\'Photo-Atomic Interactions\'/']

        if self._photoat.grps_opt == 1:
            lines.extend(self._parse_custom_file(self._photoat.grps_path))
        if self._photoat.wgt_opt == 1:
            lines.extend(self._parse_custom_file(self._photoat.wgt_path))

        lines += ['-1/']  # all reaction data
        lines += ['0/']  # stop gaminr

        # Run moder on the gaminr output
        # lines += ['moder']
        # lines += ['-73 92/']
        return lines

    def _macxsr(self, particle):
        """Returns the MATXSR input for the given reaction type.

        :param particle: The incident particle type for this MACXSR input.
        :type particle:  str, {'neutron'}
        :return: The MACXSR input lines.
        :rtype: list of str
        """
        data = self._get_data(particle, ['neutron'])
        lines = ['matxsr']
        lines += ['90 0 97/']
        lines += ['0 \'LANL NJOY\'/']
        lines += ['1 2 1 1/' if self._with_thermal else '1 1 1 1/']
        lines += [f'\'MATXS - {data.num_grps} NEUTRON GROUPS\'/']
        lines += ['\'n\'/']
        lines += [f'{data.num_grps}/']
        lines += [f'\'nscat\'/' if not self._with_thermal else f'\'nscat\' \'ntherm\'/']
        lines += ['1/' if not self._with_thermal else '1 1/']
        lines += ['1/' if not self._with_thermal else '1 1/']
        lines += [f'{self._neutron.symbol.upper()}{self._neutron.mass_number} '
                  f'{self._neutron.matnum}']
        return lines

    def _get_data(self, particle, allow_list=None):
        """Returns the appropriate data structure for the underlying
        particle type.

        :param particle: The incident particle type
        :type particle:  str, {'neutron', 'gamma', 'photoat'}
        :param allow_list: A list of allowable reaction types containing any combination of the
            allowable reaction types.
        :type allow_list: list of str
        :return: The appropriate data structure for the reaction type.
        :rtype: StandardData
        """
        if allow_list is None:
            allow_list = ['neutron', 'gamma', 'photoat']
        if particle not in allow_list:
            raise ValueError(f'Reaction type must be one of {allow_list}.')

        if particle == 'neutron' and self._neutron:
            return self._neutron
        elif particle == 'gamma' and self._gamma:
            return self._gamma
        elif particle == 'photoat' and self._photoat:
            return self._photoat
        else:
            raise AssertionError(f'The requested data for {particle} is not available.')

    @staticmethod
    def _parse_custom_file(path):
        """Parses the contents of a custom group structure or weight function file.

        :param path: Path to a custom group structure or weight function file.
        :return: A list of the lines of the parsed file.
        :rtype: list of str
        """
        lines = []
        with open(path, 'r') as f:
            for line in f:
                if line[0] != '#':
                    lines += [line.strip()]
        return lines
