"""Isolated TRELLIS.2 evaluation; never imports or changes a villa scene.

Run download with any Python, and generate with the isolated TRELLIS Python.
All checkpoint downloads are public, pinned by revision, and hash checked.
GPU means graphics processing unit; MiB means 1,048,576 bytes.
"""
from __future__ import annotations

import argparse
import ast
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from archpipe.safe_io import copy_file, save_json  # noqa: E402
TOOL = Path('/home/omar/archpipe/tools/trellis2')
OUT = ROOT / 'out/trellis'
MAIN_REVISION = 'af44b45f2e35a493886929c6d786e563ec68364d'
STRUCTURE_REVISION = '25e0d31ffbebe4b5a97464dd851910efc3002d96'


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def cuda_root(compiler, expected_release=None):
    """Derive the toolkit layout from its actual command, then require headers.

    Keep the command's prefix: Debian's nvcc is a wrapper in /usr/bin and its
    headers are in /usr/include, rather than beside the wrapped executable.
    """
    compiler = Path(compiler).absolute()
    root = compiler.parent.parent
    if (compiler.name != 'nvcc' or not compiler.is_file()
            or not os.access(compiler, os.X_OK) or not (root / 'include/cuda.h').is_file()):
        raise ValueError('CUDA toolkit requires executable bin/nvcc and include/cuda.h: ' + str(root))
    if expected_release:
        version = subprocess.check_output([str(compiler), '--version'], text=True)
        if 'release ' + expected_release + ',' not in version:
            raise ValueError('CUDA compiler must match the trial PyTorch release ' + expected_release)
    return root


def download_cuda():
    """Install only NVIDIA's official, hash-verified CUDA 12.4.1 components."""
    import shutil
    import tarfile
    base = 'https://developer.download.nvidia.com/compute/cuda/redist/'
    manifest = fetch_json(base + 'redistrib_12.4.1.json')
    folder = TOOL / 'cuda-12.4'
    receipts = []

    def install_copy(source, target):
        copy_file(source, target)
        shutil.copystat(source, target)
        return target

    for name in ('cuda_nvcc', 'cuda_cudart', 'cuda_cccl', 'cuda_nvrtc'):
        item = manifest[name]['linux-x86_64']
        archive = TOOL / 'downloads' / Path(item['relative_path']).name
        archive.parent.mkdir(parents=True, exist_ok=True)
        if not archive.is_file() or sha256(archive) != item['sha256']:
            subprocess.run(['curl', '--fail', '--location', '--retry', '3', '--output', str(archive),
                            base + item['relative_path']], check=True)
        if sha256(archive) != item['sha256']:
            raise ValueError('CUDA archive checksum mismatch: ' + name)
        extraction = TOOL / 'downloads' / name
        extraction.mkdir(exist_ok=True)
        with tarfile.open(archive) as source:
            source.extractall(extraction, filter='data')
        content = next(extraction.iterdir())
        folder.mkdir(exist_ok=True)
        for entry in content.iterdir():
            if entry.is_dir():
                shutil.copytree(entry, folder / entry.name, dirs_exist_ok=True,
                                copy_function=install_copy)
            else:
                install_copy(entry, folder / (name + '-' + entry.name))
        receipts.append(dict(component=name, version=manifest[name]['version'],
                             url=base + item['relative_path'], sha256=sha256(archive),
                             bytes=archive.stat().st_size, licence=manifest[name].get('license')))
    save_json(OUT / 'setup/cuda-components.json', receipts, indent=2)
    print(cuda_root(folder / 'bin/nvcc', '12.4'))


def fetch_json(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'ArchpipeTrellisTrial/1.0'})
    with urllib.request.urlopen(request, timeout=90) as stream:
        return json.load(stream)


def require_local_extensions(records, root):
    """Refuse a transitive resolver replacing measured local CUDA sources."""
    expected = {'nvdiffrast': 'nvdiffrast', 'nvdiffrec-render': 'nvdiffrec',
                'cumesh': 'CuMesh', 'flex-gemm': 'FlexGEMM', 'o-voxel': 'repo/o-voxel'}
    from urllib.parse import urlparse, unquote
    for name, relative in expected.items():
        url = urlparse(records.get(name, {}).get('url', ''))
        if (url.scheme != 'file' or url.netloc or
                Path(unquote(url.path)).resolve() != (Path(root) / relative).resolve()):
            raise ValueError('extension source differs from pinned local checkout: ' + name)


