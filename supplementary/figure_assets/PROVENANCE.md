# Fixed manuscript figure artwork

These five figures preserve the raster artwork in the author supplied `draft(1).pdf` and `supplementary-1.pdf`, supplied on 6 October 2026. The original image pixels were extracted without resampling. Each PDF is a one page wrapper around those pixels at the original displayed aspect ratio. The PNG counterpart preserves the decoded pixels. Figure 1 retains its original transparency mask. No vector artwork is claimed.

The PDF wrapper was verified against the decoded pixels in the source PDF for every figure. `figure_manifest.json` records source page, dimensions, SHA256 hashes for the packaged PDF and PNG, and the decoded pixel hash.

These are fixed manuscript assets. `restore_figures.py` copies the five PDFs and verifies their hashes. The optional diagnostic plots are computed from the released numerical results; they have a different design and do not recreate this artwork.
