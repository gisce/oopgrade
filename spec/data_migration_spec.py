# coding=utf-8
from expects import *
import six
if six.PY2:
    from mock import Mock, call
else:
    from unittest.mock import Mock, call

from oopgrade import DataMigration
from oopgrade.data import DataRecord
from oopgrade.oopgrade import add_columns
import os


_ROOT = os.path.abspath(os.path.dirname(__file__))


def get_fixture(*args):
    return os.path.join(_ROOT, *args)


with description('Migrating _data.xml'):
    with before.all:
        with open(get_fixture('fixtures/migration_data.xml'), 'rb') as f:
            self.xml = f.read()

    with it('must parse xml files with records'):
        cursor = Mock()
        cursor.fetchone.return_value = [435]
        dm = DataMigration(self.xml, cursor, 'module')
        expect(dm.records).to(have_len(0))
        dm.migrate()
        expect(dm.records).to(have_len(4))

    with context('a DataRecord class'):
        with before.all:
            cursor = Mock()
            cursor.fetchone.return_value = [435]
            self.r = DataRecord('id', 'model', 'noupdate', 'vals')
            self.dm = DataMigration(self.xml, cursor, 'module')
            self.dm.migrate()

        with it('must have a id, model and vals properties'):
            expect(self.r).to(have_properties('id', 'model', 'vals'))

        with it('must work without noupdate'):
            record = self.dm.records[0]
            expect(record.noupdate).to(equal(False))

        with it('must work without noupdate=1'):
            record = self.dm.records[2]
            expect(record.noupdate).to(equal(True))

        with it('must add fields to the records'):
            expect(self.dm.records[0].vals.keys()).to(contain('name', 'description'))

        with it('must to permit create a search_params with record fields'):
            search_params = {
                'test.search.model': ['code']
            }
            cursor = Mock()
            cursor.fetchone.return_value = [435]
            dm = DataMigration(self.xml, cursor, 'module', search_params)
            expect(dm.search_params).to(equal(search_params))

        with it('must work with eval attribute'):
            record = self.dm.records[1]
            expect(record.vals['flag']).to(equal(0))

        with context('working with the ref attribute'):

            with it('must work with other module ref attribute'):
                sql = self.dm.cursor.execute.call_args_list[2]
                expected_sql = call(
                    'SELECT "a"."res_id" FROM "ir_model_data" AS "a" '
                    'WHERE (("a"."module" = %s) AND ("a"."name" = %s))',
                    ('other_module', 'xml_id')
                )
                expect(sql).to(equal(expected_sql))

                record = self.dm.records[1]
                expect(record.vals['relation']).to(equal(435))

            with it('must work with internal refs'):
                sql = self.dm.cursor.execute.call_args_list[8]

                expected_sql = call(
                    'SELECT "a"."res_id" FROM "ir_model_data" AS "a" '
                    'WHERE (("a"."module" = %s) AND ("a"."name" = %s))',
                    ('module', 'record_id_0002')
                )
                expect(sql).to(equal(expected_sql))
                record = self.dm.records[3]
                expect(record.vals['test_model_id']).to(equal(435))

        with context('If reference does not exist'):
            with it('must raise a KeyError exception'):

                def callback():
                    xml = b"""<?xml version="1.0" encoding="UTF-8" ?>
<openerp>
    <data>
        <record id="record_id_0001" model="test.search.model">
            <field name="code">code</field>
            <field name="relation" ref="other_module.xml_id"/>
        </record>
    </data>
</openerp>
"""
                    cursor = Mock()
                    cursor.fetchone.return_value = []
                    dm = DataMigration(xml, cursor, 'module')
                    dm.migrate()

                expect(callback).to(raise_error(
                    KeyError,
                    'Reference: other_module.xml_id not found'
                ))

        with description('Working with search attribute'):
            with it('must work with search attribute'):
                cursor = Mock()
                cursor.fetchone.side_effect = (
                    [1],
                    [6],
                    [123],
                    [3],
                    [2],
                    [2],
                    [],
                    [4]
                )
                dm = DataMigration(self.xml, cursor, 'module')
                dm.migrate()
                record = dm.records[1]
                expect(record.vals['partner_id']).to(equal(123))

    with description('Migrating'):
        with it('must create the records into ir_model_data'):
            cursor = Mock()
            cursor.fetchone.side_effect = (
                [],  # No record record_id_0001
                [1],  # Creating record_id_0001
                [11],
                [123],
                [3],    # record_id_0003 found
                [2],    # record_id_0002 found
                [2],
                [],
                [4]
            )
            dm = DataMigration(self.xml, cursor, 'module', search_params={
                'test.search.model': ['code']
            })
            dm.migrate()
            expected_sql = [
                call(
                    'SELECT "a"."id" AS "id" FROM "test_model" AS "a" WHERE (("a"."name" = %s) AND ("a"."description" = %s))',
                    ('name', 'this is a description')
                ),
                call(
                    'INSERT INTO "test_model" ("name", "description") VALUES (%s, %s) RETURNING "test_model"."id"',
                    ('name', 'this is a description')
                ),
                call(
                    'INSERT INTO "ir_model_data" ("name", "model", "noupdate", "res_id", "module") VALUES (%s, %s, %s, %s, %s)',
                    ('record_id_0001', 'test.model', False, 1, 'module')
                ),
                call(
                    'SELECT "a"."res_id" FROM "ir_model_data" AS "a" WHERE (("a"."module" = %s) AND ("a"."name" = %s))',
                    ('other_module', 'xml_id')
                ),
                call('SELECT "a"."id" AS "id" FROM "res_partner" AS "a" WHERE (("a"."ref" = %s))', ('123',)),
                call(
                    'SELECT "a"."id" AS "id" FROM "test_search_model" AS "a" WHERE (("a"."code" = %s))', ('code',)
                ),
                call(
                    'INSERT INTO "ir_model_data" ("name", "model", "noupdate", "res_id", "module") VALUES (%s, %s, %s, %s, %s)',
                    ('record_id_0003', 'test.search.model', False, 3, 'module')
                ),
                call(
                    'SELECT "a"."id" AS "id" FROM "test_model" AS "a" WHERE (("a"."name" = %s) AND ("a"."description" = %s))',
                    ('name 2', 'this is a description 2')
                ),
                call(
                    'INSERT INTO "ir_model_data" ("name", "model", "noupdate", "res_id", "module") VALUES (%s, %s, %s, %s, %s)',
                    ('record_id_0002', 'test.model', True, 2, 'module')
                ),
                call(
                    'SELECT "a"."res_id" FROM "ir_model_data" AS "a" WHERE (("a"."module" = %s) AND ("a"."name" = %s))',
                    ('module', 'record_id_0002')
                ),
                call(
                    'SELECT "a"."id" AS "id" FROM "test_other_model" AS "a" WHERE (("a"."code" = %s) AND ("a"."test_model_id" = %s))',
                    ('1', 2)
                ),
                call(
                    'INSERT INTO "test_other_model" ("code", "test_model_id") VALUES (%s, %s) RETURNING "test_other_model"."id"',
                    ('1', 2)
                ),
                call(
                    'INSERT INTO "ir_model_data" ("name", "model", "noupdate", "res_id", "module") VALUES (%s, %s, %s, %s, %s)',
                    ('record_id_0004', 'test.other.model', False, 4, 'module')
                )
            ]
            expect(cursor.execute.call_args_list).to(contain_exactly(
                *expected_sql
            ))
    with description('Adding columns'):
        with it('using multiple at once'):
            cursor = Mock()
            cursor.fetchone.side_effect = [
                [0],  # No record for random1
                [0],  # No record for random2
            ]
            columns = {
                'test_model': [
                    ('random1', 'character varying(16)'),
                    ('random2', 'character varying(16)'),
                ]
            }
            add_columns(cursor, columns, multiple=True)
            expected_sql = [
                call(
                    "SELECT count(attname) FROM pg_attribute WHERE attrelid = (SELECT oid FROM pg_class WHERE relname = %s AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public') AND relkind = 'r') AND attname = %s", ('test_model', 'random1')
                ),
                call(
                    "SELECT count(attname) FROM pg_attribute WHERE attrelid = (SELECT oid FROM pg_class WHERE relname = %s AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public') AND relkind = 'r') AND attname = %s", ('test_model', 'random2')
                ),
                call(
                    'ALTER TABLE "test_model" ADD COLUMN "random1" character varying(16),\nADD COLUMN "random2" character varying(16)'
                ),
            ]
            expect(cursor.execute.call_args_list).to(contain_exactly(
                *expected_sql
            ))
    with description('Adding columns'):
        with it('usign column by column'):
            cursor = Mock()
            cursor.fetchone.side_effect = [
                [0],  # No record for random1
                [0],  # No record for random2
            ]
            columns = {
                'test_model': [
                    ('random1', 'character varying(16)'),
                    ('random2', 'character varying(16)'),
                ]
            }
            add_columns(cursor, columns, multiple=False)
            expected_sql = [
                call(
                    "SELECT count(attname) FROM pg_attribute WHERE attrelid = (SELECT oid FROM pg_class WHERE relname = %s AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public') AND relkind = 'r') AND attname = %s",
                    ('test_model', 'random1')),
                call(
                    'ALTER TABLE "test_model" ADD COLUMN "random1" character varying(16)'),
                call(
                    "SELECT count(attname) FROM pg_attribute WHERE attrelid = (SELECT oid FROM pg_class WHERE relname = %s AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public') AND relkind = 'r') AND attname = %s",
                    ('test_model', 'random2')),
                call(
                    'ALTER TABLE "test_model" ADD COLUMN "random2" character varying(16)'),

            ]
            expect(cursor.execute.call_args_list).to(contain_exactly(
                 *expected_sql
            ))

