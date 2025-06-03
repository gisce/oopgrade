# -*- coding: utf-8 -*-
import six
if six.PY3:
    from builtins import str
    from builtins import range
import os
import logging

logger = logging.getLogger('openerp.oopgrade')

MODULE_INSTALLED_STATES = ['installed', 'to upgrade', 'to remove']

__all__ = [
    'load_data',
    'load_data_records',
    'rename_columns',
    'rename_tables',
    'drop_columns',
    'table_exists',
    'column_exists',
    'change_column_type',
    'delete_model_workflow',
    'set_defaults',
    'set_stored_function',
    'update_module_names',
    'add_ir_model_fields',
    'install_modules',
    'get_foreign_keys',
    'get_installed_modules',
    'module_is_installed',
    'load_access_rules_from_model_name',
    'delete_record',
    'load_translation',
    'MigrationHelper',
]


def delete_record(cursor, module_name, record_names):
    import pooler
    uid = 1
    pool = pooler.get_pool(cursor.dbname)
    for record_name in record_names:
        # Find by model = ir.ui.view, module = module & name = the view_id
        logger.info(" {}: Deleting record: {}".format(module_name, record_name))
        sql_model = """
            SELECT id, model, res_id
            FROM ir_model_data WHERE
            module = %(module_name)s
            AND name = %(record_name)s
        """
        params_model = {
            'module_name': module_name,
            'record_name': record_name
        }
        cursor.execute(sql_model, params_model)
        model_data_vs = cursor.dictfetchall()
        # It should have only one.
        if model_data_vs and len(model_data_vs) == 1:
            model_data_vs = model_data_vs[0]
            if model_data_vs['model'] == 'ir.ui.view':
                # Delete all shortcuts that use this view
                sql_sc_search = """
                    SELECT id
                    FROM ir_ui_view_sc
                    WHERE view_id = %(sc_view_id)s
                """
                params_sc_id = {
                    'sc_view_id': model_data_vs['res_id']
                }
                cursor.execute(sql_sc_search, params_sc_id)
                view_id_to_delete = cursor.dictfetchall()
                if view_id_to_delete:
                    view_id_to_delete = view_id_to_delete[0]
                    sql_sc_del = """
                        DELETE FROM ir_ui_view_sc WHERE id = %(sc_view_id)s
                    """
                    params_sc_del = {
                        'sc_view_id': view_id_to_delete['id']
                    }
                    cursor.execute(sql_sc_del, params_sc_del)
            # Delete from model data.
            sql_model_del = """
                DELETE FROM ir_model_data WHERE id = %(model_data_id)s
            """
            params_model_del = {
                'model_data_id': model_data_vs['id']
            }
            cursor.execute(sql_model_del, params_model_del)

            model_o = pool.get(model_data_vs['model'])
            model_o.unlink(cursor, uid, [model_data_vs['res_id']])
        elif model_data_vs and len(model_data_vs) > 1:
            raise Exception(
                "More than one record found for model %s" % (model_data_vs['model'])
            )


def load_data(cr, module_name, filename, idref=None, mode='update'):
    """
    Load an xml or csv data file from your post script. The usual case for this is the
    occurrence of newly added essential or useful data in the module that is
    marked with "noupdate='1'" and without "forcecreate='1'" so that it will
    not be loaded by the usual upgrade mechanism. Leaving the 'mode' argument to
    its default 'init' will load the data from your migration script.
    
    Theoretically, you could simply load a stock file from the module, but be 
    careful not to reinitialize any data that could have been customized.
    Preferably, select only the newly added items. Copy these to a file
    in your migrations directory and load that file.
    Leave it to the user to actually delete existing resources that are
    marked with 'noupdate' (other named items will be deleted
    automatically).


    :param module_name: the name of the module
    :param filename: the path to the filename, relative to the module \
    directory.
    :param idref: optional hash with ?id mapping cache?
    :param mode: one of 'init', 'update', 'demo'. Always use 'init' for adding new items \
    from files that are marked with 'noupdate'. Defaults to 'init'.

    """
    import tools

    if idref is None:
        idref = {}
    logger.info('%s: loading %s' % (module_name, filename))
    _, ext = os.path.splitext(filename)
    pathname = os.path.join(module_name, filename)
    fp = tools.file_open(pathname)
    try:
        if ext == '.csv':
            noupdate = True
            tools.convert_csv_import(cr, module_name, pathname, fp.read(), idref, mode, noupdate)
        else:
            tools.convert_xml_import(cr, module_name, fp, idref, mode=mode)
    finally:
        fp.close()


