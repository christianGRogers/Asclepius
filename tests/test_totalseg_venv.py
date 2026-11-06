"""benchmark-seed's TotalSegmentator venv without ensurepip (issue #290).

Janus's system Python 3.10 has no python3.10-venv, so ``python -m venv`` cannot seed
pip. deploy/totalseg-venv.sh is run here against a stand-in for that Python (a
wrapper around this interpreter that fails like Debian's when venv would need
ensurepip) and a stub ``TotalSegmentator`` wheel, offline: pip reads
PIP_NO_INDEX / PIP_FIND_LINKS, and the find-links folder holds this Python's bundled
pip wheel and the stub.
"""

import glob
import os
import shutil
import subprocess
import sys
import zipfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HELPER = os.path.join(ROOT, 'deploy', 'totalseg-venv.sh')
DEPLOY = os.path.join(ROOT, 'deploy', 'segqueue14-deploy.sh')
VERSION = '2.18.0'

# Debian without python3.X-venv: `-m venv` fails unless --without-pip; `import
# ensurepip` fails. FAKE_NO_PIP=1 also takes away `-m pip` (no route left).
FAKE_PY = '''#!/bin/bash
args=" $* "
if [ "$1" = -m ] && [ "$2" = venv ] && [[ "$args" != *" --without-pip "* ]]; then
    echo "... because ensurepip is not available." >&2
    exit 1
fi
if [ "$1" = -m ] && [ "$2" = ensurepip ]; then echo "No module named ensurepip" >&2; exit 1; fi
if [ "$1" = -m ] && [ "$2" = pip ] && [ "${FAKE_NO_PIP:-}" = 1 ]; then
    echo "No module named pip" >&2; exit 1
fi
exec %s "$@"
'''


def _bundled_pip():
    try:
        import ensurepip
    except ImportError:
        return None
    found = glob.glob(os.path.join(os.path.dirname(ensurepip.__file__), '_bundled', 'pip-*.whl'))
    return found[0] if found else None


def _stub_wheel(folder, version=VERSION):
    """A TotalSegmentator wheel with a console script that prints its version."""
    name = f'TotalSegmentator-{version}'
    path = os.path.join(folder, f'{name}-py3-none-any.whl')
    files = {
        'totalseg_stub/__init__.py': f'def main():\n    print("stub {version}")\n',
        f'{name}.dist-info/METADATA':
            f'Metadata-Version: 2.1\nName: TotalSegmentator\nVersion: {version}\n',
        f'{name}.dist-info/WHEEL':
            'Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n',
        f'{name}.dist-info/entry_points.txt':
            '[console_scripts]\nTotalSegmentator = totalseg_stub:main\n',
    }
    record = ''.join(f'{f},,\n' for f in files) + f'{name}.dist-info/RECORD,,\n'
    with zipfile.ZipFile(path, 'w') as zf:
        for f, text in files.items():
            zf.writestr(f, text)
        zf.writestr(f'{name}.dist-info/RECORD', record)
    return path


@pytest.fixture
def setup(tmp_path):
    pip_whl = _bundled_pip()
    if pip_whl is None:
        pytest.skip('this Python has no bundled pip wheel')
    if subprocess.run([sys.executable, '-m', 'pip', '--version'], capture_output=True).returncode:
        pytest.skip('this Python has no pip (the stand-in for the live venv needs one)')
    links = tmp_path / 'links'
    links.mkdir()
    shutil.copy(pip_whl, links)
    _stub_wheel(str(links))
    fake = tmp_path / 'python3.10'
    fake.write_text(FAKE_PY % sys.executable)
    fake.chmod(0o755)
    env = dict(os.environ, PIP_NO_INDEX='1', PIP_FIND_LINKS=str(links),
               PIP_DISABLE_PIP_VERSION_CHECK='1', HOME=str(tmp_path))
    env.pop('PIP_REQUIRE_VIRTUALENV', None)
    data = tmp_path / 'segqueue-data'
    data.mkdir()
    return str(fake), str(data / 'totalseg-venv'), env


