// SPDX-FileCopyrightText: 2024 The OpenSn Authors <https://open-sn.github.io/opensn/>
// SPDX-License-Identifier: MIT

#include "framework/mesh/mesh_continuum/mesh_continuum.h"

namespace opensn
{

Cell&
LocalCellHandler::operator[](uint64_t cell_local_index)
{
  if (native_cells.empty())
  {
    std::stringstream ostr;
    ostr << "LocalCells attempted to access local cell " << cell_local_index
         << " but there are no local cells. This normally indicates"
         << " a partitioning problem.";
    throw std::invalid_argument(ostr.str());
  }

  if (cell_local_index >= native_cells.size())
  {
    std::stringstream ostr;
    ostr << "LocalCells attempted to access local cell " << cell_local_index
         << " but index out of range [0, " << native_cells.size() - 1 << "].";
    throw std::invalid_argument(ostr.str());
  }

  return *native_cells[cell_local_index];
}

const Cell&
LocalCellHandler::operator[](uint64_t cell_local_index) const
{
  if (native_cells.empty())
  {
    std::stringstream ostr;
    ostr << "LocalCells attempted to access local cell " << cell_local_index
         << " but there are no local cells. This normally indicates"
         << " a partitioning problem.";
    throw std::invalid_argument(ostr.str());
  }

  if (cell_local_index >= native_cells.size())
  {
    std::stringstream ostr;
    ostr << "LocalCells attempted to access local cell " << cell_local_index
         << " but index out of range [0, " << native_cells.size() - 1 << "].";
    throw std::invalid_argument(ostr.str());
  }

  return *native_cells[cell_local_index];
}

} // namespace opensn
