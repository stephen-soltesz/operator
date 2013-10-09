#!/usr/bin/env python

import ConfigParser
from datetime import datetime,timedelta
import gdata.spreadsheet.text_db as spreadsheet_textdb
import os
import subprocess
import sys
import time

# TODO: figure out how to get the number of rows in a spreadsheet
#       seems unsupported without fetching everything and counting
MAX_ROW_COUNT=10000

def usage():
    return """
  Summary:
    gspreadsheet.py creates a columnated, queryable, and updatable,
    key-values store using Google Drive Spreadsheets as a storge medium.

    gspreadsheet.py is written for scripting, and as an automation aid. By
    using Google Spreadsheets, the data can be viewed easily or updated by
    hand if necessary.

    gspreadsheet.py supports create, show, and update.

  Configuration:
    All values can be set on the command line.  Common values can be set using
    "spreadsheet.conf", using INI format supported by Python ConfigParser.
    
    gspreadsheet.py supports one section [main] and these parameters:
      email=        -- email address of google account to access Drive
      password=     -- password of google account
      sheetname=    -- spreadsheet name, visible in Drive
      table=        -- table name (i.e, 'sheet' name in user interface)

  Scripted Values:
    The best feature of gspreadsheet.py is that rows can be updated from
    values returned by a script.

    The script is specified using --results "command [args ...]"

    A successful script should have an exit value of zero, and print 
    column,value pairs separated by newline to stdout.
        c1,v1\\n
        c2,v2\\n
        c3,v3\\n
    
    All of these values will be assocaited with the --key given on the command
    line. Every existing column name will be updated with the corresponding
    value.  Non-existent columsn will be ignored.  Values for recurring column
    names are concatenated with a space into a single value.

    If an error occurs, the script should have a non-zero exit value, and
    print a helpful message to stderr. Any data on stdout is ignored when exit
    value is non-zero.

  Examples:
    If spreadsheet.conf contains values for email, password, and spreadsheet:

    # create table, with column names, first column is the keyname
    ./gspreadsheet.py --table test --create --columns keyname,c1,c2,c3,c4

    # add values
    ./gspreadsheet.py --table test --update --key A --values 2,3,4,5
    ./gspreadsheet.py --table test --update --key B --values 0,7,5,3
    ./gspreadsheet.py --table test --update --key C --columns c2,c3 --values 9,1

    # add values by script 
    ./gspreadsheet.py --table test --update --key D \\
                  --results "echo 'c1,{ts}\\nc2,{c1}\\nc3,{c2}\\nc4,{c3}\\n'"

    # show a single record (with implied query for, keyname=='A')
    ./gspreadsheet.py --table test --show --key A

    # show all values in column 'keyname'
    ./gspreadsheet.py --table test --show --columns keyname

    # show rows that match '--select' query
    ./gspreadsheet.py --table test --show --select 'c2>4'

    # show everything
    ./gspreadsheet.py --table test --show """

def read_local_config(options, filename):
    """ Read the given configuration filename and save values in 'options'
        This function recognizes only one section:
            '[main]'
        Within this section, this function recognizes only:
            'sheetname' - name of spreadsheet file in Drive
            'table' - table name within spreadsheet.
            'email' - google account email
            'password' - password for account

        Args:
            options - the options object returned by OptionParser.parse_args()
            filename - filename of config file
        Returns:
            None
    """
    config = ConfigParser.SafeConfigParser()
    if not os.path.exists(filename):
        # NOTE: all options can be passed via command line
        return

    config.read(filename)
    for opt_name in ['email', 'password', 'sheetname', 'table']:
        if not config.has_option('main', opt_name):
            continue
        setattr(options, opt_name, config.get('main', opt_name))
    return

def get_db(client, name, create):
    """ Searches for database 'name'. If the database is not found
    create it if 'create' is True, otherwise exit.
    Args:
        client - DatabaseClient()
        name - string, name of database
        create - bool, whether or not to create if db not found
    Returns:
        gdata.spreadsheet.text_db.Database()
    Exits:
        if database 'name' not found and 'create' is False
    """
    db_list = client.GetDatabases(name=name)
    if len(db_list) == 0:
        if not create:
            print >>sys.stderr, "Error: could not find db %s" % name
            print >>sys.stderr, "Error: use --create to create it"
            sys.exit(1)
        db = client.CreateDatabase(name)
    else:
        db = db_list[0]
    return db

