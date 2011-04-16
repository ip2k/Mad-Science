import warnings
import pexpect
import sqlite3
import time
import string
import re

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import paramiko

#---- CONSTANTS ----
const_sshhost= '127.0.0.1'
const_sshuser= 'root'
const_sshpass= 'someVerySecurePassword'
const_prompt = '[root@sip4-bench1 ~]# '

def wait(secs):
    logEvent('Sleeping for ' + str(secs) + ' seconds')
    time.sleep(secs)
    return

def initSSH():
    global ssh, chan, const_sshhost, const_sshuser, const_sshpass
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(const_sshhost, username= const_sshuser, password= const_sshpass)
    chan = ssh.invoke_shell()
    return ssh,chan

def runCommands(*someCommands):
    global testid, ssh
    initSSH()
    if ssh:
        for i in someCommands:
            chan.send(i)
            chan.send('\n')
            logCustom('SSH command sent', i)
        ssh.close()
    return

def runBlockingCommands(*someCommands):
    global testid, ssh
    initSSH()
    if ssh:
        for i in someCommands:
            buff = ''
            chan.send(i)
            chan.send('\n')
            logCustom('SSH blocking command sent', i)
            while not buff.endswith(const_prompt):
                resp = chan.recv(9999)
                buff += resp
            logCustom('SSH blocking response received', i)
    return

def doReset():
    global testid
    runBlockingCommands('/etc/init.d/mysqld restart', \
        '/etc/init.d/httpd restart', \
        '/usr/nexkit/bin/magento r -cs /home/sipfourb/sip4-bench1.nexcess.net/html', \
        '/etc/init.d/memcached-multi restart')
    wait(120)
    return

def replaceInConfig(search, replace, file):
    global testid, ssh
    initSSH()
    if ssh:
        sedstring = """sed -i 's/^.*%s.*$/%s/' %s""" % (search, replace, file)
        print sedstring
        initSSH()
        ssh.exec_command(sedstring)
        time.sleep(2)
        logCustom('sed command sent', 'Replace: ' + str(search) + ' With: ' + str(replace) + ' In File: ' + str(file))
        ssh.close()

def logEvent(eventdata):
    global testid
    statustype = 'Event'
    thisdate = time.time()
    db.execute('INSERT INTO log(test_id, date, status_type, data) VALUES(?,?,?,?)', (testid, thisdate, statustype, eventdata))
    db.commit()
    print(str(statustype) + ' ' + str(eventdata) + ' TEST ID: ' + str(testid) + ' TIME: ' + str(thisdate))
    return

def logError(eventdata):
    global testid
    statustype = 'Error'
    thisdate = time.time()
    db.execute('INSERT INTO log(test_id, date, status_type, data) VALUES(?,?,?,?)', (testid, thisdate, statustype, eventdata))
    db.commit()
    print(str(statustype) + ' ' + str(eventdata) + ' TEST ID: ' + str(testid) + ' TIME: ' + str(thisdate))
    return

def logCustom(statustype, eventdata):
    global testid
    thisdate = time.time()
    db.execute('INSERT INTO log(test_id, date, status_type, data) VALUES(?,?,?,?)', (testid, thisdate, statustype, eventdata))
    db.commit()
    print(str(statustype) + ' ' + str(eventdata) + ' TEST ID: ' + str(testid) + ' TIME: ' + str(thisdate))
    return

def runSiege(threads, reps, urlsfile):
    global testid
    tolog = 'threads: ' + threads + ' reps: ' + reps + ' urlsfile: ' + urlsfile
    logEvent('runSiege called')
    runstring = 'siege -i -b -c ' + threads + ' -r ' + reps + ' -f ' + urlsfile

    try:
        child = pexpect.spawn (runstring)
        fout = file('siege.log' , 'w')
        child.logfile = fout
        logCustom('Siege started', tolog)

        #child.expect('done.')
        child.expect('(?P<hits>[0-9]+)\shits.*' +
        'Availability:\s+(?P<up>[0-9]+\.[0-9]{2})\s%.*' +
        'Elapsed\stime:\s+(?P<time>[0-9]+\.[0-9]+)\ssecs.*' +
        'Data transferred:\s+(?P<data>[0-9]+\.[0-9]+)\sMB.*' +
        'Response time:\s+(?P<resptime>[0-9]+\.[0-9]+)\ssecs.*' +
        'Transaction rate:\s+(?P<trans>[0-9]+\.[0-9]+)\strans/sec.*' +
        'Throughput:\s+(?P<bw>[0-9]+\.[0-9]+)\sMB/sec.*' +
        'Concurrency:\s+(?P<concur>[0-9]+\.[0-9]+).*' +
        'Successful transactions:\s+(?P<ok>[0-9]+).*' +
        'Failed transactions:\s+(?P<fail>[0-9]+).*' +
        'Longest transaction:\s+(?P<long>[0-9]+\.[0-9]+).*' +
        'Shortest transaction:\s+(?P<short>[0-9]+\.[0-9]+)', timeout=None)

        resultsdict = child.match.groupdict()
        resultsdict['thetime'] = time.time()
        resultsdict['testid'] = testid
        todo = 'INSERT INTO siege VALUES(\'%(testid)s\', \'%(thetime)s\', \'%(hits)s\', \'%(up)s\', \'%(time)s\', \'%(data)s\', \'%(resptime)s\', \'%(trans)s\', \'%(bw)s\', \'%(concur)s\', \'%(ok)s\', \'%(fail)s\', \'%(long)s\', \'%(short)s\' )' % resultsdict
        print('Siege returned result! TEST ID: ' + str(resultsdict['testid']) + ' TIME: ' + str(resultsdict['thetime']))
        print resultsdict
        db.execute(todo)
        db.commit()

    except Exception as inst:
        print type(inst)
        print inst.args
        print inst
        print str(child)
        logCustom('SIEGE EXITED WITH ERROR', tolog)
        pass
    else:
        logCustom('Siege finished without errors', tolog)

    return


# ---- INIT ----
testid = "INIT"
db = sqlite3.connect('resultdb.sqlite')
c = db.cursor()
db.execute("CREATE TABLE IF NOT EXISTS log(test_id text, date text, status_type text, data text)")
db.execute("CREATE TABLE IF NOT EXISTS siege(test_id text, date text, hits text, up text, time text, data text, resptime text, trans text, bw text, concur text, ok text, fail text, long text, short text)")
db.commit()

# ---- MAIN ----

# ---- TESTS ----
#doReset()
#testid = 'testbench1'
#runCommands('w', 'uptime', 'touch test2', 'touch test3')
#runSiege('100', '100', 'urls-bench1.txt')
#doReset()

# test where id is mysql-[threads]-[test iter]
# runs ten tests for each iter
for i in range(1, 21):
    #tosed = 'thread_concurrency = %s' % (i)
    replaceInConfig('thread_concurrency', 'thread_concurrency = %i' % (i), '/etc/my.cnf')
    wait(5)
    for x in range(1,11):
        testid = 'mysql-' + str(i) + '-' + str(x)
        doReset()
        runSiege('100','100','urls-local.txt')


#testid = 'testbench2'
#runCommands('w', 'uptime', 'touch test2', 'touch test3')
#runSiege('10', '5', 'urls.txt')
#doReset()
#print 'Reached End!'
