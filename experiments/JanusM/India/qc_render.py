"""Render short-axis slices (basal, mid, apical) of one subject: CT, AHA segment and transmural layer.
Writes a PNG to the given path (kept out of the repository: it is an image of a CT)."""
import sys, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import ndimage as ndi
import lvgeom as G

def plane(vol, g, fr, s, size=90, step=0.5, order=0):
    u = np.arange(-size / 2, size / 2, step)
    U, V = np.meshgrid(u, u, indexing="ij")
    c = fr["base"] + s * fr["axis"]
    W = c[None, None] + U[..., None] * fr["e1"] + V[..., None] * np.cross(fr["axis"], fr["e1"])
    inv = np.linalg.inv(g["affine"])
    ijk = W.reshape(-1, 3) @ inv[:3, :3].T + inv[:3, 3]
    return ndi.map_coordinates(vol.astype(np.float32), ijk.T, order=order).reshape(U.shape)

d, out = sys.argv[1], sys.argv[2]
g = G.resample_masks(G.load_subject(d), 0.5); g["myo"] = G.keep_largest(g["myo"])
fr = G.lv_frame(g); seg = G.aha17(g, fr); td, _ = G.depth_distance(g["myo"], g["lv"], g["spacing"])
L = G.layers(td, g["myo"])
L_ = np.linalg.norm(fr["apex"] - fr["base"])
fig, ax = plt.subplots(3, 3, figsize=(10, 10))
for i, f in enumerate((0.2, 0.45, 0.7)):
    s = f * L_
    ax[0, i].imshow(plane(g["ct"], g, fr, s, order=1), cmap="gray", vmin=-100, vmax=500)
    ax[1, i].imshow(plane(seg, g, fr, s), cmap="tab20", vmin=0, vmax=19, interpolation="nearest")
    ax[2, i].imshow(plane(L, g, fr, s), cmap="viridis", vmin=0, vmax=3, interpolation="nearest")
    ax[0, i].set_title(f"{f:.2f} of base-apex; arc {fr['septal_arc_deg']:.0f}")
for a in ax.flat: a.axis("off")
plt.tight_layout(); plt.savefig(out, dpi=70)