def get_table(db, table_name, column_names, create):
    """ Searches for table 'table_name'.  If the table is not found
    and 'create' is True, then create the table.  Otherwise, exit.
    Args:
        db - Database(), returned by get_db() or similar
        table_name - string, name of table or 'sheet' in web-UI
        column_names - list of string, column header names
        create - bool, whether or not to create if table not found
    Returns:
        gdata.spreadsheet.text_db.Table()
    Exits:
        if table 'name' not found and 'create' is False
    """
    table_list = db.GetTables(name=table_name)
    if len(table_list) == 0:
        if not create:
            print >>sys.stderr, "Error: could not find table %s" % table_name
            print >>sys.stderr, "Error: use --create to create it"
            sys.exit(1)
        # NOTE: cannot create a table without headers.
        assert(column_names is not None and len(column_names) > 0 )
        if config.verbose:
            print >>sys.stderr, "Creating table: %s" % table_name
            print >>sys.stderr, "With headers: %s" % column_names
        table = db.CreateTable(table_name, column_names)
    else:
        table = table_list[0]
    return table

def add_record(table, data):
    row = table.AddRecord(data)
    return row

def update_record(record, data):
    record.content.update(data)
    record.Push()
    return record

def get_records(table, config):
    rs=[]
    if config.select:
        rs=table.FindRecords(config.select)
    elif config.key:
        rs=table.FindRecords(config.headers[0]+"=="+config.key)
    else:
        # TODO: need a way to determine total length.
        # NOTE: get everything
        rs = table.GetRecords(1,MAX_ROW_COUNT)
    return rs

def delete_record(rec):
    # TODO: add ability to delete 'rec'
    pass

def parse_args():
    from optparse import OptionParser
    parser = OptionParser(usage=usage())

    # NOTE: spreadsheet configuration & access
    parser.add_option("", "--sheetname", dest="sheetname",
                      default=None,
                      help="Name of Spreadsheet (visible in Google Drive)")
    parser.add_option("", "--table",     dest="table",
                      default=None,
                      help="Table name (i.e. page, sheet) within spreadsheet.")
    parser.add_option("", "--email",     dest="email",
                      default=None,
                      help="user email address")
    parser.add_option("", "--password",  dest="password",
                      default=None,
                      help="application or user password")
    parser.add_option("", "--config",    dest="configfile",
                      default="spreadsheet.conf",
                      help="Config file containing spreadsheet values")

    # OPTIONAL
    parser.add_option("", "--verbose", dest="verbose",
                      default=False, action="store_true",
                      help="Print some extra messages.")

    # NOTE: mutually exclusive options.
    parser.add_option("", "--create", dest="create",
                      default=False, action="store_true",
                      help="Creates a new spreadsheet in GoogleDrive.")
    parser.add_option("", "--update", dest="update",
                      default=False, action="store_true",
                      help="add or update records that match selected rows")
    parser.add_option("", "--show", dest="show",
                      default=False, action="store_true",
                      help="display records that match selected rows")
    parser.add_option("", "--header", dest="header", action="store_true",
                      default=False,
                      help="For --show, print header as first line")
    parser.add_option("", "--delete", dest="delete",
                      default=False, action="store_true",
                      help="TODO: delete records that match selected rows")

    # NOTE: how to specifiy rows, data, or commands that produce data
    parser.add_option("", "--key", dest="key",
                      default=None,
                      help="Row identifier to operate on.")
    parser.add_option("", "--select", dest="select",
                      default=None,
                      help="Select statement to choose rows to operate on.")
    parser.add_option("", "--columns", dest="columns",
                      default=None,
                      help="Column names to operate on.")
    parser.add_option("", "--values", dest="values",
                      default=None,
                      help="Values to associate with corresponding 'column'")
    parser.add_option("", "--results",  dest="results",
                      default=None,
                      help="Excecute the steps for completing a node update.")

    (config, args) = parser.parse_args()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    # NOTE: confirm some options are mutually exclusive
    count = sum([config.create,config.update,config.show,config.delete])
    if count == 0 or count > 1:
        print "Error: Specify one of create, update, show, or delete"
        sys.exit(1)

    # NOTE: continue checking arguments
    if config.create:
        if config.columns is None:
            print "Error: for --create also specify --columns"
            sys.exit(1)
    if config.update:
        if config.key is None:
            print "Error: for --update you must specify --key"
            sys.exit(1)
        if config.select:
            print "Error: sorry, --select not supported for --update"
            print "Error: --select only supported for --show"
            sys.exit(1)
        if config.key and config.results and config.values:
            print "Error: specify one of --results or --values"
            sys.exit(1)
        if not ((config.key and config.results) or
                (config.key and config.values)):
            print "Error: specify --key with --results, or"
            print "Error: specify --key with --values"
            sys.exit(1)
    if config.delete:
        print "Error: sorry, --delete not yet supported"
        sys.exit(1)
        if ((config.key is None and config.select is None) or
            (config.key and config.select)):
            print "Error: for --delete specify either --key or --select"
            sys.exit(1)

    # NOTE: Get any local config information
    read_local_config(config, config.configfile)

    if config.email is None or config.password is None:
        print "Error: please provide username & password"
        sys.exit(1)
    if config.sheetname is None or config.table is None:
        print "Error: please provide sheetname & table names"
        sys.exit(1)

    if config.columns:
        config.columns = config.columns.split(',')
    if config.values:
        # NOTE: values are only used during update.
        config.values = config.values.split(',')
        # TODO: maybe add a 'tr' like feature to convert chars after split
        #       in case we want ',' in values

    return (config, args)

