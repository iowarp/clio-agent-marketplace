from spack.package import *

CLIO_MARK = "clio-jarvis VTX patch"

# Upstream vtk.xml points TIME at the int ``step``. clio-jarvis follows one VTX
# contract for every solver: TIME is a double ``time`` in model units, here
# ``step * dt``.
WRITER_H_EDITS = [
    (
        "    adios2::Variable<int> var_step;\n",
        "    adios2::Variable<int> var_step;\n"
        f"    adios2::Variable<double> var_time; // {CLIO_MARK}\n",
        1,
    ),
]
WRITER_CPP_EDITS = [
    (
        '<DataArray Name="TIME">\n                    step\n                  </DataArray>',
        '<DataArray Name="TIME">time</DataArray>',
        1,
    ),
    (
        '    var_step = io.DefineVariable<int>("step");\n',
        '    var_step = io.DefineVariable<int>("step");\n'
        f'    var_time = io.DefineVariable<double>("time"); // {CLIO_MARK}\n',
        1,
    ),
    (
        "writer.Put<int>(var_step, &step);\n",
        "writer.Put<int>(var_step, &step);\n"
        "        writer.Put<double>(var_time, step * settings.dt, adios2::Mode::Sync);\n",
        3,
    ),
]


def apply_edits(path, edits):
    with open(path) as handle:
        text = handle.read()
    for old, new, count in edits:
        found = text.count(old)
        if found != count:
            raise InstallError(f"{path}: expected {count} of {old[:50]!r}, found {found}")
        text = text.replace(old, new)
    with open(path, "w") as handle:
        handle.write(text)


class GrayScott(CMakePackage):
    """ADIOS2's Gray-Scott reaction-diffusion example
    (examples/simulations/gray-scott), built on its own against an installed
    ADIOS2 of the same release series.

    The clio variant adds a double ``time`` (``step * dt``) and points the
    vtk.xml TIME array at it, so ParaView's ADIOS2VTXReader shows model time.
    """

    homepage = "https://github.com/ornladios/ADIOS2/tree/master/examples/simulations/gray-scott"
    url = "https://github.com/ornladios/ADIOS2/archive/v2.10.2.tar.gz"
    git = "https://github.com/ornladios/ADIOS2.git"

    license("Apache-2.0")

    version("2.10.2", sha256="14cf0bcd94772194bce0f2c0e74dba187965d1cffd12d45f801c32929158579e")

    variant("clio", default=False, description="CLIO patch: a double time for the VTX TIME array")

    root_cmakelists_dir = join_path("examples", "simulations", "gray-scott")

    depends_on("c", type="build")
    depends_on("cxx", type="build")
    depends_on("cmake@3.12:", type="build")

    depends_on("mpi")
    depends_on("adios2@2.10+mpi", when="@2.10")

    def patch(self):
        if self.spec.satisfies("+clio"):
            source = join_path(self.root_cmakelists_dir, "simulation")
            apply_edits(join_path(source, "writer.h"), WRITER_H_EDITS)
            apply_edits(join_path(source, "writer.cpp"), WRITER_CPP_EDITS)

    def cmake_args(self):
        # The example installs to CMAKE_INSTALL_BINDIR without including GNUInstallDirs.
        return [self.define("CMAKE_INSTALL_BINDIR", "bin")]
