# coding=utf-8
from __future__ import absolute_import
from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
import click
from tqdm import tqdm
import psycopg2
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
    import tempfile
    from oopgrade.utils import pip_install_requirements, ProgressBarContext
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
    total_requirements = ''
    for module in tqdm(modules, desc='Merging requirements'):
        req_path = os.path.join(conf['addons_path'], module, 'requirements.txt')
        if os.path.exists(req_path):
            with open(req_path) as f:
                total_requirements += f.read()
    if total_requirements:
        with tempfile.NamedTemporaryFile(mode='w', delete=True) as f:
            f.write(total_requirements)
            f.flush()
            with ProgressBarContext(label='Installing...'):
                pip_install_requirements(f.name, silent=True)


@oopgrade.command()
@click.option('--channel')
@click.argument('method')
@click.option('--kwargs', type=JSONParamType())
@click.pass_obj
def pubsub(ctx, channel, method, kwargs):
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
    msg = json.dumps({
        'method': method,
        'kwargs': kwargs or {}
    })
    sent_to = send_msg(redis_url, secret, channel, msg)
    print('-> Message sent to {} nodes'.format(sent_to))
