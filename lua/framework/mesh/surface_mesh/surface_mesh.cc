// SPDX-FileCopyrightText: 2024 The OpenSn Authors <https://open-sn.github.io/opensn/>
// SPDX-License-Identifier: MIT

#include "lua/framework/mesh/surface_mesh/surface_mesh.h"
#include "lua/framework/lua.h"
#include "lua/framework/console/console.h"
#include "framework/mesh/surface_mesh/surface_mesh.h"
#include "framework/runtime.h"
#include "framework/logging/log.h"

using namespace opensn;

namespace opensnlua
{

RegisterLuaFunctionInNamespace(MeshSurfaceMeshCreate, mesh, SurfaceMeshCreate);
RegisterLuaFunctionInNamespace(MeshComputeLoadBalancing, mesh, ComputeLoadBalancing);
RegisterLuaFunctionInNamespace(MeshSurfaceMeshImportFromOBJFile,
                               mesh,
                               SurfaceMeshImportFromOBJFile);
RegisterLuaFunctionInNamespace(MeshSurfaceMeshImportFromTriangleFiles,
                               mesh,
                               SurfaceMeshImportFromTriangleFiles);

int
MeshSurfaceMeshCreate(lua_State* L)
{
  auto new_mesh = std::make_shared<SurfaceMesh>();

  opensn::object_stack.emplace_back(new_mesh);

  size_t index = opensn::object_stack.size() - 1;

  opensn::log.LogAllVerbose2() << "mesh.SurfaceMeshCreate: Empty SurfaceMesh object, " << index
                               << ", created" << std::endl;

  return LuaReturn(L, index);
}

int
MeshComputeLoadBalancing(lua_State* L)
{
  const std::string fname = "mesh.ComputeLoadBalancing";
  LuaCheckArgs<size_t, std::vector<double>, std::vector<double>>(L, fname);

  // Get reference surface mesh
  auto surf_handle = LuaArg<size_t>(L, 1);

  auto& cur_surf =
    opensn::GetStackItem<SurfaceMesh>(opensn::surface_mesh_stack, surf_handle, __FUNCTION__);

  auto x_cuts = LuaArg<std::vector<double>>(L, 2);
  auto y_cuts = LuaArg<std::vector<double>>(L, 3);

  // Call compute balance
  std::stable_sort(x_cuts.begin(), x_cuts.end());
  std::stable_sort(y_cuts.begin(), y_cuts.end());
  cur_surf.ComputeLoadBalancing(x_cuts, y_cuts);

  return LuaReturn(L);
}

int
MeshSurfaceMeshImportFromOBJFile(lua_State* L)
{
  const std::string fname = "mesh.SurfaceMeshImportFromOBJFile";
  LuaCheckArgs<size_t, std::string>(L, fname);

  auto handle = LuaArg<size_t>(L, 1);
  const auto file_name = LuaArg<std::string>(L, 2);
  auto as_poly = LuaArgOptional<bool>(L, 3, true);
  auto translation_vec = LuaArgOptional<Vector3>(L, 4, Vector3(0, 0, 0));

  auto& surface_mesh =
    opensn::GetStackItem<SurfaceMesh>(opensn::object_stack, handle, __FUNCTION__);

  opensn::log.Log0Verbose2() << fname << ": Loading Wavefront .obj file: " << std::endl;

  surface_mesh.ImportFromOBJFile(file_name, as_poly, translation_vec);

  return LuaReturn(L);
}

int
MeshSurfaceMeshImportFromTriangleFiles(lua_State* L)
{
  const std::string fname = "mesh.SurfaceMeshImportFromTriangleFiles";
  LuaCheckArgs<size_t, std::string>(L, fname);
  auto handle = LuaArg<size_t>(L, 1);
  const std::string file_name = LuaArg<std::string>(L, 2);
  auto as_poly = LuaArgOptional<bool>(L, 3, true);

  auto& surface_mesh = opensn::GetStackItem<SurfaceMesh>(opensn::surface_mesh_stack, handle, fname);

  surface_mesh.ImportFromTriangleFiles(file_name.c_str(), as_poly);

  return LuaReturn(L);
}

int
SurfaceMeshImportFromMshFiles(lua_State* L)
{
  LuaCheckArgs<int, std::string>(L, "SurfaceMeshImportFromMshFiles");
  auto handle = LuaArg<int>(L, 1);
  const auto file_name = LuaArg<std::string>(L, 2);
  auto as_poly = LuaArgOptional<bool>(L, 3, true);

  auto& surface_mesh =
    opensn::GetStackItem<SurfaceMesh>(opensn::surface_mesh_stack, handle, __FUNCTION__);

  std::stringstream outtext;
  outtext << "SurfaceMeshImportFromMshFiles: Loading a gmsh ascii file: " << file_name << std::endl;
  opensn::log.LogAllVerbose2() << outtext.str();
  surface_mesh.ImportFromMshFiles(file_name.c_str(), as_poly);

  return LuaReturn(L);
}

} // namespace opensnlua
