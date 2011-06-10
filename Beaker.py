from statlib import stats
import sqlite3
import sys
import getopt
import csv


#TODO Add export to CSV functionality

# ---- FUNCTIONS ----
def getMedian(numericValues):
    theValues = sorted(numericValues)

    if len(theValues) % 2 == 1:
        return theValues[(len(theValues)+1)/2-1]
    else:
        lower = theValues[len(theValues)/2-1]
        upper = theValues[len(theValues)/2]

    return (float(lower + upper)) / 2  

def getSQLiteConn():
    global c
    dbconn = sqlite3.connect(sqlitefile)
    dbconn.row_factory = sqlite3.Row
    c = dbconn.cursor()
    return

def usage():
    print """ Usage: python26 Beaker.py [OPTION]... [test id selector]

    -h, --help
            This message (Usage)

    -f sqlitedb, --db=sqlitedb
            Parse [sqlitedb].  If none given, the default sqlitedb file name is './resultdb.sqlite'

    -e outputCSVFile, --csv=outputCSVFile
            Export siege results to CSV file.  Can be optionally used with a test ID selector to only export a subset of the results.

    "test id selector" should be a test id pattern to match against; 'apache-' would match 'apache-1' through 'apache-9999' and also 
'apache-vs-something-1

    If no test id selector is given, a list of all test IDs in the SQLite database will be shown.
    """
    sys.exit(0)
    return

def writecsv(outputFile, testIDSelector):
    """
    Exports the raw siege result data from the sqlite database to CSV format where test IDs match the testIDSelector
    Required:
      -CSV output file name as outputFile(string)
      -test ID to glob on as testIDSelector(string)
    """

    print "Exporting raw siege test results to", outputFile, "using test ID selector", testIDSelector
    getSQLiteConn()
    writer = csv.writer(open(outputFile, 'wb'))
    headers = ('test_id', 'date', 'hits', 'up', 'time', 'data', 'resptime', 'trans', 'bw', 'concur', 'ok', 'fail', 'long', 'short')
    writer.writerow(headers)
    exportquery = 'SELECT test_id, date, hits, up, time, data, resptime, trans, bw, concur, ok, fail, long, short FROM siege WHERE test_id LIKE \'' + str(testIDSelector) + '%\''
    for row in c.execute(exportquery):
        thisrow = list(row)
        writer.writerow(thisrow)
    print "Done exporting to", outputFile
    print "Please see http://www.sqlite.org/sqlite.html for more data export options via SQLite directly"
    return

def ensureValidTestID():
    """
    Ensures that a valid Test ID Selector is supplied.

    Inputs: none (implied: last element of sys.argv)
    Returns: none (implied: testIDSelector)
    Side Effects: global testIDSelector gets set to a valid Test ID Selector
    """

    global sometestid
    try:
        sometestid = str(sys.argv[-1])
    except NameError:
        sometestid = None
    if sometestid in (sqlitefile, csvfilename, None):
        #usage()
        sometestid= '%'
    return

def main(argv):
    global sqlitefile
    global csvfilename
    csvfilename = None # need to set this to some sane default because ensureValidTestID() won't work without it
    try:
        sqlitefile = 'resultdb.sqlite'
        opts, args = getopt.getopt(argv, 'hf:e:', ['help', 'db=', 'csv='])
    except getopt.GetoptError:
        usage()
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage()
        elif opt in ('-f', '--db='):
            sqlitefile = arg
            ensureValidTestID()
        elif opt in ('-e','--csv='):
            csvfilename = arg
            ensureValidTestID()
            writecsv(csvfilename, sometestid)
            sys.exit(0)
# ---- INIT ----
#    dbconn = sqlite3.connect(sqlitefile)
#    dbconn.row_factory = sqlite3.Row
#    c = dbconn.cursor()
    getSQLiteConn()
    myquery = 'SELECT test_id, date, hits, up, time, data, resptime, trans, bw, concur, ok, fail, long, short FROM siege WHERE test_id LIKE \'' + str(sometestid) + '%\''

    #todo = ['hits', 'up', 'time', 'data', 'resptime', 'trans', 'bw', 'concur', 'ok', 'fail', 'long', 'short']
    floats = ['up', 'time', 'data', 'resptime', 'trans', 'bw', 'concur', 'long', 'short']
    ints = ['hits', 'ok', 'fail']
    # todo is a dict with each key as the col name and each val as a list containing all the vals

    """
    Siege example return and var types
    (u'mysql-1-1', u'1303101006.08', u'6830', u'85.88', u'352.12', u'48.83', u'5.05', u'19.40', u'0.14', u'97.88', u'6840', u'1123', u'15.41', u'0.56')
    str(test_id)
    int(date)
    int(hits)
    float(up)
    float(time)
    float(data)
    float(resptime)
    float(trans)
    float(bw)
    float(concur)
    int(ok)
    int(fail)
    float(long)
    float(short)
    """

    mydict = {}

    # create empty lists
    for i in floats + ints:
        mydict[i] = []
    # we can now just map keys in our dict to results in the DB query since the names are 1:1

    data = c.execute(myquery)
    numrows = c.fetchone()
    if numrows is None:
        print "No tests found when using test ID selector:", sometestid
        print "Displaying a list of test IDs in", sqlitefile
        for row in c.execute('select test_id from siege'):
            print row[0]
        print '(For help / usage info, see', sys.argv[0], '--help)'
        sys.exit(2)
    for row in data:
        for key in floats:
            mydict[key].append(float(row[key]))
        for key in ints:
            mydict[key].append(int(row[key]))

    meandict = {}
    mediandict = {}
    stdevdict = {}
    for key, val in mydict.iteritems():
        meandict[key] = stats.mean(val)
        stdevdict[key] = stats.stdev(val)
        mediandict[key] = getMedian(val)

    print 'Test ID selector: ' + sometestid
    print "Raw dump of dataset to parse: "
    print mydict
    print '\r\nMean: '
    print meandict

    print '\r\nMedian: '
    print mediandict

    print '\r\nStandard Deviation: '
    print stdevdict

    # select test_id, datetime(date, 'unixepoch') from siege where test_id = 'mysql-1-1';
    #print mydict['trans']
    # ---- MAIN ----
    return

if __name__ == "__main__":
    main(sys.argv[1:])
