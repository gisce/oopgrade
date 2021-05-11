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


def install_requirements(module, addons_path, silent=False, done=None):
    """Install module requirements and its dependecies
    """
    if done is None:
        done = []
    subprocess_kwargs = {}
    if silent:
        FNULL = open(os.devnull, 'w')
        subprocess_kwargs = {
            'stderr': FNULL,
            'stdout': FNULL
        }
    pip = os.path.join(sys.prefix, 'bin', 'pip')
    if os.path.exists(pip):
        modules_requirements = get_dependencies(module, addons_path)
        modules_requirements.append(module)
        for module_requirements in modules_requirements:
            if module_requirements in done:
                continue
            addons_path_module = os.path.join(addons_path, module_requirements)
            req = os.path.join(addons_path_module, 'requirements.txt')
            if os.path.exists(req):
                logger.info('Requirements file %s found. Installing...', req)
                subprocess.check_call([pip, "install", "-r", req], **subprocess_kwargs)
        return modules_requirements
    return [module]
