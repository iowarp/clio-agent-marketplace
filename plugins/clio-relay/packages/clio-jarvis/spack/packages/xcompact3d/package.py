from spack.package import *

VTX_MARK = "clio-jarvis VTX patch"
GEOMETRY_MARK = "clio geometry patch"

# Incompact3d src/visu.f90: define vtk.xml from ./clio-vtk.xml and put the time
# ``t`` as ``time`` in every snapshot step, so ParaView's ADIOS2VTXReader
# follows data.bp5.
VISU_EDITS = [
    (
        '    call decomp_2d_open_io(io_name, "data", mode)\n#endif',
        "    ! " + VTX_MARK + "\n"
        "    if (mode == decomp_2d_write_mode) call clio_vtk_xml_attribute()\n"
        '    call decomp_2d_open_io(io_name, "data", mode)\n#endif',
    ),
    (
        '#ifdef ADIOS2\n    call decomp_2d_start_io(io_name, "data")\n#endif',
        '#ifdef ADIOS2\n    call decomp_2d_start_io(io_name, "data")\n'
        "    ! " + VTX_MARK + "\n"
        '    call decomp_2d_clio_put_scalar(io_name, "data", "time", real(t, kind=8))\n'
        "#endif",
    ),
    (
        "    use decomp_2d_io, only : decomp_2d_start_io\n",
        "    use decomp_2d_io, only : decomp_2d_start_io, decomp_2d_clio_put_scalar\n"
        "    use var, only : t\n",
    ),
    (
        "  subroutine visu_finalise()",
        """  ! MARK: define the vtk.xml attribute from ./clio-vtk.xml when present.
  subroutine clio_vtk_xml_attribute()

    use decomp_2d_io, only : decomp_2d_clio_attribute

    implicit none

    logical :: found
    integer :: unit, nbytes
    character(len=:), allocatable :: xml

    inquire(file="clio-vtk.xml", exist=found, size=nbytes)
    if (.not. found .or. nbytes <= 0) return
    allocate(character(len=nbytes) :: xml)
    open(newunit=unit, file="clio-vtk.xml", access="stream", form="unformatted", &
         action="read", status="old")
    read(unit) xml
    close(unit)
    call decomp_2d_clio_attribute(io_name, "vtk.xml", xml)
    if (nrank == 0) write(*, "(A,I0,A)") " clio: vtk.xml attribute defined (", nbytes, " bytes)"

  end subroutine clio_vtk_xml_attribute

""".replace("MARK", VTX_MARK)
        + "  subroutine visu_finalise()",
    ),
]

# Incompact3d src/genepsi3d.f90: pass dz to the cylinder case.
GENEPSI_EDITS = [
    (
        "CALL geomcomplex_cyl(epsi, nxi, nxf, ny, nyi, nyf, nzi, nzf, dx, yp, remp)",
        "CALL geomcomplex_cyl(epsi, nxi, nxf, ny, nyi, nyf, nzi, nzf, dx, yp, dz, remp) ! "
        + GEOMETRY_MARK,
    ),
]

