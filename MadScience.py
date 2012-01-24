import warnings
from termcolor import colored
import pexpect
import sqlite3
import time
import string
import re
import urllib2

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import paramiko

# ---- CONSTANTS ----
const_debug = False
const_sshhost= '10.0.0.1'
const_sshuser= 'root'
const_sshpass= 'some-secure-password'
const_prompt = '[root@server ~]# '
const_httpcheckurl = 'http://10.0.0.1/apparel.html'
const_mysqlhost = '10.0.0.1'
const_mysqluser = 'test'
const_mysqlpass = 'test'
const_mysqldbname = 'test'
const_lswstestcmd = 'pgrep litespeed'
const_apachetestcmd = 'pgrep -u apache httpd'
# TODO: add abstractions for apache user, suexec user, path to html files


## {{{ http://code.activestate.com/recipes/576925/ (r4)
import inspect

def callee():
    return inspect.getouterframes(inspect.currentframe())[1][1:4]

def caller():
    return inspect.getouterframes(inspect.currentframe())[2][1:4]
        ## end of http://code.activestate.com/recipes/576925/ }}}


# ---- FUNCTIONS ----
def logEvent(eventdata):
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    global testid
    statustype = 'Event'
    thisdate = time.time()
    db.execute('INSERT INTO log(test_id, date, status_type, data) VALUES(?,?,?,?)', (testid, thisdate, statustype, eventdata))
    db.commit()
    print colored(str(statustype) + ' ' + str(eventdata) + ' TEST ID: ' + str(testid) + ' TIME: ' + str(thisdate), 'magenta')
    return

def logSSH(eventdata):
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    global testid
    statustype = 'SSH'
    thisdate = time.time()
    db.execute('INSERT INTO log(test_id, date, status_type, data) VALUES(?,?,?,?)', (testid, thisdate, statustype, eventdata))
    db.commit()
    print colored(str(statustype) + ' ' + str(eventdata) + ' TEST ID: ' + str(testid) + ' TIME: ' + str(thisdate), 'blue')
    return

def logError(eventdata):
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    global testid
    statustype = 'Error'
    thisdate = time.time()
    db.execute('INSERT INTO log(test_id, date, status_type, data) VALUES(?,?,?,?)', (testid, thisdate, statustype, eventdata))
    db.commit()
    print colored(str(statustype) + ' ' + str(eventdata) + ' TEST ID: ' + str(testid) + ' TIME: ' + str(thisdate), 'red')
    return

def logOk(eventdata):
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    global testid
    statustype = 'Success'
    thisdate = time.time()
    db.execute('INSERT INTO log(test_id, date, status_type, data) VALUES(?,?,?,?)', (testid, thisdate, statustype, eventdata))
    db.commit()
    print colored(str(statustype) + ' ' + str(eventdata) + ' TEST ID: ' + str(testid) + ' TIME: ' + str(thisdate), 'green')
    return

def logCustom(statustype, eventdata):
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    global testid
    thisdate = time.time()
    db.execute('INSERT INTO log(test_id, date, status_type, data) VALUES(?,?,?,?)', (testid, thisdate, statustype, eventdata))
    db.commit()
    print colored(str(statustype) + ' ' + str(eventdata) + ' TEST ID: ' + str(testid) + ' TIME: ' + str(thisdate), 'cyan')
    return

def wait(secs):
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    logEvent('Sleeping for ' + str(secs) + ' seconds')
    time.sleep(secs)
    return

def initSSH():
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    global ssh, chan, const_sshhost, const_sshuser, const_sshpass
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(const_sshhost, username= const_sshuser, password= const_sshpass)
    chan = ssh.invoke_shell()
    if chan:
        return ssh,chan

def runCommands(*somecommands):
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    global ssh
    initSSH()
    if ssh:
        for i in somecommands:
            chan.send(i)
            chan.send('\n')
            logSSH(str(i))
        ssh.close()
    return

