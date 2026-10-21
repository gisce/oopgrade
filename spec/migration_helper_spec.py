# coding=utf-8
from expects import *
import six
if six.PY2:
    from mock import Mock, call
else:
    from unittest.mock import Mock, call

from oopgrade.oopgrade import MigrationHelper


with description('MigrationHelper'):
    with context('updating module translations'):
        with before.each:
            self.cursor = Mock()
            self.module_o = Mock()
            self.model_pool = Mock()
            self.model_pool.get.return_value = self.module_o
            self.helper = MigrationHelper(self.cursor, 'test_module')
            self.helper._create_pool = Mock()
            self.helper.pool = self.model_pool

        with it('updates the translations and remains chainable'):
            self.module_o.search.return_value = [42]

            result = self.helper.update_translations()

            expect(result).to(be(self.helper))
            expect(self.model_pool.get.call_args_list).to(equal([
                call('ir.module.module')
            ]))
            expect(self.module_o.search.call_args_list).to(equal([
                call(self.cursor, 1, [('name', '=', 'test_module')])
            ]))
            expect(self.module_o.update_translations.call_args_list).to(equal([
                call(self.cursor, 1, [42])
            ]))

        with it('uses the provided user ID'):
            self.module_o.search.return_value = [42]

            self.helper.update_translations(uid=7)

            expect(self.module_o.search.call_args_list).to(equal([
                call(self.cursor, 7, [('name', '=', 'test_module')])
            ]))
            expect(self.module_o.update_translations.call_args_list).to(equal([
                call(self.cursor, 7, [42])
            ]))

        with it('does nothing when the module is not found'):
            self.module_o.search.return_value = []

            result = self.helper.update_translations()

            expect(result).to(be(self.helper))
            expect(self.module_o.update_translations.called).to(be_false)
