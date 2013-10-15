#!/usr/bin/env python2
""" a wrapper around the nagios 'scheduled downtime' functionality. """

import os
import sys
import time
import signal
from copy import copy
from optparse import Option, OptionValueError
from datetime import datetime, timedelta

STATE_OK = 0
STATE_WARNING = 1
STATE_CRITICAL = 2
STATE_UNKNOWN = 3
STATE_DEPENDENT = 4

state_list = [ STATE_OK, STATE_WARNING, STATE_CRITICAL, 
               STATE_UNKNOWN, STATE_DEPENDENT, ]

def custom_command(opt, args):
    nagios_cmd_pipe = "/var/spool/nagios/rw/nagios.cmd"

    values = {'start' : int(time.mktime(opt.start_time.timetuple())),
              'end'   : int(time.mktime(opt.end_time.timetuple())),
              'user'  : os.environ['USER'] ,
              'comment' : opt.comment,
              'timestamp' : int(time.time()),
              'hostname' : opt.hostname,}

    if opt.type == "service":
        values['servicename'] = opt.servicename
        command="[%(timestamp)s] SCHEDULE_SVC_DOWNTIME;%(hostname)s;"
        command+="%(servicename)s;%(start)s;%(end)s;1;0;7200;%(user)s;"
        command+="%(comment)s" 
        command = command % values
    elif opt.type == "hostservices":
        command="[%(timestamp)s] SCHEDULE_HOST_DOWNTIME;%(hostname)s;"
        command+="%(start)s;%(end)s;1;0;7200;%(user)s;%(comment)s"
        command+="\n[%(timestamp)s] SCHEDULE_HOST_SVC_DOWNTIME;%(hostname)s;"
        command+="%(start)s;%(end)s;1;0;7200;%(user)s;%(comment)s"
        command = command % values
    elif opt.type == "host":
        command="[%(timestamp)s] SCHEDULE_HOST_DOWNTIME;%(hostname)s;"
        command+="%(start)s;%(end)s;1;0;7200;%(user)s;%(comment)s"
        command = command % values

    print command
    if not os.path.exists(nagios_cmd_pipe):
        print "Error: nagios command file missing"
        print "Error: tried here: %s" % nagios_cmd_pipe
        print "Error: cannot continue"
        sys.exit(1)

    fd = open(nagios_cmd_pipe, 'a')
    ret = fd.write(command+"\n")
    fd.close()

    return (STATE_OK, command)

def check_date(option, opt, value):
    try:
        return datetime.strptime(value, "%Y-%m-%d-%H:%M")
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except:
            raise OptionValueError("option %s: invalid date value: %r. Should have a format like \"YYYY-MM-DD[-HH:MM]\"" % (opt, value))

class DateOption (Option):
    TYPES = Option.TYPES + ("date",)
    TYPE_CHECKER = copy(Option.TYPE_CHECKER) 
    TYPE_CHECKER["date"] = check_date

def usage():
    msg = """
    Usage: 

        Hi. this is a test.
    """
    return msg
def parse_args():
    from optparse import OptionParser
    parser = OptionParser(usage=usage(), option_class=DateOption)
    parser.add_option("-v", "--verbose", dest="verbose", 
                       default=False, 
                       action="store_true", 
                       help="Verbose mode: print extra details.")
    parser.add_option("", "--hostname", dest="hostname", 
                       default=None, 
                       help="hostname for downtime.")
    parser.add_option("", "--comment", dest="comment", 
                       default="Downtime scheduled with %s." % sys.argv[0], 
                       help="Add a comment to event.")
    parser.add_option("", "--service", dest="servicename", 
                       default=None, 
                       help="service name for downtime (also requires hostname)")
    parser.add_option("", "--type", dest="type", 
                       default="host", 
                       help="Types of downtime: host, service, hostservices")
    parser.add_option("", "--start", dest="start_time", 
                       type="date", 
                       default=datetime.now(), 
                       help="Begin downtime at 'start' (format: YYYYMMDD[-HH:MM]).")
    parser.add_option("", "--end", dest="end_time", 
                       type="date", 
                       default=datetime.now()+timedelta(1), 
                       help="End downtime at 'end'.")
 
    (options, args) = parser.parse_args()

    if len(sys.argv) == 1 or options.hostname is None: 
        parser.print_help()
        sys.exit(1)

    return (options, args)


def main():
    (opt, args) = parse_args()

    # defaults
    ret = STATE_UNKNOWN
    timeout_error = 0
    exception_error = 0

    try:
        (ret,msg) = custom_command(opt, args)
        if ret not in state_list:
            raise Exception("Returned wrong state type from custom_command(): should be one of %s" % state_list)

    except KeyboardInterrupt:
        sys.exit(STATE_UNKNOWN)
    except Exception, err:
        exception_error = 1
        import traceback
        # this shouldn't happen, so more details won't hurt.
        traceback.print_exc()
        sys.exit(1)

    sys.exit(ret)

if __name__ == "__main__":
    main()

