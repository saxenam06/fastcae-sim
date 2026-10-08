"""The environment builds what the rest of zenryx relies on (PLT-2)."""

import importlib

import pytest


def test_package_imports():
    import zenryx

    assert zenryx.__version__ == "0.1.0"


@pytest.mark.parametrize("name", ["pydantic", "numpy", "scipy"])
def test_core_dependencies_import(name):
    importlib.import_module(name)


def test_cadquery_builds_an_exact_box():
    cq = pytest.importorskip("cadquery")
    box = cq.Workplane("XY").box(10, 20, 30)
    assert box.val().Volume() == pytest.approx(6000.0, rel=1e-9)


@pytest.mark.parametrize("name", ["gmsh", "manifold3d", "skimage", "trimesh", "pyvista"])
def test_geometry_dependencies_import(name):
    pytest.importorskip(name)