def load_data_records(cr, module_name, filename, record_ids, mode='update', multi=False):
    """
    :param module_name: the name of the module
    :param filename: the path to the filename, relative to the module \
    directory.
    :param record_ids: List of records to process
    :param mode: one of 'init', 'update', 'demo'. Always use 'init' for adding new items \
    from files that are marked with 'noupdate'. Defaults to 'update'.
    :param multi: If false, it will only find the first occurence of the record_id passed. Otherwise, it will find all
    """
    from lxml import etree
    from tools import config, xml_import

    xml_path = '{}/{}/{}'.format(config['addons_path'], module_name, filename)
    if not os.path.exists(xml_path):
        raise Exception('Data {} not found'.format(xml_path))
    if not record_ids:
        raise Exception("Maybe you want to run 'load_data' because you don't pass any record id")
    xml_to_import = xml_import(cr, module_name, {}, mode, noupdate=False)
    doc = etree.parse(xml_path)
    logger.info('{}: loading file {}'.format(module_name, filename))
    for record_id in record_ids:
        logger.info("{}: Loading record id: {}".format(module_name, record_id))
        if not multi:
            rec = doc.findall("//*[@id='{}']".format(record_id))[0]
            data = doc.findall("//*[@id='{}']/..".format(record_id))[0]
            xml_to_import._tags[rec.tag](cr, rec, data)
        else:
            recs = doc.findall("//*[@id='{}']".format(record_id))
            datas = doc.findall("//*[@id='{}']/..".format(record_id))
            for rec, data in zip(recs, datas):
                xml_to_import._tags[rec.tag](cr, rec, data)

def load_access_rules_from_model_name(cr, module_name, model_ids, filename='security/ir.model.access.csv', mode='init'):
    # Example: load_access_rules_from_model_name(cursor, 'base', ['model_ir_auto_vacuum'], mode='init')
    import tools
    if not isinstance(model_ids, (tuple, list)):
        model_ids = [model_ids]

    logger.info('%s: loading %s %s' % (module_name, filename, model_ids))
    _, ext = os.path.splitext(filename)
    pathname = os.path.join(module_name, filename)
    fp = tools.file_open(pathname)
    file_lines = fp.readlines()
    clean_str = lambda _s: _s.replace('\n', '').replace('\t', '').replace('\r', '')
    header = clean_str(file_lines.pop(0))
    header_len = len(header.split(','))
    rules_lines = [header]
    for _f_line in file_lines:
        clean_line = clean_str(_f_line)
        split_line = clean_line.split(',')
        if len(split_line) == header_len and split_line[2].replace('"', "") in model_ids:
            rules_lines.append(clean_line)
    data_lines = '\n'.join(rules_lines)
    fp.close()
    # check
    for _model in model_ids:
        if '"{}"'.format(_model) not in data_lines:
            raise Exception('{} not found in {}'.format(_model, pathname))
    tools.convert_csv_import(cr, module_name, filename, data_lines, mode=mode)


def table_exists(cr, table):
    """ Check whether a certain table or view exists """
    cr.execute(
        'SELECT count(relname) FROM pg_class WHERE relname = %s',
        (table,))
    return cr.fetchone()[0] == 1


def rename_columns(cr, column_spec):
    """
    Rename table columns. Typically called in the pre script.

    :param column_spec: a hash with table keys, with lists of tuples as values. \
    Tuples consist of (old_name, new_name).

    """
    for table in list(column_spec.keys()):
        for (old, new) in column_spec[table]:
            logger.info("table %s, column %s: renaming to %s",
                        table, old, new)
            cr.execute('ALTER TABLE "%s" RENAME "%s" TO "%s"' % (table, old, new,))


def rename_tables(cr, table_spec):
    """
    Rename tables. Typically called in the pre script.
    :param column_spec: a list of tuples (old table name, new table name).

    """
    for (old, new) in table_spec:
        logger.info("table %s: renaming to %s",
                    old, new)
        cr.execute('ALTER TABLE "%s" RENAME TO "%s"' % (old, new,))


