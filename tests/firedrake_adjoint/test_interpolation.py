import pytest
pytest.importorskip("firedrake")

from firedrake import *
from firedrake_adjoint import *

from numpy.random import rand
from numpy.testing import assert_allclose


def test_interpolate_scalar_valued():
    mesh = IntervalMesh(10, 0, 1)
    V1 = FunctionSpace(mesh, "CG", 1)
    V2 = FunctionSpace(mesh, "CG", 2)
    V3 = FunctionSpace(mesh, "CG", 3)

    x, = SpatialCoordinate(mesh)
    f = interpolate(x, V1)
    g = interpolate(sin(x), V2)
    u = Function(V3)

    u.interpolate(3*f**2 + Constant(4.0)*g)

    J = assemble(u**2*dx)
    rf = ReducedFunctional(J, Control(f))

    h = Function(V1)
    h.vector()[:] = rand(V1.dim())
    assert taylor_test(rf, f, h) > 1.9

    rf = ReducedFunctional(J, Control(g))
    h = Function(V2)
    h.vector()[:] = rand(V2.dim())
    assert taylor_test(rf, g, h) > 1.9


def test_interpolate_vector_valued():
    mesh = UnitSquareMesh(10, 10)
    V1 = VectorFunctionSpace(mesh, "CG", 1)
    V2 = VectorFunctionSpace(mesh, "DG", 0)
    V3 = VectorFunctionSpace(mesh, "CG", 2)

    x = SpatialCoordinate(mesh)
    f = interpolate(as_vector((x[0]*x[1], x[0]+x[1])), V1)
    g = interpolate(as_vector((sin(x[1])+x[0], cos(x[0])*x[1])), V2)
    u = Function(V3)

    u.interpolate(f*dot(f,g) - 0.5*g)

    J = assemble(inner(f, g)*u**2*dx)
    rf = ReducedFunctional(J, Control(f))

    h = Function(V1)
    h.vector()[:] = 1
    assert taylor_test(rf, f, h) > 1.9


def test_interpolate_tlm():
    mesh = UnitSquareMesh(10, 10)
    V1 = VectorFunctionSpace(mesh, "CG", 1)
    V2 = VectorFunctionSpace(mesh, "DG", 0)
    V3 = VectorFunctionSpace(mesh, "CG", 2)

    x = SpatialCoordinate(mesh)
    f = interpolate(as_vector((x[0]*x[1], x[0]+x[1])), V1)
    g = interpolate(as_vector((sin(x[1])+x[0], cos(x[0])*x[1])), V2)
    u = Function(V3)

    u.interpolate(f - 0.5*g + f/(1+dot(f,g)))

    J = assemble(inner(f, g)*u**2*dx)
    rf = ReducedFunctional(J, Control(f))

    h = Function(V1)
    h.vector()[:] = 1
    f.tlm_value = h

    tape = get_working_tape()
    tape.evaluate_tlm()

    assert J.tlm_value is not None
    assert taylor_test(rf, f, h, dJdm=J.tlm_value) > 1.9

def test_interpolate_tlm_wit_constant():
    mesh = IntervalMesh(10, 0, 1)
    V1 = FunctionSpace(mesh, "CG", 2)
    V2 = FunctionSpace(mesh, "DG", 1)


    x = SpatialCoordinate(mesh)
    f = interpolate(x[0], V1)
    g = interpolate(sin(x[0]), V1)
    c = Constant(5.0)

    u = Function(V2)
    u.interpolate(c * f ** 2)

    # test tlm w.r.t constant only:
    c.tlm_value = Constant(1.0)
    J = assemble(u**2*dx)
    rf = ReducedFunctional(J, Control(c))
    h = Constant(1.0)

    tape = get_working_tape()
    tape.evaluate_tlm()
    assert abs(J.tlm_value - 2.0) < 1e-5
    assert taylor_test(rf, c, h, dJdm=J.tlm_value) > 1.9

    # test tlm w.r.t constant c and function f:
    tape.reset_tlm_values()
    c.tlm_value = Constant(0.4)
    f.tlm_value = g
    rf(c)  # replay to reset checkpoint values based on c=5
    tape.evaluate_tlm()
    assert abs(J.tlm_value - (0.8 + 100. * (5*cos(1.) - 3*sin(1.)))) < 1e-4

def test_interpolate_bump_function():
    mesh = UnitSquareMesh(10, 10)
    V = FunctionSpace(mesh, "CG", 2)
    x, y = SpatialCoordinate(mesh)
    #c = Constant((0.5, 0.5))
    cx = Constant(0.5)
    cy = Constant(0.5)
    f = interpolate(exp(-1/(1-(x-cx)**2)-1/(1-(y-cy)**2)), V)
    J = assemble(f*y**3*dx)
    rf = ReducedFunctional(J, [Control(cx), Control(cy)])
    h = [Constant(0.1), Constant(0.1)]
    assert taylor_test(rf, [cx, cy], h) > 1.9
