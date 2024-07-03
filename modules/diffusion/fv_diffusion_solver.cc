// SPDX-FileCopyrightText: 2024 The OpenSn Authors <https://open-sn.github.io/opensn/>
// SPDX-License-Identifier: MIT

#include "modules/diffusion/fv_diffusion_solver.h"
#include "framework/runtime.h"
#include "framework/object_factory.h"
#include "framework/logging/log.h"
#include "framework/utils/timer.h"
#include "framework/mesh/mesh_continuum/mesh_continuum.h"
#include "framework/field_functions/field_function_grid_based.h"
#include "framework/math/spatial_discretization/finite_volume/finite_volume.h"
#include "framework/math/functions/scalar_spatial_material_function.h"

namespace opensn
{
namespace diffusion
{

OpenSnRegisterObjectInNamespace(diffusion, FVSolver);
OpenSnRegisterSyntaxBlockInNamespace(diffusion,
                                     FVBoundaryOptionsBlock,
                                     FVSolver::BoundaryOptionsBlock);

FVSolver::FVSolver(const std::string& name)
  : opensn::Solver(name, {{"max_iters", int64_t(500)}, {"residual_tolerance", 1.0e-2}}),
    num_local_dofs_(0),
    num_global_dofs_(0),
    x_(nullptr),
    b_(nullptr),
    A_(nullptr)
{
}

InputParameters
FVSolver::GetInputParameters()
{
  InputParameters params = Solver::GetInputParameters();
  params.AddOptionalParameter<double>("residual_tolerance", 1.0e-2, "Solver relative tolerance");
  params.AddOptionalParameter<int>("max_iters", 500, "Solver relative tolerance");
  return params;
}

InputParameters
FVSolver::OptionsBlock()
{
  InputParameters params;
  params.AddOptionalParameterArray(
    "boundary_conditions", {}, "An array contain tables for each boundary specification.");
  params.LinkParameterToBlock("boundary_conditions", "FVSolver::BoundaryOptionsBlock");
  return params;
}

InputParameters
FVSolver::BoundaryOptionsBlock()
{
  InputParameters params;
  params.SetGeneralDescription("Set options for boundary conditions");
  params.AddRequiredParameter<std::string>("boundary",
                                           "Boundary to apply the boundary condition to.");
  params.AddRequiredParameter<std::string>("type", "Boundary type specification.");
  params.AddOptionalParameterArray<double>("coeffs", {}, "Coefficients.");
  return params;
}

FVSolver::FVSolver(const InputParameters& params)
  : opensn::Solver(params),
    num_local_dofs_(0),
    num_global_dofs_(0),
    x_(nullptr),
    b_(nullptr),
    A_(nullptr)
{
  basic_options_.AddOption("residual_tolerance",
                           params.GetParamValue<double>("residual_tolerance"));
  basic_options_.AddOption<int64_t>("max_iters", params.GetParamValue<int>("max_iters"));
}

FVSolver::~FVSolver()
{
  VecDestroy(&x_);
  VecDestroy(&b_);
  MatDestroy(&A_);
}

void
FVSolver::SetDCoefFunction(std::shared_ptr<ScalarSpatialMaterialFunction> function)
{
  d_coef_function_ = function;
}

void
FVSolver::SetQExtFunction(std::shared_ptr<ScalarSpatialMaterialFunction> function)
{
  q_ext_function_ = function;
}

void
FVSolver::SetSigmaAFunction(std::shared_ptr<ScalarSpatialMaterialFunction> function)
{
  sigma_a_function_ = function;
}

void
FVSolver::SetOptions(const InputParameters& params)
{
  const auto& user_params = params.ParametersAtAssignment();

  for (size_t p = 0; p < user_params.NumParameters(); ++p)
  {
    const auto& spec = user_params.GetParam(p);
    if (spec.Name() == "boundary_conditions")
    {
      spec.RequireBlockTypeIs(ParameterBlockType::ARRAY);
      for (size_t b = 0; b < spec.NumParameters(); ++b)
      {
        auto bndry_params = BoundaryOptionsBlock();
        bndry_params.AssignParameters(spec.GetParam(b));
        SetBoundaryOptions(bndry_params);
      }
    }
  }
}

void
FVSolver::SetBoundaryOptions(const InputParameters& params)
{
  const std::string fname = "FVSolver::SetBoundaryOptions";

  const auto& user_params = params.ParametersAtAssignment();
  const auto boundary = user_params.GetParamValue<std::string>("boundary");
  const auto bc_type = user_params.GetParamValue<std::string>("type");
  const auto bc_type_lc = LowerCase(bc_type);

  if (bc_type_lc == "reflecting")
  {
    opensn::diffusion::FVSolver::BoundaryInfo bndry_info;
    bndry_info.first = opensn::diffusion::BoundaryType::Reflecting;
    boundary_preferences_.insert(std::make_pair(boundary, bndry_info));
    opensn::log.Log() << "Boundary " << boundary << " set as Reflecting.";
  }
  else if (bc_type_lc == "dirichlet")
  {
    const auto coeffs = user_params.GetParamVectorValue<double>("coeffs");
    if (coeffs.size() < 1)
      throw std::invalid_argument("Expecting one value in the 'coeffs' parameter.");
    auto boundary_value = coeffs[0];
    opensn::diffusion::FVSolver::BoundaryInfo bndry_info;
    bndry_info.first = opensn::diffusion::BoundaryType::Dirichlet;
    bndry_info.second = {boundary_value};
    boundary_preferences_.insert(std::make_pair(boundary, bndry_info));
    opensn::log.Log() << "Boundary " << boundary << " set as Dirichlet with value "
                      << boundary_value;
  }
  else if (bc_type_lc == "neumann")
  {
    const auto coeffs = user_params.GetParamVectorValue<double>("coeffs");
    if (coeffs.size() < 1)
      throw std::invalid_argument("Expecting one value in the 'coeffs' parameter.");
    auto f_value = coeffs[0];
    opensn::diffusion::FVSolver::BoundaryInfo bndry_info;
    bndry_info.first = opensn::diffusion::BoundaryType::Robin;
    bndry_info.second = {0.0, 1.0, f_value};
    boundary_preferences_.insert(std::make_pair(boundary, bndry_info));
    opensn::log.Log() << "Boundary " << boundary << " set as Neumann with D grad(u) dot n = ("
                      << f_value << ") ";
  }
  else if (bc_type_lc == "vacuum")
  {
    opensn::diffusion::FVSolver::BoundaryInfo bndry_info;
    bndry_info.first = opensn::diffusion::BoundaryType::Robin;
    bndry_info.second = {0.25, 0.5, 0.0};
    boundary_preferences_.insert(std::make_pair(boundary, bndry_info));
    opensn::log.Log() << "Boundary " << boundary << " set as Vacuum.";
  }
  else if (bc_type_lc == "robin")
  {
    const auto coeffs = user_params.GetParamVectorValue<double>("coeffs");
    if (coeffs.size() < 3)
      throw std::invalid_argument("Expecting three values in the 'coeffs' parameter.");
    auto a_value = coeffs[0];
    auto b_value = coeffs[1];
    auto f_value = coeffs[2];
    opensn::diffusion::FVSolver::BoundaryInfo bndry_info;
    bndry_info.first = opensn::diffusion::BoundaryType::Robin;
    bndry_info.second = {a_value, b_value, f_value};
    boundary_preferences_.insert(std::make_pair(boundary, bndry_info));
    opensn::log.Log() << "Boundary " << boundary << " set as Robin with a,b,f = (" << a_value << ","
                      << b_value << "," << f_value << ") ";
  }
  else
    throw std::invalid_argument(fname + ": Unsupported boundary type '" + bc_type + "'.");
}

void
FVSolver::Initialize()
{
  const std::string fname = "diffusion::FVSolver::Initialize";
  log.Log() << "\n"
            << program_timer.GetTimeString() << " " << TextName()
            << ": Initializing FV Diffusion solver ";

  // Get grid
  grid_ptr_ = GetCurrentMesh();
  const auto& grid = *grid_ptr_;
  if (grid_ptr_ == nullptr)
    throw std::logic_error(std::string(__PRETTY_FUNCTION__) + " No grid defined.");

  log.Log() << "Global num cells: " << grid.GetGlobalNumberOfCells();

  // BIDs
  auto globl_unique_bndry_ids = grid.GetDomainUniqueBoundaryIDs();

  const auto& grid_boundary_id_map = grid_ptr_->GetBoundaryIDMap();
  for (uint64_t bndry_id : globl_unique_bndry_ids)
  {
    if (grid_boundary_id_map.count(bndry_id) == 0)
      throw std::logic_error(fname + ": Boundary id " + std::to_string(bndry_id) +
                             " does not have a name-assignment.");

    const auto& bndry_name = grid_boundary_id_map.at(bndry_id);
    if (boundary_preferences_.find(bndry_name) != boundary_preferences_.end())
    {
      BoundaryInfo bndry_info = boundary_preferences_.at(bndry_name);
      auto& bndry_vals = bndry_info.second;
      switch (bndry_info.first)
      {
        case BoundaryType::Reflecting:
        {
          boundaries_.insert(
            std::make_pair(bndry_id, Boundary{BoundaryType::Reflecting, {0.0, 0.0, 0.0}}));
          log.Log() << "Boundary " << bndry_name << " set to reflecting.";
          break;
        }
        case BoundaryType::Dirichlet:
        {
          if (bndry_vals.empty())
            bndry_vals.resize(1, 0.0);
          boundaries_.insert(
            std::make_pair(bndry_id, Boundary{BoundaryType::Dirichlet, {bndry_vals[0], 0.0, 0.0}}));
          log.Log() << "Boundary " << bndry_name << " set to dirichlet.";
          break;
        }
        case BoundaryType::Robin:
        {
          if (bndry_vals.size() != 3)
            throw std::logic_error(std::string(__PRETTY_FUNCTION__) +
                                   " Robin needs 3 values in boundary values.");
          boundaries_.insert(std::make_pair(
            bndry_id,
            Boundary{BoundaryType::Robin, {bndry_vals[0], bndry_vals[1], bndry_vals[2]}}));
          log.Log() << "Boundary " << bndry_name << " set to robin." << bndry_vals[0] << ","
                    << bndry_vals[1] << "," << bndry_vals[2];
          break;
        }
        case BoundaryType::Vacuum:
        {
          boundaries_.insert(
            std::make_pair(bndry_id, Boundary{BoundaryType::Robin, {0.25, 0.5, 0.}}));
          log.Log() << "Boundary " << bndry_name << " set to vacuum.";
          break;
        }
        case BoundaryType::Neumann:
        {
          if (bndry_vals.size() != 3)
            throw std::logic_error(std::string(__PRETTY_FUNCTION__) +
                                   " Neumann needs 3 values in boundary values.");
          boundaries_.insert(std::make_pair(
            bndry_id, Boundary{BoundaryType::Robin, {0.0, bndry_vals[0], bndry_vals[1]}}));
          log.Log() << "Boundary " << bndry_name << " set to neumann." << bndry_vals[0];
          break;
        }
      } // switch boundary type
    }
    else
    {
      boundaries_.insert(
        std::make_pair(bndry_id, Boundary{BoundaryType::Dirichlet, {0.0, 0.0, 0.0}}));
      log.Log0Verbose1() << "No boundary preference found for boundary index " << bndry_name
                         << "Dirichlet boundary added with zero boundary value.";
    }
  } // for bndry

  // Make SDM
  sdm_ptr_ = FiniteVolume::New(*grid_ptr_);
  const auto& sdm = *sdm_ptr_;

  const auto& OneDofPerNode = sdm.UNITARY_UNKNOWN_MANAGER;
  num_local_dofs_ = sdm.GetNumLocalDOFs(OneDofPerNode);
  num_global_dofs_ = sdm.GetNumGlobalDOFs(OneDofPerNode);

  log.Log() << "Num local DOFs: " << num_local_dofs_;
  log.Log() << "Num global DOFs: " << num_global_dofs_;

  // Initializes Mats and Vecs
  const auto n = static_cast<int64_t>(num_local_dofs_);
  const auto N = static_cast<int64_t>(num_global_dofs_);

  A_ = CreateSquareMatrix(n, N);
  x_ = CreateVector(n, N);
  b_ = CreateVector(n, N);

  std::vector<int64_t> nodal_nnz_in_diag;
  std::vector<int64_t> nodal_nnz_off_diag;
  sdm.BuildSparsityPattern(nodal_nnz_in_diag, nodal_nnz_off_diag, OneDofPerNode);

  InitMatrixSparsity(A_, nodal_nnz_in_diag, nodal_nnz_off_diag);

  if (field_functions_.empty())
  {
    std::string solver_name;
    if (not TextName().empty())
      solver_name = TextName() + "-";

    std::string text_name = solver_name + "phi";

    auto initial_field_function =
      std::make_shared<FieldFunctionGridBased>(text_name, sdm_ptr_, Unknown(UnknownType::SCALAR));

    field_functions_.push_back(initial_field_function);
    field_function_stack.push_back(initial_field_function);
  } // if not ff set
}

void
FVSolver::Execute()
{
  log.Log() << "\nExecuting FV Diffusion solver";

  const auto& grid = *grid_ptr_;
  const auto& sdm = *sdm_ptr_;

  // Assemble the system
  // P ~ Present cell
  // N ~ Neighbor cell
  log.Log() << "Assembling system: ";
  for (const auto& cell_P : grid.local_cells)
  {
    const auto& cell_mapping = sdm.GetCellMapping(cell_P);
    const double volume_P = cell_mapping.CellVolume(); // Volume of present cell
    const auto& x_cc_P = cell_P.centroid_;

    const auto imat = cell_P.material_id_;

    const double sigma_a = sigma_a_function_->Evaluate(imat, x_cc_P);
    const double q_ext = q_ext_function_->Evaluate(imat, x_cc_P);
    const double D_P = d_coef_function_->Evaluate(imat, x_cc_P);

    const int64_t imap = sdm.MapDOF(cell_P, 0);
    MatSetValue(A_, imap, imap, sigma_a * volume_P, ADD_VALUES);
    VecSetValue(b_, imap, q_ext * volume_P, ADD_VALUES);

    for (size_t f = 0; f < cell_P.faces_.size(); ++f)
    {
      const auto& face = cell_P.faces_[f];
      const auto& x_fc = face.centroid_;
      const auto x_PF = x_fc - x_cc_P;
      const auto A_f = cell_mapping.FaceArea(f);
      const auto A_f_n = A_f * face.normal_;

      if (face.has_neighbor_)
      {
        const auto& cell_N = grid.cells[face.neighbor_id_];
        const int jmat = cell_N.material_id_;
        const auto& x_cc_N = cell_N.centroid_;
        const auto x_PN = x_cc_N - x_cc_P;

        const double D_N = d_coef_function_->Evaluate(jmat, x_cc_N);

        const double w = x_PF.Norm() / x_PN.Norm();
        const double D_f = 1.0 / (w / D_P + (1.0 - w) / D_N);

        const double entry_ii = A_f_n.Dot(D_f * x_PN / x_PN.NormSquare());
        const double entry_ij = -entry_ii;

        const int64_t jmap = sdm.MapDOF(cell_N, 0);
        MatSetValue(A_, imap, imap, entry_ii, ADD_VALUES);
        MatSetValue(A_, imap, jmap, entry_ij, ADD_VALUES);
      } // internal face
      else
      {
        const auto& bndry = boundaries_[face.neighbor_id_];

        if (bndry.type_ == BoundaryType::Robin)
        {
          const auto& aval = bndry.values_[0];
          const auto& bval = bndry.values_[1];
          const auto& fval = bndry.values_[2];

          if (std::fabs(bval) < 1e-8)
            throw std::logic_error("if b=0, this is a Dirichlet BC, not a Robin BC");

          if (std::fabs(aval) > 1.0e-8)
            MatSetValue(A_, imap, imap, A_f * aval / bval, ADD_VALUES);
          if (std::fabs(fval) > 1.0e-8)
            VecSetValue(b_, imap, A_f * fval / bval, ADD_VALUES);
        } // if Robin

        if (bndry.type_ == BoundaryType::Dirichlet)
        {
          const auto& boundary_value = bndry.values_[0];

          const auto& x_cc_N = x_cc_P + 2.0 * x_PF;
          const auto x_PN = x_cc_N - x_cc_P;

          const double D_f = D_P;
          const double entry_ii = A_f_n.Dot(D_f * x_PN / x_PN.NormSquare());

          MatSetValue(A_, imap, imap, entry_ii, ADD_VALUES);
          VecSetValue(b_, imap, entry_ii * boundary_value, ADD_VALUES);
        } // if Dirichlet
      }   // bndry face
    }     // for f
  }       // for cell

  log.Log() << "Global assembly";

  MatAssemblyBegin(A_, MAT_FINAL_ASSEMBLY);
  MatAssemblyEnd(A_, MAT_FINAL_ASSEMBLY);
  VecAssemblyBegin(b_);
  VecAssemblyEnd(b_);

  log.Log() << "Done global assembly";

  // Create Krylov Solver
  log.Log() << "Solving: ";
  auto petsc_solver =
    CreateCommonKrylovSolverSetup(A_,
                                  TextName(),
                                  KSPCG,
                                  PCGAMG,
                                  0.0,
                                  basic_options_("residual_tolerance").FloatValue(),
                                  basic_options_("max_iters").IntegerValue());

  // Solve
  KSPSolve(petsc_solver.ksp, b_, x_);

  UpdateFieldFunctions();

  log.Log() << "Done solving";
}

void
FVSolver::UpdateFieldFunctions()
{
  auto& ff = *field_functions_.front();
  ff.UpdateFieldVector(x_);
}

} // namespace diffusion
} // namespace opensn