def runBlockingCommands(*somecommands):
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    global ssh
    initSSH()
    if ssh:
        for i in somecommands:
            buff = ''
            chan.send(i)
            chan.send('\n')
            logSSH('Sent blocking command: ' + i)
            while not buff.endswith(const_prompt):
                resp = chan.recv(9999)
                buff += resp
            logSSH('Got response from blocking command: ' + str(i))
    return

def runCommandGetExit(somecommand):
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    global ssh
    logSSH('Running command and getting exit status: ' + str(somecommand))
    initSSH()
    if ssh:
        mychan = ssh.get_transport().open_session()
        mychan.exec_command(somecommand)
        return mychan.recv_exit_status()
"""
def doReset():
    runBlockingCommands('(/etc/init.d/mysqld stop; sleep 10; killall mysqld; sleep 10; killall -9 mysqld; sleep 10; /etc/init.d/mysqld restart)', \
        '(/etc/init.d/httpd stop; sleep 10; killall httpd; sleep 10; killall -9 httpd; sleep 10; /etc/init.d/httpd restart)', \
        '/usr/nexkit/bin/magento r -cs /home/sipfourb/sip4-bench1.nexcess.net/html', \
        '/etc/init.d/memcached-multi restart')
    wait(30)
    verifyHttp()
    return
"""

def doReset():
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    runBlockingCommands('/etc/init.d/mysqld restart', '/etc/init.d/httpd restart', '/etc/init.d/memcached-multi restart')
    wait(10)
    fixMagento()
    verifyMysql()
    verifyHttp()
    wait (30)
    return

def fixMagento():
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    global currentwebserver
    logEvent('Fixing Magento permissions, cache, and sessions')
    runBlockingCommands('/usr/nexkit/bin/magento r -cops /home/sipfourb/sip4-bench1.nexcess.net/html')
    if currentwebserver == 'lsws':
        runBlockingCommands('chown -R sipfourb.sipfourb /home/sipfourb/sip4-bench1.nexcess.net/html')
    if currentwebserver == 'apache':
        runBlockingCommands('chown -R apache.apache /home/sipfourb/sip4-bench1.nexcess.net/html')
    return

def replaceInConfig(search, replace, file):
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    global ssh
    initSSH()
    if ssh:
        sedstring = """sed -i 's/^.*%s.*$/%s/' %s""" % (search, replace, file)
        ssh.exec_command(sedstring)
        time.sleep(2)
        logCustom('sed command sent', 'Replace: ' + str(search) + ' With: ' + str(replace) + ' In File: ' + str(file))
        ssh.close()
    return

def setWebServer(webserver):
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    global currentwebserver
    if webserver:
        currentwebserver = webserver
        logCustom('Switching to different webserver', currentwebserver)
        if currentwebserver == 'lsws':
            runBlockingCommands('/etc/init.d/httpd.old stop', 'rm -rf /etc/init.d/httpd', 'ln -s /etc/init.d/lsws /etc/init.d/httpd', '/etc/init.d/lsws start')
            ensureLsws()
        if currentwebserver == 'apache':
            runBlockingCommands('/etc/init.d/lsws stop', 'rm -rf /etc/init.d/httpd', 'ln -s /etc/init.d/httpd.old /etc/init.d/httpd', '/etc/init.d/httpd.old start')
            ensureApache()
    return

def setOpcodeCache(cache):
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    if cache:
        logEvent('Switching to PHP opcode cache: ' + cache)
        if cache == 'apc':
            runBlockingCommands('rm -rf /etc/php.d/eaccelerator.ini', 'yum -y remove php-eaccelerator', 'yum -y install php-pecl-apc', '/etc/init.d/httpd restart')
            verifyHttp()
        if cache == 'eaccelerator':
            runBlockingCommands('rm -rf /etc/php.d/apc.ini', 'yum -y remove php-pecl-apc', 'yum -y install php-eaccelerator', '/etc/init.d/httpd restart')
            verifyHttp()
    return

