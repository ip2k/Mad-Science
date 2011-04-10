import pexpect
import paramiko
import sqlite3
import time

def runCommands(*someCommands):
    global testid
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('127.0.0.1', username='root', password='some-password-CHANGEME')
    for i in someCommands:
        ssh.exec_command(i)
        logCustom('SSH COMMAND SENT', i)
    return

def doReset():
    global testid
    runCommands('/etc/init.d/mysqld restart', \
        '/etc/init.d/httpd restart', \
        'do-something-else-CHANGEME')
    return

def logResult(*stuff):
    global testid
    statustype = 'RESULT'
    thisdate = time.time()
    for i in stuff:
        db.execute('INSERT INTO results(test_id, date, status_type, data) VALUES(?,?,?,?)', (testid, thisdate, statustype, i))
    db.commit()
    return

def logEvent(eventdata):
    global testid
    statustype = 'EVENT'
    thisdate = time.time()
    db.execute('INSERT INTO results(test_id, date, status_type, data) VALUES(?,?,?,?)', (testid, thisdate, statustype, eventdata))
    db.commit()
    return

def logCustom(statustype, eventdata):
    global testid
    thisdate = time.time()
    db.execute('INSERT INTO results(test_id, date, status_type, data) VALUES(?,?,?,?)', (testid, thisdate, statustype, eventdata))
    db.commit()
    return

def runSiege(threads, reps, urlsfile):
    tolog = 'threads: ' + threads + ' reps: ' + reps + ' urlsfile: ' + urlsfile
    logCustom('runSiege CALLED', tolog)
    runstring = 'siege -i -b -c ' + threads + ' -r ' + reps + ' -f ' + urlsfile
    child = pexpect.spawn (runstring)
    child.expect ('^done.')
    print child.before

# ---- INIT ----
testid = "INIT"
db = sqlite3.connect('resultdb.sqlite')
c = db.cursor()
db.execute("CREATE TABLE IF NOT EXISTS results(test_id text, date text, status_type text, data text)")
db.commit()

# ---- MAIN ----
doReset()

# ---- TESTS ----
testid = 'testbench1'
doReset()
runCommands('w', 'uptime', 'touch test2', 'touch test3', 'make-some-config-change')
runSiege('50', '10', 'urls.txt')

testid = 'testbench2'
doReset()
runCommands('make-some-other-config-change')
runSiege('50', '10', 'urls.txt')