def rename_models(cr, model_spec):
    """
    Rename models. Typically called in the pre script.
    :param column_spec: a list of tuples (old table name, new table name).
    
    Use case: if a model changes name, but still implements equivalent
    functionality you will want to update references in for instance
    relation fields.

    """
    for (old, new) in model_spec:
        logger.info("model %s: renaming to %s",
                    old, new)
        cr.execute('UPDATE ir_model_fields SET relation = %s '
                   'WHERE relation = %s', (new, old,))


def drop_columns(cr, column_spec):
    """
    Drop columns but perform an additional check if a column exists.
    This covers the case of function fields that may or may not be stored.
    Consider that this may not be obvious: an additional module can govern
    a function fields' store properties.

    :param column_spec: a list of (table, column) tuples
    """
    for (table, column) in column_spec:
        logger.info("table %s: drop column %s",
                    table, column)
        if column_exists(cr, table, column):
            cr.execute('ALTER TABLE "%s" DROP COLUMN "%s"' %
                       (table, column))
        else:
            logger.warn("table %s: column %s did not exist",
                        table, column)


def add_columns(cr, column_spec, multiple=True):
    """
    Add columns

    :param cr: Database cursor
    :param column_spec: a hash with table keys, with lists of tuples as values.
        Tuples consist of (column name, type).
    :param multiple: Choose to create all columns at the same DDL sentence
    """
    for table in column_spec:
        columns_spec = []
        for (column, type_) in column_spec[table]:
            logger.info("table %s: add column %s",
                        table, column)
            if column_exists(cr, table, column):
                logger.warning("table %s: column %s already exists",
                            table, column)
            else:
                if multiple:
                    columns_spec.append(
                        'ADD COLUMN "{column}" {col_type}'.format(
                            column=column, col_type=type_
                        )
                    )
                else:
                    cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' %
                               (table, column, type_))
        if multiple and columns_spec:
            columns_ddl = ',\n'.join(columns_spec)
            sentence_sql = 'ALTER TABLE "{table}" {columns_ddl}'.format(
                        table=table, columns_ddl=columns_ddl
                )
            logger.info(sentence_sql)
            cr.execute(sentence_sql)



def add_columns_fk(cr, column_spec):
    """
    Add columns with foreign key constraint

    :param cr: Database cursor
    :param column_spec: a hash with table keys, with lists of tuples as values.
        Tuples consist of (column name, type, foreing table name, foreing key column, on delete action).
    """
    for table in column_spec:
        for (column, type_, fk_table_name, fk_col, on_delete_act) in column_spec[table]:
            add_columns(cr, {table: [(column, type_)]})
            constraint = table + '_' + column + '_fkey'
            if not on_delete_act:
                on_delete_act = 'restrict'
            logger.info("table %s: add constraint %s",
                        table, constraint)
            cr.execute('ALTER TABLE "%s" ADD CONSTRAINT "%s" FOREIGN KEY (%s) REFERENCES %s(%s) \
                        ON DELETE %s' %
                       (table, constraint, column, fk_table_name, fk_col, on_delete_act))


def set_stored_function(cr, obj, fields):
    """
    Init newly created stored functions calling the function and storing them
    to the database.

    ..note:: Use in the post stage

    :param cr: Database cursor
    :param obj: Object
    :param fields: list of fields
    """
    from datetime import datetime

    for k in fields:
        logger.info("storing computed values of fields.function '%s'" % (k,))
        field = obj._columns[k]
        ss = field._symbol_set
        update_query = 'UPDATE "%s" SET "%s"=%s WHERE id=%%s' % (
            obj._table, k, ss[0])
        cr.execute('select id from ' + obj._table)
        ids_lst = [x[0] for x in cr.fetchall()]
        logger.info("storing computed values for %s objects" % len(ids_lst))
        start = datetime.now()

        def chunks(l, n):
            """Yield successive n-sized chunks from l."""
            for i in range(0, len(l), n):
                yield l[i:i + n]

        for ids in chunks(ids_lst, 100):
            res = field.get(cr, obj, ids, k, 1, {})
            for key, val in list(res.items()):
                if field._multi:
                    val = val[k]
                # if val is a many2one, just write the ID
                if type(val) == tuple:
                    val = val[0]
                if (val is not False) or (type(val) != bool):
                    cr.execute(update_query, (ss[1](val), key))
        logger.info("stored in {0}".format(datetime.now() - start))


