import re

from spack.package import *

CLIO_MARK = "clio-jarvis VTX patch"

PUBLIC_OLD = "decomp_2d_start_io, decomp_2d_end_io, &\n             gen_iodir_name"
PUBLIC_NEW = (
    "decomp_2d_start_io, decomp_2d_end_io, &\n"
    "             decomp_2d_clio_attribute, decomp_2d_clio_put_scalar, &\n"
    "             gen_iodir_name"
)
ROUTINES = """
   ! MARK: metadata for ParaView's ADIOS2VTXReader. Not upstream.
   subroutine decomp_2d_clio_attribute(io_name, attr_name, attr_value)

      implicit none

      character(len=*), intent(in) :: io_name, attr_name, attr_value
#ifdef ADIOS2
      type(adios2_io) :: io
      type(adios2_attribute) :: attr
      integer :: ierror

      call adios2_at_io(io, adios, io_name, ierror)
      if (ierror /= 0) call decomp_2d_abort(__FILE__, __LINE__, ierror, "adios2_at_io")
      call adios2_define_attribute(attr, io, attr_name, attr_value, ierror)
      if (ierror /= 0) call decomp_2d_abort(__FILE__, __LINE__, ierror, "adios2_define_attribute")
#else
      associate (nm => io_name, an => attr_name, av => attr_value)
      end associate
#endif

   end subroutine decomp_2d_clio_attribute

   subroutine decomp_2d_clio_put_scalar(io_name, io_dir, var_name, val)

      implicit none

      character(len=*), intent(in) :: io_name, io_dir, var_name
      real(kind=8), intent(in) :: val
#ifdef ADIOS2
      type(adios2_io) :: io
      type(adios2_variable) :: var
      integer :: idx, ierror

      call adios2_at_io(io, adios, io_name, ierror)
      if (ierror /= 0) call decomp_2d_abort(__FILE__, __LINE__, ierror, "adios2_at_io")
      call adios2_inquire_variable(var, io, var_name, ierror)
      if (.not. var%valid) then
         call adios2_define_variable(var, io, var_name, adios2_type_dp, ierror)
         if (ierror /= 0) call decomp_2d_abort(__FILE__, __LINE__, ierror, "adios2_define_variable")
      end if
      idx = get_io_idx(io_name, io_dir)
      if (idx < 1) call decomp_2d_abort(__FILE__, __LINE__, idx, "clio: IO is not open")
      if (nrank == 0) then
         call adios2_put(engine_registry(idx), var, val, adios2_mode_sync, ierror)
         if (ierror /= 0) call decomp_2d_abort(__FILE__, __LINE__, ierror, "adios2_put")
      end if
#else
      associate (nm => io_name, dr => io_dir, vn => var_name, v => val)
      end associate
#endif

   end subroutine decomp_2d_clio_put_scalar

end module decomp_2d_io""".replace("MARK", CLIO_MARK)

BP5_EXT_OLD = '         ext = ".bp4"\n'
BP5_EXT_NEW = (
    '         ext = ".bp4"\n'
    '      else if (io%engine_type == "BP5") then\n'
    '         ext = ".bp5"\n'
)
UNKNOWN_ENGINE = re.compile(r'[ \t]*print \*, "ERROR: Unkown engine type!.*?\n[ \t]*stop\n', re.S)

FINDFFTW_DOWNLOAD = re.compile(
    r"[ \t]*configure_file\(\$\{CMAKE_SOURCE_DIR\}/cmake/fft/downloadFindFFTW\.cmake\.in"
    r".*?set\(findFFTW_DIR \$\{CMAKE_CURRENT_BINARY_DIR\}/findFFTW-src\)",
    re.S,
)


def replace_once(path, old, new):
    with open(path) as handle:
        text = handle.read()
    found = len(old.findall(text)) if hasattr(old, "findall") else text.count(old)
    if found != 1:
        raise InstallError(f"{path}: expected one patch anchor, found {found}")
    text = old.sub(lambda _: new, text) if hasattr(old, "sub") else text.replace(old, new)
    with open(path, "w") as handle:
        handle.write(text)


