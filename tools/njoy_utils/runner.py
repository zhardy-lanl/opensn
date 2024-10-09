import os
import sys
import argparse
import textwrap
import subprocess

import utils
from data import NeutronData
from data import GammaData
from data import PhotoatomicData
from data import ThermalScatteringData
from njoy import NJOY
from reader import NJOYReader

if __name__ == '__main__':
    # Check Python version
    if sys.version_info[0] < 3:
        print(f'\nError: This script requires python3 but was executed '
              f'with version:\n\n{sys.version}\n')
        sys.exit(1)

    # Define parser
    parser = argparse.ArgumentParser(
        description='Prepares input/output files for NJOY2016 and executes NJOY2016',
        formatter_class=utils.CustomFormatter,
        epilog=textwrap.dedent('''\
        Additional information:
          Neutron group structure options (ign):
           1   arbitrary structure (read in)
           2   csewg 239-group structure
           3   lanl 30-group structure
           4   anl 27-group structure
           5   rrd 50-group structure
           6   gam-i 68-group structure
           7   gam-ii 100-group structure
           8   laser-thermos 35-group structure
           9   epri-cpm 69-group structure
           10  lanl 187-group structure
           11  lanl 70-group structure
           12  sand-ii 620-group structure
           13  lanl 80-group structure
           14  eurlib 100-group structure
           15  sand-iia 640-group structure
           16  vitamin-e 174-group structure
           17  vitamin-j 175-group structure
           18  xmas nea-lanl
           19  ecco 33-group structure
           20  ecco 1968-group structure
           21  tripoli 315-group structure
           22  xmas lwpc 172-group structure
           23  vit-j lwpc 175-group structure
           24  shem cea 281-group structure
           25  shem epm 295-group structure
           26  shem cea/epm 361-group structure
           27  shem epm 315-group structure
           28  rahab aecl 89-group structure
           29  ccfe 660-group structure (30 MeV)
           30  ukaea 1025-group structure (30 MeV)
           31  ukaea 1067-group structure (200 MeV)
           32  ukaea 1102-group structure (1 GeV)
           33  ukaea 142-group structure (200 MeV)
           34  lanl 618-group structure
           
           Neutron group structure weighting options (iwt):
           1   read in smooth weight function
           2   constant
           3   1/e
           4   1/e + fission spectrum + thermal maxwellian
           5   epri-cell lwr
           6   (thermal) -- (1/e) -- (fission + fusion)
           7   same with t-dep thermal part
           8   thermal--1/e--fast reactor--fission + fusion
           9   claw weight function
           10  claw with t-dependent thermal part
           11  vitamin-e weight function (ornl-5505)
           12  vit-e with t-dep thermal part
           
          Gamma group structure options (igg):
           0   none
           1   arbitrary structure (read in)
           2   csewg 94-group structure
           3   lanl 12-group structure
           4   steiner 21-group gamma-ray structure
           5   straker 22-group  structure
           6   lanl 48-group structure
           7   lanl 24-group structure
           8   vitamin-c 36-group structure
           9   vitamin-e 38-group structure
           10  vitamin-j 42-group structure
           
           Gamma group structure weighting options (giwt):
           1   read in smooth weight function
           2   constant
           3   1/e + rolloffs
           
        Example Custom group structure file:
        ------
        # Number of groups
        31/
        # Group boundaries
        1.0000e-05 4.6589e+05 9.3178e+05 1.3977e+06 1.8636e+06 2.3295e+06
        2.7953e+06 3.2612e+06 3.7271e+06 4.1930e+06 4.6589e+06 5.1248e+06
        5.5907e+06 6.0566e+06 6.5225e+06 6.9884e+06 7.4775e+06 7.9434e+06
        8.4093e+06 8.8752e+06 9.3411e+06 9.8070e+06 1.0273e+07 1.0739e+07
        1.1205e+07 1.1671e+07 1.2136e+07 1.2602e+07 1.3068e+07 1.3534e+07
        1.3999e+07 1.4000e+07/
        ------
        
        Example Custom smooth weight function:
        See spectrum_file.txt
        '''))

    parser.add_argument(
        '-exe', '--njoy-executable',
        type=str, default='njoy',
        help='The NJOY executable')

    parser.add_argument(
        '--neutron-endf',
        type=str,
        help='Path to an incident neutron ENDF file.')

    parser.add_argument(
        '--gamma-endf',
        type=str,
        help='Path the incident gamma ENDF file.')

    parser.add_argument(
        '--photoat-endf',
        type=str,
        help='Path to photo-atomic ENDF file.')

    parser.add_argument(
        '--thermal-endf',
        type=str,
        help='Path to S(alpha, beta) thermal scattering ENDF file.')

    parser.add_argument(
        '--neutron-num-groups',
        type=int, required=True,
        help='The number of neutron energy groups.')

    parser.add_argument(
        '--neutron-group-structure',
        type=int, default=3, choices=[*range(1, 35)],
        help=textwrap.dedent('''\
        The neutron group structure. 
        If 1, --custom-neutron-gs-file is required.
        Default 3, LANL 30-group structure.'''))

    parser.add_argument(
        '--custom-neutron-gs-file',
        type=str,
        help=textwrap.dedent('''\
        The path to the custom neutron group structure file. 
        If --neutron-group-structure is not 1, this is ignored.'''))

    parser.add_argument(
        '--neutron-weight-function',
        type=int, default=6, choices=[*range(1, 13)],
        help=textwrap.dedent('''\
        The neutron weight function. 
        If 1, --custom-neutron-wt-file is required.
        Default 8, thermal--1/e--fast reactor--fission + fusion.'''))

    parser.add_argument(
        '--custom-neutron-wt-file',
        type=str,
        help=textwrap.dedent('''\
        The path to the custom neutron weight function file.
        If --neutron-weight-function is not 1, this is ignored.'''))

    parser.add_argument(
        '--gamma-num-groups',
        type=int, default=0,
        help='The number of gamma energy groups.')

    parser.add_argument(
        '--gamma-group-structure',
        type=int, default=0, choices=[*range(0, 11)],
        help=textwrap.dedent('''\
        The gamma group structure.
        If 1, --custom-gamma-gs-file is required.
        Default 0, no gamma group structure.'''))

    parser.add_argument(
        '--custom-gamma-gs-file',
        type=str,
        help=textwrap.dedent('''\
        The path to the custom gamma group structure file.
        If --gamma-group-structure is not 1, this is ignored.'''))

    parser.add_argument(
        '--gamma-weight-function',
        type=int, default=2, choices=[*range(1, 4)],
        help=textwrap.dedent('''\
        The gamma weight function.
        If 1, --custom-gamma-wt-file is required.
        Default 2, constant.'''))

    parser.add_argument(
        '--custom-gamma-wt-file',
        type=str,
        help=textwrap.dedent('''\
        The path to the custom gamma weight function file.
        If --gamma-weight-function is not 1, this is ignored.'''))

    parser.add_argument(
        '--temperature',
        type=float, default=296.0,
        help='The material temperature.')

    parser.add_argument(
        '--thermal-inelastic-mt',
        type=int,
        help='MT number to use for incoherent inelastic scattering.')

    parser.add_argument(
        '--thermal-coherent-mt',
        type=int,
        help='MT number to use for coherent/incoherent elastic scattering.')

    parser.add_argument(
        '--thermal-num-atoms',
        type=int, default=1,
        help='Number of atoms in the thermal scattering molecule.')

    parser.add_argument(
        '--no-thermal',
        action='store_true', default=False,
        help='A flag for excluding any thermal scattering.')

    parser.add_argument(
        '--fissionable',
        action='store_true', default=False,
        help='A flag for fissionable materials.')

    parser.add_argument(
        '--output-directory',
        type=str, default=os.getcwd(),
        help=textwrap.dedent('''\
        A directory to save the output to.
        If unspecified, output are saved to the current directory.'''))

    parser.add_argument(
        '--output-filename',
        type=str, default='NJOY_INPUT.txt',
        help=textwrap.dedent('''\
        A filename to save the output to.
        If unspecified, output are given a generic name.'''))

    argv = parser.parse_args()

    # Build neutron data
    ngs_opt = argv.neutron_group_structure
    ngs_path = argv.custom_neutron_gs_file
    ngs = ngs_path if ngs_path else ngs_opt

    nwt_opt = argv.neutron_weight_function
    nwt_path = argv.custom_neutron_wt_file
    nwt = nwt_path if nwt_path else nwt_opt

    neutron_data = NeutronData(endf=argv.neutron_endf,
                               num_grps=argv.neutron_num_groups,
                               group_structure=ngs,
                               weight_function=nwt)

    # Build gamma and photoatomic data
    gamma_data, photoat_data = None, None
    if argv.gamma_num_groups > 0:
        ggs_opt = argv.gamma_group_structure
        ggs_path = argv.custom_gamma_gs_file
        ggs = ggs_path if ggs_path else ggs_opt

        gwt_opt = argv.gamma_weight_function
        gwt_path = argv.custom_gamma_wt_file
        gwt = gwt_path if gwt_path else gwt_opt

        if argv.gamma_endf:
            gamma_data = GammaData(endf=argv.gamma_endf,
                                   num_grps=argv.gamma_num_groups,
                                   group_structure=ggs)
        if argv.photoat_endf:
            photoat_data = PhotoatomicData(endf=argv.photoat_endf,
                                           num_grps=argv.gamma_num_groups,
                                           group_structure=ggs,
                                           weight_function=gwt,
                                           is_isotope=False)

    # Build thermal data
    thermal_data = None
    if not argv.no_thermal and argv.thermal_endf:
        thermal_data = ThermalScatteringData(endf=argv.thermal_endf,
                                             num_atoms=argv.thermal_num_atoms,
                                             mti=argv.thermal_inelastic_mt,
                                             mtc=argv.thermal_coherent_mt)

    njoy = NJOY(neutron_data, gamma_data, photoat_data, thermal_data, not argv.no_thermal,
                argv.fissionable, argv.temperature)
    njoy.write('NJOY_INPUT.txt')

    output = f'{argv.output_directory}/{argv.output_filename}'
    njoy.run('NJOY_INPUT.txt', f'{output}')

    reader = NJOYReader(f'{output}.njoy')
    reader.read()