def delete_model_workflow(cr, model):
    """ 
    Forcefully remove active workflows for obsolete models,
    to prevent foreign key issues when the orm deletes the model.
    """
    logged_query(
        cr,
        "DELETE FROM wkf_workitem WHERE act_id in "
        "( SELECT wkf_activity.id "
        "  FROM wkf_activity, wkf "
        "  WHERE wkf_id = wkf.id AND "
        "  wkf.osv = %s"
        ")", (model,))
    logged_query(
        cr,
        "DELETE FROM wkf WHERE osv = %s", (model,))


def remove_model(cursor, models):
    """
    Removes a list of models and all of its remaining
    elements like menu, values, actions, views, etc.

    :param cursor: Database cursor
    :param models: list of model names
           I.E. ['res.partner.foo', 'res.partner.staff']
    """
    import pooler

    pool = pooler.get_pool(cursor.dbname)
    for model in models:
        model_id = pool.get('ir.model').search(cursor, 1, [('model', '=', model)])

        if len(model_id):
            model_id = model_id[0]
        else:
            raise Exception("Migration: error wizard model {} not found. "
                            "It can't be removed.".format(model))

        # Menus
        act_list = tuple()
        cursor.execute(
            "SELECT id FROM ir_act_window WHERE res_model = '{}'".format(model)
        )
        action_records = cursor.fetchall()
        for act_record in action_records:
            act_list += (
                'ir.actions.act_window,{}'.format(act_record[0]),
                'ir.actions.act_window, {}'.format(act_record[0]),
            )
        if act_list:
            cursor.execute(
                "DELETE from ir_ui_menu WHERE id in ("
                "select res_id from ir_values where model = 'ir.ui.menu' and value in {})".format(str(act_list)))

            # Values
            cursor.execute(
                "DELETE FROM ir_values WHERE value in {}".format(str(act_list))
            )

        # Shortcuts
        cursor.execute("select id from ir_ui_view where model = '{}'".format(model))
        data_records = cursor.fetchall()
        record_ids = [record[0] for record in data_records]
        if record_ids:
            cursor.execute("DELETE from ir_ui_view_sc where view_id in "
                           "(select id from ir_ui_view where model = '{}')".format(model))

        # Actions
        cursor.execute("select id from ir_act_window where res_model = '{}'".format(model))
        data_records = cursor.fetchall()
        record_ids = [record[0] for record in data_records]
        if record_ids:
            cursor.execute(
                "DELETE from ir_model_data where model = 'ir.actions.act_window' and res_id in "
                "(select id from ir_act_window where res_model = '{}')".format(model))
        cursor.execute("DELETE from ir_act_window where res_model = '{}'".format(model))

        # Views
        cursor.execute("select id from ir_ui_view where model = '{}'".format(model))
        data_records = cursor.fetchall()
        record_ids = [record[0] for record in data_records]
        if record_ids:
            cursor.execute(
                "DELETE from ir_model_data where model = 'ir.ui.view' and res_id in "
                "(select id from ir_ui_view where model = '{}')".format(model))
        cursor.execute("DELETE from ir_ui_view where model = '{}'".format(model))

        # Access rules
        cursor.execute("select id from ir_model_access where model_id = '{}'".format(model_id))
        data_records = cursor.fetchall()
        record_ids = [record[0] for record in data_records]
        if record_ids:
            cursor.execute(
                "DELETE from ir_model_data where model = 'ir.model.access' and res_id in "
                "(select id from ir_model_access where model_id = '{}')".format(model_id))
        cursor.execute("DELETE from ir_model_access where model_id = {}".format(model_id))

        # Model
        cursor.execute("DELETE from ir_model_data where model = 'ir.model' and res_id = {}".format(model_id))
        cursor.execute("DELETE from ir_model where id = {}".format(model_id))

        # Fields
        cursor.execute("select id from ir_model_fields where model_id = '{}'".format(model_id))
        data_records = cursor.fetchall()
        record_ids = [record[0] for record in data_records]
        if record_ids:
            cursor.execute(
                "DELETE from ir_model_data where model = 'ir.model.fields' and res_id in "
                "(select id from ir_model_fields where model_id = '{}')".format(model_id))