#const_lswstestcmd = 'pgrep litespeed'
#const_apachetestcmd = 'pgrep -u apache httpd'
def ensureApache():
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    global currentwebserver, const_lswstestcmd, const_apachetestcmd
    currentwebserver = 'apache'
    logEvent('Ensuring that Litespeed is not running...')
    runBlockingCommands('killall -9 litespeed')
    myexit = runCommandGetExit(const_lswstestcmd)
    while myexit == 0:
        runBlockingCommands('killall -9 litespeed', 'sleep 5', 'killall -9 httpd', 'sleep 5', '/etc/init.d/httpd.old restart', 'sleep 5')
        myexit = runCommandGetExit(const_lswstestcmd)
    logEvent('Ensuring that Apache is running...')
    runBlockingCommands('killall -9 httpd', '/etc/init.d/httpd.old restart', 'sleep 5')
    myexit = runCommandGetExit(const_apachetestcmd)
    while myexit == 1:
        runBlockingCommands('killall -9 httpd', 'sleep 5', '/etc/init.d/httpd.old restart', 'sleep 5')
        myexit = runCommandGetExit(const_apachetestcmd)
    verifyHttp()
    return

def ensureLsws():
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    global currentwebserver, const_lswstestcmd, const_apachetestcmd
    currentwebserver = 'lsws'
    logEvent('Ensuring that Apache is not running...')
    runBlockingCommands('/etc/init.d/httpd.old stop')
    # make sure that apache is NOT running first
    # pgrep will return 0 if apache is still running, so in that case we need to re-try killing it
    myexit = runCommandGetExit(const_apachetestcmd)
    while myexit == 0:
        runBlockingCommands('killall -9 httpd', 'sleep 5', 'killall -9 litespeed', 'sleep 5', '/etc/init.d/lsws restart', 'sleep 5')
        myexit = runCommandGetExit(const_apachetestcmd)
    # now make sure that litespeed IS running.
    logEvent('Ensuring that Litespeed is running...')
    runBlockingCommands('killall -9 litespeed', '/etc/init.d/lsws restart', 'sleep 5')
    myexit = runCommandGetExit(const_lswstestcmd)
    # pgrep litespeed will return 0 (status OK, so pgrep DID find one or more litespeed processes) once apache has started
    # litespeed stupidly starts a process owned by root called 'httpd (lscgid)' so we have to limit pgrep by user = apache
    while myexit == 1:
        # while pgrep returns an error finding apache-owned httpd processes (so while apache is NOT running)
        runBlockingCommands('killall -9 litespeed', 'sleep 5', '/etc/init.d/lsws restart', 'sleep 5')
        myexit = runCommandGetExit(const_lswstestcmd)
    verifyHttp()
    return

def verifyHttp():
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    global currentwebserver, const_httpcheckurl
    logEvent('Verifying valid HTTP response')
    wait(5)
    try:
        myresp = urllib2.urlopen(const_httpcheckurl, timeout=30)
    except (urllib2.URLError, urllib2.HTTPError), e:
        print e
        logError(currentwebserver + ' down, will attempt recover. Got no HTTP response code at URL: ' + const_httpcheckurl)
        verifyMemcached()
        fixMagento()
        wait(5)
        setWebServer(currentwebserver)
        return
    validhttpresponsecodes = [100, 101, 200, 201, 202, 203, 204, 205, 206, 300, 301, 302, 303, 304, 305, 306, 307]
    if myresp.getcode():
        respcode = myresp.getcode()
        if not respcode in validhttpresponsecodes:
            logError(currentwebserver + ' down, will attempt recover. HTTP response code: ' + str(respcode) + ' at URL: ' + const_httpcheckurl)
            verifyMemcached()
            fixMagento()
            wait(5)
            setWebServer(currentwebserver)
        elif respcode in validhttpresponsecodes:
            logOk('Got valid HTTP response! HTTP Response code: ' + str(respcode) + ' at URL: ' + const_httpcheckurl)
    return

def verifyMysql():
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    global const_mysqluser, const_mysqlpass
    logEvent('Verifying that MySQL is up and connectable locally on remote host')
    testcmd = 'mysql -u%s -p%s -e "show databases"' % (const_mysqluser, const_mysqlpass)
    myexit = runCommandGetExit(testcmd)
    while myexit > 0:
        # TODO: add better self-healing for when mysqld is down
        logError('MySQL is not connectable on remote host!  Attempting to restart it...')
        runBlockingCommands('/etc/init.d/mysqld stop', 'sleep 5', 'killall mysqld', 'sleep 5', 'killall -9 mysqld', 'sleep 5', '/etc/init.d/mysqld restart', 'sleep 5')
        myexit = runCommandGetExit(testcmd)
    logOk('Successfully verified that MySQL is up and connectable locally on remote host')
    return

