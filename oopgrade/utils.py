from ast import literal_eval
import logging
import os
import sys
import subprocess

__all__ = [
    'get_dependencies',
    'install_requirements',
]

logger = logging.getLogger(__name__)


def get_dependencies(module, addons_path=None, deps=None):
    """Get all the dependencies of a module without database

    Using `__terp__.py` files and is used to check requirements.txt in the
    dependencies.

    :param module: Module to find the dependencies
    :param addons_path: Path to find the modules
    :return: a listt of dependencies.
    """
    if deps is None:
        deps = []
    pj = os.path.join
    module_path = pj(addons_path, module)
    if not os.path.exists(module_path):
        raise Exception('Module \'{}\' not found in {}'.format(
            module, addons_path
        ))
    terp_path = pj(module_path, '__terp__.py')
    if not os.path.exists(terp_path):
        raise Exception(
            'Module {} is not a valid module. Missing __terp__.py file'.format(
                module
            )
        )
    with open(terp_path, 'r') as terp_file:
        terp = literal_eval(terp_file.read())

    for dep in terp['depends']:
        if dep not in deps:
            deps.append(dep)
            deps += get_dependencies(dep, addons_path, deps)

    return list(set(deps))


def parse_requirement_line(line):
    line = line.strip()
    if not line or line.startswith('#'):
        return None, None
    parts = line.split(';', 1)
    req = parts[0].strip()
    marker = parts[1].strip() if len(parts) > 1 else ''
    name = req.split('==')[0].split('<=')[0].split('>=')[0].split('<')[0].split('>')[0].strip().lower()
    return (name, marker), req + (' ; ' + marker if marker else '')


def _has_version_spec(req_line):
    return any(op in req_line for op in ['==', '>=', '<=', '>', '<'])


def clean_requirements_lines(lines):
    from collections import defaultdict
    all_versions = defaultdict(dict)  # key = package name (lowercase), value = {marker: line}

    for line in lines:
        key_marker, full_req = parse_requirement_line(line)
        if not key_marker:
            continue
        name, marker = key_marker
        existing = all_versions[name].get(marker)
        has_ver = _has_version_spec(full_req)

        if not existing:
            all_versions[name][marker] = full_req
        else:
            current_has_ver = _has_version_spec(existing)
            # Prefer the new one if it has a version and the existing one does not
            if has_ver and not current_has_ver:
                all_versions[name][marker] = full_req
            # If both have versions, keep the longest (most restrictive)
            elif has_ver and len(full_req) > len(existing):
                all_versions[name][marker] = full_req

    cleaned = []
    for name, markers in all_versions.items():
        if '' in markers and len(markers) > 1:
            generic = markers['']
            # Check if all specific markers refer to the same version
            versions = set()
            for m, req in markers.items():
                if m == '':
                    continue
                parts = req.split(';', 1)[0]
                versions.add(parts.strip())
            # If all marker-specific lines use the same version and it's not equal to the generic one
            if len(versions) == 1 and generic.strip().split(';')[0] not in versions:
                # Remove the unmarked (generic) requirement as it's redundant
                del markers['']
        cleaned.extend(markers.values())

    return sorted(cleaned)


def pip_install_requirements(requirements_path, silent=False):
    subprocess_kwargs = {}
    if silent:
        FNULL = open(os.devnull, 'w')
        subprocess_kwargs = {
            'stderr': FNULL,
            'stdout': FNULL
        }
    pip = os.path.join(sys.prefix, 'bin', 'pip')
    if os.path.exists(requirements_path):
        logger.info('Requirements file %s found. Installing...', requirements_path)
        subprocess.check_call([pip, "install", "-r", requirements_path], **subprocess_kwargs)


def install_requirements(module, addons_path, silent=False, done=None):
    """Install module requirements and its dependecies
    """
    if done is None:
        done = []
    pip = os.path.join(sys.prefix, 'bin', 'pip')
    if os.path.exists(pip):
        modules_requirements = get_dependencies(module, addons_path)
        modules_requirements.append(module)
        for module_requirements in modules_requirements:
            if module_requirements in done:
                continue
            addons_path_module = os.path.join(addons_path, module_requirements)
            req = os.path.join(addons_path_module, 'requirements.txt')
            pip_install_requirements(req, silent)
        return modules_requirements
    return [module]


def gather_requirements_files(modules, addons_path):
    req_files = []
    seen = set()
    for module in modules:
        dependencies = get_dependencies(module, addons_path)
        dependencies.append(module)
        for mod in dependencies:
            if mod in seen:
                continue
            seen.add(mod)
            req_path = os.path.join(addons_path, mod, 'requirements.txt')
            if os.path.exists(req_path):
                req_files.append(req_path)
    return req_files

def unify_and_install_requirements(modules, addons_path):
    import tempfile
    req_files = gather_requirements_files(modules, addons_path)
    raw_lines = []
    for path in req_files:
        with open(path, 'r') as f:
            raw_lines.extend(f.readlines())
    cleaned_lines = clean_requirements_lines(raw_lines)
    with tempfile.NamedTemporaryFile('w+', delete=False) as tmp_file:
        tmp_file.write('\n'.join(cleaned_lines))
        tmp_file.flush()
        pip_install_requirements(tmp_file.name, silent=False)
