# -*- coding: utf-8 -*-
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
    'load_access_rules_from_model_name'
    "delete_registers"
]


def load_data(cr, module_name, filename, idref=None, mode='init'):
def load_data(cr, module_name, filename, idref=None, mode="init"):
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
    logger.info("%s: loading %s" % (module_name, filename))
    _, ext = os.path.splitext(filename)
    pathname = os.path.join(module_name, filename)
    fp = tools.file_open(pathname)
    try:
        if ext == '.csv':
        if ext == ".csv":
            noupdate = True
            tools.convert_csv_import(cr, module_name, pathname, fp.read(), idref, mode, noupdate)
        else:
            tools.convert_xml_import(cr, module_name, fp, idref, mode=mode)
    finally:
        fp.close()


def load_data_records(cr, module_name, filename, record_ids, mode='update'):
def load_data_records(cr, module_name, filename, record_ids, mode="update"):
    """
    :param module_name: the name of the module
    :param filename: the path to the filename, relative to the module \
    directory.
    :param record_ids: List of records to process
    :param mode: one of 'init', 'update', 'demo'. Always use 'init' for adding new items \
    from files that are marked with 'noupdate'. Defaults to 'update'.
    """
    from lxml import etree
    from tools import config, xml_import

    xml_path = '{}/{}/{}'.format(config['addons_path'], module_name, filename)
    xml_path = "{}/{}/{}".format(config["addons_path"], module_name, filename)
    if not os.path.exists(xml_path):
        raise Exception('Data {} not found'.format(xml_path))
        raise Exception("Data {} not found".format(xml_path))
    if not record_ids:
        raise Exception("Maybe you want to run 'load_data' because you don't pass any record id")
    xml_to_import = xml_import(cr, module_name, {}, mode, noupdate=False)
    doc = etree.parse(xml_path)
    logger.info('{}: loading file {}'.format(module_name, filename))
    logger.info("{}: loading file {}".format(module_name, filename))
    for record_id in record_ids:
        logger.info("{}: Loading record id: {}".format(module_name, record_id))
        rec = doc.findall("//*[@id='{}']".format(record_id))[0]
        data = doc.findall("//*[@id='{}']/..".format(record_id))[0]
        xml_to_import._tags[rec.tag](cr, rec, data)


def load_access_rules_from_model_name(cr, module_name, model_ids, filename='security/ir.model.access.csv', mode='init'):
def load_access_rules_from_model_name(cr, module_name, model_ids, filename="security/ir.model.access.csv", mode="init"):
    # Example: load_access_rules_from_model_name(cursor, 'base', ['model_ir_auto_vacuum'], mode='init')
    import tools

    if not isinstance(model_ids, (tuple, list)):
        model_ids = [model_ids]

    logger.info('%s: loading %s %s' % (module_name, filename, model_ids))
    logger.info("%s: loading %s %s" % (module_name, filename, model_ids))
    _, ext = os.path.splitext(filename)
    pathname = os.path.join(module_name, filename)
    fp = tools.file_open(pathname)
    file_lines = fp.readlines()
    clean_str = lambda _s: _s.replace('\n', '').replace('\t', '').replace('\r', '')
    clean_str = lambda _s: _s.replace("\n", "").replace("\t", "").replace("\r", "")
    header = clean_str(file_lines.pop(0))
    header_len = len(header.split(','))
    header_len = len(header.split(","))
    rules_lines = [header]
    for _f_line in file_lines:
        clean_line = clean_str(_f_line)
        split_line = clean_line.split(',')
        split_line = clean_line.split(",")
        if len(split_line) == header_len and split_line[2].replace('"', "") in model_ids:
            rules_lines.append(clean_line)
    data_lines = '\n'.join(rules_lines)
    data_lines = "\n".join(rules_lines)
    fp.close()
    # check
    for _model in model_ids:
        if '"{}"'.format(_model) not in data_lines:
            raise Exception('{} not found in {}'.format(_model, pathname))
            raise Exception("{} not found in {}".format(_model, pathname))
    tools.convert_csv_import(cr, module_name, filename, data_lines, mode=mode)


def table_exists(cr, table):
    """ Check whether a certain table or view exists """
    cr.execute(
        'SELECT count(relname) FROM pg_class WHERE relname = %s',
        (table,))
    cr.execute("SELECT count(relname) FROM pg_class WHERE relname = %s", (table,))
    return cr.fetchone()[0] == 1


def rename_columns(cr, column_spec):
    """
    Rename table columns. Typically called in the pre script.

    :param column_spec: a hash with table keys, with lists of tuples as values. \
    Tuples consist of (old_name, new_name).

    """
    for table in column_spec.keys():
        for (old, new) in column_spec[table]:
            logger.info("table %s, column %s: renaming to %s",
                        table, old, new)
            cr.execute('ALTER TABLE "%s" RENAME "%s" TO "%s"' % (table, old, new,))
            )