def handle_show(table, config):
    if config.header:
        # TODO: maybe support a separator character here.
        print " ".join(config.columns)

    rs=get_records(table, config)
    for record in rs:
        for key in config.columns:
            if record.content.has_key(key):
                print record.content[key],
            else:
                msg = "Error: record does not contain key: '%s'" % key
                print >>sys.stderr, msg
                sys.exit(1)
        print ""

def handle_update(table, config):
    rs = get_records(table, config)
    if config.values:
        handle_update_values(table, config, rs)
    elif config.results:
        handle_update_results(table, config, rs)
    else:
        print >>sys.stderr, "Error: specify --results, or"
        print >>sys.stderr, "Error: specify --values"
        sys.exit(1)

def handle_update_values(table, config, rs):
    data_list = []
    # TODO: allow smaller --columns --values pairs
    # TODO: allow out of order combinations

    if not config.columns and len(config.headers[1:]) == len(config.values):
        new_data = dict(zip(config.headers[1:], config.values))

    elif config.columns and len(config.columns) == len(config.values):
        # NOTE: this might update the 'key', maybe not ideal.
        new_data = dict(zip(config.columns, config.values))

    else:
        col_len = len(config.columns[1:]) # don't include first, keyname col
        print >>sys.stderr, "Error: --values length do not match --columns."
        print >>sys.stderr, "Error: Specify both --values and --columns, or"
        msg = "Error: Specify enough --values to equal columns " + col_len
        print >>sys.stderr, msg
        sys.exit(1)

    new_data.update({config.columns[0] : config.key})

    if len(rs) == 0:
        # NOTE: there was no field found, so add it.
        if config.verbose:
            print >>sys.stderr, "Adding data: %s" % new_data
        add_record(table, new_data)
        return
 
    # NOTE: len(rs) > 0
    for rec in rs:
        if config.verbose:
            print >>sys.stderr, "Updating data to", new_data
        update_record(rec, new_data)
    return

