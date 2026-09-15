"""Embedded in both notebooks; standalone VerSe checkpoint inference and reporting."""
import os
os.environ.setdefault('MPLCONFIGDIR', '/tmp/verse_matplotlib')
import argparse, csv, hashlib, html, json, shutil, time, zipfile
from pathlib import Path
import nibabel as nib
import numpy as np
import SimpleITK as sitk
from scipy import ndimage
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import ListedColormap, BoundaryNorm, to_hex
from nnunet.preprocessing.preprocessing import get_do_separate_z, get_lowres_axis, resample_data_or_seg

NAMES = {**{i: f'C{i}' for i in range(1, 8)},
         **{i: f'T{i-7}' for i in range(8, 20)},
         **{i: f'L{i-19}' for i in range(20, 26)}}
COLORS = [(0, 0, 0, 0)] + [tuple(plt.cm.hsv((i * .61803398875) % 1)) for i in range(1, 26)]
CMAP = ListedColormap(COLORS)
NORM = BoundaryNorm(np.arange(-.5, 26.5), 26)
LIMITS = ('Research segmentation report; not a diagnostic CT interpretation. '
          'Labels require whole-spine anatomical counting. Missing labels may be outside the scan '
          'or missed by the model. L6 is a model label, not confirmation of lumbarization. '
          'This checkpoint cannot predict T13, sacrum or coccyx, or classify fractures, tumors or Castellvi types.')

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(8 * 1024**2), b''):
            h.update(block)
    return h.hexdigest()