# Alias for backward compatibility: remove_wizard = remove_model
remove_wizard = remove_model


def clean_old_wizard(cr, old_wizard_name, module):
    """
    :param cr:
    :param old_wizard_name:
    :param module:
    """

    # Buscar per name = old_wizard
    sql_wizard = """
        SELECT id 
        FROM ir_act_wizard
        WHERE wiz_name = %(old_wiz_name)s
    """
    params_wizard = {
        'old_wiz_name': old_wizard_name
    }
    cr.execute(sql_wizard, params_wizard)
    wiz_ids = cr.fetchall()

    # Buscar per model = ir.actions.wizard i per module = module
    # i res_id = al resultat de buscar al wizard_obj
    if wiz_ids:
        for wiz_id in wiz_ids:
            sql_model = """
                SELECT id
                FROM ir_model_data
                WHERE model = 'ir.actions.wizard'
                AND module = %(module)s
                AND res_id in %(wiz_id)s
            """
            params_model = {
                'module': module,
                'wiz_id': wiz_id
            }
            cr.execute(sql_model, params_model)
            model_id = cr.fetchone()

            sql_value = """
                SELECT id, model, res_id
                FROM ir_values
                WHERE value = 'ir.actions.wizard,' || %(wiz_id)s
            """
            params_value = {
                'wiz_id': wiz_id
            }
            cr.execute(sql_value, params_value)
            values_datas = cr.dictfetchall()
            sql_del_wiz = """
                DELETE FROM ir_act_wizard WHERE id in %(wiz_id)s;
            """
            params_del_wiz = {
                'wiz_id': wiz_id
            }
            cr.execute(sql_del_wiz, params_del_wiz)

            # un cop trobats els ids, validar que tots només tenen un registre i llavors eliminar-los tots
            if model_id and len(model_id) == 1:
                sql_del = """
                    DELETE FROM ir_model_data WHERE id in %(model_id)s
                """
                params_del = {
                    'model_id': model_id
                }
                cr.execute(sql_del, params_del)

            for value_data in values_datas:
                sql_del = """
                    DELETE FROM ir_values WHERE id = %(value_id)s
                """
                params_del = {
                    'value_id': value_data['id']
                }
                cr.execute(sql_del, params_del)
                # the associated menus of the old wizard are also deleted if any
                if value_data['model'] == 'ir.ui.menu':
                    sql_del_menu = """
                    DELETE
                    FROM ir_ui_menu
                    WHERE id = %(menu_id)s;
                    DELETE
                    FROM ir_model_data
                    WHERE res_id = %(menu_id)s
                      AND model = 'ir.ui.menu';
                    """
                    cr.execute(sql_del_menu, {'menu_id': value_data['res_id']})