def handle_update_results(table, config, rs):
    if len(rs) == 0:
        # NOTE: there was no field found, so add it.
        if not config.key:
            msg = "Cannot add new records from empty --select queries"
            print >>sys.stderr, "Error: " + msg
            sys.exit(1)

        # NOTE: treat the first column as the key for row.
        default_data = {config.columns[0] : config.key}
        if len(config.columns) > 1:
            for key in config.columns[1:]:
                default_data[key] = ''
        if config.verbose:
            print >>sys.stderr, default_data
        (status, new_data) = handle_results_execution(default_data,
                                                      config.results)
        if not status:
            msg = "Failed to collect data for record %s" % default_data
            print >>sys.stderr, "Warning: " + msg
            msg = "adding empty entry to spreadsheet"
            print >>sys.stderr, "Warning: " + msg

        default_data.update(new_data)
        add_record(table, default_data)
        return

    # NOTE: len(rs) > 0
    for rec in rs:
        if config.verbose:
            print >>sys.stderr, rec.content
        (status, new_data) = handle_results_execution(rec.content.copy(),
                                                      config.results)
        if not status:
            msg = "Failed to collect data for record %s" % new_data
            print >>sys.stderr, "Warning: " + msg

        update_record(rec, new_data)
    return

def handle_results_execution(config, current_data, command_format):
    # NOTE: format command to run using execute_fmt and current record values
    (status, value_raw) = command_wrapper(config, current_data, command_format)

    if status is False:
        print >>sys.stderr, "Error: %s" % (value_raw)
        return (False, {})

    # NOTE: status == True, so success
    # TODO: maybe make ',' configurable?
    new_data = parse_raw_values(value_raw)
    if config.verbose: 
        print >>sys.stderr, "new data:", new_data
    return (True, new_data)

def parse_raw_values(value_raw, separator=','):
    """ Takes a raw string blob that represents one or more lines separated
    by '\\n', and key,value pairs separated by 'separator' and returns a
    dictionary of the { key : value } pairs..

    If the same 'key' is found more than once, the value is appended with a
    space, 'value1 value2'.

    Args:
        value_raw - string, blob of text with key,value pairs
        separator - string, how key,value pairs are separated.
    Returns:
        dict of key,value pairs
    """
    value_list = value_raw.split('\n')
    new_data = {}
    for key_value in value_list:
        f = key_value.split(separator)
        if len(f) > 1:
            k,v = f
            if k in new_data:
                new_data[k] += " "+v.strip()
            else:
                new_data[k] = v.strip()
    return new_data

def command_wrapper(config, current_data, command_format):
    # NOTE: Schedule downtime for 2 days
    date_ts = time.strftime("%Y-%m-%dT%H:%M")
    date = time.strftime("%Y-%m-%d")
    ts = int(time.time())

    args = current_data.copy()
    for k,v in args.iteritems():
        if v is None:
            args[k] = ''
    args.update({'ts' : ts, 'date_ts' : date_ts, 'date' : date})

    cmd = command_format.format(** args)
    p = subprocess.Popen(cmd,
                         shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    input_str=None
    (s_out, s_err) = p.communicate(input_str)
    if p.returncode != 0:
        return (False, s_err)

    # NOTE: success!
    if config.verbose:
        print >>sys.stderr, "STDOUT"
        print >>sys.stderr, s_out.strip()
        print >>sys.stderr, "END"
        print >>sys.stderr, "STDERR"
        print >>sys.stderr, s_err.strip()
        print >>sys.stderr, "END"
    return (True, s_out)

def main():
    (config, args) = parse_args()

    # NOTE: setup connection to db & table
    client = spreadsheet_textdb.DatabaseClient(config.email, config.password)
    db = get_db(client, config.sheetname, config.create)
    table = get_table(db, config.table, config.columns, config.create)

    # NOTE: look up columns automatically (if not given)
    #if not config.columns and (config.show or config.update):
    if config.show or config.update:
        table.LookupFields()
        config.headers = table.fields

    # NOTE: process mutually exclusive options create, show, update, delete
    if config.create:
        # NOTE: all operations for create are processsed at this point.
        sys.exit(0)

    elif config.show:
        handle_show(table, config)
    
    elif config.update:
        handle_update(table, config)

    elif config.delete:
        # TODO: add delete
        print >>sys.stderr, "TODO: implement --delete"
        sys.exit(1)

    sys.exit(0)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
