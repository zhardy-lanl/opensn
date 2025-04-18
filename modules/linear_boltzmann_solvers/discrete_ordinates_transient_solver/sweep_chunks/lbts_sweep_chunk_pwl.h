// SPDX-FileCopyrightText: 2024 The OpenSn Authors <https://open-sn.github.io/opensn/>
// SPDX-License-Identifier: MIT

#pragma once

#if 0
#include "framework/mesh/mesh_continuum/mesh_continuum.h"

#include "framework/math/spatial_discretization/spatial_discretization.h"

#include "modules/linear_boltzmann_solvers/discrete_ordinates_problem/sweep/sweep_chunk_base.h"

#include "Ca_DO_SteadyState/lbs_DO_steady_state.h"
#include "modules/linear_boltzmann_solvers/lbs_problem/groupset/lbs_groupset.h"

namespace lbs
{

/// Sweep chunk for cartesian PWLD discretization Theta-scheme timestepping.
class SweepChunkPWLTransientTheta : public opensn::SweepChunk
{
protected:
  const std::shared_ptr<MeshContinuum> grid_view_;
  opensn::SpatialDiscretization& grid_fe_view_;
  const std::vector<UnitCellMatrices>& unit_cell_matrices_;
  std::vector<CellLBSView>& grid_transport_view_;
  const std::vector<double>& q_moments_;
  LBSGroupset& groupset_;
  const std::map<int, std::shared_ptr<MultiGroupXS>>& xs_;
  const int num_moments_;
  const size_t num_groups_;
  const int max_num_cell_dofs_;
  const bool save_angular_flux_;

  const std::vector<double>& psi_prev_;
  const double theta_;
  const double dt_;

  // Runtime params
  bool a_and_b_initialized_;
  std::vector<std::vector<double>> Amat_;
  std::vector<std::vector<double>> Atemp_;
  std::vector<double> source_;

public:
  std::vector<std::vector<double>> b_;

  SweepChunkPWLTransientTheta(std::shared_ptr<MeshContinuum> grid_ptr,
                              opensn::SpatialDiscretization& discretization,
                              const std::vector<UnitCellMatrices>& unit_cell_matrices,
                              std::vector<CellLBSView>& cell_transport_views,
                              std::vector<double>& destination_phi,
                              std::vector<double>& destination_psi,
                              const std::vector<double>& psi_prev_ref,
                              double input_theta,
                              double time_step,
                              const std::vector<double>& source_moments,
                              LBSGroupset& groupset,
                              const std::map<int, std::shared_ptr<MultiGroupXS>>& xs,
                              int num_moments,
                              int max_num_cell_dofs);

  void Sweep(opensn::sweep_management::AngleSet* angle_set) override;

  struct Upwinder
  {
    opensn::FLUDS& fluds;
    opensn::AngleSet* angle_set;
    size_t spls_index;
    size_t angle_set_index;
    int in_face_counter;
    int preloc_face_counter;
    int out_face_counter;
    int deploc_face_counter;
    uint64_t bndry_id;
    int angle_num;
    uint64_t cell_local_id;
    int f;
    int gs_gi;
    size_t gs_ss_begin;
    bool surface_source_active;

    const double* GetUpwindPsi(int fj, bool local, bool boundary) const;
    double* GetDownwindPsi(int fi, bool local, bool boundary, bool reflecting_bndry) const;
  };
};
} // namespace lbs
#endif
