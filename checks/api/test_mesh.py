"""zenryx.api.mesh is fastcae-v1:src/fastcae/api/mesh.py, copied: it gives the original's bytes."""

import hashlib

import numpy as np

from zenryx.api.mesh import MAGIC, encode

# The original's encode() on the cube below, computed once from fastcae-v1's own file (9 October
# 2026, 03:10) without importing fastcae.
ORIGINAL_SHA256 = "f46b82491029fb9d4b93afa6a68c5ddef0026af9ee2d4b16ee4ad1130b4fd0ac"

CUBE = np.array(
    [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]],
    float,
)
TRIANGLES = np.array(
    [
        [0, 2, 1],
        [0, 3, 2],
        [4, 5, 6],
        [4, 6, 7],
        [0, 1, 5],
        [0, 5, 4],
        [1, 2, 6],
        [1, 6, 5],
        [2, 3, 7],
        [2, 7, 6],
        [3, 0, 4],
        [3, 4, 7],
    ]
)
FACES = np.array([0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5])


def test_the_copy_gives_the_originals_bytes():
    blob = encode(CUBE, TRIANGLES, FACES)
    assert blob[:8] == MAGIC
    assert hashlib.sha256(blob).hexdigest() == ORIGINAL_SHA256


def test_a_cube_keeps_its_edges_sharp():
    # Welded by normal: each of the six faces keeps its own four corners, 24 vertices in all.
    blob = encode(CUBE, TRIANGLES, FACES)
    vertices = int.from_bytes(blob[8:12], "little")
    assert vertices == 24
