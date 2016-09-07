# coding=utf-8
from spec.fixtures import get_fixture
from expects import *
from mock import Mock, call

from oopgrade import DataMigration
from oopgrade.data import DataRecord



with description('Migrating _data.xml'):
    with before.all:
        with open(get_fixture('migration_data.xml'), 'r') as f:
            self.xml = f.read()

    with it('must parse xml files with records'):
        cursor = Mock()
        cursor.fetchone.return_value = [435]
        dm = DataMigration(self.xml, cursor, 'module')
        expect(dm.records).to(have_len(3))

    with context('a DataRecord class'):
        with before.all:
            cursor = Mock()
            cursor.fetchone.return_value = [435]
            self.r = DataRecord('id', 'model', 'noupdate', 'vals')
            self.dm = DataMigration(self.xml, cursor, 'module')

        with it('must have a id, model and vals properties'):
            expect(self.r).to(have_properties('id', 'model', 'vals'))

        with it('must work without noupdate'):
            record = self.dm.records[0]
            expect(record.noupdate).to(equal(0))

        with it('must work without noupdate=1'):
            record = self.dm.records[2]
            expect(record.noupdate).to(equal(1))

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

        with it('must work with ref attribute'):
            sql = self.dm.cursor.execute.call_args_list[0]
            expected_sql = call(
                'SELECT "a"."res_id" FROM "ir_model_data" AS "a" '
                'WHERE (("a"."module" = %s) AND ("a"."name" = %s))',
                ('other_module', 'xml_id')
            )
            expect(sql).to(equal(expected_sql))

            record = self.dm.records[1]
            expect(record.vals['relation']).to(equal(435))
        with context('If reference does not exist'):
            with it('must raise a KeyError exception'):

                def callback():
                    cursor = Mock()
                    cursor.fetchone.return_value = []
                    DataMigration(self.xml, cursor, 'module')

                expect(callback).to(raise_error(
                    KeyError,
                    'Reference: other_module.xml_id not found'
                ))

        with description('Working with search attribute'):
            with it('must work with search attribute'):
                cursor = Mock()
                cursor.fetchone.side_effect = ([435], [3])
                dm = DataMigration(self.xml, cursor, 'module')
                record = dm.records[1]
                expect(record.vals['partner_id']).to(equal(3))

    with description('Migrating'):
        with it('must create the records into ir_model_data'):
            cursor = Mock()
            cursor.fetchone.side_effect = (
                [5],    # other module
                [123],  # Search partner with referece
                [],     # No record record_id_0001
                [1],    # Creating record_id_0001
                [3],    # record_id_0003 found
                [2],    # record_id_0002 found
            )
            dm = DataMigration(self.xml, cursor, 'module', search_params={
                'test.search.model': ['code']
            })
            dm.migrate()
            expect(cursor.execute.call_args_list).to(contain_exactly(
                call('SELECT "a"."res_id" FROM "ir_model_data" AS "a" WHERE (("a"."module" = %s) AND ("a"."name" = %s))', ('other_module', 'xml_id')),
                call('SELECT "a"."id" FROM "res_partner" AS "a" WHERE (("a"."ref" = %s))', ('123',)),
                call('SELECT "a"."id" FROM "test_model" AS "a" WHERE (("a"."name" = %s) AND ("a"."description" = %s))', ('name', 'this is a description')),
                call('INSERT INTO "test_model" ("name", "description") VALUES (%s, %s) RETURNING "id"', ('name', 'this is a description')),
                call('INSERT INTO "ir_model_data" ("name", "model", "noupdate", "res_id", "module") VALUES (%s, %s, %s, %s, %s)', ('record_id_0001', 'test.model', 0, 1, 'module')),
                call('SELECT "a"."id" FROM "test_search_model" AS "a" WHERE (("a"."code" = %s))', ('code',)),
                call('INSERT INTO "ir_model_data" ("name", "model", "noupdate", "res_id", "module") VALUES (%s, %s, %s, %s, %s)', ('record_id_0003', 'test.search.model', 0, 3, 'module')),
                call('SELECT "a"."id" FROM "test_model" AS "a" WHERE (("a"."name" = %s) AND ("a"."description" = %s))', ('name 2', 'this is a description 2')),
                call('INSERT INTO "ir_model_data" ("name", "model", "noupdate", "res_id", "module") VALUES (%s, %s, %s, %s, %s)', ('record_id_0002', 'test.model', 1, 2, 'module'))
            ))


