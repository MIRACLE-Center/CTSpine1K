#!/usr/bin/env bash
set -euo pipefail

SESSION="${SESSION:-verse-gdrive-gpu-2314}"
DEVICE="${DEVICE:-gpu}"
GPU="${GPU:-T4}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
COLAB="${COLAB:-colab}"
ADC="${ADC:-${ROOT}/.gcloud-colab/application_default_credentials.json}"
FOLDER_ID="${FOLDER_ID:-YOUR_GOOGLE_DRIVE_FOLDER_ID}"
DRIVE_URL="${DRIVE_URL:-https://drive.google.com/drive/folders/${FOLDER_ID}?usp=sharing}"
RESULT_DIR="${RESULT_DIR:-$RESULT_STORAGE/verse_gdrive_gpu_results_20260913}"
POLL_SECONDS="${POLL_SECONDS:-60}"

export GOOGLE_APPLICATION_CREDENTIALS="${ADC}"
mkdir -p "${RESULT_DIR}"

"${COLAB}" --auth=adc sessions >/dev/null || true
if ! "${COLAB}" --auth=adc sessions | grep -F "[${SESSION}]" >/dev/null 2>&1; then
  if [[ -n "${GPU}" ]]; then
    "${COLAB}" --auth=adc new -s "${SESSION}" --gpu "${GPU}"
  else
    "${COLAB}" --auth=adc new -s "${SESSION}"
  fi
fi

"${COLAB}" --auth=adc exec --timeout 300 -s "${SESSION}" <<PY
from pathlib import Path
Path('/content/verse_${DEVICE}').mkdir(parents=True, exist_ok=True)
PY

"${COLAB}" --auth=adc upload -s "${SESSION}" \
  "${ROOT}/ai_spine_feasibility/colab/verse_notebooks/verse_pipeline.py" \
  "/content/verse_${DEVICE}/verse_pipeline.py"
"${COLAB}" --auth=adc upload -s "${SESSION}" \
  "${ROOT}/ai_spine_feasibility/colab/verse_notebooks/verse_casewise_colab.py" \
  "/content/verse_${DEVICE}/verse_casewise_colab.py"

for case_id in CASE_000 CASE_001 CASE_002 CASE_003 CASE_004 CASE_005 CASE_006; do
  local_zip="${RESULT_DIR}/${case_id}_VerSe.zip"
  if [[ -s "${local_zip}" ]] && unzip -t "${local_zip}" >/dev/null 2>&1 && ! unzip -l "${local_zip}" | grep -q 'FAILED.txt'; then
    echo "valid_local ${case_id} ${local_zip}"
    continue
  fi

  python3 - "${DRIVE_URL}" "${case_id}" "${DEVICE}" <<'PY' | "${COLAB}" --auth=adc exec --timeout 300 -s "${SESSION}"
import json
import sys

drive_url, case_id, device = sys.argv[1:4]
code = f"""
from pathlib import Path
import json, os, subprocess, sys, time

root = Path('/content/verse_{device}')
archive = root / '{case_id}_VerSe.zip'
pidfile = root / '{case_id}.pid'
state = root / '{case_id}.state.json'
if archive.exists():
    archive.unlink()
if pidfile.exists():
    try:
        os.kill(int(pidfile.read_text().strip()), 0)
        print('already_running {case_id}')
        raise SystemExit
    except OSError:
        pidfile.unlink()
cmd = [
    '/usr/bin/python3', '-u', str(root / 'verse_casewise_colab.py'),
    '--drive-folder-url', {json.dumps(drive_url)},
    '--case-id', {json.dumps(case_id)},
    '--device', {json.dumps(device)},
    '--force',
]
log = open(root / '{case_id}.bg.log', 'ab', buffering=0)
proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
pidfile.write_text(str(proc.pid))
state.write_text(json.dumps({{'case': '{case_id}', 'pid': proc.pid, 'started': time.time()}}, indent=2))
print('started {case_id}', proc.pid)
"""
print(code)
PY

  while true; do
    remote_zip="/content/verse_${DEVICE}/${case_id}_VerSe.zip"
    if "${COLAB}" --auth=adc download -s "${SESSION}" "${remote_zip}" "${local_zip}" >/dev/null 2>&1; then
      unzip -t "${local_zip}" >/dev/null
      echo "downloaded ${case_id} ${local_zip}"
      break
    fi
    "${COLAB}" --auth=adc exec --timeout 300 -s "${SESSION}" <<PY || true
from pathlib import Path
p=Path('/content/verse_${DEVICE}/${case_id}.bg.log')
if p.exists():
    lines=p.read_text(errors='replace').splitlines()
    print('\\n'.join(lines[-8:]))
else:
    print('waiting_for_log ${case_id}')
PY
    sleep "${POLL_SECONDS}"
  done
done