def check_extensions():
    from importlib.metadata import distribution
    records = {}
    for name in ('nvdiffrast', 'nvdiffrec-render', 'cumesh', 'flex-gemm', 'o-voxel'):
        installed = distribution(name)
        records[name] = dict(json.loads(installed.read_text('direct_url.json')),
                             version=installed.version)
    require_local_extensions(records, TOOL)
    save_json(OUT / 'setup/extension-origins.json', records, indent=2)
    print('All CUDA extension distributions retain their pinned local source origins.')


def require_model_dependencies(paths, importer=None):
    """Check unconditional imports in actual pinned model code before GPU work.

    Relative helper files are supplied explicitly; optional and deferred imports
    remain the model loader's responsibility. This does not execute model code.
    """
    import importlib
    importer = importer or importlib.import_module
    modules = set()
    for path in paths:
        for node in ast.parse(Path(path).read_text()).body:
            if isinstance(node, ast.Import):
                modules.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules.add(node.module.split('.')[0])
    missing = []
    for name in sorted(modules):
        try:
            importer(name)
        except ImportError as error:
            missing.append(name + ': ' + str(error))
    if missing:
        raise ValueError('Pinned model dependencies unavailable: ' + '; '.join(missing))
    return sorted(modules)


def check_model_dependencies():
    prepare_environment()
    paths = [TOOL / 'models/background/birefnet.py',
             TOOL / 'models/background/BiRefNet_config.py',
             TOOL / 'repo/trellis2/modules/image_feature_extractor.py']
    modules = require_model_dependencies(paths)
    save_json(OUT / 'setup/model-imports.json',
              dict(modules=modules, sources={str(p): sha256(p) for p in paths}), indent=2)
    print('Pinned model imports passed: ' + ', '.join(modules), flush=True)


