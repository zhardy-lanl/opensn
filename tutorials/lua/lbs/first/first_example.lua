--[[ @doc

# A First Example

This is a complete simulation transport example. Each aspect of the simulation process is kept to a minimum:
- We use an orthogonal 2D grid;
- We introduce the concept of domain decomposition ("partitioning");
- The domain is homogeneous (single material, uniform isotropic external source), vacuum boundary conditions apply;
- The cross sections are given in a text file (with our OpenSn format); we use only one energy group in this example;
- The angular quadrature (discretization in angle) is introduced;
- The Linear Boltzmann Solver (LBS) options are keep to a minimum.


Because transport simulations are computationally expensive due to the high dimensional of the phase-space
(physical space, energy, direction), they are often performed using several parallel processes (e.g., CPU cores).
In what follows, we enforce that this first example be run with 4 MPI processes.

---
## Check the number of processes
This portion of the lua input is not mandatory. The user is free to delete it and run the code with a different number
of processes. However, to reproduce the graphics below, one needs to run with 4 MPI ranks.

The lua input performs this following checks:
+ `check_num_procs==nil` will be true when running serially without MPI
+ `number_of_processes ~= num_procs` will be true when the number of MPI processes requested is not equal to the preset value of `4`.

To run the code, simply type: `mpiexec -n 4 path/to/opensn -i input_filename.lua`

For more runtime options, type `path/to/opensn -h` for help.
--]]
-- Check num_procs
num_procs = 4
if check_num_procs == nil and number_of_processes ~= num_procs then
  Log(
    LOG_0ERROR,
    "Incorrect amount of processors. "
      .. "Expected "
      .. tostring(num_procs)
      .. ". Pass check_num_procs=false to override if possible."
  )
  os.exit(false)
end

--[[ @doc
## Mesh
Here, we will use the in-house orthogonal mesh generator for a simple Cartesian grid.
### List of nodes
We first create a lua table for the list of nodes. The nodes will be spread from -1 to +1.
Be mindful that lua indexing starts at 1.
--]]
-- Setup the mesh
nodes = {}
n_cells = 10
length = 2.
xmin = -length / 2.
dx = length / n_cells
for i = 1, (n_cells + 1) do
  k = i - 1
  nodes[i] = xmin + k * dx
end
--[[ @doc
### Orthogonal Mesh Generation
We use the `OrthogonalMeshGenerator` and pass the list of nodes per dimension. Here, we pass 2 times the same list of
nodes to create a 2D geometry with square cells. Thus, we create a square domain, of side length 2, centered on the origin (0,0).

We also partition the 2D mesh into 2x2 subdomains using `KBAGraphPartitioner`. Since we want the split the x-axis in 2,
we give only 1 value in the xcuts array (x=0). Likewise for ycuts (y=0). The assignment to a partition is done based on where the
cell center is located with respect to the various xcuts, ycuts, and zcuts (a fuzzy logic is applied to avoid issues).

The resulting mesh and partition is shown below:

![Mesh_Partition](images/first_example_mesh_partition.png)
--]]
meshgen = mesh.OrthogonalMeshGenerator.Create({
  node_sets = { nodes, nodes },
  partitioner = mesh.KBAGraphPartitioner.Create({
    nx = 2,
    ny = 2,
    xcuts = { 0.0 },
    ycuts = { 0.0 },
  }),
})

grid = meshgen:Execute()

--[[ @doc
### Material IDs
When using the in-house `OrthogonalMeshGenerator`, no material IDs are assigned. The user needs to
assign material IDs to all cells. Here, we have a homogeneous domain, so we assign a material ID
with value 0 for each cell in the spatial domain.
--]]
-- Set block IDs
grid:SetUniformBlockID(0)

--[[ @doc
## Cross Sections
We load the cross sections from an OpenSn file format.
See the tutorials' section on materials for more details on cross sections.
--]]
xs_matA = xs.LoadFromOpenSn("xs_1g_MatA.xs")

--[[ @doc
## Volumetric Source
We create a volumetric multigroup source which will be assigned to the material with given block IDs.
Volumetric sources are assigned to the solver via the `options` parameter in the LBS block (see below).
--]]
num_groups = 1
strength = {}
for g = 1, num_groups do
  strength[g] = 1.0
end
mg_src = lbs.VolumetricSource.Create({ block_ids = { 0 }, group_strength = strength })

--[[ @doc
## Angular Quadrature
We create a product Gauss-Legendre-Chebyshev angular quadrature and pass the total number of polar cosines
(here `npolar = 4`) and the number of azimuthal subdivisions in **four quadrants** (`nazimu = 4`).
This creates a 2D angular quadrature for XY geometry.
--]]
-- Setup the Angular Quadrature
nazimu = 4
npolar = 4
pquad = aquad.CreateGLCProductQuadrature2DXY(npolar, nazimu)

--[[ @doc
## Linear Boltzmann Solver
### Options for the Linear Boltzmann Solver (LBS)
In the LBS block, we provide
+ the number of energy groups,
+ the groupsets (with 0-indexing), the handle for the angular quadrature, the angle aggregation, the solver type,
tolerances, and other solver options.
--]]
-- Setup LBS parameters
lbs_block = {
  mesh = grid,
  num_groups = num_groups,
  groupsets = {
    {
      groups_from_to = { 0, 0 },
      angular_quadrature = pquad,
      angle_aggregation_num_subsets = 1,
      inner_linear_method = "petsc_gmres",
      l_abs_tol = 1.0e-6,
      l_max_its = 300,
      gmres_restart_interval = 30,
    },
  },
  xs_map = {
    { block_ids = { 0 }, xs = xs_matA },
  },
  options = {
    volumetric_sources = { mg_src },
  },
}
--[[ @doc
### Putting the Linear Boltzmann Solver Together
We then create the physics solver, initialize it, and execute it.
--]]
phys = lbs.DiscreteOrdinatesProblem.Create(lbs_block)

-- Initialize and Execute Solver
ss_solver = lbs.SteadyStateSolver.Create({ lbs_problem = phys })

ss_solver:Initialize()
ss_solver:Execute()

--[[ @doc
## Post-Processing via Field Functions
We extract the scalar flux (i.e., the first entry in the field function list; recall that lua
indexing starts at 1) and export it to a VTK file whose name is supplied by the user. See the tutorials' section
on post-processing for more details on field functions.

The resulting scalar flux is shown below:

![Scalar_flux](images/first_example_scalar_flux.png)
--]]
-- Retrieve field functions and export them
fflist = lbs.GetScalarFieldFunctionList(phys)
vtk_basename = "first_example"
fieldfunc.ExportToVTK(fflist[1], vtk_basename)

--[[ @doc
## Possible Extensions
1. Change the number of MPI processes (you may want to delete the safeguard at the top of the input file to run with any number of MPI ranks);
2. Change the spatial resolution by increasing or decreasing the number of cells;
3. Change the angular resolution by increasing or decreasing the number of polar and azimuthal subdivisions.
--]]