def rename_tables(cr, table_spec):
    """
    Rename tables. Typically called in the pre script.
    :param column_spec: a list of tuples (old table name, new table name).

    """
    for (old, new) in table_spec:
        logger.info("table %s: renaming to %s",
                    old, new)
        cr.execute('ALTER TABLE "%s" RENAME TO "%s"' % (old, new,))
        )


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
        )


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
        logger.info("table %s: drop column %s", table, column)
        if column_exists(cr, table, column):
            cr.execute('ALTER TABLE "%s" DROP COLUMN "%s"' %
                       (table, column))
            cr.execute('ALTER TABLE "%s" DROP COLUMN "%s"' % (table, column))
        else:
            logger.warn("table %s: column %s did not exist",
                        table, column)
            logger.warn("table %s: column %s did not exist", table, column)


def add_columns(cr, column_spec):
    """
    Add columns

    :param cr: Database cursor
    :param column_spec: a hash with table keys, with lists of tuples as values.
        Tuples consist of (column name, type).
    """
    for table in column_spec:
        for (column, type_) in column_spec[table]:
            logger.info("table %s: add column %s",
                        table, column)
            logger.info("table %s: add column %s", table, column)
            if column_exists(cr, table, column):
                logger.warn("table %s: column %s already exists",
                            table, column)
                logger.warn("table %s: column %s already exists", table, column)
            else:
                cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' %
                           (table, column, type_))
                cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (table, column, type_))


def add_columns_fk(cr, column_spec):
    """
    Add columns with foreign key constraint

    :param cr: Database cursor
    :param column_spec: a hash with table keys, with lists of tuples as values.
        Tuples consist of (column name, type, foreing table name, foreing key column, on delete action).
    """
    for table in column_spec:
        for (column, type_, fk_table_name, fk_col, on_delete_act) in column_spec[table]:
        for column, type_, fk_table_name, fk_col, on_delete_act in column_spec[table]:
            add_columns(cr, {table: [(column, type_)]})
            constraint = table + '_' + column + '_fkey'
            constraint = table + "_" + column + "_fkey"
            if not on_delete_act:
                on_delete_act = 'restrict'
            logger.info("table %s: add constraint %s",
                        table, constraint)
            cr.execute('ALTER TABLE "%s" ADD CONSTRAINT "%s" FOREIGN KEY (%s) REFERENCES %s(%s) \
                        ON DELETE %s' %
                       (table, constraint, column, fk_table_name, fk_col, on_delete_act))
            )


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
        cr.execute("select id from " + obj._table)
        ids_lst = map(lambda x: x[0], cr.fetchall())
        logger.info("storing computed values for %s objects" % len(ids_lst))
        start = datetime.now()

        def chunks(l, n):
            """Yield successive n-sized chunks from l."""
            for i in range(0, len(l), n):
                yield l[i:i + n]
                yield l[i : i + n]

        for ids in chunks(ids_lst, 100):
            res = field.get(cr, obj, ids, k, 1, {})
            for key, val in res.items():
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
    logged_query(cr, "DELETE FROM wkf WHERE osv = %s", (model,))


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
    params_wizard = {"old_wiz_name": old_wizard_name}
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
            params_model = {"module": module, "wiz_id": wiz_id}
            cr.execute(sql_model, params_model)
            model_id = cr.fetchone()

            sql_value = """
                SELECT id
                FROM ir_values
                WHERE value = 'ir.actions.wizard,%(wiz_id)s'
            """
            params_value = {
                'wiz_id': wiz_id
            }
            params_value = {"wiz_id": wiz_id}
            cr.execute(sql_value, params_value)
            value_id = cr.fetchone()

            sql_del_wiz = """
                DELETE FROM ir_act_wizard WHERE id in %(wiz_id)s;
            """
            params_del_wiz = {
                'wiz_id': wiz_id
            }
            params_del_wiz = {"wiz_id": wiz_id}
            cr.execute(sql_del_wiz, params_del_wiz)

            # un cop trobats els ids, validar que tots només tenen un registre i llavors eliminar-los tots
            if model_id and len(model_id) == 1:
                sql_del = """
                    DELETE FROM ir_model_data WHERE id in %(model_id)s
                """
                params_del = {
                    'model_id': model_id
                }
                params_del = {"model_id": model_id}
                cr.execute(sql_del, params_del)

            if value_id and len(value_id) == 1:
                sql_del = """
                    DELETE FROM ir_value WHERE id in %(value_id)s
                """
                params_del = {
                    'value_id': value_id
                }
                params_del = {"value_id": value_id}
                cr.execute(sql_del, params_del)


