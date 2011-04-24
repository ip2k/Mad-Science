import warnings

import pexpect
import sqlite3
import time
import string
import re
import urllib

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import paramiko

# ---- CONSTANTS ----
const_sshhost= '127.0.0.1'
const_sshuser= 'root'
const_sshpass= 'YOUR-ROOT-PASSWORD'
const_prompt = '[root@sip4-bench1 ~]# '
const_httpcheckurl = 'http://127.0.0.1'

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

def runCommands(*somecommands):
    global ssh
    initSSH()
    if ssh:
        for i in somecommands:
            chan.send(i)
            chan.send('\n')
            logCustom('SSH command sent', i)
        ssh.close()
    return

def runBlockingCommands(*somecommands):
    global ssh
    initSSH()
    if ssh:
        for i in somecommands:
            buff = ''
            chan.send(i)
            chan.send('\n')
            logCustom('SSH blocking command sent', i)
            while not buff.endswith(const_prompt):
                resp = chan.recv(9999)
                buff += resp
            logCustom('SSH blocking response received', i)
    return

def runCommandGetExit(somecommand):
    global ssh
    logEvent('runCommandGetExit called')
    initSSH()
    if ssh:
        mychan = ssh.get_transport().open_session()
        mychan.exec_command(somecommand)
        return mychan.recv_exit_status()

def doReset():
    runBlockingCommands('(/etc/init.d/mysqld stop; sleep 10; killall mysqld; sleep 10; killall -9 mysqld; sleep 10; /etc/init.d/mysqld restart)', \
        '(/etc/init.d/httpd stop; sleep 10; killall httpd; sleep 10; killall -9 httpd; sleep 10; /etc/init.d/httpd restart)', \
        '/usr/nexkit/bin/magento r -cs /home/sipfourb/sip4-bench1.nexcess.net/html', \
        '/etc/init.d/memcached-multi restart')
    wait(30)
    return

def replaceInConfig(search, replace, file):
    global ssh
    initSSH()
    if ssh:
        sedstring = """sed -i 's/^.*%s.*$/%s/' %s""" % (search, replace, file)
        ssh.exec_command(sedstring)
        time.sleep(2)
        logCustom('sed command sent', 'Replace: ' + str(search) + ' With: ' + str(replace) + ' In File: ' + str(file))
        ssh.close()
    return

def ensureApache():
    global currentwebserver
    currentwebserver = 'apache'
    logEvent('Ensuring that Litespeed is not running...')
    # make sure that litespeed is NOT running first
    # pgrep will return 0 if litespeed is still running, so in that case we need to re-try killing it
    myexit = runCommandGetExit('pgrep litespeed')
    while myexit == 0:
        runBlockingCommands('killall -9 litespeed', 'sleep 5', 'killall -9 httpd', 'sleep 5', '/etc/init.d/httpd.old restart', 'sleep 5')
        myexit = runCommandGetExit('pgrep litespeed')
    # now make sure that apache IS running.
    logEvent('Ensuring that Apache is running...')
    myexit = runCommandGetExit('pgrep -u apache httpd')
    # pgrep httpd will return 0 (status OK, so pgrep DID find one or more httpd processes) once apache has started
    # litespeed stupidly starts a process owned by root called 'httpd (lscgid)' so we have to limit pgrep by user = apache
    while myexit == 1:
        # while pgrep returns an error finding apache-owned httpd processes (so while apache is NOT running)
        runBlockingCommands('killall -9 httpd', 'sleep 5', '/etc/init.d/httpd.old restart', 'sleep 5')
        myexit = runCommandGetExit('pgrep -u apache httpd')
    verifyHttp()
    return

def ensureLsws():
    global currentwebserver
    currentwebserver = 'lsws'
    logEvent('Ensuring that Apache is not running...')
    # make sure that apache is NOT running first
    # pgrep will return 0 if apache is still running, so in that case we need to re-try killing it
    myexit = runCommandGetExit('pgrep -u apache httpd')
    while myexit == 0:
        runBlockingCommands('killall -9 httpd', 'sleep 5', 'killall -9 litespeed', 'sleep 5', '/etc/init.d/lsws restart', 'sleep 5')
        myexit = runCommandGetExit('pgrep -u apache httpd')
    # now make sure that apache IS running.
    logEvent('Ensuring that Litespeed is running...')
    myexit = runCommandGetExit('pgrep litespeed')
    # pgrep litespeed will return 0 (status OK, so pgrep DID find one or more litespeed processes) once apache has started
    # litespeed stupidly starts a process owned by root called 'httpd (lscgid)' so we have to limit pgrep by user = apache
    while myexit == 1:
        # while pgrep returns an error finding apache-owned httpd processes (so while apache is NOT running)
        runBlockingCommands('killall -9 litespeed', 'sleep 5', '/etc/init.d/lsws restart', 'sleep 5')
        myexit = runCommandGetExit('pgrep litespeed')
    verifyHttp()
    return

def verifyHttp():
    global currentwebserver
    logEvent('Verifying valid HTTP response')
    myhttp = urllib.urlopen(const_httpcheckurl)
    validhttpresponsecodes = [100, 101, 200, 201, 202, 203, 204, 205, 206, 300, 301, 302, 303, 304, 305, 306, 307]
    if not myhttp.getcode() in validhttpresponsecodes:
        if currentwebserver == 'lsws':
            logEvent('Webserver down, trying to get litespeed back up...')
            ensureLsws()
        elif currentwebserver == 'apache':
            logEvent('Verifying valid HTTP response')
            ensureApache()
    return

def setWebServer(webserver):
    global currentwebserver
    if webserver:
        currentwebserver = webserver
        logEvent('Switching to web server: ' + currentwebserver)
        if currentwebserver == 'lsws':
            runBlockingCommands('/etc/init.d/httpd.old stop', 'rm -rf /etc/init.d/httpd', 'ln -s /etc/init.d/lsws /etc/init.d/httpd', '/etc/init.d/lsws start')
            ensureLsws()
        if currentwebserver == 'apache':
            runBlockingCommands('/etc/init.d/lsws stop', 'rm -rf /etc/init.d/httpd', 'ln -s /etc/init.d/httpd.old /etc/init.d/httpd', '/etc/init.d/httpd.old start')
            ensureApache()
    return

def setOpcodeCache(cache):
    if cache:
        logEvent('Switching to PHP opcode cache: ' + cache)
        if cache == 'apc':
            runBlockingCommands('rm -rf /etc/php.d/eaccelerator.ini', 'yum -y remove php-eaccelerator', 'yum -y install php-pecl-apc', '/etc/init.d/httpd restart')
        if cache == 'eaccelerator':
            runBlockingCommands('rm -rf /etc/php.d/apc.ini', 'yum -y remove php-pecl-apc', 'yum -y install php-eaccelerator', '/etc/init.d/httpd restart')
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
switchToWebServer('lsws')
setOpcodeCache('apc')