def verifyMemcached():
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    logEvent('Verifying that memcached is up on the remote host')
    testcmd = 'netstat -lnp |grep memcache |grep LISTEN'
    myexit = runCommandGetExit(testcmd)
    while myexit > 0:
        # TODO: add better self-healing for when memcached is down (check if sock / IP conn, check permissions, try to connecting using netcat)
        logError('Memcached is not listening on the remote host!  Attempting to restart it...')
        runBlockingCommands('/etc/init.d/memcached-multi stop', '/etc/init.d/memcached stop', 'sleep 5', 'killall memcached', 'sleep 5', 'killall -9 memcached', 'sleep 5', '/etc/init.d/memcached-multi start', '/etc/init.d/memcached start', 'sleep 5')
        myexit = runCommandGetExit(testcmd)
    logOk('Successfully verified that memcached is listening on remote host')
    return

def runSiege(threads, reps, urlsfile):
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    global testid
    tolog = 'threads: ' + threads + ' reps: ' + reps + ' urlsfile: ' + urlsfile
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
        #print str(child)
        logError('Siege exited with error! ' + tolog)
        pass
    else:
        logOk('Siege finished without errors ' + tolog)

    return
"""
const_mysqlhost = '10.0.0.1'
const_mysqluser = 'test'
const_mysqlpass = 'test'
const_mysqldbname = 'test'
"""

def runSysbench(threads, requests, tablesize):
    if const_debug:
        print "Function %s called from function %s" % (callee(), caller())

    if threads and requests and tablesize:
        global testid, const_mysqlhost, const_mysqluser, const_mysqlpass, const_mysqldbname
        tolog = 'threads: ' + threads + ' requests: ' + requests + ' tablesize: ' + tablesize
        mycmd = 'sysbench --num-threads=' + str(threads) + ' --max-requests=' + str(requests) + ' --test=oltp --mysql-table-engine=innodb --oltp-test-mode=complex --oltp-table-size=' + str(tablesize) + ' --db-driver=mysql --mysql-user=' + str(const_mysqluser) + ' --mysql-password=' + str(const_mysqlpass) + '--mysql-db=' + str(const_mysqldbname) + ' --mysql-host=' + str(const_mysqlhost)
        print mycmd
        return
"""
try:
            child = pexpect.spawn(mycmd + ' prepare')
            child.expect('')
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
            #print str(child)
            logError('Sysbench exited with error! ' + tolog)
            pass
        else:
            logOk('Sysbench finished without errors ' + tolog)
"""

# ---- INIT ----
testid = "INIT"
currentwebserver = "apache"
db = sqlite3.connect('resultdb.sqlite')
c = db.cursor()
db.execute("CREATE TABLE IF NOT EXISTS log(test_id text, date text, status_type text, data text)")
db.execute("CREATE TABLE IF NOT EXISTS siege(test_id text, date text, hits text, up text, time text, data text, resptime text, trans text, bw text, concur text, ok text, fail text, long text, short text)")
db.commit()

# ---- MAIN ----

# ---- TESTS ----
#setWebServer('apache')
#doReset()
#testid = 'testbench1'
#runCommands('w', 'uptime', 'touch test2', 'touch test3')
#runSiege('100', '100', 'urls-local.txt')
#doReset()


# ---- ea vs apc on apache and lsws ----

setWebServer('lsws')
setOpcodeCache('apc')

for i in range(1, 11):
    testid = 'lsws-411-50-' + str(i)
    doReset()
    runSiege('50', '100', 'urls-local.txt')

for i in range(1, 11):
    testid = 'lsws-411-100-' + str(i)
    doReset()
    runSiege('100', '100', 'urls-local.txt')


print "Reached end!"
