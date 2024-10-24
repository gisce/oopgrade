from expects import *
import six
if six.PY2:
    from mock import Mock, call
else:
    from unittest.mock import Mock, call

from my_module import backup_table, restore_table, add_index, drop_index, check_data_integrity, migrate_data_between_tables

with description('Database Utilities'):
    with description('Backing up and restoring tables'):
        with it('should create a backup of a table'):
            cursor = Mock()
            backup_table(cursor, 'test_table')
            expected_sql = [
                call("CREATE TABLE test_table_backup AS TABLE test_table"),
            ]
            expect(cursor.execute.call_args_list).to(contain_exactly(*expected_sql))

        with it('should restore a table from its backup'):
            cursor = Mock()
            restore_table(cursor, 'test_table')
            expected_sql = [
                call("DROP TABLE IF EXISTS test_table"),
                call("ALTER TABLE test_table_backup RENAME TO test_table"),
            ]
            expect(cursor.execute.call_args_list).to(contain_exactly(*expected_sql))

    with description('Adding and dropping indexes'):
        with it('should add a unique index on multiple columns'):
            cursor = Mock()
            add_index(cursor, 'test_table', ['column1', 'column2'], unique=True)
            expected_sql = [
                call("CREATE UNIQUE INDEX test_table_column1_column2_idx ON test_table (column1, column2)"),
            ]
            expect(cursor.execute.call_args_list).to(contain_exactly(*expected_sql))

        with it('should add a non-unique index on a single column'):
            cursor = Mock()
            add_index(cursor, 'test_table', ['column1'], unique=False)
            expected_sql = [
                call("CREATE INDEX test_table_column1_idx ON test_table (column1)"),
            ]
            expect(cursor.execute.call_args_list).to(contain_exactly(*expected_sql))

        with it('should drop an existing index'):
            cursor = Mock()
            drop_index(cursor, 'test_index')
            expected_sql = [
                call("DROP INDEX IF EXISTS test_index"),
            ]
            expect(cursor.execute.call_args_list).to(contain_exactly(*expected_sql))

    with description('Checking data integrity'):
        with it('should detect null values in non-nullable columns'):
            cursor = Mock()
            cursor.fetchone.side_effect = [
                ['column1'],  # Non-nullable columns
                [5],  # Null values found
            ]
            result = check_data_integrity(cursor, 'test_table')
            expect(result).to(be_false)
            expected_sql = [
                call("SELECT column_name FROM information_schema.columns WHERE table_name = %s AND is_nullable = 'NO'", ('test_table',)),
                call("SELECT COUNT(*) FROM test_table WHERE column1 IS NULL"),
            ]
            expect(cursor.execute.call_args_list).to(contain_exactly(*expected_sql))

        with it('should detect foreign key violations'):
            cursor = Mock()
            cursor.fetchone.side_effect = [
                [],  # No null violations
                ['fk_column', 'test_table', 'ref_table', 'ref_column'],  # Foreign key constraint
                [3],  # Foreign key violations found
            ]
            result = check_data_integrity(cursor, 'test_table')
            expect(result).to(be_false)
            expected_sql = [
                call("SELECT column_name FROM information_schema.columns WHERE table_name = %s AND is_nullable = 'NO'", ('test_table',)),
                call("SELECT tc.constraint_name, kcu.column_name, ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name FROM information_schema.table_constraints AS tc JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name WHERE constraint_type = 'FOREIGN KEY' AND tc.table_name = %s", ('test_table',)),
                call("SELECT COUNT(*) FROM test_table t1 LEFT JOIN ref_table t2 ON t1.fk_column = t2.ref_column WHERE t2.ref_column IS NULL"),
            ]
            expect(cursor.execute.call_args_list).to(contain_exactly(*expected_sql))

        with it('should pass when there are no integrity issues'):
            cursor = Mock()
            cursor.fetchone.side_effect = [
                [],  # No null violations
                [],  # No foreign key constraints
            ]
            result = check_data_integrity(cursor, 'test_table')
            expect(result).to(be_true)

    with description('Migrating data between tables'):
        with it('should migrate data from one table to another'):
            cursor = Mock()
            column_mapping = {'source_col1': 'dest_col1', 'source_col2': 'dest_col2'}
            migrate_data_between_tables(cursor, 'source_table', 'dest_table', column_mapping)
            expected_sql = [
                call("INSERT INTO dest_table (dest_col1, dest_col2) SELECT source_col1, source_col2 FROM source_table"),
            ]
            expect(cursor.execute.call_args_list).to(contain_exactly(*expected_sql))
