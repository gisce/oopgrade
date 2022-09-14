# coding=utf-8
from __future__ import absolute_import
import click
from tqdm import tqdm
import psycopg2
import ConfigParser
from osconf import config_from_environment


@click.group()
@click.option('--config', required=False, default=None)
@click.pass_context
def oopgrade(ctx, config):
    ctx.obj = {}
    if config:
        conf = ConfigParser.ConfigParser()
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
    from oopgrade.oopgrade import get_installed_modules
    from oopgrade.utils import install_requirements
    conn = psycopg2.connect(
        dbname=conf['db_name'], user=conf['db_user'],
        password=conf['db_password'], host=conf['db_host']
    )
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