# Incompact3d src/Case-Cylinder-wake.f90 (itype = 5): when clio-geometry.txt
# (mask points, origin, spacing) and clio-geometry.bin (nx*ny*nz bytes, x
# fastest, 1 inside) exist in the run directory, the immersed body comes from
# that voxel mask instead of the analytic cylinder. Each snapshot also writes
# ``ep`` so viewers can draw the body.
_VISU_INIT = '    call decomp_2d_register_variable(io_name, "critq", 1, 0, output2D, mytype)\n'
_VISU_WRITE = (
    '    call write_field(di1, ".", "critq", num, flush = .true.) '
    "! Reusing temporary array, force flush\n"
)
CYLINDER_EDITS = [
    (
        "  integer :: FS\n",
        """  integer :: FS
  ! MARK: voxel mask state
  logical, save :: clio_geom_checked = .false., clio_geom_on = .false.
  integer, save :: cg_n(3)
  real(mytype), save :: cg_o(3), cg_d(3)
  integer(kind=1), allocatable, save :: cg_mask(:,:,:)
""".replace("MARK", GEOMETRY_MARK),
    ),
    (
        "  subroutine geomcomplex_cyl(epsi,nxi,nxf,ny,nyi,nyf,nzi,nzf,dx,yp,remp)",
        "  subroutine geomcomplex_cyl(epsi,nxi,nxf,ny,nyi,nyf,nzi,nzf,dx,yp,dz,remp)",
    ),
    (
        "    real(mytype)               :: dx\n    real(mytype)               :: remp\n",
        "    real(mytype)               :: dx, dz\n"
        "    real(mytype)               :: remp\n"
        "    integer                    :: ii, jj, kk\n",
    ),
    (
        "    ! Intitialise epsi\n    epsi(:,:,:)=zero\n",
        """    ! Intitialise epsi
    epsi(:,:,:)=zero

    ! MARK: body from a voxel mask when clio-geometry.txt is present
    if (.not. clio_geom_checked) call clio_geom_load()
    if (clio_geom_on) then
       do k=nzi,nzf
          kk = nint((real(k-1,mytype)*dz - cg_o(3))/cg_d(3)) + 1
          if (kk < 1 .or. kk > cg_n(3)) cycle
          do j=nyi,nyf
             jj = nint((yp(j) - cg_o(2))/cg_d(2)) + 1
             if (jj < 1 .or. jj > cg_n(2)) cycle
             do i=nxi,nxf
                ii = nint((real(i-1,mytype)*dx - cg_o(1))/cg_d(1)) + 1
                if (ii < 1 .or. ii > cg_n(1)) cycle
                if (cg_mask(ii,jj,kk) /= 0) epsi(i,j,k)=remp
             enddo
          enddo
       enddo
       return
    endif
""".replace("MARK", GEOMETRY_MARK),
    ),
    (
        "  end subroutine geomcomplex_cyl\n",
        """  end subroutine geomcomplex_cyl

  ! MARK: read clio-geometry.txt and clio-geometry.bin once
  subroutine clio_geom_load()

    implicit none

    logical :: found
    integer :: unit

    clio_geom_checked = .true.
    inquire(file="clio-geometry.txt", exist=found)
    if (.not. found) return
    open(newunit=unit, file="clio-geometry.txt", status="old", action="read")
    read(unit,*) cg_n
    read(unit,*) cg_o
    read(unit,*) cg_d
    close(unit)
    allocate(cg_mask(cg_n(1),cg_n(2),cg_n(3)))
    open(newunit=unit, file="clio-geometry.bin", access="stream", form="unformatted", &
         status="old", action="read")
    read(unit) cg_mask
    close(unit)
    clio_geom_on = .true.
    if (nrank == 0) write(*,"(A,3(1X,I0),A,I0)") " clio: geometry mask", cg_n, &
         ", solid voxels ", count(cg_mask /= 0)

  end subroutine clio_geom_load
""".replace("MARK", GEOMETRY_MARK),
    ),
    (
        _VISU_INIT,
        _VISU_INIT
        + "    ! "
        + GEOMETRY_MARK
        + "\n"
        + '    call decomp_2d_register_variable(io_name, "ep", 1, 0, output2D, mytype)\n',
    ),
    (
        _VISU_WRITE,
        _VISU_WRITE
        + "    ! "
        + GEOMETRY_MARK
        + "\n"
        + '    call write_field(ep1, ".", "ep", num, .true., flush = .true.)\n',
    ),
]


def apply_edits(path, edits):
    with open(path) as handle:
        text = handle.read()
    for old, new in edits:
        found = text.count(old)
        if found != 1:
            raise InstallError(f"{path}: expected one patch anchor, found {found}: {old[:60]!r}")
        text = text.replace(old, new)
    with open(path, "w") as handle:
        handle.write(text)


class Xcompact3d(CMakePackage):
    """Xcompact3d (Incompact3d): high-order finite-difference solvers for
    turbulent incompressible flows on 2DECOMP&FFT pencils.

    The clio variant makes the ADIOS2 snapshots (data.bp5) readable by
    ParaView's ADIOS2VTXReader (a vtk.xml attribute from ./clio-vtk.xml and a
    double ``time`` per step) and lets the cylinder wake case (itype = 5)
    immerse a voxel-mask body from ./clio-geometry.txt and .bin, writing ``ep``
    with each snapshot.
    """

    homepage = "https://www.incompact3d.com/"
    url = "https://github.com/xcompact3d/Incompact3d/archive/refs/tags/v5.0.tar.gz"
    git = "https://github.com/xcompact3d/Incompact3d.git"

    license("BSD-3-Clause")

    version("5.0", sha256="115433db20739189e5e27e688866c4b0cf2d167137ffb05d2dded8d8d77a42d4")

    variant(
        "clio",
        default=False,
        description="CLIO patches: VTX metadata in data.bp5 and the voxel-mask body",
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
    depends_on("decomp2d-fft@2:")
    depends_on("decomp2d-fft+clio io=adios2", when="+clio")
    depends_on("adios2+mpi+fortran", when="^decomp2d-fft io=adios2")

    def patch(self):
        if self.spec.satisfies("+clio"):
            apply_edits(join_path("src", "visu.f90"), VISU_EDITS)
            apply_edits(join_path("src", "genepsi3d.f90"), GENEPSI_EDITS)
            apply_edits(join_path("src", "Case-Cylinder-wake.f90"), CYLINDER_EDITS)

    def cmake_args(self):
        spec = self.spec
        decomp = spec["decomp2d-fft"]
        return [
            self.define("CMAKE_C_COMPILER", spec["mpi"].mpicc),
            self.define("CMAKE_CXX_COMPILER", spec["mpi"].mpicxx),
            self.define("CMAKE_Fortran_COMPILER", spec["mpi"].mpifc),
            self.define("IO_BACKEND", decomp.variants["io"].value),
            self.define("DECOMP2D_DIR", join_path(decomp.prefix, "lib", "decomp2d")),
            self.define("BUILD_TESTING", False),
        ]
