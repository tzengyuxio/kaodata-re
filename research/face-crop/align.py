"""Find where a small face image sits in a large one.

The large image is shrunk by a sweep of scales and the small one is matched against it with an FFT sum of squared
differences (coarse); Nelder-Mead then refines x, y and the scale with bicubic sampling (fine). Pixels are weighted
by the large image's alpha, so a background only the small image has is ignored, and optionally by the small
image's alpha too. The result is the box in large-image pixels that, resized to the small size, matches it best.
"""
import numpy as np
from PIL import Image
from scipy.optimize import minimize
from scipy.signal import fftconvolve


def rgba(im):
    a = np.asarray(im.convert("RGBA"), dtype=np.float64)
    return a[..., :3], a[..., 3] / 255


def sample(large, x, y, s, size):
    w, h = size
    return large.transform(size, Image.EXTENT, (x, y, x + w * s, y + h * s), Image.BICUBIC)


def _ssd(L, A, T, W):
    """Weighted mean squared error of T at every position of L, and how much of T's weight L's alpha covers."""
    k = W[::-1, ::-1]
    cov = fftconvolve(A, k, "valid")
    tot = 0
    for c in range(3):
        l, t = L[..., c], T[..., c]
        tot = tot + fftconvolve(A * l * l, k, "valid") - 2 * fftconvolve(A * l, (W * t)[::-1, ::-1], "valid") \
            + fftconvolve(A, (W * t * t)[::-1, ::-1], "valid")
    return tot / np.maximum(cov, 1e-9) / 3, cov / W.sum()


def align(large, small, scales, min_cover=0.6, small_alpha=False):
    """large, small: PIL images. scales: large pixels per small pixel to try. min_cover: least share of the small
    image that must land on opaque large pixels (the box may run past the figure into a transparent background).
    Returns dict(x, y, w, h, scale, rmse) with rmse on 0-255."""
    sw, sh = small.size
    T, ta = rgba(small)
    W = ta if small_alpha else np.ones(ta.shape)
    best = None
    for s in scales:
        lw, lh = round(large.width / s), round(large.height / s)
        if lw < sw or lh < sh:
            continue
        L, A = rgba(large.resize((lw, lh), Image.BOX))
        m, cov = _ssd(L, A, T, W)
        m[cov < min_cover] = np.inf
        i = np.unravel_index(np.argmin(m), m.shape)
        if best is None or m[i] < best[0]:
            best = (m[i], i[1] * large.width / lw, i[0] * large.height / lh, large.width / lw)
    _, x, y, s = best

    def cost(p):
        L, A = rgba(sample(large, p[0], p[1], p[2], small.size))
        w = A * W
        if w.sum() < min_cover * W.sum():
            return 1e9
        return ((L - T) ** 2 * w[..., None]).sum() / w.sum() / 3

    r = minimize(cost, [x, y, s], method="Nelder-Mead",
                 options=dict(xatol=0.02, fatol=0.001, maxiter=600,
                              initial_simplex=[[x, y, s], [x + s, y, s], [x, y + s, s], [x, y, s * 1.02]]))
    x, y, s = map(float, r.x)
    return dict(x=x, y=y, w=sw * s, h=sh * s, scale=s, rmse=float(r.fun) ** .5)


def rounded(box):
    return {k: round(v, 3) for k, v in box.items()}