def set_defaults(cr, pool, default_spec, force=False):
    """
    Set default value. Useful for fields that are newly required. Uses orm, so
    call from the post script.
    
    :param default_spec: a hash with model names as keys. Values are lists of \
    tuples (field, value). None as a value has a special meaning: it assigns \
    the default value. If this value is provided by a function, the function is \
    called as the user that created the resource.
    :param force: overwrite existing values. To be used for assigning a non- \
    default value (presumably in the case of a new column). The ORM assigns \
    the default value as declared in the model in an earlier stage of the \
    process. Beware of issues with resources loaded from new data that \
    actually do require the model's default, in combination with the post \
    script possible being run multiple times.
    """
    from osv import osv

    def write_value(ids, field, value):
        logger.info("model %s, field %s: setting default value of %d resources to %s",
                    model, field, len(ids), str(value))
        obj.write(cr, 1, ids, {field: value})

    for model in list(default_spec.keys()):
        obj = pool.get(model)
        if not obj:
            raise osv.except_osv("Migration: error setting default, no such model: %s" % model, "")

    for field, value in default_spec[model]:
        domain = not force and [(field, '=', False)] or []
        ids = obj.search(cr, 1, domain)
        if not ids:
            continue
        if value is None:
            # Set the value by calling the _defaults of the object.
            # Typically used for company_id on various models, and in that
            # case the result depends on the user associated with the object.
            # We retrieve create_uid for this purpose and need to call the _defaults
            # function per resource. Otherwise, write all resources at once.
            if field in obj._defaults:
                if not callable(obj._defaults[field]):
                    write_value(ids, field, obj._defaults[field])
                else:
                    # existence users is covered by foreign keys, so this is not needed
                    # cr.execute("SELECT %s.id, res_users.id FROM %s LEFT OUTER JOIN res_users ON (%s.create_uid = res_users.id) WHERE %s.id IN %s" %
                    #                     (obj._table, obj._table, obj._table, obj._table, tuple(ids),))
                    cr.execute("SELECT id, COALESCE(create_uid, 1) FROM %s " % obj._table + "WHERE id in %s",
                               (tuple(ids),))
                    fetchdict = dict(cr.fetchall())
                    for id in ids:
                        write_value([id], field, obj._defaults[field](obj, cr, fetchdict.get(id, 1), None))
                        if id not in fetchdict:
                            logger.info(
                                "model %s, field %s, id %d: no create_uid defined or user does not exist anymore",
                                model, field, id)
            else:
                error = ("OpenUpgrade: error setting default, field %s with "
                         "None default value not in %s' _defaults" % (
                             field, model))
                logger.error(error)
                # this exeption seems to get lost in a higher up try block
                osv.except_osv("OpenUpgrade", error)
        else:
            write_value(ids, field, value)


def logged_query(cr, query, args=None):
    if args is None:
        args = []
    res = cr.execute(query, args)
    logger.debug('Running %s', query)
    if not res:
        query = query % args
        logger.warn('No rows affected for query "%s"', query)
    return res


def column_exists(cr, table, column):
    """
    Check whether a certain column exists

    :param cr: Database cursor
    :param table: Table name
    :type table: str or unicode
    :param column: Column
    :type column: str or unicode
    :return: True if the column exists
    :rtype: bool
    """
    query = (
        "SELECT count(attname) FROM pg_attribute WHERE attrelid = ("
        "SELECT oid FROM pg_class WHERE relname = %s AND relnamespace = ("
        "SELECT oid FROM pg_namespace WHERE nspname = 'public') "
        "AND relkind = 'r') AND attname = %s"
    )
    cr.execute(query, (table, column))
    return cr.fetchone()[0] == 1


def change_column_type(cursor, column_spec):
    """
    :param cr: Cursor
    :param colum_spec: a hash with table keys, with lists of tuples as values.
        Tuples consist of (column name, new_def). new_def as in
        posgresql_language
    :return: execute result
    """
    for table, spec in list(column_spec.items()):
        for column, new_def in spec:
            logged_query(
                cursor,
                'ALTER TABLE %s ALTER COLUMN %s TYPE %s' % (
                    table, column, new_def)
            )
    return True


def update_module_names(cr, namespec):
    """
    Deal with changed module names of certified modules
    in order to prevent  'certificate not unique' error,
    as well as updating the module reference in the
    XML id.
    
    :param namespec: tuple of (old name, new name)
    """
    for (old_name, new_name) in namespec:
        query = ("UPDATE ir_module_module SET name = %s "
                 "WHERE name = %s")
        logged_query(cr, query, (new_name, old_name))
        query = ("UPDATE ir_model_data SET module = %s "
                 "WHERE module = %s ")
        logged_query(cr, query, (new_name, old_name))


def add_ir_model_fields(cr, columnspec):
    """
    Typically, new columns on ir_model_fields need to be added in a very
    early stage in the upgrade process of the base module, in raw sql
    as they need to be in place before any model gets initialized.
    Do not use for fields with additional SQL constraints, such as a
    reference to another table or the cascade constraint, but craft your
    own statement taking them into account.
    
    :param columnspec: tuple of (column name, column type)
    """
    for column in columnspec:
        query = 'ALTER TABLE ir_model_fields ADD COLUMN %s %s' % (
            column)
        logged_query(cr, query, [])


def install_modules(cursor, *modules):
    """Installs a module.

    :param cr: Cursor database
    :param module: The module to install
    """
    import pooler

    uid = 1
    mod_obj = pooler.get_pool(cursor.dbname).get('ir.module.module')
    mod_obj.update_list(cursor, uid)
    search_params = [('name', 'in', modules), ('state', '=', 'uninstalled')]
    mod_ids = mod_obj.search(cursor, uid, search_params)
    mod_obj.button_install(cursor, uid, mod_ids)
    return True


