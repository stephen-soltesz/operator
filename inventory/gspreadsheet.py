#!/usr/bin/env python

import ConfigParser
from datetime import datetime,timedelta
import gdata.spreadsheet.text_db as spreadsheet_textdb
import os
import subprocess
import sys
import time

# TODO: figure out how to get the number of rows in a spreadsheet
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
    db_list = client.GetDatabases(name=name)
    if len(db_list) == 0:
        if create:
            db = client.CreateDatabase(name)
        else:
            print >>sys.stderr, "Error: could not find db"
            print >>sys.stderr, "Error: try --create ?"
            sys.exit(1)
    else:
        db = db_list[0]
    return db

def get_table(db, table_name, type_list, create):
    try:
        table_list = db.GetTables(name=table_name)
    except:
        print >>sys.stderr, "exception"
        table_list = []
    if len(table_list) == 0:
        # NOTE: cannot create a table without headers.
        if create:
            assert(type_list is not None)
            print >>sys.stderr, "creating table: %s" % table_name
            print >>sys.stderr, "with headers: %s" % type_list
            table = db.CreateTable(table_name, type_list)
        else:
            print >>sys.stderr, "Error: could not find table"
            print >>sys.stderr, "Error: try --create ?"
            sys.exit(1)
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
    # TODO: delete 'rec'
    pass

def usage():
    return """
    Examples:
       A sheet is created with specified columns. First column is row-id
          
         --create --columns a,b,c,d,e
      
         --update --row A --columns c,e --values C,E
         --update --row A --results "command.sh %(key_a)s [...]"
         --update --select <expr> --results "command.sh %(key_a)s [...]"
      
         --show   --row A [--columns b,c,d]
         --show   --select <expr> [--columns b,c,d] 
      
         --delete --row A
         --delete --select <expr>
    """

def main():
    from optparse import OptionParser
    parser = OptionParser(usage=usage())

    parser.set_defaults(sheetname=None,
                        table=None,
                        email=None,
                        password=None)

    # NOTE: spreadsheet configuration & access
    parser.add_option("", "--sheetname", dest="sheetname", help="")
    parser.add_option("", "--table",     dest="table", help="")
    parser.add_option("", "--email",     dest="email", help="")
    parser.add_option("", "--password",  dest="password", help="")
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

    # NOTE: specifiy rows, data, or commands that produce data
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
                (config.row and config.columns and config.values)):
            print "Error: for --row specify --results, or --columns & --values"
            sys.exit(1)
    if config.delete:
        if ((config.row is None and config.select is None) or 
            (config.row and config.select)):
            print "Error: for --delete specify either --row or --select"
            sys.exit(1)

    if config.columns:
        config.columns = config.columns.split(',')

    # NOTE: Get any local config information
    read_local_config(config, config.configfile)
    if config.email is None or config.password is None:
        print "Error: please provide username/ password"
        sys.exit(1)
    if config.sheetname is None or config.table is None:
        print "Error: please provide sheetname & table names"
        sys.exit(1)

    # NOTE: setup db & table
    client = spreadsheet_textdb.DatabaseClient(config.email, config.password)
    db = get_db(client, config.sheetname, config.create)
    table = get_table(db, config.table, config.columns, config.create)

    # NOTE: look up columns automatically (if not given)
    if not config.columns and (config.show or config.update):
        table.LookupFields()
        config.columns = table.fields

    if config.create:
        # NOTE: nothing else to do
        sys.exit(0)

    elif config.show:
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
    
    elif config.update:
        # NOTE: values are only used during update.
        rs = get_records(table, config)

        if config.values:
            data_list = []
            config.values = config.values.replace("+", " ")
            config.values = [ v.replace(';', ',') for v in config.values.split(',') ]
            new_data = dict(zip(config.columns, config.values))
            if len(rs) == 0:
                # NOTE: there was no field found, so add it.
                print >>sys.stderr, "Adding data: %s" % data_list[0]
                add_record(table, new_data)
            else:
                for rec in rs:
                    print >>sys.stderr, "Updating data where: %s to " % config.update, new_data
                    update_record(rec, new_data)

        elif config.results:

            if len(rs) == 0:
                # NOTE: there was no field found, so add it.
                if not config.row:
                    msg = "Cannot add new records from empty --select queries"
                    print >>sys.stderr, "Error: " + msg
                    sys.exit(1)

                # NOTE: treat the first column as the key for row.
                default_data = {config.columns[0] : config.row}
                print default_data
                (status, new_data) = handle_execution(default_data,
                                                      config.results)
                if not status:
                    msg = "Failed to collect data for record %s" % default_data
                    print >>sys.stderr, "Warning: " + msg
                    msg = "adding empty entry to spreadsheet"
                    print >>sys.stderr, "Warning: " + msg

                default_data.update(new_data)
                add_record(table, default_data)
                    
            else:
                for rec in rs:
                    print >>sys.stderr, rec.content
                    (status, new_data) = handle_execution(rec.content.copy(),
                                                          config.results)
                    if not status:
                        msg = "Failed to collect data for record %s" % new_data
                        print >>sys.stderr, "Warning: " + msg

                    update_record(rec, new_data)

    sys.exit(0)

def handle_execution(current_data, command_format):
    # NOTE: format command to run using execute_fmt and current record values
    (status, value_raw) = command_wrapper(current_data, command_format)

    new_data = {}
    if status is False:
        print >>sys.stderr, "Error: %s" % (value_raw)
        return (status, new_data)

    value_list = value_raw.split('\n')
    print value_list
    for key_value in value_list:
        f = key_value.split(",")
        if len(f) > 1:
            k,v = f 
            if k in new_data:
                new_data[k] += " "+v.strip()
            else:
                new_data[k] = v.strip()
    print >>sys.stderr, "new data:", new_data
    return (status, new_data)

def command_wrapper(current_data, command_str):
    # NOTE: Schedule downtime for 2 days
    date = time.strftime("%Y-%m-%d")
    date_ts = time.strftime("%Y-%m-%dT%H:%M")
    ts = int(time.time())

    args = current_data.copy()
    args.update({'ts' : ts, 'date_ts' : date_ts, 'date' : date})
    cmd = command_str % args
    print >>sys.stderr, cmd
    p = subprocess.Popen(cmd, 
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, 
                         shell=True)
    (s_out, s_err) = p.communicate(None)
    if p.returncode == 0:
        print >>sys.stderr, "START"
        print >>sys.stderr, s_out
        print >>sys.stderr, "END"
        return (True, s_out)

    return (False, s_err)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
