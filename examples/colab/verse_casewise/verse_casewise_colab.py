#!/usr/bin/env python3
"""Casewise CTSpine1K Task056_VerSe Colab runner.

Downloads the user's Drive CT folder once, runs one selected case, then writes a
single ZIP so the local wrapper can download it immediately.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(cmd: list[str], **kwargs) -> None:
    print("+ " + " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True, **kwargs)


def setup(root: Path, device: str) -> tuple[Path, Path, dict[str, str]]:
    root.mkdir(parents=True, exist_ok=True)
    venv = root / "py312"
    py = venv / "bin/python"
    if not py.exists():
        run([sys.executable, "-m", "pip", "install", "-q", "uv"])
        run([sys.executable, "-m", "uv", "venv", "--python", "3.12", str(venv)])
    uv_pip_args = [
        sys.executable,
        "-m",
        "uv",
        "pip",
        "install",
        "--python",
        str(py),
    ]
    if device == "gpu":
        run(uv_pip_args + ["torch==2.4.1"])
    run(
        uv_pip_args
        + [
            "nnunet==1.7.1",
            "numpy==1.26.4",
            "scipy==1.13.1",
            "scikit-image==0.24.0",
            "scikit-learn==1.5.2",
            "pandas==2.2.3",
            "matplotlib==3.9.4",
            "batchgenerators==0.25.1",
            "nibabel==5.3.2",
            "SimpleITK==2.4.1",
            "pydicom==3.0.1",
            "gdown==5.2.0",
        ]
    )
    env = os.environ.copy()
    env.update(
        MPLCONFIGDIR=str(root / "mpl"),
        MPLBACKEND="Agg",
        nnUNet_raw_data_base=str(root / "raw"),
        nnUNet_preprocessed=str(root / "preprocessed"),
        RESULTS_FOLDER=str(root / "models"),
        OMP_NUM_THREADS="2",
        nnUNet_def_n_proc="1",
        TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD="1",
    )
    if device == "cpu":
        env["CUDA_VISIBLE_DEVICES"] = ""
    for key in ("MPLCONFIGDIR", "nnUNet_raw_data_base", "nnUNet_preprocessed", "RESULTS_FOLDER"):
        Path(env[key]).mkdir(parents=True, exist_ok=True)
    check = "import torch; print('torch', torch.__version__); "
    check += "assert torch.cuda.is_available(), 'GPU runtime not available'" if device == "gpu" else "print('cpu ready')"
    run([str(py), "-c", check], env=env)
    model = root / "models/3d_fullres/Task056_VerSe/nnUNetTrainerV2__nnUNetPlansv2.1"
    (model / "all").mkdir(parents=True, exist_ok=True)
    return py, model, env


def fetch_model(py: Path, model: Path, root: Path) -> None:
    assets = {
        "plans.pkl": (
            "1tjCxFW5H11ccio7Kqbywfo0U3i9SLKkD",
            "5dfbab18873e1e6c34e4edb28fda53e919ba4fcf19ca25085fee100e65332213",
            385756,
        ),
        "all/model_final_checkpoint.model.pkl": (
            "1FGYP61NbnEPx4ePEOx8sEPqEJSJI_TGL",
            "715ed0de4bbaa19fb51ea8ffbceb859da3b65b7f3e0df1c2dcf99d1d3872f4cf",
            11620,
        ),
        "all/model_final_checkpoint.model": (
            "1XT1LrGDrn_mctsGM6lb8-opSKPWrWqvj",
            "b506b4283bf6b84f949d66b8f7bd3fd3a18000343c11568415cf90614bc7bec7",
            252909130,
        ),
    }
    resources = {
        "model_source": "https://github.com/MIRACLE-Center/CTSpine1K",
        "model": {},
        "note": "Task056_VerSe checkpoint only; public dataset archive skipped for inference.",
    }
    for name, (file_id, checksum, expected_bytes) in assets.items():
        target = model / name
        if not target.exists() or sha256(target) != checksum:
            part = target.with_suffix(target.suffix + ".part")
            url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
            for attempt in range(1, 5):
                resume = part.exists() and part.stat().st_size < expected_bytes
                cmd = ["curl", "-fL", "--retry", "8", "--retry-delay", "5", "--max-time", "3600"]
                if resume:
                    cmd += ["-C", "-"]
                else:
                    if part.exists() and part.stat().st_size != expected_bytes:
                        part.unlink()
                    cmd += ["-o", str(part)]
                if resume:
                    cmd += ["-o", str(part)]
                cmd.append(url)
                print(f"Downloading {name}, attempt {attempt}, existing={part.stat().st_size if part.exists() else 0}/{expected_bytes}", flush=True)
                subprocess.run(cmd, check=False)
                if part.exists() and part.stat().st_size == expected_bytes and sha256(part) == checksum:
                    break
            if not part.exists() or part.stat().st_size != expected_bytes or sha256(part) != checksum:
                part.unlink(missing_ok=True)
                run([str(py), "-m", "gdown", "--id", file_id, "-O", str(part)])
            if sha256(part) != checksum:
                size = part.stat().st_size if part.exists() else 0
                raise RuntimeError(f"Checkpoint checksum mismatch: {name}; size={size}/{expected_bytes}")
            part.replace(target)
        resources["model"][name] = checksum
    (root / "resources.json").write_text(json.dumps(resources, indent=2))


def drive_folder(root: Path, py: Path, url: str) -> list[Path]:
    target = root / "drive_folder"
    if not list(target.glob("*.nrrd")) and not list(target.glob("*.nii")) and not list(target.glob("*.nii.gz")):
        target.mkdir(parents=True, exist_ok=True)
        run([str(py), "-m", "gdown", "--folder", url, "-O", str(target)])
    inputs = sorted([p for p in target.iterdir() if p.is_file() and str(p).lower().endswith((".nrrd", ".nii", ".nii.gz"))])
    if not inputs:
        raise RuntimeError("No NRRD/NIfTI scans found in Drive folder")
    return inputs


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--drive-folder-url", required=True)
    p.add_argument("--case-id", required=True)
    p.add_argument("--device", choices=["gpu", "cpu"], default="gpu")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    root = Path("/content/verse_" + args.device)
    py, model, env = setup(root, args.device)
    fetch_model(py, model, root)
    inputs = drive_folder(root, py, args.drive_folder_url)
    index = int(args.case_id.rsplit("_", 1)[1])
    source = inputs[index]
    run_id = args.case_id + "_VerSe"
    result = root / run_id
    archive = root / f"{run_id}.zip"
    if args.force and result.exists():
        shutil.rmtree(result)
    if args.force and archive.exists():
        archive.unlink()
    cfg = {
        "root": str(root),
        "model": str(model),
        "inputs": [str(source)],
        "run_id": run_id,
        "device": args.device,
        "tta": False,
    }
    (root / "run_config.json").write_text(json.dumps(cfg, indent=2))
    pipeline = root / "verse_pipeline.py"
    log = root / f"{run_id}.log"
    rc = 0
    with log.open("w") as f:
        proc = subprocess.run([str(py), "-u", str(pipeline), "--config", str(root / "run_config.json")], env=env, stdout=f, stderr=subprocess.STDOUT, text=True)
        rc = proc.returncode
    if archive.exists():
        with zipfile.ZipFile(archive) as z:
            bad = z.testzip()
            if bad:
                raise RuntimeError("ZIP check failed: " + bad)
    else:
        fail_dir = result
        fail_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(log, fail_dir / log.name)
        (fail_dir / "FAILED.txt").write_text(f"VerSe pipeline failed before archive, rc={rc}\n")
        archive = Path(shutil.make_archive(str(result), "zip", result))
    print(json.dumps({"case": args.case_id, "source": source.name, "returncode": rc, "archive": str(archive), "sha256": sha256(archive)}, indent=2), flush=True)


if __name__ == "__main__":
    main()