def get_foreign_keys(cursor, table):
    """Get all the foreign keys from the given table

    Returns a dict with column_name as a key and the following keys:
      - constraint_name
      - table_name
      - column_name
      - foreign_table_name
      - foreign_column_name

    :param cursor: Database cursor
    :param table: Table name to get the foreign keys
    :return: dict
    """
    cursor.execute(
        "SELECT"
        " tc.constraint_name, tc.table_name, kcu.column_name,"
        " ccu.table_name AS foreign_table_name,"
        " ccu.column_name AS foreign_column_name"
        " FROM "
        "   information_schema.table_constraints AS tc"
        " JOIN information_schema.key_column_usage AS kcu"
        "   ON tc.constraint_name = kcu.constraint_name"
        " JOIN information_schema.constraint_column_usage AS ccu"
        "   ON ccu.constraint_name = tc.constraint_name"
        " WHERE constraint_type = 'FOREIGN KEY' AND tc.table_name=%s",
        (table,)
    )
    res = {}
    for fk in cursor.dictfetchall():
        res[fk['column_name']] = fk.copy()
    return res


def get_installed_modules(cursor):
    cursor.execute(
        "SELECT"
        " name "
        "FROM "
        "  ir_module_module "
        "WHERE state = 'installed'"
    )
    return [x[0] for x in cursor.fetchall()]


def module_is_installed(cursor, module_name):
    """Test if modules is installed.

    :param cr: Cursor database
    :param module_name: The module name
    """
    import pooler

    uid = 1
    mod_obj = pooler.get_pool(cursor.dbname).get('ir.module.module')
    search_params = [('name', '=', module_name),
                     ('state', 'in', MODULE_INSTALLED_STATES)]
    mod_ids = mod_obj.search(cursor, uid, search_params)
    return len(mod_ids) > 0


def load_translation(cursor, lang, name, type, res_id, src, value):
    if res_id is not False and res_id is not None:
        insert_sql = """
        INSERT INTO ir_translation(lang, name, type, res_id, src, value) 
        VALUES (%(lang)s, %(name)s, %(type)s, %(res_id)s, %(src)s, %(value)s) 
        ON CONFLICT (lang, src_md5, name, type, res_id) WHERE res_id = %(res_id)s DO UPDATE SET value = EXCLUDED.value
        """
    else:
        res_id = None  # Per si ens arriba False, perque en SQL False != null
        insert_sql = """
        INSERT INTO ir_translation(lang, name, type, res_id, src, value) 
        VALUES (%(lang)s, %(name)s, %(type)s, %(res_id)s, %(src)s, %(value)s) 
        ON CONFLICT (lang, src_md5, name, type) WHERE res_id is null DO UPDATE SET value = EXCLUDED.value
        """
    cursor.execute(insert_sql, {'lang': lang, 'name': name, 'type': type, 'res_id': res_id, 'src': src, 'value': value})


