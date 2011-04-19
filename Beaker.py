from statlib import stats
import sqlite3
import sys

# ---- FUNCTIONS ----
def getMedian(numericValues):
    theValues = sorted(numericValues)

    if len(theValues) % 2 == 1:
        return theValues[(len(theValues)+1)/2-1]
    else:
        lower = theValues[len(theValues)/2-1]
        upper = theValues[len(theValues)/2]

    return (float(lower + upper)) / 2  

# ---- INIT ----
sometestid = str(sys.argv[1:][0])
dbconn = sqlite3.connect('resultdb.sqlite')
dbconn.row_factory = sqlite3.Row
c = dbconn.cursor()

# ---- MAIN ----
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
for row in c.execute(myquery):
    for key in floats:
#        mydict[key].append(float(row[key]))
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
