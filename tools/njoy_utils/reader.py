import sys
import utils
import matplotlib.pyplot as plt


class NJOYReader:

    def __init__(self, path):
        utils.validate_filepath(path)
        self._path = path

        self._groups = {'neutron': {}, 'gamma': {}}
        self._xs = {}
        self._transfers = {'neutron': {}, 'gamma': {}, 'photoat': {}}

    def read(self):
        with open(self._path, 'r') as file:
            lines = file.readlines()

        # Go through the files
        for n in range(len(lines)):
            line = lines[n].strip()
            if not line:
                continue

            # Parse group structures
            if 'sigma zeroes' in line:
                e_bdys = self._process_group_structure(n, lines)
                self._groups['neutron']['e_bdys'] = e_bdys
                self._groups['neutron']['n_grps'] = len(e_bdys) - 1
            if 'gamma group structure......' in line:
                if 'gamma' not in self._groups:
                    e_bdys = self._process_group_structure(n, lines)
                    self._groups['gamma']['e_bdys'] = e_bdys
                    self._groups['gamma']['n_grps'] = len(e_bdys) - 1

            # Stop when reaction data is found
            if line.startswith('for mf') and 'mt' in line:
                entries = line.split()

                # Define the reaction MF and MT numbers
                if entries[1] == 'mf':
                    mf = int(entries[2])
                    mt = int(entries[5] if entries[4] == 'mt' else entries[4].strip('mt'))
                else:
                    mf = int(entries[1].strip('mf'))
                    mt = int(entries[3].strip('mt'))

                # Process standard cross sections
                if mf == 3 and line.endswith('cross section'):
                    # Process cross-sections
                    mtname = entries[-3]
                    self._xs[mtname] = self._process_xs(n, lines)

                    # Process weight spectra with total cross sections
                    if mf == 3 and mt == 1:
                        self._groups['neutron']['wgts'] = self._process_xs(n, lines, True)

                # Process auxiliary vector data
                mtnames = ['inverse velocity', 'average energy',
                           'free gas', 'inelastic s(a,b)', 'elastic s(a,b)',
                           'total nubar', 'prompt nubar', 'delayed nubar']
                if mf == 3:
                    for mtname in mtnames:
                        if mtname in line:
                            particle = entries[-1]
                            mtname = mtname + ' ' + particle
                            self._xs[mtname] = self._process_xs(n, lines)

                # Process spectrum data
                if mf == 5:
                    particle = entries[-1]
                    if 'prompt chi' in line:
                        mtname = 'prompt chi ' + particle
                        self._xs[mtname] = self._process_prompt_chi(n, lines)
                    if 'delayed chi' in line:
                        mtname = 'decay constants ' + particle
                        self._xs[mtname] = self._process_decay_constants(n, lines)
                        mtname = 'delayed chi ' + particle
                        self._xs[mtname] = self._process_delayed_chi(n, lines)

                # Process transfer matrix data
                if line.endswith('matrix'):
                    particle = entries[-2]
                    if 'free gas' in line:
                        mtname = 'free gas'
                    elif 's(a,b)' in line:
                        mtname = f'{entries[-4]} s(a,b)'
                    else:
                        mtname = entries[-3]

                    if 'fission' not in line:
                        self._transfers[particle][mtname] = self._process_transfers(n, lines)
                    else:
                        self._transfers[particle][mtname] = self._process_fission_matrix(n, lines)

                # Process photo-atomic cross sections
                if mf == 23:
                    mtname = entries[-1]
                    self._xs[mtname] = self._process_xs(n, lines)
                    if mt == 522:
                        self._xs[mtname + ' heat'] = self._process_photoat_heat(n, lines)

                # Process photo-atomic transfer matrix data
                if mf == 26:
                    mtname = entries[-1]
                    self._transfers['photoat'][mtname] = self._process_transfers(n, lines, True)
                    if mt == 504 or mt == 516:
                        self._xs[mtname + ' heat'] = self._process_photoat_heat(n, lines)

    def _process_group_structure(self, n, lines):
        """Returns group structure boundaries from highest to lowest.

        :param n: The current line number.
        :type n: int
        :param lines: The list of file lines.
        :type lines: list of str
        :rtype: list
        """
        # Go to the first line of data
        line = lines[n].strip()
        while not line or line.split()[0] != '1':
            n, line = self._advance_line(n, lines)

        # Parse the group structure boundaries
        grp_struct = []
        while line:
            entries = line.split()
            if not grp_struct:
                grp_struct.append(float(entries[1]))
            grp_struct.append(float(entries[3]))
            n, line = self._advance_line(n, lines)
        return grp_struct

    def _process_xs(self, n, lines, wt_spec=False):
        """Returns a cross-section or weight function vector from the highest
        energy group to the lowest.

        :param n: The current line number.
        :type n: int
        :param lines: The list of file lines.
        :type lines: list of str
        :param wt_spec: A flag for whether a weight spectrum is present.
        :type wt_spec: bool
        :rtype: list
        """
        # Go to first line of data
        line = lines[n].strip()
        while not line or not line.split()[0].isdigit():
            n, line = self._advance_line(n, lines)

            # When this is encountered, no data is available
            if line.startswith('group constants'):
                return []

        # Parse the cross-sections
        xs = []
        while len(line.split()) >= 2:
            entries = line.split()
            val = self._string_to_float(entries[1])
            if wt_spec and entries[0] == 'flx':
                xs.append(val)
            elif not wt_spec and entries[0].isdigit():
                grp = int(entries[0]) - 1
                xs.append((grp, val))
            n, line = self._advance_line(n, lines)
        return xs

    def _process_prompt_chi(self, n, lines):
        """Returns the prompt fission spectrum from the highest energy group
        to the lowest.

        :param n: The current line number.
        :type n: int
        :param lines: The list of file lines.
        :type lines: list of str
        :rtype: list
        """
        # Go to first line of data
        n += 6 if 'spectrum constant' in lines[n + 2] else 4
        line = lines[n].strip()

        # Parse the fission spectrum data
        chi = []
        while len(line.split()) >= 2:
            entries = line.split()
            grp = int(entries[0]) - 1
            for g in range(len(entries[1:])):
                val = self._string_to_float(entries[g + 1])
                chi.append((grp + g, val))
            n, line = self._advance_line(n, lines)
        return chi

    def _process_decay_constants(self, n, lines):
        """Returns the delayed neutron decay constants.

        :param n: The current line number.
        :type n: int
        :param lines: The list of file lines.
        :type lines: list of str
        :rtype: list
        """
        # Go to first line of data
        n += 5 if 'spectrum constant' in lines[n + 2] else 3
        line = lines[n].strip()
        if line.split()[0] != 'group':
            raise AssertionError("Unexpected line encountered.")
        return [self._string_to_float(val) for val in line.split()[1:]]

    def _process_delayed_chi(self, n, lines):
        """Returns the delayed neutron emission spectra from the highest
        energy group to the lowest. Each entry is a list containing the
        emission spectrum for a particular group for each delayed neutron
        precursor group.

        :param n: The current line number.
        :type n: int
        :param lines: The list of file lines.
        :type lines: list of str
        :rtype: list
        """
        # Go to first line of data
        n += 7 if "spectrum constant" in lines[n + 2] else 5
        line = lines[n].strip()

        # Parse the emission spectrum data
        chi = []
        while len(line.split()) >= 2:
            entries = line.split()
            grp = int(entries[0]) - 1
            vals = [self._string_to_float(val) for val in entries[1:]]
            chi.append((grp, vals))
            n, line = self._advance_line(n, lines)
        return chi

    def _process_transfers(self, n, lines, overflow=False):
        """Returns a Legendre transfer matrices ordered first by initial group,
        then by final group, then by Legendre order.

        :param n: The current line number.
        :type n: int
        :param lines: The list of file lines.
        :type lines: list of str
        :param overflow: A flag for overflow lines
        :type overflow: bool
        :rtype: list of list
        """
        # Go to the first line of data
        skip = 1 if 'mf26' in lines[n] else 0
        skip += 1 if 'particle emission' in lines[n + 1] else 0
        n += skip + 2

        # Determine matrix type
        if 'legendre' in lines[n]:
            matrix_type = 'legendre'
        elif 'isotropic' in lines[n]:
            matrix_type = 'isotropic'
        else:
            raise AssertionError('Unrecognized matrix type.')

        # Go to the next block of data
        n += 3
        line = lines[n].strip()

        # Parse the transfer matrices
        matrix = []
        while len(line.split()) > 2:

            # There are several cases in which an incompatible line exists
            # within transfer matrix data. Using a try/except block allows
            # these lines to be  skipped without the need to define a list
            # a "buzzwords" to look for. The known cases of bad lines are:
            #
            # 1) For MF26 data, sometimes there is an additional line
            #    containing the group-wise cross-section. This has the
            #    word "xsec" within the line.
            #
            # 2) For MF26 data, sometimes there is an additional line
            #    containing the heating cross-section. This has the word
            #    "heat" within the line.
            #
            # 3) For (n,xn) reactions there are occasionally lines that
            #    feature a normalization value. This has the word
            #    "normalization" within the line.

            try:
                entries = line.split()

                # Parse the data on the line
                gi = int(entries[0]) - 1
                gf = int(entries[1]) - 1
                vals = [self._string_to_float(val) for val in entries[2:]]

                # Check next line for overflow
                if overflow:
                    n, line = self._advance_line(n, lines)
                    entries = lines[n].strip().split()
                    vals.extend([self._string_to_float(val) for val in entries])

                # Store the data
                if matrix_type == 'legendre':
                    matrix.append([gi, gf, vals])
                else:
                    matrix.extend([[gi, gf + g, [vals[g]]] for g in range(len(vals))])
            except (ValueError, IndexError):
                pass
            n, line = self._advance_line(n, lines)
        return matrix

    def _process_fission_matrix(self, n, lines):
        """Returns a Legendre transfer matrices ordered first by initial group,
        then by final group, then by Legendre order.

        :param n: The current line number.
        :type n: int
        :param lines: The list of file lines.
        :type lines: list of str
        :rtype: list of list
        """
        # Go to the first line of data
        n += 4 if 'spectrum constant' in lines[n + 2] else 2

        # Determine matrix type
        if 'legendre' in lines[n]:
            matrix_type = 'legendre'
        elif 'isotropic' in lines[n]:
            matrix_type = 'isotropic'
        else:
            raise AssertionError('Unrecognized matrix type.')

        # Go to the start of the low energy data block
        n += 3
        line = lines[n].strip()

        # Initialize the matrix
        matrix = []

        # Read the spectrum and production data
        if line.split()[0] == 'spec':
            grp = 1
            spec = []
            while line and line.split()[0] == 'spec':
                entries = line.split()

                # Check that no bookkeeping mistakes were made.
                expected_grp = int(entries[1])
                if expected_grp != grp:
                    raise AssertionError('The current group and expected starting '
                                         'group for this line are different.')

                # Parse the data on this line
                grp += len(entries[2:])  # update the current group index
                spec.extend([self._string_to_float(val) for val in entries[2:]])
                n, line = self._advance_line(n, lines)

            # Go to the start of the low energy production data
            n, line = self._advance_line(n, lines)

            # If no production data is found, exit, this matrix should
            # be formed using an outer product formulation with prompt chi,
            # prompt nubar, and the fission cross-section.
            if not line:
                return

            # Otherwise, expect to see the 'prod' keyword
            elif line and line.split()[1] != 'prod':
                raise AssertionError('Unrecognized behavior when trying to read '
                                     'low energy vector production data. \'prod\' '
                                     'keyword not found.')

            # Read the production data
            grp = 1
            prod = []
            while line and line.split()[1] == 'prod':
                entries = line.split()

                # Check that no bookkeeping mistakes were made.
                expected_grp = int(entries[0])
                if expected_grp != grp:
                    raise AssertionError('The current group and expected starting '
                                         'group for this line are different.')

                # Parse the data on this line
                grp += len(entries[2:])  # update the current group index
                prod.extend([self._string_to_float(val) for val in entries[2:]])
                n, line = self._advance_line(n, lines)

            # Initialize the matrix with the outer product data
            for gi in range(len(prod)):
                for gf in range(len(spec)):
                    matrix.append((gi, gf, [spec[gf] * prod[gi]]))

            # Go to the start of the fission matrix
            n, line = self._advance_line(n, lines)

        while len(line.split()) > 2:
            entries = line.split()

            # Parse the data on the line
            gi = int(entries[0]) - 1
            gf = int(entries[1]) - 1
            vals = [self._string_to_float(val) for val in entries[2:]]

            # Store the data
            if matrix_type == 'legendre':
                matrix.append([gi, gf, vals])
            else:
                matrix.extend([(gi, gf + g, [vals[g]]) for g in range(len(vals))])

            n, line = self._advance_line(n, lines)
        return matrix

    def _process_photoat_heat(self, n, lines):
        """Returns the heating from photo-atomic interactions.

        :param n: The current line number.
        :type n: int
        :param lines: The list of file lines.
        :type lines: list of str
        :rtype: list of list
        """
        skip = 4

        # Parse heating data
        heat = []
        if 'mf26' in lines[n]:
            n += skip
            line = lines[n].strip()
            while len(line.split()) >= 2:
                if 'heat' in lines[n]:
                    entries = line.split()
                    grp = int(entries[0]) - 1
                    val = self._string_to_float(entries[-1])
                    heat.append((grp, val))
                n, line = self._advance_line(n, lines)
        elif 'mf23' in lines[n] and 'mt522' in lines[n]:
            n += skip
            line = lines[n].strip()
            while len(line.split()) == 3:
                entries = line.split()
                grp = int(entries[0]) - 1
                val = self._string_to_float(entries[-1])
                heat.append((grp, val))
                n, line = self._advance_line(n, lines)
        else:
            raise AssertionError('Unrecognized reaction type for heating.')
        return heat

    @staticmethod
    def _get_particle_type(mf, line):
        """Returns the particle type given an MF number and the
        corresponding line the reaction type is printed on.

        :param mf: The MF reaction category.
        :type mf: int
        :param line: The line the reaction type is printed on.
        :type line: str
        :rtype: str
        """

        if mf == 3:
            if line.endswith('cross section'):
                if '(n,' in line:
                    return 'neutron'
                elif '(g,' in line:
                    return 'gamma'
                else:
                    raise AssertionError(f'Unrecognized particle type on '
                                         f'line {line}.')
            else:
                if 'free gas' in line or 's(a,b)' in line:
                    return 'neutron'
                else:
                    return line[line.rfind('(') + 1:line.rfind(')')]
        elif mf == 5:
            if 'chi' in line:
                return line[line.rfind('(') + 1:line.rfind(')')]
        elif mf == 6:
            if line.endswith('matrix'):
                if 'free gas' in line or 's(a,b)' in line:
                    return 'neutron'

    @staticmethod
    def _advance_line(n, lines):
        if n < len(lines):
            return n + 1, lines[n + 1].strip()
        else:
            return n, ''

    @staticmethod
    def _string_to_float(string):
        """Returns the value represented by a string

        :param string: A float string.
        :type string: str
        :rtype: float
        """
        if 'E' in string or 'e' in string:
            return float(string)

        number = string.replace("+", "E+")
        if "-" in number:
            if number.count("-") == 2:
                pos = number.rfind("-")
                number = f"{number[:pos]}E-{number[pos + 1:]}"
            elif number.find("-") != 0:
                number = number.replace("-", "E-")
        return float(number)
