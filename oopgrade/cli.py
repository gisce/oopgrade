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


@oopgrade.command()
@click.option('--channel')
@click.argument('msg')
@click.pass_obj
def pubsub(ctx, channel, msg):
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
    sent_to = send_msg(redis_url, secret, channel, msg)
    print('-> Message sent to {} nodes'.format(sent_to))
