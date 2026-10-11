"""ImageCAS-X centreline start points (the expert ostia) from legacy VTK 5.1 polydata (binary or ASCII), without the vtk
package (keeps the Trillium venv small). Validated against vtk.vtkPolyDataReader on all local centreline files
(see README). Returns points in nibabel world coordinates (RAS): ImageCAS-X stores LPS.
Usage (module): start_points(path) -> (k, 3) float array, or None if the file has no start_points array."""
import re
import numpy as np

_DT = {b'float': '>f4', b'double': '>f8', b'int': '>i4', b'vtktypeint64': '>i8', b'long': '>i8'}


def _read(b, offset, count, dtype, ascii_):
    if not ascii_:
        return np.frombuffer(b, np.dtype(_DT[dtype]), count, offset).astype(float)
    toks = re.finditer(rb'\S+', b[offset:])
    out = np.empty(count, float)
    for i in range(count):
        out[i] = float(next(toks).group(0))
    return out


def start_points(path):
    b = open(path, 'rb').read()
    head = b[:200]
    if not b.startswith(b'# vtk DataFile') or (b'\nBINARY\n' not in head and b'\nASCII\n' not in head):
        raise ValueError(f'{path}: not a legacy VTK file')
    ascii_ = b'\nASCII\n' in head
    m = re.search(rb'\nPOINTS (\d+) (float|double)\s*\n', b)
    if not m:
        raise ValueError(f'{path}: no POINTS section')
    n = int(m.group(1))
    P = _read(b, m.end(), 3 * n, m.group(2), ascii_).reshape(n, 3)
    m = re.search(rb'\nstart_points 1 (\d+) (int|vtktypeint64|long)\s*\n', b)
    if not m:
        return None
    if int(m.group(1)) != n:
        raise ValueError(f'{path}: start_points has {m.group(1)} values for {n} points')
    s = _read(b, m.end(), n, m.group(2), ascii_)
    return P[s > 0] * np.array([-1.0, -1.0, 1.0])
