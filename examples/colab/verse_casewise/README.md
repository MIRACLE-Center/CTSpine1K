# VerSe Colab notebooks

Open `VerSe_CT_CPU.ipynb` or `VerSe_CT_GPU.ipynb` in Google Colab and run top to bottom.
Each notebook embeds its entire helper program. No other local file is required.
For GPU, select a GPU runtime before starting.

The setup downloads all three author checkpoint assets with fixed SHA256 checks,
then the complete VerSe19 validation archive (2,162,900,394 bytes) before CT upload.
Select `DATASET_SCOPE = 'all'` for all six official VerSe archives. These datasets
are reference resources; pretrained inference does not require retraining or the
full training corpus. Archives remain compressed, indexed, and CRC-checked.

Accepted inputs: one or multiple 3D NIfTI/NRRD CT volumes, or one CT DICOM series
per ZIP. CT intensities must be HU. Multiple DICOM series, duplicate/missing slices,
gantry tilt and oblique geometry are rejected with explicit messages. For these,
use a validated converter/resampler to create an orthogonal CT NIfTI first.

The resulting ZIP contains per-case PDF/HTML reports, nine or more tagged color
images (three overview planes plus three per predicted vertebra), combined and
individual masks, converted CT, physical-volume measurements, JSON, checksums
and logs. Failed cases are marked; partial archives never imply all cases passed.
Model classes are C1-C7, T1-T12 and L1-L6. T13/sacrum/coccyx are unsupported.
These are segmentation and numbering candidates, not diagnostic findings.

## Script review and corrections

Reviewed the workspace's script inventory, existing CT upload/conversion and
reporting workflows, VerSe download/centroid scripts, and CPU/GPU Task056 runners;
checked relevant upstream model conversion, inference and checkpoint-loading code.
Cloned repositories also contain unrelated training, documentation and excluded
CTSpinoPelvic1K scripts; they are not included in the notebooks.

Corrections to the existing workflows:

- Checkpoint files belong in `all/`; validate their contents, not only file size.
- Instantiate the published trainer with local plans and stage 1, avoiding the
  checkpoint's original author's absolute directory paths and task-ID discovery.
- Explicit CPU/GPU placement; disable mixed precision on CPU. nnUNet 1.7.1 has
  CPU inference paths, so no blanket CUDA monkey-patching is needed.
- Load the legacy checkpoint in a separate process with trusted-checkpoint
  compatibility enabled only after SHA256 verification.
- Normalize to LPS, matching the upstream training preparation, and restore masks
  to the original physical grid; check both shape and affine.
- Support arbitrary uploaded filenames and process multiple cases sequentially.
- Use physical aspect ratios, consistent label colors, actual on-image tags,
  orientation letters, readable reports, and non-destructive timestamped output.
- Do not invent T13 support from the broader VerSe dataset label dictionary.

Sources: [CTSpine1K model](https://github.com/MIRACLE-Center/CTSpine1K),
[VerSe datasets](https://github.com/anjany/verse),
[nnUNet v1](https://github.com/MIC-DKFZ/nnUNet/tree/nnunetv1).

## Validation performed locally

Both notebook JSON files and all code cells compile. The author checkpoint loaded
successfully and ran a real CPU forward pass, producing 26 finite channels.
Synthetic anisotropic, noncanonical CT/mask data passed conversion and physical
geometry checks, color/label checks, nine-image report generation, and ZIP CRC.
Misaligned masks and ZIP traversal were rejected. PDF passed `qpdf --check` and
the sagittal preview was visually inspected. Dataset URL returned HTTP 200 with
the expected content length. Test artifacts are under `validation/`.

Full Colab installation/session execution, GPU inference and full clinical-volume
inference have not been verified here. CPU inference can take hours and require
more RAM than a free Colab runtime; the GPU notebook still needs adequate host RAM.

Rebuild with `ai_spine_feasibility/.venv/bin/python
ai_spine_feasibility/colab/verse_notebooks/build_notebooks.py` from workspace root.
