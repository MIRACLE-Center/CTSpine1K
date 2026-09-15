#!/usr/bin/env bash
set -euo pipefail

SESSION="${SESSION:-verse-fresh-gpu}"
GPU="${GPU-T4}"
DEVICE="${DEVICE:-gpu}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
COLAB="${COLAB:-colab}"
ADC="${ADC:-${ROOT}/.gcloud-colab/application_default_credentials.json}"
FOLDER_ID="${FOLDER_ID:-YOUR_GOOGLE_DRIVE_FOLDER_ID}"
DRIVE_URL="${DRIVE_URL:-https://drive.google.com/drive/folders/${FOLDER_ID}?usp=sharing}"
RESULT_DIR="${RESULT_DIR:-$RESULT_STORAGE/verse_casewise_results}"
EXEC_TIMEOUT="${EXEC_TIMEOUT:-21600}"

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

remote_write() {
  local src="$1"
  local dst="$2"
  if "${COLAB}" --auth=adc upload -s "${SESSION}" "${src}" "${dst}"; then
    return 0
  fi
  echo "Upload API failed; writing ${dst} via exec fallback."
  python3 - "${src}" "${dst}" <<'PY' |
import base64
import json
import sys
from pathlib import Path

src, dst = sys.argv[1:3]
payload = base64.b64encode(Path(src).read_bytes()).decode("ascii")
print("import base64, pathlib")
print("pathlib.Path(" + json.dumps(dst) + ").parent.mkdir(parents=True, exist_ok=True)")
print("pathlib.Path(" + json.dumps(dst) + ").write_bytes(base64.b64decode(" + json.dumps(payload) + "))")
PY
    "${COLAB}" --auth=adc exec --timeout 300 -s "${SESSION}"
}

remote_write \
  "${ROOT}/ai_spine_feasibility/colab/verse_notebooks/verse_pipeline.py" \
  /content/verse_${DEVICE}/verse_pipeline.py
remote_write \
  "${ROOT}/ai_spine_feasibility/colab/verse_notebooks/verse_casewise_colab.py" \
  /content/verse_${DEVICE}/verse_casewise_colab.py

for case_id in CASE_000 CASE_001 CASE_002 CASE_003 CASE_004 CASE_005 CASE_006; do
  echo "=== VerSe ${case_id} ==="
  local_zip="${RESULT_DIR}/${case_id}_VerSe.zip"
  if [[ -s "${local_zip}" ]] && unzip -t "${local_zip}" >/dev/null 2>&1 && ! unzip -l "${local_zip}" | grep -q 'FAILED.txt'; then
    echo "Valid local ZIP exists, skipping ${case_id}: ${local_zip}"
    continue
  fi
  python3 - "${DRIVE_URL}" "${case_id}" "${DEVICE}" <<'PY' |
import json
import sys

drive_url, case_id, device = sys.argv[1:4]
argv = [
    "/content/verse_" + device + "/verse_casewise_colab.py",
    "--drive-folder-url",
    drive_url,
    "--case-id",
    case_id,
    "--device",
    device,
    "--force",
]
print("import runpy, sys")
print("sys.argv=" + json.dumps(argv))
print("_ = runpy.run_path(sys.argv[0], run_name='__main__')")
PY
    "${COLAB}" --auth=adc exec --timeout "${EXEC_TIMEOUT}" -s "${SESSION}" || true

  remote_zip="/content/verse_${DEVICE}/${case_id}_VerSe.zip"
  if ! "${COLAB}" --auth=adc status -s "${SESSION}" >/dev/null 2>&1; then
    echo "Session ${SESSION} is gone; stopping case loop."
    exit 1
  fi
  if "${COLAB}" --auth=adc download -s "${SESSION}" "${remote_zip}" "${local_zip}"; then
    unzip -t "${local_zip}" >/dev/null
    echo "Downloaded ${local_zip}"
  else
    echo "No ZIP downloaded for ${case_id}; session may be lost or the case failed before packaging."
    exit 1
  fi
done

echo "VerSe casewise run complete. Local copies: ${RESULT_DIR}"
