"""Install isolated worker dependencies and Radiance under the user's home.

Run on Ubuntu using system Python. No administrator access or global
package changes. Downloads come from the official Radiance distribution.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request

RADIANCE_URL = ('https://www.radiance-online.org/download-install/'
                'radiance-source-code/latest-release/rad6R0P1.tar.gz/at_download/file')
RADIANCE_SHA256 = 'b720d39e43fcf2ea09ab1699b62418836dfad8316743727761d29e85f82585cf'
RADIANCE_TOOLS = ['rtrace','oconv','ies2rad','xform','gensky','gendaylit',
                  'rpict','rcalc','getinfo','pvalue','pfilt','genbox']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(argv, log, **kwargs):
    with Path(log).open('a') as stream:
        result = subprocess.run([str(v) for v in argv], stdin=subprocess.DEVNULL,
                                stdout=stream, stderr=subprocess.STDOUT, **kwargs)
    if result.returncode:
        raise RuntimeError('Command failed; see ' + str(log))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--release', type=Path, required=True)
    ap.add_argument('--root', type=Path, default=Path.home()/'archpipe')
    ap.add_argument('--radiance', action='store_true')
    a = ap.parse_args()
    root, release = a.root.resolve(), a.release.resolve()
    if not root.is_relative_to(Path.home()) or not release.is_relative_to(root/'releases'):
        raise ValueError('Worker installation must stay under the user-owned release directory')
    (root/'logs').mkdir(parents=True, exist_ok=True)
    req = release/'requirements-worker.txt'
    env_id = sha(req)[:16]
    envdir = root/'envs'/env_id
    venv = envdir/'venv'
    install_log = root/'logs'/('setup-'+env_id+'.log')
    if not (venv/'bin/python').is_file():
        run([sys.executable, '-m', 'venv', venv], install_log, timeout=120)
    if not (envdir/'installed.json').is_file():
        run([venv/'bin/python', '-m', 'pip', 'install', '-r', req], install_log, timeout=900)
        freeze = subprocess.check_output([venv/'bin/python', '-m', 'pip', 'freeze'], text=True)
        (envdir/'installed.json').write_text(json.dumps({'requirements_sha256':sha(req),
            'python':sys.version, 'packages':freeze.splitlines()}, indent=2))
    report = {'python':str(venv/'bin/python'), 'environment':str(envdir/'installed.json'),
              'release':str(release), 'blender':str(Path.home()/'opt/blender/blender')}
    if a.radiance:
        install = root/'tools/radiance-6.0.1'
        rad_log = root/'logs/radiance-install.log'
        if not (install/'source.json').is_file():
            cache = root/'downloads'
            cache.mkdir(exist_ok=True)
            archive = cache/'rad6R0P1.tar.gz'
            if not archive.is_file():
                request = urllib.request.Request(RADIANCE_URL, headers={'User-Agent':'archpipe/1.0'})
                with urllib.request.urlopen(request, timeout=90) as response:
                    temporary = archive.with_suffix('.part')
                    with temporary.open('wb') as dest:
                        while block := response.read(1024*1024):
                            dest.write(block)
                    temporary.replace(archive)
            if sha(archive) != RADIANCE_SHA256:
                raise RuntimeError('Radiance source checksum differs from the pinned official download')
            source_root = root/'build/radiance-6.0.1'
            source_root.mkdir(parents=True, exist_ok=True)
            with tarfile.open(archive) as tf:
                tf.extractall(source_root, filter='data')
            cmake_file = next(source_root.rglob('CMakeLists.txt'), None)
            if cmake_file is None:
                raise RuntimeError('Official source archive lacks CMake; inspect source before choosing a build route')
            source = cmake_file.parent
            build = source_root/'cmake-build'
            run(['cmake','-S',source,'-B',build,'-DBUILD_HEADLESS=ON',
                 '-DBUILD_QT=OFF','-DCMAKE_BUILD_TYPE=Release',
                 '-DCMAKE_INSTALL_PREFIX='+str(install)], rad_log, timeout=180)
            # The 6.0 patch release still builds its OpenGL helper library
            # unconditionally with BUILD_HEADLESS. Build named command-line
            # targets rather than adding desktop dependencies to a worker.
            run(['cmake','--build',build,'--parallel','8','--target',*RADIANCE_TOOLS], rad_log, timeout=900)
            (install/'bin').mkdir(parents=True, exist_ok=True)
            for tool in RADIANCE_TOOLS:
                shutil.copy2(build/'bin'/tool, install/'bin'/tool)
            shutil.copytree(build/'lib',install/'lib',dirs_exist_ok=True)
            (install/'source.json').write_text(json.dumps({'url':RADIANCE_URL,
                'sha256':sha(archive), 'checksum_provenance':'Measured on official download; not publisher-signed',
                'tools':RADIANCE_TOOLS, 'scope':'Headless simulation and conversion tools; no interactive viewer',
                'installed_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}, indent=2))
        report['radiance'] = str(install)
    (root/'worker-environment.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