def delete_registers(cursor, module_name, view_ids):
    """
    Clean the <ir.ui.view> and <ir.model.data> registers associated to the
    views passed as parameter that were deleted from the specified module.

    NOTE: Ideally the 'view_ids' should be a list but if it is one view only it
    accepts a string.

    :param cursor: Database cursor
    :param module_name: Module name where the deleted views were
    :type module_name: str
    :param view_ids: View identifiers of the deleted views
    :type view_ids: list[str]
    """
    import pooler

    uid = 1

    if not view_ids:
        raise Exception('You have to specify a list of view names')
        raise Exception("You have to specify a list of view names")
    if not module_name:
        raise Exception("You have to specify a module where the record views are")
    if not isinstance(view_ids, (list)):
        view_ids = [view_ids]

    mod_data_obj = pooler.get_pool(cursor.dbname).get("ir.model.data")
    for view_id in view_ids:
        # Find by model = ir.ui.view, module = module & name = the view_id
        logger.info(" {}: Deleting view: {}".format(module_name, view_id))
        sql_model = """
                        SELECT id, model
                        FROM ir_model_data
                        WHERE module = %(module)s
                        AND name = %(view_id)s
                    """
        params_model = {"module": module_name, "view_id": view_id}
        cursor.execute(sql_model, params_model)
        model_data = cursor.fetchall()

        if len(model_data) == 0:
            # do nothing
            logger.info("The register {} doesn't exists".format(view_id))
            break

        if len(model_data) > 1:
            raise Exception("The register {} is being used in more than one place".format(view_id))

        # Get the id of model_type from <ir.model.data> (res_id)
        ui_view_id = False
        model_id = model_data[0][0]
        model_type = model_data[0][1].replace('.', '_')

        # It should have only one.
        if model_data and model_id:
            ui_view_id = mod_data_obj.read(cursor, uid, model_id, ["res_id"])["res_id"]
            # Delete from model data.
            cursor.execute('DELETE FROM ir_model_data WHERE id = {}'.format(model_id))
        # Use 'ui_view_id' to delete view register in model_type
        if ui_view_id:
            cursor.execute('DELETE FROM {} WHERE id = {}'.format(model_type, ui_view_id))


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
                    model, field, len(ids), unicode(value))
        )
        obj.write(cr, 1, ids, {field: value})

    for model in default_spec.keys():
        obj = pool.get(model)
        if not obj:
            raise osv.except_osv("Migration: error setting default, no such model: %s" % model, "")

    for field, value in default_spec[model]:
        domain = not force and [(field, '=', False)] or []
        domain = not force and [(field, "=", False)] or []
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
                    )
                    fetchdict = dict(cr.fetchall())
                    for id in ids:
                        write_value([id], field, obj._defaults[field](obj, cr, fetchdict.get(id, 1), None))
                        if id not in fetchdict:
                            logger.info(
                                "model %s, field %s, id %d: no create_uid defined or user does not exist anymore",
                                model, field, id)
                            )
            else:
                error = ("OpenUpgrade: error setting default, field %s with "
                         "None default value not in %s' _defaults" % (
                             field, model))
                )
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
    logger.debug("Running %s", query)
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
    cr.execute(
        'SELECT count(attname) FROM pg_attribute '
        'WHERE attrelid = '
        '( SELECT oid FROM pg_class WHERE relname = %s ) '
        'AND attname = %s',
        (table, column));
    )
    return cr.fetchone()[0] == 1


def change_column_type(cursor, column_spec):
    """
    :param cr: Cursor
    :param colum_spec: a hash with table keys, with lists of tuples as values.
        Tuples consist of (column name, new_def). new_def as in
        posgresql_language
    :return: execute result
    """
    for table, spec in column_spec.items():
        for column, new_def in spec:
            logged_query(
                cursor,
                'ALTER TABLE %s ALTER COLUMN %s TYPE %s' % (
                    table, column, new_def)
            )
            logged_query(cursor, "ALTER TABLE %s ALTER COLUMN %s TYPE %s" % (table, column, new_def))
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
        query = "UPDATE ir_module_module SET name = %s " "WHERE name = %s"
        logged_query(cr, query, (new_name, old_name))
        query = ("UPDATE ir_model_data SET module = %s "
                 "WHERE module = %s ")
        query = "UPDATE ir_model_data SET module = %s " "WHERE module = %s "
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
        query = "ALTER TABLE ir_model_fields ADD COLUMN %s %s" % (column)
        logged_query(cr, query, [])


def install_modules(cursor, *modules):
    """Installs a module.

    :param cr: Cursor database
    :param module: The module to install
    """
    import pooler

    uid = 1
    mod_obj = pooler.get_pool(cursor.dbname).get('ir.module.module')
    mod_obj = pooler.get_pool(cursor.dbname).get("ir.module.module")
    mod_obj.update_list(cursor, uid)
    search_params = [('name', 'in', modules), ('state', '=', 'uninstalled')]
    search_params = [("name", "in", modules), ("state", "=", "uninstalled")]
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
        (table,),
    )
    res = {}
    for fk in cursor.dictfetchall():
        res[fk['column_name']] = fk.copy()
        res[fk["column_name"]] = fk.copy()
    return res


def get_installed_modules(cursor):
    cursor.execute(
        "SELECT"
        " name "
        "FROM "
        "  ir_module_module "
        "WHERE state = 'installed'"
    )
    cursor.execute("SELECT" " name " "FROM " "  ir_module_module " "WHERE state = 'installed'")
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
    search_params = [("name", "=", module_name), ("state", "in", MODULE_INSTALLED_STATES)]
    mod_ids = mod_obj.search(cursor, uid, search_params)
    return len(mod_ids) > 0