class MigrationHelper:
    """Helper class for GISCE ERP migrations."""

    def __init__(self, cursor, module_name, logger_name='openerp.migration'):
        """Initialize the migration helper.

        :param cursor: Database cursor (e.g. psycopg2 cursor).
        :type cursor: any
        :param module_name: Module name (e.g. 'giscedata_facturacio_switching').
        :type module_name: str
        :param logger_name: Name of the logger (default: 'openerp.migration').
        :type logger_name: str
        """
        self.cursor = cursor
        self.logger = logging.getLogger(logger_name)
        self.module_name = module_name
        self.pool = None

    def init_model(self, model_name):
        """Initialize a model’s database table.

        :param model_name: Full name of the model (e.g. 'wizard.accions.massives.giscedata.lot').
        :type model_name: str

        :return: self
        :rtype: MigrationHelper
        """
        import pooler

        # Initialize the pool if it hasn't been set up yet.
        if not hasattr(self, 'pool') or self.pool is None:
            self.logger.info("Creating pooler")
            self.pool = pooler.get_pool(self.cursor.dbname)

        table_name = model_name.replace('.', '_')
        is_new_table = not table_exists(self.cursor, table_name)

        model = self.pool.get(model_name)
        self.logger.info("{action} table: {model_name}".format(action="Creating" if is_new_table else "Updating", model_name=model_name))
        model._auto_init(self.cursor, context={'module': self.module_name})
        self.logger.info("Table {action} successfully.".format(action="created" if is_new_table else "updated"))

        return self

    def update_xml(self, xml_path, mode='update'):
        """Update an entire XML file.

        :param xml_path: Path to the XML file.
        :type xml_path: str
        :param mode: 'update' (default) for existing XML or 'init' for initializing a new XML.
        :type mode: str

        :return: self
        :rtype: MigrationHelper
        """
        action = "Updating" if mode == 'update' else "Initializing"
        self.logger.info("{action} XML '{xml_path}'".format(action=action, xml_path=xml_path))
        load_data(self.cursor, self.module_name, xml_path, idref=None, mode=mode)
        result_action = "updated" if mode == 'update' else "initialized"
        self.logger.info("XML successfully {action}.".format(action=result_action))

        return self

    def update_xml_records(self, xml_path, init_record_ids=None, update_record_ids=None, multi=False):
        """Update specific records in an XML file.

        :param xml_path: Path to the XML file.
        :type xml_path: str
        :param init_record_ids: List of record IDs to initialize. Can be None to skip initialization.
        :type init_record_ids: list of str or None
        :param update_record_ids: List of record IDs to update. Can be None to skip updating.
        :type update_record_ids: list of str or None
        :param multi: If False, only the first occurrence of each ID is processed. If True, all occurrences are processed.
        :type multi: bool

        :return: self
        :rtype: MigrationHelper
        """
        if not init_record_ids and not update_record_ids:
            self.logger.warn("No records to update!")
            return self

        if init_record_ids:
            self.logger.info("Initializing specific records in {xml_path}".format(xml_path=xml_path))
            load_data_records(self.cursor, self.module_name, xml_path, init_record_ids, mode='init', multi=multi)
            self.logger.info("XML records successfully initialized.")

        if update_record_ids:
            self.logger.info("Updating specific records in {xml_path}".format(xml_path=xml_path))
            load_data_records(self.cursor, self.module_name, xml_path, update_record_ids, mode='update', multi=multi)
            self.logger.info("XML records successfully updated.")

        return self

    def update_xml_records_multi(self, xml_path, init_record_ids=None, update_record_ids=None):
        """Update specific records in an XML file, processing all occurrences of each ID.

        :param xml_path: Path to the XML file.
        :type xml_path: str
        :param init_record_ids: List of record IDs to initialize. Can be None to skip initialization.
        :type init_record_ids: list of str or None
        :param update_record_ids: List of record IDs to update. Can be None to skip updating.
        :type update_record_ids: list of str or None

        :return: self
        :rtype: MigrationHelper
        """
        return self.update_xml_records(xml_path, init_record_ids, update_record_ids, multi=True)

    def update_access_csv(self, model_ids, filename='security/ir.model.access.csv', mode='update'):
        """Update access rules from a CSV file.

        :param model_ids: List of model IDs to update access rules for.
        :type model_ids: list of str
        :param filename: Path to the CSV file (default: 'security/ir.model.access.csv').
        :type filename: str
        :param mode: 'init' for initial load or 'update' (default) for updating existing rules.
        :type mode: str

        :return: self
        :rtype: MigrationHelper
        """
        self.logger.info("Updating access rules for models: {model_ids}".format(model_ids=model_ids))
        load_access_rules_from_model_name(self.cursor, self.module_name, model_ids=model_ids, filename=filename, mode=mode)
        self.logger.info("Access rules successfully updated.")

        return self

    def execute_sql(self, sql_query, params=None):
        """Execute a raw SQL query.

        :param sql_query: SQL query string.
        :type sql_query: str
        :param params: Parameters for the query, or None if no parameters.
        :type params: list or tuple or None

        :return: self
        :rtype: MigrationHelper
        """
        self.logger.info("Executing SQL: {}...".format(sql_query[:60]))
        if params:
            self.cursor.execute(sql_query, params)
        else:
            self.cursor.execute(sql_query)
        self.logger.info("SQL executed successfully.")

        return self