def safe_extract(source, target):
    target = Path(target).resolve()
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as z:
        if sum(i.file_size for i in z.infolist()) > shutil.disk_usage(target).free - 2 * 1024**3:
            raise RuntimeError('Insufficient disk space to extract ZIP.')
        for i in z.infolist():
            p = (target / i.filename).resolve()
            if not p.is_relative_to(target) or (i.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Unsafe ZIP member: ' + i.filename)
        z.extractall(target)

def convert(source, out):
    source, out = Path(source), Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == '.zip':
        root = out.parent / 'dicom_extracted'
        safe_extract(source, root)
        import pydicom
        groups = {}
        for p in sorted(root.rglob('*')):
            if not p.is_file():
                continue
            try:
                ds = pydicom.dcmread(p, stop_before_pixels=True)
            except Exception:
                continue
            if getattr(ds, 'Modality', '') != 'CT' or not hasattr(ds, 'ImagePositionPatient'):
                continue
            if int(getattr(ds, 'NumberOfFrames', 1)) != 1:
                raise ValueError('Enhanced multiframe DICOM: convert to NIfTI before upload.')
            groups.setdefault(str(ds.SeriesInstanceUID), []).append((p, ds))
        if len(groups) != 1:
            raise ValueError(f'ZIP contains {len(groups)} CT series. Upload exactly one CT series per ZIP.')
        records = next(iter(groups.values()))
        if len(records) < 3:
            raise ValueError('At least three CT slices are required.')
        orient = np.array(records[0][1].ImageOrientationPatient, float)
        normal = np.cross(orient[:3], orient[3:])
        records.sort(key=lambda r: np.dot(np.array(r[1].ImagePositionPatient, float), normal))
        positions = np.array([np.array(d.ImagePositionPatient, float) for _, d in records])
        for _, d in records:
            if not np.allclose(d.ImageOrientationPatient, orient, atol=1e-4):
                raise ValueError('Inconsistent DICOM orientation.')
            if not np.allclose(d.PixelSpacing, records[0][1].PixelSpacing, atol=1e-4):
                raise ValueError('Inconsistent pixel spacing.')
        gaps = np.diff(positions @ normal)
        if np.any(gaps <= 0) or not np.allclose(gaps, np.median(gaps), rtol=.02, atol=.05):
            raise ValueError('Duplicate, missing or irregularly spaced DICOM slices.')
        if not np.allclose(np.diff(positions, axis=0), gaps[:, None] * normal, atol=.1):
            raise ValueError('Gantry tilt/shear: convert with a validated DICOM converter first.')
        reader = sitk.ImageSeriesReader()
        reader.SetFileNames([str(p) for p, _ in records])
        img = reader.Execute()
    else:
        if not str(source).lower().endswith(('.nii', '.nii.gz', '.nrrd')):
            raise ValueError('Supported: NIfTI, self-contained NRRD, or ZIP of one CT DICOM series.')
        img = sitk.ReadImage(str(source))
    if img.GetDimension() != 3 or img.GetNumberOfComponentsPerPixel() != 1:
        raise ValueError('Expected scalar 3D CT.')
    arr = sitk.GetArrayViewFromImage(img)
    if not np.isfinite(arr).all() or np.ptp(arr) == 0:
        raise ValueError('CT is empty, constant or non-finite.')
    if min(img.GetSpacing()) <= 0:
        raise ValueError('Invalid CT spacing.')
    # Remove metadata strings from the derived NIfTI; uploaded source stays untouched.
    for key in img.GetMetaDataKeys():
        img.EraseMetaData(key)
    sitk.WriteImage(img, str(out), True)
    return img

def infer(ct, prediction, model, work, device, tta):
    import torch
    from nnunet.training.network_training.nnUNetTrainerV2 import nnUNetTrainerV2
    torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
    if device == 'gpu' and not torch.cuda.is_available():
        raise RuntimeError('Enable a GPU Colab runtime and rerun.')
    original = sitk.ReadImage(str(ct))
    direction = np.array(original.GetDirection()).reshape(3, 3)
    # Match the repository training orientation (LPS). Reject oblique input rather than
    # silently applying the upstream rounding-based orientation code to it.
    if not np.allclose(direction, np.round(direction), atol=1e-3):
        raise ValueError('Oblique CT must first be resampled onto an orthogonal grid.')
    normalized = sitk.DICOMOrient(original, 'LPS')
    normalized_path = work / 'normalized_0000.nii.gz'
    sitk.WriteImage(normalized, str(normalized_path), True)
    trainer = nnUNetTrainerV2(str(model / 'plans.pkl'), 'all',
                            output_folder=str(work / 'trainer'), dataset_directory=str(work),
                            stage=1, fp16=(device == 'gpu'))
    trainer.initialize(training=False)
    trainer.load_checkpoint(str(model / 'all/model_final_checkpoint.model'), train=False)
    trainer.network.to('cuda' if device == 'gpu' else 'cpu')
    trainer.network.eval()
    trainer.data_aug_params['do_mirror'] = bool(tta)
    pred_lps = work / 'prediction_lps.nii.gz'
    print('preprocessing...', flush=True)
    data, _, properties = trainer.preprocess_patient([str(normalized_path)])
    print('predicting...', flush=True)
    seg, _ = trainer.predict_preprocessed_data_return_seg_and_softmax(
        data,
        do_mirroring=trainer.data_aug_params['do_mirror'],
        mirror_axes=trainer.data_aug_params['mirror_axes'],
        use_sliding_window=True,
        step_size=0.5,
        use_gaussian=True,
        pad_border_mode='constant',
        pad_kwargs={'constant_values': 0},
        verbose=True,
        all_in_gpu=False,
        mixed_precision=device == 'gpu')
    del data
    seg = seg.transpose(trainer.transpose_backward)
    target_shape = properties['size_after_cropping']
    if tuple(seg.shape) != tuple(target_shape):
        if get_do_separate_z(properties['original_spacing']):
            lowres_axis = get_lowres_axis(properties['original_spacing'])
        elif get_do_separate_z(properties['spacing_after_resampling']):
            lowres_axis = get_lowres_axis(properties['spacing_after_resampling'])
        else:
            lowres_axis = None
        if lowres_axis is not None and len(lowres_axis) != 1:
            lowres_axis = None
        print('low-memory label resample:', seg.shape, '->', target_shape, flush=True)
        seg = resample_data_or_seg(seg[None].astype(np.uint8), target_shape, is_seg=True,
                                   axis=lowres_axis, order=0,
                                   do_separate_z=lowres_axis is not None,
                                   order_z=0)[0].astype(np.uint8)
    original_shape = properties['original_size_of_raw_data']
    bbox = properties.get('crop_bbox')
    if bbox is not None:
        restored_seg = np.zeros(original_shape, dtype=np.uint8)
        for c in range(3):
            bbox[c][1] = min(bbox[c][0] + seg.shape[c], original_shape[c])
        restored_seg[bbox[0][0]:bbox[0][1],
                     bbox[1][0]:bbox[1][1],
                     bbox[2][0]:bbox[2][1]] = seg[:bbox[0][1]-bbox[0][0],
                                                   :bbox[1][1]-bbox[1][0],
                                                   :bbox[2][1]-bbox[2][0]]
    else:
        restored_seg = seg
    seg_img = sitk.GetImageFromArray(restored_seg.astype(np.uint8))
    seg_img.SetSpacing(properties['itk_spacing'])
    seg_img.SetOrigin(properties['itk_origin'])
    seg_img.SetDirection(properties['itk_direction'])
    sitk.WriteImage(seg_img, str(pred_lps), True)
    restored = sitk.Resample(sitk.ReadImage(str(pred_lps)), original,
                            sitk.Transform(), sitk.sitkNearestNeighbor, 0, sitk.sitkUInt8)
    sitk.WriteImage(restored, str(prediction), True)

def report(ct_path, pred_path, out, metadata):
    out = Path(out)
    for folder in ('images', 'masks'):
        (out / folder).mkdir(parents=True, exist_ok=True)
    ct_img, pred_img = nib.load(str(ct_path)), nib.load(str(pred_path))
    if ct_img.shape != pred_img.shape or not np.allclose(ct_img.affine, pred_img.affine, atol=1e-4):
        raise ValueError('CT/mask geometry mismatch.')
    pred = np.asanyarray(pred_img.dataobj)
    labels = np.unique(pred)
    if not np.isfinite(pred).all() or not np.equal(pred, np.round(pred)).all() or labels.min() < 0 or labels.max() > 25:
        raise ValueError('Invalid labels for this checkpoint.')
    present = [int(x) for x in labels if x > 0]
    if not present:
        raise ValueError('Empty segmentation; no successful report will be produced.')
    voxel_ml = abs(np.linalg.det(pred_img.affine[:3, :3])) / 1000
    rows = []
    for lab in present:
        mask = pred == lab
        count = int(mask.sum())
        center = ndimage.center_of_mass(mask)
        world = nib.affines.apply_affine(pred_img.affine, center)
        touches = any(np.any(np.take(mask, i, axis=a)) for a in range(3) for i in (0, -1))
        tags = ['predicted_label', 'verify_numbering']
        if touches:
            tags.append('touches_scan_boundary')
        if lab == 25:
            tags.append('L6_label_requires_anatomical_confirmation')
        rows.append(dict(label_id=lab, label=NAMES[lab], color=to_hex(COLORS[lab]),
                         voxels=count, volume_ml=round(count * voxel_ml, 3),
                         centroid_R_mm=round(float(world[0]), 3), centroid_A_mm=round(float(world[1]), 3),
                         centroid_S_mm=round(float(world[2]), 3), tags='; '.join(tags)))
        header = pred_img.header.copy()
        header.set_data_dtype(np.uint8)
        nib.save(nib.Nifti1Image(mask.astype(np.uint8), pred_img.affine, header),
                 out / 'masks' / f'{NAMES[lab]}.nii.gz')
    with (out / 'measurements.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    ct_c = nib.as_closest_canonical(ct_img)
    pc = np.asanyarray(nib.as_closest_canonical(pred_img).dataobj)
    cc = np.asanyarray(ct_c.dataobj)
    spacing = ct_c.header.get_zooms()[:3]
    summary = dict(metadata, shape=list(ct_img.shape), spacing_mm=list(map(float, ct_img.header.get_zooms()[:3])),
                   affine=ct_img.affine.tolist(), labels=rows, geometry_verified=True,
                   nonzero_voxels=int(np.count_nonzero(pred)), limitations=LIMITS,
                   model='MIRACLE-Center/CTSpine1K Task056_VerSe; 25 foreground classes',
                   input_sha256=digest(ct_path), prediction_sha256=digest(pred_path))
    (out / 'report.json').write_text(json.dumps(summary, indent=2))
    planes = [(0, 'sagittal', 'P', 'A', 'S', 'I'),
              (1, 'coronal', 'L', 'R', 'S', 'I'),
              (2, 'axial', 'L', 'R', 'A', 'P')]
    images = []
    with PdfPages(out / 'CT_report.pdf') as pdf:
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.text(.06, .95, 'VerSe CT segmentation report', fontsize=18, va='top')
        import textwrap
        intro = f"Case: {metadata.get('case_id', 'test')} | Device: {metadata.get('device', 'test')}\n"
        intro += f"Shape: {ct_img.shape} | Spacing (mm): {tuple(round(float(s), 3) for s in ct_img.header.get_zooms()[:3])}\n"
        intro += 'Geometry verified. Bone display window: level 400 / width 1800 HU.\n\n'
        intro += '\n'.join(textwrap.wrap(LIMITS, 88))
        fig.text(.06, .89, intro, fontsize=10, va='top')
        for n, row in enumerate(rows):
            y = .65 - n * .020
            fig.text(.07, y, '\u25a0', color=row['color'], fontsize=12)
            fig.text(.10, y, f"{row['label']:4} {row['volume_ml']:8.2f} mL  |  {row['voxels']} voxels", fontsize=9)
        pdf.savefig(fig)
        plt.close(fig)
        def render(axis, plane, index, name, edges):
            image = np.take(cc, index, axis=axis).T
            mask = np.take(pc, index, axis=axis).T
            dims = [d for d in range(3) if d != axis]
            extent = (0, image.shape[1]*spacing[dims[0]], 0, image.shape[0]*spacing[dims[1]])
            fig, ax = plt.subplots(figsize=(8.27, 10), layout='constrained')
            ax.imshow(image, cmap='gray', vmin=-500, vmax=1300, origin='lower', extent=extent)
            ax.imshow(np.ma.masked_equal(mask, 0), cmap=CMAP, norm=NORM, alpha=.48,
                      origin='lower', extent=extent, interpolation='nearest')
            for lab in np.unique(mask):
                if lab <= 0:
                    continue
                yy, xx = ndimage.center_of_mass(mask == lab)
                ax.text((xx+.5)*spacing[dims[0]], (yy+.5)*spacing[dims[1]], NAMES[int(lab)],
                        color='white', fontsize=9, ha='center',
                        bbox=dict(facecolor=COLORS[int(lab)], alpha=.85, edgecolor='white', pad=2))
            left, right, top, bottom = edges
            for x, y, t in ((.01,.5,left),(.98,.5,right),(.5,.99,top),(.5,.01,bottom)):
                ax.text(x,y,t,transform=ax.transAxes,color='cyan',ha='center',va='center',weight='bold')
            ax.set_title(f'{name} | {plane} slice {index}\nPredicted labels — numbering requires review', fontsize=11)
            ax.set_xlabel('mm'); ax.set_ylabel('mm')
            path = out / 'images' / f'{name}_{plane}.png'
            fig.savefig(path, dpi=150)
            pdf.savefig(fig)
            plt.close(fig)
            images.append(path.relative_to(out).as_posix())
        for axis, plane, *edges in planes:
            occ = np.count_nonzero(pc, axis=tuple(a for a in range(3) if a != axis))
            render(axis, plane, int(occ.argmax()), 'overview', edges)
        for lab in present:
            for axis, plane, *edges in planes:
                occ = np.count_nonzero(pc == lab, axis=tuple(a for a in range(3) if a != axis))
                render(axis, plane, int(occ.argmax()), NAMES[lab], edges)
    table = ''.join(f"<tr><td style='color:{r['color']}'>{r['label']}</td><td>{r['volume_ml']}</td><td>{html.escape(r['tags'])}</td></tr>" for r in rows)
    gallery = ''.join(f'<figure><img loading="lazy" src="{p}"><figcaption>{p}</figcaption></figure>' for p in images)
    (out / 'CT_report.html').write_text('<!doctype html><meta charset="utf-8"><title>VerSe CT report</title>'
        '<style>body{font:16px sans-serif;max-width:1100px;margin:30px auto}td,th{padding:8px;border-bottom:1px solid #ccc}'
        'img{max-width:100%}figure{display:inline-block;width:45%;vertical-align:top;margin:2%}</style>'
        f'<h1>VerSe CT segmentation report</h1><p>{html.escape(LIMITS)}</p>'
        '<p>Stable label colors; orientation letters and physical spacing shown on each image. '
        'Each overview is one selected slice, not a projection of the entire spine.</p>'
        '<table><tr><th>Predicted level</th><th>Volume mL</th><th>Tags</th></tr>'+table+'</table>'+gallery)
    return summary

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', required=True)
    args = p.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    root = Path(cfg['root'])
    result = root / cfg['run_id']
    result.mkdir(exist_ok=True)
    failures = []
    for i, source in enumerate(cfg['inputs'], 1):
        case_id = f'case_{i:03d}'
        out = result / case_id
        out.mkdir(exist_ok=True)
        signature = dict(source_sha256=digest(source), device=cfg['device'], tta=cfg['tta'])
        marker = out / 'COMPLETE.json'
        if marker.exists() and json.loads(marker.read_text()) == signature:
            print('Reusing completed:', case_id, flush=True)
            continue
        work = root / (cfg['run_id'] + '_work') / case_id
        work.mkdir(parents=True, exist_ok=True)
        try:
            started = time.time()
            print('Processing', case_id, flush=True)
            ct, pred = out / 'CT.nii.gz', out / 'vertebrae.nii.gz'
            convert(source, ct)
            infer(ct, pred, Path(cfg['model']), work, cfg['device'], cfg['tta'])
            report(ct, pred, out, dict(case_id=case_id, device=cfg['device'], tta=cfg['tta'],
                                     elapsed_inference_seconds=round(time.time()-started, 2)))
            marker.write_text(json.dumps(signature))
        except Exception as e:
            import traceback
            traceback.print_exc()
            failures.append(dict(case=case_id, error=str(e)))
            (out / 'FAILED.txt').write_text(str(e))
    shutil.copy2(root / 'resources.json', result / 'resources.json')
    (result / 'run_status.json').write_text(json.dumps({'failed': failures, 'case_count': len(cfg['inputs'])}, indent=2))
    manifest = {str(f.relative_to(result)): digest(f) for f in sorted(result.rglob('*')) if f.is_file()}
    (result / 'manifest_sha256.json').write_text(json.dumps(manifest, indent=2))
    archive = shutil.make_archive(str(result), 'zip', result)
    with zipfile.ZipFile(archive) as z:
        if z.testzip():
            raise RuntimeError('ZIP integrity check failed')
    print('ZIP:', archive, flush=True)
    if failures:
        raise RuntimeError(f'{len(failures)} case(s) failed. ZIP contains partial results and failure details.')

if __name__ == '__main__':
    main()
