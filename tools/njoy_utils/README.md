# NJOY Utilities

Prepares NJOY inputs and converts NJOY output to multi-group transport
cross-section formats. This utility is meant to be expanded upon as needed to support
a number of different multi-group transport cross-section formats.

## How to use this converter

### Step 1: Download and set up your flavor of ENDF

- The full ENDF/B-VIII.0 library (Preferred)
  [ENDF-BVIII.0](https://www.nndc.bnl.gov/endf-b8.0/download.html)
  (~500Mb on download, ~2Gb extracted)
- The entire ENDF7.1 library
  [ENDF-BVII.1](https://www.nndc.bnl.gov/endf-b7.1/download.html)
- Older versions.
  Go to Brookhaven National Laboratory's site
  [National Nuclear Data Center](https://www.nndc.bnl.gov/endf-b8.0)
  and download what you need.

Extract this library in a directory of your choice.

For example, on Linux machines, you can do this using:

- ```shell 
  curl -O https://www.nndc.bnl.gov/endf/b8.0/zips/ENDF-B-VIII.0.zip
  ```
- unzip using the ```unzip``` command
- set the envrionement variable `ENDF_ROOT` to where ENDF was extracted.
  In bash, this is
  ```shell
  export ENDF_ROOT=<path-to-endf>
  ``` 

### Step 2: Download and install NJOY2016

This converter processes NJOY2016 output files.
Note that rigorous testing for each version has not been performed.
NJOY2016 is hosted on GitHub at
[https://github.com/njoy/NJOY2016](https://github.com/njoy/NJOY2016).
After this is completed, go to a directory where you would like to unpack NJOY2016 and run:

```shell
# Download the source code
git clone https://github.com/njoy/NJOY2016
cd NJOY2016

# Configure the build
mkdir build
cd build
cmake -D CMAKE_BUILD_TYPE=Release ..

# Build and test NJOY2016
make -j8
```

This will result in the executable `njoy` in the `build` directory.
To install to a different location, use `-DCMAKE_INSTALL_PREFIX=<path/to/install>` and run `make install` after
building.
See the NJOY2016 documentation for troubleshooting the installation.

After NJOY2016 is built, add the path to the installation directory to `$PATH` via

```shell
export PATH=<path/to/install/bin>:$PATH
```

### Step 3: Use the NJOY automation tool

The automation script ```automate.py``` automatically writes input scripts of the same
format as those found in ```examples```.
The aim of the script is to provide a streamlined input for generating cross-sections
for a number of materials, group structures, and temperatures.
The available input options are ```--materials```, ```--group_structures```,
```--temperatures```, ```--no-thermal```, ```--option```, and ```--plot```.

The ```--materials``` are specified as a space separated list where each material
has the form ```<zzz>-<symbol>-<aaa>-<molecule>```, where ```<molecule>``` should
only be specified when thermal S(alpha, beta) treatment is desired.
Note that only a few molecules are implemented in this code because each molecule
corresponds to an accompanying set of molecule-specific inputs.
To implement other molecules, the user should define the molecule parameters
within the ```get_thermal_info``` routine within ```utils.py```.

The ```--group_structures``` inputs are also specified as a space separated list.
Group structures are specified via ```<type><g><p>``` where currently implemented
types are ```custom``` and ```lanl```, ```g``` is the number of energy groups, and
```p``` is the first letter of the particle type.
Note that for custom group structures the file
```/path/to/repo/output/<endf-version>/custom<g><p>/custom<g><p>.txt``` must exist.
For LANL group structures, only the available group structures within NJOY can
be specified.
One can see a list of all neutron and gamma group structures by calling
```python3 njoy_utilities/runner.py --help```.
If different available group structures are desired, the user is encouraged to
implement this within ```get_group_structure_info``` routine within ```utils.py```.
Multi-particle group structures can similarly be specified using a ```-``` between
group structure specifications.

The ```--temperatures``` are specified as a space separated list of floats.
This argument defaults to room temperature.

The ```--no-thermal``` input is used to turn off thermal treatment for particular
materials that were specified.
This input takes the form of a list of integers where each integer corresponds to the
index of a material in the ```--materials``` list.
This input is optional. By default, thermal treatment is on for all materials.

The ```--option``` flag is an integer input that specifies whether to run NJOY,
process an existing NJOY output, or both.
When 0, NJOY is run and the output processed.
This is the default behavior.
When 1, only NJOY is run.
When 2, only an NJOY output is processed.
Note that when 2 is specified, the run will fail if NJOY output files for the
specified materials, group structures, and temperatures do not exist.
The script searches for such files in the predefined directory structure
```/path/to/repo/output/<endf-version>/<group-structure>/<temperature>k```.

The ```--plot``` flag, when specified, will produce plots for each of the
cross-sections generated.
This does nothing when ```--option``` is set to 1.

### Step 4b: Adapt one of the example scripts to your specific application

The example scripts are a collection of neutron only examples:

- `example1a.sh`, U235 with a xmas172 neutron group structure
- `example1b.sh`, same as 1a but using graphite, showcasing how to include S(a,b) thermal scattering
- `example1c.sh`, same as 1b but now with a custom weighting spectrum
- `example1d.sh`, same as 1b but with completely custom group structure

And a collection of neutron-gamma examples:

- `example2a`, O16 with the lanl30 neutron group structure and the lanl12 gamma group structure
- `example2b`, O16 with the xmas172 neutron group structure and the lanl48 gamma group structure

The basic input for each example is:

```shell
if [[ -z "${ENDF_ROOT}" ]]; then
  echo "ENDF_ROOT not set. Please set or specify custom paths."
  exit
fi

CWD=$PWD
cd njoy_utilities ||exit

#================================= Set properties here

export ENDF_ROOT=/Users/janv4/Desktop/Projects/ENDF/ENDF-B-VII.1
neutron_file="n-092_U_235.endf"

output_directory="output/ENDF-B-VII-1/xmas172/"
output_file_prefix="U235"

#================================= Run NJOY

python njoy_runner.py \
--path-to-neutron-endf=$ENDF_ROOT/neutrons/$neutron_file \
--temperature=293.6 \
--neutron-group-structure=22 \
--output-directory=../$output_directory \
--output-filename=$output_file_prefix.njoy

cd "$CWD" || exit

echo "********** DONE with GENERATION"

python3 njoy_processor.py \
--output-directory=$output_directory \
--njoy-output-filename=$output_file_prefix.njoy \
--xs-filename=$output_file_prefix.xs \
--plot

echo "********** DONE with PROCESSING"

cd "$CWD" || exit
```

## Note:

The user should be warned that NJOY outputs have a tendency to differ based
on the specified NJOY options.
For this reason, if a previously unseen NJOY output is observed, the parsers
used by the NJOY processor should be modified to account for that particular
type of output.

Further, it should be noted that several difficulties have been observed in
generating photonuclear cross-sections with low-Z materials.
This problem may lie within NJOY or be a lack of understanding by the author.
In any case, the user should be wary when attempting to generate such data.

Users are encouraged to submit additions to the code such as additional
supported molecules or group structures to the repository via a pull-request.

If any bugs are observed or features desired, the user is encouraged to submit
an issue.

## FAQs:

### FAQ-1: General format of input examples

The two python scripts are `njoy_runner.py` and `njoy_processor.py` located
in the ```njoy_utilities``` directory.

The `njoy_runner.py` script basically runs NJOY and has the following
inputs (most of which are optional):

```
# --path-to-neutron-endf=$ENDF_ROOT/neutrons/$neutron_file \
# --path-to-gamma-endf=$ENDF_ROOT/gammas/$gamma_file \
# --path-to-photoat-endf=$ENDF_ROOT/photoat/$photoat_file \
# --path-to-sab-endf=$ENDF_ROOT/thermal_scatt/$sab_file \
# --neutron-group-structure=22 \
# --custom-neutron-gs-file="" \
# --neutron-weight-function=8 \
# --custom-neutron-wt-file="" \
# --gamma-group-structure=0 \
# --custom-gamma-gs-file="" \
# --gamma-weight-function=2 \
# --custom-gamma-wt-file="" \
# --temperature=296.0 \
# --inelastic-thermal-number=229 \
# --inelastic-thermal-num-atoms=1 \
# --elastic-thermal-number=230 \
# --output-directory=$output_directory \
# --output-filename=../$output_file_prefix.njoy \

```

The `njoy_processor.py` script converts NJOY output to the desired multi-group
tranport cross-section format.
It only has three required inputs:

```
#--output-directory=$output_directory \
#--njoy-output-filename=$output_file_prefix.njoy \
#--xs-filename=$output_file_prefix.xs
```

Optionally a ```--plot``` flag can be used to visualize the data.

### FAQ-2: How to specify S(a,b) thermal scattering

Simply run `njoy_runner.py` with `--path-to-sab-endf`,
`--inelastic-thermal-number=`, `--inelastic-thermal-num-atoms`,
and `--elastic-thermal-number` specified.
The latter is only required for some molecules.

There aren't a lot of materials that have S(a,b) elastic treatment,
so it is worth doing some homework on them and verifying a semi-infinite
medium spectrum like done in the `tests` folder.

### FAQ-3: How to produce neutron-gamma cross-sections?

The moment you supply the option `--path-to-gamma-endf` or
`--path-to-photoat-endf`, then the script will know to run with gamma
production and make `--gamma-group-structure` required.

### FAQ-4: Format of a custom weighting spectrum file

The file is in ENDF TAB1-record format which can be confusing.
An example spectrum file is supplied in
`Docs/SampleWeightingSpectrum/spectrum_file.txt` and is the same for
custom neutron AND gamma spectra.

**Note:** remember the `/` terminator and the blank line at the end of the file.

### FAQ-5: Format of a custom group structure file

The first line of a group structure file is the total number of groups `G`.
Then followed by the lowest energy cutoff then a total of `G` upper bin boundaries
(all in eV):

```
# Number of groups G
6
# G+1 boundaries, lower bound first then all upper bounds (eV)
1.0e-5
5.0e-2
5.0e-1
1.0e2
1.0e5
1.0e6
20.0e6/
```

**Note:** remember the `/` terminator and the blank line at the end of the file.
