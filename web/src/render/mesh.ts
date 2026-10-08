// The mesh types and the FCMESH03 decoder, copied from fastcae-v1:ui/src/api/client.ts
// (fastcae's tag): the interfaces Mesh and VoxelCells as they are there, and the decoding body
// of fetchMesh, made a function of an ArrayBuffer (zenryx bundles its meshes; nothing is
// fetched).

export interface VoxelCells {
  faces: Uint32Array;
  size: number;
  shape: [number, number, number];
  origin: [number, number, number];
}

export interface Mesh {
  positions: Float32Array;
  normals: Int8Array;
  faceIds: Uint32Array;
  indices: Uint32Array;
  vertexCount: number;
  indexCount: number;
  /** For a surface drawn over the part: how far each vertex stands off it, 0 on it to 255. */
  standing?: Uint8Array;
}

/** A mesh from its FCMESH03 bytes (zenryx.api.mesh.encode). */
export function decodeMesh(buffer: ArrayBuffer): Mesh {
  const magic = new TextDecoder().decode(new Uint8Array(buffer, 0, 8));
  if (magic !== "FCMESH03") {
    throw new Error(`unexpected mesh format "${magic}", expected FCMESH03`);
  }

  const view = new DataView(buffer);
  const vertexCount = view.getUint32(8, true);
  const triangleCount = view.getUint32(12, true);

  // Laid out so every array starts on a four-byte boundary: positions, then four bytes of normal
  // per vertex, then the face id, then the index buffer.
  let offset = 16;
  const positions = new Float32Array(buffer, offset, vertexCount * 3);
  offset += vertexCount * 12;
  const normals = new Int8Array(buffer, offset, vertexCount * 4);
  offset += vertexCount * 4;
  const faceIds = new Uint32Array(buffer, offset, vertexCount);
  offset += vertexCount * 4;
  const indices = new Uint32Array(buffer, offset, triangleCount * 3);
  offset += triangleCount * 12;
  // A surface drawn over the part may end with a byte per vertex: how far it stands off the part.
  const standing =
    buffer.byteLength >= offset + vertexCount
      ? new Uint8Array(buffer, offset, vertexCount)
      : undefined;

  return {
    positions,
    normals,
    faceIds,
    indices,
    vertexCount,
    indexCount: triangleCount * 3,
    standing,
  };
}

/** A mesh from base64 text: how the snapshot carries it. */
export function meshFromBase64(text: string): Mesh {
  const raw = atob(text);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
  return decodeMesh(bytes.buffer);
}
