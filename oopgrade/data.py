# coding=utf-8
from __future__ import absolute_import

from collections import namedtuple
from ast import literal_eval

from lxml import objectify
from oopgrade.oopgrade import get_foreign_keys, logger
from ooquery import OOQuery
from sql import Table


DataRecord = namedtuple('DataRecord', ['id', 'model', 'noupdate', 'vals'])


class DataMigration(object):
    """Data Migration class
    """
    def __init__(self, content, cursor, module, search_params=None):
        self.content = content
        self.cursor = cursor
        self.module = module
        if search_params is None:
            search_params = {}
        self.search_params = search_params.copy()
        self.records = []
        obj = objectify.fromstring(self.content)
        for record in obj.iter(tag='record'):
            self.records.append(self._record(record))

    def _record(self, record):
        vals = {}
        noupdate = int(record.getparent().attrib.get('noupdate', '0'))
        for field in record.iter(tag='field'):
            key = field.attrib['name']
            attrs = field.attrib
            if attrs.get('eval'):
                value = literal_eval(attrs['eval'])
            elif attrs.get('ref'):
                value = self._ref(attrs['ref'])
            elif attrs.get('search') and attrs.get('model'):
                value = self._search(attrs['model'], attrs['search'])
            else:
                value = field.text
            vals[key] = value
        return DataRecord(
            record.attrib['id'], record.attrib['model'], noupdate, vals
        )

    def _ref(self, ref):
        if '.' in ref:
            module, xml_id = ref.split('.')
        else:
            xml_id = ref
            module = self.module

        t = Table('ir_model_data')
        select = t.select(t.res_id)
        select.where = (t.module == module) & (t.name == xml_id)

        self.cursor.execute(*select)
        res = self.cursor.fetchone()
        if not res:
            raise KeyError('Reference: {}.{} not found'.format(
                module, xml_id
            ))
        return res[0]

    def _search(self, model, search):
        table = model.replace('.', '_')
        search_params = literal_eval(search)
        q = OOQuery(table, lambda t: get_foreign_keys(self.cursor, t))
        sql = q.select(['id']).where(search_params)
        self.cursor.execute(*sql)
        return self.cursor.fetchone()[0]

    def migrate(self):
        t = Table('ir_model_data')
        for record in self.records:
            res_id = None
            sp = []
            for field in self.search_params.get(record.model, record.vals.keys()):
                sp.append((field, '=', record.vals[field]))
            logger.info('Trying to find existing record with query: {}'.format(
                sp
            ))
            table = record.model.replace('.', '_')
            q = OOQuery(table)
            sql = q.select(['id']).where(sp)
            logger.debug(tuple(sql))
            self.cursor.execute(*sql)
            res_id = self.cursor.fetchone()
            if res_id:
                res_id = res_id[0]
                logger.info('Record {}.{} found! ({} id:{})'.format(
                    self.module, record.id, record.model, res_id
                ))
            else:
                logger.info('Record {}.{} not found!'.format(
                    self.module, record.id
                ))
                # We have to create the model
                table_model = Table(record.model.replace('.', '_'))
                columns = []
                values = []
                for col, value in record.vals.items():
                    columns.append(getattr(table_model, col))
                    values.append(value)

                sql = table_model.insert(
                    columns=columns, values=[values], returning=[table_model.id]
                )
                logger.debug(tuple(sql))
                self.cursor.execute(*sql)
                res_id = self.cursor.fetchone()[0]
                logger.info('Creating record {}.{} ({} id:{})'.format(
                    self.module, record.id, record.model, res_id
                ))

            sql = t.insert(
                columns=[t.name, t.model, t.noupdate, t.res_id, t.module],
                values=[(record.id, record.model, record.noupdate, res_id,
                         self.module)]
            )
            logger.debug(tuple(sql))
            logger.info('Linking model data {}.{} -> record {} id:{}'.format(
                self.module, record.id, record.model, res_id
            ))
            self.cursor.execute(*sql)
