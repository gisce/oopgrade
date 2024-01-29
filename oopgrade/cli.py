# coding=utf-8
from __future__ import absolute_import
from __future__ import print_function
import six
from future import standard_library
standard_library.install_aliases()
import click
from tqdm import tqdm
import psycopg2
if six.PY2:
    import ConfigParser as configparser
else:
    import configparser
from osconf import config_from_environment


class JSONParamType(click.ParamType):
    name = "json"

    def convert(self, value, param, ctx):
        import json
        try:
            return json.loads(value)
        except ValueError:
            self.fail("{0} is not a valid json".format(value), param, ctx)


@click.group()
@click.option('--config', required=False, default=None)
@click.pass_context
def oopgrade(ctx, config):
    ctx.obj = {}
    if config:
        conf = configparser.ConfigParser()
        conf.read(config)
        ctx.obj = dict(conf.items('options'))
    envconf = config_from_environment('OPENERP')
    ctx.obj.update(envconf)


@oopgrade.group()
def requirements():
    pass


@requirements.command()
@click.pass_obj
def install(conf):
    import os.path
    from oopgrade.oopgrade import get_installed_modules
    from oopgrade.utils import install_requirements, pip_install_requirements
    conn = psycopg2.connect(
        dbname=conf['db_name'], user=conf['db_user'],
        password=conf['db_password'], host=conf['db_host']
    )
    main_req = os.path.join(conf['root_path'], '..', 'requirements.txt')
    if os.path.exists(main_req):
        click.echo('Installing main requirements')
        pip_install_requirements(main_req, silent=True)
    click.echo('Getting installed modules...')
    with conn:
        with conn.cursor() as cursor:
            modules = get_installed_modules(cursor)
    conn.close()
    done = []
    for module in tqdm(modules, desc='Installing'):
        if module in done:
            continue
        done += install_requirements(
            module, conf['addons_path'], silent=True, done=done
        )


@oopgrade.command()
@click.option('--channel')
@click.argument('method')
@click.option('--kwargs', type=JSONParamType())
@click.option('--n-retries', default=0, type=click.INT, help='Will retry method n times')
@click.option(
    '--on-max-retries-method', type=click.STRING, help='If fails n times tou can provide alternative method'
)
@click.option('--on-max-retries-kwargs', type=JSONParamType(), help='Arguments for alternative method')
@click.pass_obj
def pubsub(ctx, channel, method, kwargs, n_retries, on_max_retries_method, on_max_retries_kwargs):
    import json
    from oopgrade.pubsub import send_msg
    secret = ctx.get('secret')
    if not secret:
        raise ValueError('Secret (key: secret) not found in config')
    redis_url = ctx.get('redis_url')
    if not redis_url:
        raise ValueError('Redis URL (key: redis_url) not found in config')
    db_name = ctx.get('db_name')
    if not db_name:
        raise ValueError('Databse (key: db_name) not found in config')
    channel = '{}.{}'.format(db_name, channel)
    msg = {
        'method': method,
        'kwargs': kwargs or {},
        'n_retries': n_retries or 0,
        'on_max_retries_method': on_max_retries_method or False,
        'on_max_retries_kwargs': on_max_retries_kwargs or {},
    }
    msg = json.dumps(msg)
    sent_to = send_msg(redis_url, secret, channel, msg)
    print('-> Message sent to {} nodes'.format(sent_to))