def _run(step, py, venv, env, version=VERSION):
    return subprocess.run(['bash', HELPER, step, py, venv, version], env=env,
                          capture_output=True, text=True, timeout=300)


def test_the_stand_in_fails_like_janus(setup, tmp_path):
    py, _, env = setup
    out = subprocess.run([py, '-m', 'venv', str(tmp_path / 'v')], env=env,
                         capture_output=True, text=True)
    assert out.returncode != 0 and 'ensurepip is not available' in out.stderr


def test_install_without_ensurepip(setup):
    py, venv, env = setup
    assert _run('check', py, venv, env).returncode == 1
    out = _run('install', py, venv, env)
    assert out.returncode == 0, out.stdout + out.stderr
    assert 'without ensurepip' in out.stdout and 'did not work' not in out.stdout
    ts = subprocess.run([os.path.join(venv, 'bin', 'TotalSegmentator')],
                        capture_output=True, text=True)
    assert ts.stdout.strip() == f'stub {VERSION}'
    assert _run('check', py, venv, env).returncode == 0
    # Re-running changes nothing.
    again = _run('install', py, venv, env)
    assert again.returncode == 0 and 'already installed' in again.stdout


@pytest.mark.parametrize('half', ['no_python', 'no_pip', 'wrong_version'])
def test_half_made_venv_is_recreated(setup, half):
    py, venv, env = setup
    if half == 'no_python':   # what the failed `-m venv` on janus left behind
        os.makedirs(os.path.join(venv, 'bin'))
        with open(os.path.join(venv, 'pyvenv.cfg'), 'w') as f:
            f.write('home = /usr/bin\n')
    elif half == 'no_pip':
        subprocess.run([sys.executable, '-m', 'venv', '--without-pip', venv], check=True)
    else:                     # a working venv, but not the pinned version
        _stub_wheel(env['PIP_FIND_LINKS'], version='2.17.0')
        assert _run('install', py, venv, env, version='2.17.0').returncode == 0
    with open(os.path.join(venv, 'leftover'), 'w') as f:
        f.write('x')
    sibling = os.path.join(os.path.dirname(venv), 'keep-me')
    with open(sibling, 'w') as f:
        f.write('x')
    assert _run('check', py, venv, env).returncode == 1
    out = _run('install', py, venv, env)
    assert out.returncode == 0, out.stdout + out.stderr
    assert 'incomplete; recreating' in out.stdout
    assert not os.path.exists(os.path.join(venv, 'leftover'))
    assert os.path.exists(sibling)
    assert _run('check', py, venv, env).returncode == 0


def test_no_route_fails_with_the_remedy(setup, tmp_path):
    py, venv, env = setup
    bin_dir = tmp_path / 'bin'   # bash and coreutils only: no uv, no virtualenv
    bin_dir.mkdir()
    for tool in ('bash', 'dirname', 'cat', 'env'):
        found = shutil.which(tool)
        if found:
            os.symlink(found, bin_dir / tool)
    env = dict(env, FAKE_NO_PIP='1', PATH=str(bin_dir))
    out = _run('install', py, venv, env)
    assert out.returncode == 1
    last = out.stderr.strip().splitlines()[-1]
    assert 'sudo apt install python3.' in last and '--seed-file' in last


@pytest.mark.parametrize('bad', ['', '/', 'relative/venv', '/venv'])
def test_refuses_a_venv_path_outside_a_data_dir(setup, bad):
    py, _, env = setup
    out = _run('install', py, bad, env)
    assert out.returncode == 1 and 'refusing venv path' in out.stderr


def test_deploy_uses_the_helper_not_a_bare_venv():
    text = open(DEPLOY).read()
    assert 'totalseg-venv.sh' in text
    assert '-m venv "$TS_VENV"' not in text
