#!/usr/bin/env bash
# Run only after the isolated PyTorch installation has completed.
# No project Python, Blender, system packages or user home settings are changed.
set -euo pipefail
TRELLIS_ROOT=/home/omar/archpipe/tools/trellis2
TRIAL_ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
TRIAL_LOG="$TRIAL_ROOT/out/trellis/setup"
export PATH="$TRELLIS_ROOT/venv/bin:$PATH"
export CUDA_HOME
CUDA_HOME=$(python "$TRIAL_ROOT/scripts/trellis_trial.py" cuda-root \
    --compiler "$TRELLIS_ROOT/cuda-12.4/bin/nvcc" --expected-release 12.4)
export CC=/usr/bin/gcc-12 CXX=/usr/bin/g++-12
export TORCH_CUDA_ARCH_LIST=8.6 MAX_JOBS=4 OMP_NUM_THREADS=8
export TORCH_EXTENSIONS_DIR="$TRELLIS_ROOT/cache/torch-extensions"
export FLEX_GEMM_AUTOTUNE_CACHE_PATH="$TRELLIS_ROOT/cache/flex-gemm.json"
export UV_CACHE_DIR="$TRELLIS_ROOT/cache/uv"
mkdir -p "$TRELLIS_ROOT/cache" "$TRIAL_LOG"
UV=/home/omar/.local/bin/uv
"$UV" pip install --python "$TRELLIS_ROOT/venv/bin/python" \
    'setuptools<81' wheel packaging ninja imageio imageio-ffmpeg tqdm easydict \
    opencv-python-headless trimesh 'transformers==4.57.6' 'huggingface-hub==0.36.2' \
    'timm>=1.0.22,<1.1' 'einops==0.8.2' kornia scipy zstandard 'xformers==0.0.29.post3' \
    'git+https://github.com/EasternJournalist/utils3d.git@9a4eb15e4021b67b12c460c7057d642626897ec8' \
    > "$TRIAL_LOG/basic-install.log" 2>&1
# FlexGEMM's runtime honours this cache variable, but its setup script writes
# a hardcoded home cache. Keep the small installation-only patch and its diff.
python - "$TRELLIS_ROOT" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
path = root/'FlexGEMM/setup.py'
source = path.read_text()
source = source.replace('os.path.expanduser("~/.flex_gemm")',
                        'os.path.dirname(os.environ["FLEX_GEMM_AUTOTUNE_CACHE_PATH"])')
source = source.replace('os.path.expanduser("~/.flex_gemm/autotune_cache.json")',
                        'os.environ["FLEX_GEMM_AUTOTUNE_CACHE_PATH"]')
if '~/.flex_gemm' in source:
    raise SystemExit('Unrecognised setup cache path; refusing shared home write')
path.write_text(source)
PY
git -C "$TRELLIS_ROOT/FlexGEMM" diff > "$TRIAL_LOG/flexgemm-isolation.patch"
for TRIAL_EXTENSION in nvdiffrast nvdiffrec CuMesh FlexGEMM repo/o-voxel; do
    TRIAL_NAME=${TRIAL_EXTENSION//\//-}
    "$UV" pip install --python "$TRELLIS_ROOT/venv/bin/python" \
        "$TRELLIS_ROOT/$TRIAL_EXTENSION" --no-build-isolation --no-deps \
        > "$TRIAL_LOG/$TRIAL_NAME-build.log" 2>&1
done
"$UV" pip freeze --python "$TRELLIS_ROOT/venv/bin/python" > "$TRIAL_LOG/packages.txt"
python "$TRIAL_ROOT/scripts/trellis_trial.py" check-extensions > "$TRIAL_LOG/extension-origins.log"
"$UV" pip check --python "$TRELLIS_ROOT/venv/bin/python" > "$TRIAL_LOG/package-check.log" 2>&1
python -c 'import torch, xformers, nvdiffrast, nvdiffrec_render, cumesh, flex_gemm, o_voxel; print(torch.__version__)' \
    > "$TRIAL_LOG/imports.log" 2>&1
# Downloaded model code has its own dependencies. Generation unconditionally
# checks it before GPU acquisition, including when bootstrap preceded download.
if [ -f "$TRELLIS_ROOT/models/background/birefnet.py" ]; then
    python "$TRIAL_ROOT/scripts/trellis_trial.py" check-model-imports > "$TRIAL_LOG/model-imports.log" 2>&1
fi