def download():
    """Download immutable public checkpoints, including auxiliary provenance."""
    setup = OUT / 'setup'
    setup.mkdir(parents=True, exist_ok=True)
    main = fetch_json('https://huggingface.co/api/models/microsoft/TRELLIS.2-4B/revision/'
                      + MAIN_REVISION + '?blobs=true')
    config = fetch_json('https://huggingface.co/microsoft/TRELLIS.2-4B/resolve/'
                        + MAIN_REVISION + '/pipeline.json')
    external = fetch_json('https://huggingface.co/api/models/microsoft/TRELLIS-image-large'
                          '/revision/' + STRUCTURE_REVISION + '?blobs=true')
    encoder = fetch_json('https://huggingface.co/api/models/timm/vit_large_patch16_dinov3.lvd1689m'
                         '/revision/30c1109559f65dea34316b0d4842d35c5771fe11?blobs=true')
    background = fetch_json('https://huggingface.co/api/models/ZhengPeng7/BiRefNet'
                            '/revision/e2bf8e4460fc8fa32bba5ea4d94b3233d367b0e4?blobs=true')
    records = []
    for metadata in (main, external, encoder, background):
        (setup / (metadata['id'].replace('/', '--') + '-api.json')).write_text(
            json.dumps(metadata, indent=2) + '\n')
    jobs = []
    main_files = {'pipeline.json', 'README.md'}
    external_files = {'README.md'}
    for name, value in config['args']['models'].items():
        if name.endswith('_1024'):
            continue
        if value.startswith('microsoft/TRELLIS-image-large/'):
            prefix = value.removeprefix('microsoft/TRELLIS-image-large/')
            external_files.update({prefix + '.json', prefix + '.safetensors'})
        else:
            main_files.update({value + '.json', value + '.safetensors'})
    for metadata, names, folder in (
        (main, main_files, 'main'), (external, external_files, 'structure'),
        (encoder, {'config.json', 'model.safetensors', 'LICENSE.md', 'README.md'}, 'encoder'),
        (background, {'config.json', 'model.safetensors', 'BiRefNet_config.py', 'birefnet.py',
                      'README.md'}, 'background')):
        if metadata.get('gated'):
            raise ValueError('refusing an access-gated download: ' + metadata['id'])
        for item in metadata['siblings']:
            name = item['rfilename']
            if name not in names:
                continue
            target = TOOL / 'models' / folder / name
            expected = item.get('lfs', {}).get('sha256')
            jobs.append((metadata, name, target, expected))

    def transfer(job):
        metadata, name, target, expected = job
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or (expected and sha256(target) != expected):
            url = ('https://huggingface.co/' + metadata['id'] + '/resolve/' + metadata['sha']
                   + '/' + name + '?download=true')
            partial = target.with_name(target.name + '.part')
            result = subprocess.run(['curl', '--fail', '--location', '--retry', '5',
                                     '--retry-delay', '5', '--connect-timeout', '60',
                                     '--speed-time', '120', '--speed-limit', '1024',
                                     '--output', str(partial), url],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            if result.returncode:
                raise RuntimeError(name + ': ' + result.stderr.decode(errors='replace')[-1000:])
            if expected and sha256(partial) != expected:
                raise ValueError('download checksum mismatch: ' + name)
            partial.replace(target)
        receipt = dict(repository=metadata['id'], revision=metadata['sha'], file=name,
                       path=str(target), bytes=target.stat().st_size, sha256=sha256(target),
                       expected_sha256=expected)
        print('verified', metadata['id'], name, receipt['bytes'], flush=True)
        return receipt

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for receipt in pool.map(transfer, jobs):
            records.append(receipt)
            (setup / 'download-receipt.json').write_text(json.dumps(records, indent=2) + '\n')
    derived = json.loads(json.dumps(config))
    derived['args']['models'] = {key: str(TOOL / 'models' / (
        'structure/' + value.removeprefix('microsoft/TRELLIS-image-large/')
        if value.startswith('microsoft/TRELLIS-image-large/') else 'main/' + value))
        for key, value in derived['args']['models'].items() if not key.endswith('_1024')}
    derived['args']['image_cond_model'] = dict(name='TrialTimmDino', args={})
    derived['args']['rembg_model']['args']['model_name'] = str(TOOL / 'models/background')
    derived['args']['default_pipeline_type'] = '512'
    derived['args']['low_vram'] = True
    (TOOL / 'models/main/trial-pipeline.json').write_text(json.dumps(derived, indent=2) + '\n')


def prepare_environment():
    """Keep all runtime caches and model imports in the isolated installation."""
    for key, relative in (
        ('HF_HOME', 'cache/huggingface'), ('TORCH_HOME', 'cache/torch'),
        ('TORCH_EXTENSIONS_DIR', 'cache/torch-extensions'),
        ('TRITON_CACHE_DIR', 'cache/triton'), ('XDG_CACHE_HOME', 'cache/xdg')):
        os.environ[key] = str(TOOL / relative)
    os.environ.update(ATTN_BACKEND='xformers', SPARSE_ATTN_BACKEND='xformers',
                      CUDA_HOME=str(TOOL / 'cuda-12.4'), CC='/usr/bin/gcc-12', CXX='/usr/bin/g++-12',
                      TORCH_CUDA_ARCH_LIST='8.6', MAX_JOBS='4',
                      PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True',
                      FLEX_GEMM_AUTOTUNE_CACHE_PATH=str(TOOL / 'cache/flex-gemm.json'),
                      HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                      OMP_NUM_THREADS='8', OPENBLAS_NUM_THREADS='8')
    os.environ['PATH'] = str(TOOL / 'cuda-12.4/bin') + os.pathsep + os.environ['PATH']
    sys.path.insert(0, str(TOOL / 'repo'))


def uniform_scale(bounds, target_m, datum):
    """One positive scale for every axis; no inferred independent dimensions.

    Bounds are two three-coordinate corners in source units. Datum selects
    height along z or the largest horizontal extent. The target is metres.
    """
    import math
    if (len(bounds) != 2 or any(len(row) != 3 for row in bounds)
            or not all(math.isfinite(v) for row in bounds for v in row)
            or isinstance(target_m, bool) or not math.isfinite(target_m) or target_m <= 0):
        raise ValueError('finite bounds and positive authored target required')
    extents = [bounds[1][k] - bounds[0][k] for k in range(3)]
    if any(v <= 0 for v in extents):
        raise ValueError('trial objects must have three positive extents')
    if datum not in ('height', 'horizontal'):
        raise ValueError('explicit height or horizontal datum required')
    value = extents[2] if datum == 'height' else max(extents[:2])
    factor = target_m / value
    return dict(scale_xyz=[factor] * 3, dimensions_m=[value * factor for value in extents],
                target_m=target_m, datum=datum, source_bounds=bounds,
                size_basis='authored trial assumption; no photographic size measurement')


def mesh_measurement(vertices, triangles):
    """Measure raw indexing and geometric closure separately at export seams.

    Vertices are three-coordinate positions; triangles contain three vertex
    indices. Geometric welding groups coordinates rounded to eight decimal
    places for measurement only. Neither source arrays nor files are edited.
    """
    import numpy as np
    vertices = np.asarray(vertices, dtype=float)
    triangles = np.asarray(triangles)
    if (vertices.ndim != 2 or vertices.shape[1] != 3 or not len(vertices)
            or not np.isfinite(vertices).all() or triangles.ndim != 2
            or triangles.shape[1] != 3 or not len(triangles)
            or not np.issubdtype(triangles.dtype, np.integer)
            or triangles.min() < 0 or triangles.max() >= len(vertices)):
        raise ValueError('finite vertices and valid indexed triangles required')
    _, inverse = np.unique(np.round(vertices, 8), axis=0, return_inverse=True)

    def edges(faces):
        all_edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
        _, counts = np.unique(np.sort(all_edges, axis=1), axis=0, return_counts=True)
        degenerate = int(np.count_nonzero((faces[:, 0] == faces[:, 1])
                                          | (faces[:, 1] == faces[:, 2])
                                          | (faces[:, 2] == faces[:, 0])))
        return dict(boundary_edges=int(np.count_nonzero(counts == 1)),
                    nonmanifold_edges=int(np.count_nonzero(counts > 2)),
                    degenerate_triangles=degenerate,
                    closed=bool(np.all(counts == 2) and degenerate == 0))

    return dict(vertices=len(vertices), triangles=len(triangles),
                bounds=[vertices.min(0).tolist(), vertices.max(0).tolist()],
                dimensions=(vertices.max(0) - vertices.min(0)).tolist(),
                indexed_topology=edges(triangles),
                geometric_topology=edges(inverse[triangles]),
                closure_basis='undirected edge incidence, welded at 8 decimal places; '
                              'not proof of self-intersection freedom, volume or manufacture')


def convert_encoder():
    """Strictly map the public timm weights into TRELLIS's Transformers API.

    The timm checkpoint omits zero attention biases and the unused masked
    image token. Disable those biases and supply a zero mask token; inference
    never masks the conditioning photograph. All trained weights must map.
    """
    prepare_environment()
    import torch
    import timm
    import numpy as np
    from PIL import Image
    from safetensors.torch import load_file
    from transformers import DINOv3ViTConfig, DINOv3ViTModel
    torch.set_num_threads(8)
    source_path = TOOL / 'models/encoder/model.safetensors'
    source = load_file(str(source_path))
    target = {}
    fixed = {'cls_token': 'embeddings.cls_token', 'reg_token': 'embeddings.register_tokens',
             'patch_embed.proj.weight': 'embeddings.patch_embeddings.weight',
             'patch_embed.proj.bias': 'embeddings.patch_embeddings.bias',
             'norm.weight': 'norm.weight', 'norm.bias': 'norm.bias'}
    for name, tensor in source.items():
        if name in fixed:
            target[fixed[name]] = tensor
            continue
        parts = name.split('.')
        if parts[0] != 'blocks':
            raise ValueError('unmapped pretrained encoder weight: ' + name)
        prefix = 'layer.' + parts[1] + '.'
        rest = '.'.join(parts[2:])
        if rest == 'attn.qkv.weight':
            for component, values in zip(('q_proj', 'k_proj', 'v_proj'), tensor.chunk(3, dim=0)):
                target[prefix + 'attention.' + component + '.weight'] = values.contiguous()
        elif rest in ('gamma_1', 'gamma_2'):
            target[prefix + 'layer_scale' + rest[-1] + '.lambda1'] = tensor
        elif rest.startswith(('norm1.', 'norm2.')):
            target[prefix + rest] = tensor
        elif rest.startswith('attn.proj.'):
            target[prefix + 'attention.o_proj.' + rest.split('.')[-1]] = tensor
        elif rest.startswith('mlp.fc1.'):
            target[prefix + 'mlp.up_proj.' + rest.split('.')[-1]] = tensor
        elif rest.startswith('mlp.fc2.'):
            target[prefix + 'mlp.down_proj.' + rest.split('.')[-1]] = tensor
        else:
            raise ValueError('unmapped pretrained encoder weight: ' + name)
    config = DINOv3ViTConfig(hidden_size=1024, intermediate_size=4096, num_hidden_layers=24,
                            num_attention_heads=16, num_register_tokens=4, image_size=512,
                            layer_norm_eps=1e-5, query_bias=False, key_bias=False, value_bias=False)
    target['embeddings.mask_token'] = torch.zeros(1, 1, 1024)
    model = DINOv3ViTModel(config).eval()
    model.load_state_dict(target, strict=True)
    # Independent native timm implementation, with the same raw-token output
    # convention. This comparison is performed on CPU, outside GPU scheduling.
    reference = timm.create_model('vit_large_patch16_dinov3', pretrained=False, img_size=512,
                                  dynamic_img_size=True, num_classes=0).eval()
    reference.load_state_dict(source, strict=True)
    reference.norm = torch.nn.Identity()
    image = Image.open(ROOT / 'out/trellis/inputs/candidate-116407253.jpg').convert('RGB').resize((512, 512))
    pixels = torch.from_numpy(np.array(image).astype(np.float32) / 255).permute(2, 0, 1)[None]
    pixels = (pixels - torch.tensor([.485, .456, .406])[None, :, None, None]) / torch.tensor(
        [.229, .224, .225])[None, :, None, None]
    with torch.no_grad():
        value = model.embeddings(pixels, bool_masked_pos=None)
        position = model.rope_embeddings(pixels)
        for layer in model.layer:
            value = layer(value, position_embeddings=position)
        actual = torch.nn.functional.layer_norm(value, value.shape[-1:])
        other = reference.forward_features(pixels)
        other = torch.nn.functional.layer_norm(other, other.shape[-1:])
    difference = (actual - other).abs()
    record = dict(source_sha256=sha256(source_path), mapped_source_tensors=len(source),
                  target_tensors=len(target), strict_load=True, unused_mask_token='zero; never used',
                  zero_qkv_biases='disabled, matching timm public checkpoint',
                  image_size=[512, 512], output_shape=list(actual.shape),
                  max_absolute_feature_difference=float(difference.max()),
                  mean_absolute_feature_difference=float(difference.mean()),
                  comparison_limits=dict(max_absolute=.002, mean_absolute=.0001),
                  passed=bool(difference.max() < .002 and difference.mean() < .0001))
    save_json(OUT / 'setup/encoder-conversion.json', record, indent=2)
    if not record['passed']:
        raise ValueError('encoder conversion disagrees with independent timm feature output')
    destination = TOOL / 'models/encoder-transformers'
    model.save_pretrained(destination, safe_serialization=True)
    config_path = TOOL / 'models/main/trial-pipeline.json'
    pipeline = json.loads(config_path.read_text())
    pipeline['args']['image_cond_model'] = dict(name='DinoV3FeatureExtractor',
        args=dict(model_name=str(destination)))
    save_json(config_path, pipeline, indent=2)
    print(json.dumps(record), flush=True)


def generate(name, attempt='512'):
    prepare_environment()
    check_model_dependencies()
    import fcntl
    import traceback
    import threading
    import torch
    import numpy as np
    from PIL import Image
    from trellis2.pipelines import Trellis2ImageTo3DPipeline
    conversion = json.loads((OUT / 'setup/encoder-conversion.json').read_text())
    if conversion.get('passed') is not True:
        raise ValueError('encoder conversion requires an independent feature comparison')
    inputs = json.loads((OUT / 'inputs/manifest.json').read_text())
    source = next(row for row in inputs if row['id'] == name)
    path = ROOT / source['path']
    if sha256(path) != source['sha256']:
        raise ValueError('photo bytes differ from licensed input receipt')
    if not attempt or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in attempt):
        raise ValueError('attempt must be a simple lowercase directory name')
    folder = OUT / name / attempt
    folder.mkdir(parents=True, exist_ok=False)
    record = dict(status='failed', object=name, pipeline_type='512', seed=42,
                  photo=source, low_vram=True, code_revision=subprocess.check_output(
                      ['git', '-C', str(TOOL / 'repo'), 'rev-parse', 'HEAD'], text=True).strip(),
                  model_revision=MAIN_REVISION, encoder='public timm weights; strict Transformers conversion',
                  background='MIT BiRefNet', texture_size=2048, decimation_target=200000)
    monitor_stop = threading.Event()
    samples = []

    def monitor():
        while not monitor_stop.is_set():
            result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,utilization.gpu',
                                     '--format=csv,noheader,nounits'], capture_output=True, text=True)
            if result.returncode == 0:
                samples.append(dict(seconds=round(time.monotonic() - start, 3),
                                    reading=result.stdout.strip()))
            monitor_stop.wait(.25)

    with Path('/home/omar/archpipe/locks/graphics.lock').open('rb') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not torch.cuda.is_available():
            raise RuntimeError('host CUDA unavailable; no inference has run')
        # Wait for the shared lock; never remove a lock or kill another lane.
        start = time.monotonic()
        record['gpu_name'] = torch.cuda.get_device_name()
        torch.cuda.reset_peak_memory_stats()
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        try:
            pipeline = Trellis2ImageTo3DPipeline.from_pretrained(
                str(TOOL / 'models/main'), config_file='trial-pipeline.json')
            pipeline.cuda()
            image = pipeline.preprocess_image(Image.open(path))
            image.save(folder / 'preprocessed.png')
            record['preprocessed_sha256'] = sha256(folder / 'preprocessed.png')
            mesh = pipeline.run(image, seed=42, pipeline_type='512', preprocess_image=False)[0]
            torch.cuda.synchronize()
            record['generation_seconds'] = time.monotonic() - start
            np.savez_compressed(folder / 'raw.npz', vertices=mesh.vertices.cpu().numpy(),
                                faces=mesh.faces.cpu().numpy())
            record['raw_vertices'] = int(mesh.vertices.shape[0])
            record['raw_triangles'] = int(mesh.faces.shape[0])
            import o_voxel
            mesh.simplify(16777216)
            glb = o_voxel.postprocess.to_glb(
                vertices=mesh.vertices, faces=mesh.faces, attr_volume=mesh.attrs,
                coords=mesh.coords, attr_layout=mesh.layout, voxel_size=mesh.voxel_size,
                aabb=[[-.5, -.5, -.5], [.5, .5, .5]], decimation_target=200000,
                texture_size=2048, remesh=True, remesh_band=1, remesh_project=0, verbose=True)
            glb.export(str(folder / 'model.glb'), extension_webp=False)
            torch.cuda.synchronize()
            record.update(status='generated', model_sha256=sha256(folder / 'model.glb'))
        except Exception:
            record['failure'] = traceback.format_exc()
            raise
        finally:
            monitor_stop.set()
            thread.join(timeout=5)
            record.update(wall_seconds=time.monotonic() - start,
                          peak_torch_allocated_mib=torch.cuda.max_memory_allocated() / 1048576,
                          peak_torch_reserved_mib=torch.cuda.max_memory_reserved() / 1048576,
                          sampled_peak_device_mib=max((int(s['reading'].split(',')[0])
                                                       for s in samples), default=None))
            (folder / 'gpu-samples.json').write_text(json.dumps(samples, indent=2) + '\n')
            (folder / 'generation.json').write_text(json.dumps(record, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['download', 'generate', 'cuda-root', 'cuda-download',
                                             'convert-encoder', 'check-extensions', 'check-model-imports'])
    parser.add_argument('--object', choices=['pendant', 'plant', 'stool'])
    parser.add_argument('--compiler', type=Path)
    parser.add_argument('--expected-release')
    parser.add_argument('--attempt', default='512')
    args = parser.parse_args()
    if args.operation == 'cuda-root':
        if not args.compiler:
            parser.error('--compiler is required')
        print(cuda_root(args.compiler, args.expected_release))
    elif args.operation == 'cuda-download':
        download_cuda()
    elif args.operation == 'convert-encoder':
        convert_encoder()
    elif args.operation == 'check-extensions':
        check_extensions()
    elif args.operation == 'check-model-imports':
        check_model_dependencies()
    elif args.operation == 'download':
        download()
    else:
        if not args.object:
            parser.error('--object is required for generate')
        generate(args.object, args.attempt)


if __name__ == '__main__':
    main()
