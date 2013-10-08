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
    elif config.row:
        rs=table.FindRecords(config.columns[0]+"=="+config.row)
    else:
        # TODO: need a way to determine total length.
        # NOTE: get everything
        rs = table.GetRecords(1,MAX_ROW_COUNT)
    return rs

def delete_record(rec):
    # TODO: add ability to delete 'rec'
    pass

def usage():
    return """
  Usage:
    # setup spreadsheet.conf with sheetname, email, password, then:
    ./gspreadsheet.py --table test --create --columns a,b,c,d,e
    ./gspreadsheet.py --table test --show   --row A
    ./gspreadsheet.py --table test --update --row A --values 2,3,4,5
    ./gspreadsheet.py --table test --show   --row A
    ./gspreadsheet.py --table test --update --row A \\
                      --results "echo 'b,{ts}\\nc,{b}\\nd,{c}\\ne,{d}\\n'"
    ./gspreadsheet.py --table test --show   --row A

  Examples:
    A sheet is created with specified columns. First column is row-id
          
     --create --table name --columns a,b,c,d,e
  
     --update --table name --row A --columns c,e --values C,E
     --update --table name --row A --results "command.sh {key_a} [...]"
     --update --table name --select <expr> --results "command.sh {key_a} [...]"
  
     --show   --table name --row A [--columns b,c,d]
     --show   --table name --select <expr> [--columns b,c,d]
  
     TODO: --delete --row A
     TODO: --delete --select <expr>
    """

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
                      help="delete records that match selected rows")

    # NOTE: how to specifiy rows, data, or commands that produce data
    parser.add_option("", "--row", dest="row",
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
        if ((config.row is None and config.select is None) or
            (config.row and config.select)):
            print "Error: for --update specify --row or --select"
            sys.exit(1)
        if config.select and config.results is None:
            print "Error: for --select also specify --results"
            sys.exit(1)
        if not ((config.row and config.results) or
                (config.row and config.values)):
            print "Error: for --row specify --results, or --values"
            sys.exit(1)
    if config.delete:
        if ((config.row is None and config.select is None) or
            (config.row and config.select)):
            print "Error: for --delete specify either --row or --select"
            sys.exit(1)

    # NOTE: Get any local config information
    read_local_config(config, config.configfile)
    if config.email is None or config.password is None:
        print "Error: please provide username/ password"
        sys.exit(1)
    if config.sheetname is None or config.table is None:
        print "Error: please provide sheetname & table names"
        sys.exit(1)

    if config.columns:
        config.columns = config.columns.split(',')
    if config.values:
        config.values = config.values.split(',')
        # TODO: maybe add a 'tr' like feature to convert chars after split
        #       in case we want ',' in values


    return (config, args)

def handle_show(table, config):
    if config.header:
        print " ".join(config.columns)

    rs=get_records(table, config)
    for record in rs:
        for key in config.columns:
            if record.content.has_key(key):
                print record.content[key],
            else:
                print >>sys.stderr, "Error: record does not contain key: '%s'" % key
                sys.exit(1)
        print ""

def handle_update(table, config):
    rs = get_records(table, config)
    if config.values:
        handle_update_values(table, config, rs)
    elif config.results:
        handle_update_results(table, config, rs)

def handle_update_values(table, config, rs):
    data_list = []
    # NOTE: values are only used during update.
    if len(config.columns) == len(config.values):
        new_data = dict(zip(config.columns, config.values))
    elif len(config.columns[1:]) == len(config.values):
        new_data = dict(zip(config.columns[1:], config.values))
    else:
        print "Error: --values without --columns lengths do not match."
        print "Error: Specify both --values and --columns, or"
        print "Error: Specify enough --values to equal columns"
        sys.exit(1)

    new_data.update({config.columns[0] : config.row})

    if len(rs) == 0:
        # NOTE: there was no field found, so add it.
        print >>sys.stderr, "Adding data: %s" % new_data
        add_record(table, new_data)
        return
    
    # NOTE: len(rs) > 0
    for rec in rs:
        print >>sys.stderr, "Updating data to", new_data
        update_record(rec, new_data)
    return

def handle_update_results(table, config, rs):
    if len(rs) == 0:
        # NOTE: there was no field found, so add it.
        if not config.row:
            msg = "Cannot add new records from empty --select queries"
            print >>sys.stderr, "Error: " + msg
            sys.exit(1)

        # NOTE: treat the first column as the key for row.
        default_data = {config.columns[0] : config.row}
        print default_data
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
        print >>sys.stderr, rec.content
        (status, new_data) = handle_results_execution(rec.content.copy(),
                                                      config.results)
        if not status:
            msg = "Failed to collect data for record %s" % new_data
            print >>sys.stderr, "Warning: " + msg

        update_record(rec, new_data)
    return

def handle_results_execution(current_data, command_format):
    # NOTE: format command to run using execute_fmt and current record values
    (status, value_raw) = command_wrapper(current_data, command_format)

    if status is False:
        print >>sys.stderr, "Error: %s" % (value_raw)
        return (False, {})

    # NOTE: status == True, so success
    # TODO: maybe make ',' configurable?
    new_data = parse_raw_values(value_raw)
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

def command_wrapper(current_data, command_format):
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
    print >>sys.stderr, "STDOUT"
    print >>sys.stderr, s_out,
    print >>sys.stderr, "END"
    print >>sys.stderr, "STDERR"
    print >>sys.stderr, s_err,
    print >>sys.stderr, "END"
    return (True, s_out)

def main():
    (config, args) = parse_args()

    # NOTE: setup connection to db & table
    client = spreadsheet_textdb.DatabaseClient(config.email, config.password)
    db = get_db(client, config.sheetname, config.create)
    table = get_table(db, config.table, config.columns, config.create)

    # NOTE: look up columns automatically (if not given)
    if not config.columns and (config.show or config.update):
        table.LookupFields()
        config.columns = table.fields

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