class Decomp2dFft(CMakePackage):
    """2DECOMP&FFT: 2D pencil decomposition and distributed FFTs for Fortran MPI codes.

    With io=adios2 the BP5 engine gets the ``.bp5`` extension that later
    releases use (2.0.4 stops on any engine it does not know). The clio variant
    adds two public routines, ``decomp_2d_clio_attribute`` and
    ``decomp_2d_clio_put_scalar``, which ``xcompact3d +clio`` uses to write
    ParaView's VTX metadata.
    """

    homepage = "https://2decomp-fft.github.io/"
    url = "https://github.com/2decomp-fft/2decomp-fft/archive/refs/tags/v2.0.4.tar.gz"
    git = "https://github.com/2decomp-fft/2decomp-fft.git"

    license("BSD-3-Clause")

    version("2.0.4", sha256="aedc767c66f43aea6a4aa88d1004a983a5837db077a28a02a0e870cdb2a2c4a5")

    variant(
        "io",
        default="mpi",
        values=("mpi", "adios2"),
        multi=False,
        description="IO backend: MPI-IO or ADIOS2",
    )
    variant(
        "fft",
        default="generic",
        values=("generic", "fftw"),
        multi=False,
        description="FFT backend: the built-in generic FFT or FFTW3",
    )
    variant(
        "clio",
        default=False,
        description="Add the VTX metadata routines used by xcompact3d +clio",
    )
    variant(
        "build_type",
        default="Release",
        values=("Debug", "Release"),
        description="CMake build type",
    )

    depends_on("c", type="build")
    depends_on("cxx", type="build")
    depends_on("fortran", type="build")
    depends_on("cmake@3.20:", type="build")

    depends_on("mpi")
    depends_on("adios2+mpi+fortran", when="io=adios2")
    depends_on("fftw@3: precision=double", when="fft=fftw")

    # The FFTW backend clones findFFTW at configure time; fetch it with the source instead.
    resource(
        name="findfftw",
        git="https://github.com/egpbos/findfftw.git",
        commit="d449ea0bcbf94a4a1c3dbb2108aa57609a4967ff",
        placement="findFFTW-src",
        when="fft=fftw",
    )

    conflicts("+clio", when="io=mpi", msg="The clio VTX metadata needs the ADIOS2 backend")

    def patch(self):
        io_f90 = join_path("src", "io.f90")
        if self.spec.satisfies("io=adios2"):
            replace_once(io_f90, BP5_EXT_OLD, BP5_EXT_NEW)
            replace_once(io_f90, UNKNOWN_ENGINE, '         ext = ""\n')
        if self.spec.satisfies("+clio"):
            replace_once(io_f90, PUBLIC_OLD, PUBLIC_NEW)
            replace_once(io_f90, "\nend module decomp_2d_io", ROUTINES)
        if self.spec.satisfies("fft=fftw"):
            replace_once(
                join_path("cmake", "fft", "fft.cmake"),
                FINDFFTW_DOWNLOAD,
                "  set(findFFTW_DIR ${CMAKE_SOURCE_DIR}/findFFTW-src)",
            )

    def cmake_args(self):
        spec = self.spec
        args = [
            self.define("CMAKE_C_COMPILER", spec["mpi"].mpicc),
            self.define("CMAKE_CXX_COMPILER", spec["mpi"].mpicxx),
            self.define("CMAKE_Fortran_COMPILER", spec["mpi"].mpifc),
            self.define("CMAKE_INSTALL_LIBDIR", "lib"),
            self.define_from_variant("IO_BACKEND", "io"),
            self.define_from_variant("FFT_Choice", "fft"),
            self.define("BUILD_TESTING", False),
        ]
        if spec.satisfies("fft=fftw"):
            args.append(self.define("FFTW_ROOT", spec["fftw"].prefix))
        return args
