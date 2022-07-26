#!/usr/bin/python3
import os
import sys
import subprocess

cf = '/etc/sysconfig/ovios.conf'

AUTO_RESTORE_H = """Run a restore at boot time from the last available osbackup. It will look at the system.backup.pool and if there is a 
pool defined there it will look at <pool>/osbackup. If this is empty it will try to mount it, if there is nothing 
inside that volume it will exit.
Otherwise the system options , users, network setting and anything else requested by the admin in the backup will 
will be restored.
If the option system.backup.pool is not set, it will lookt at a backup in /tmp.
If you want to keep /tmp as backup location make sure it is nto cleared during boot. Set:
options keep.tmp on """

## format of this Dictionary:
# human readable option : OS readable option (in ovios.conf) -> Definition -> default value -> is on/off only (true or false) 
options={
    'auto.restore': ['AUTO_RESTORE', AUTO_RESTORE_H, 'off', True],
    'nfs4.domain': [ 'NFS_DOMAIN', 'Set a domain name for NFSv4', None, False ] ,
    'smb.port': [ 'SMB_PORT', 'Specify custom ports for the SMB server to listen to. If multiple values, enter inside quotes.','', False],
    'ftp.enable': ['FTP_ENABLE','Enable or disable the FTP service start option during boot.','off', True],
    'nfs.disable.vers': ['NFS_NO_VERS','Disable specific NFS version(s). If multiple values, enter between quotes. EX: options nfs.disable.vers "2 4"',None, False],
    'exclude.pools': ['OVIOS_EXCLUDE_POOLS','Pools that should not be started or stopped by ovios. \nIntroduced for the docker image primarily. \
    Multiple pools can be specified \ninside quotes with space between. "pool1 pool2 pool3". To reset, run: options exclude.pools reset',None, False],
    'vbcheck.rootfs': ['VERBOSE_CHECK','If set to on the system will print verbose messages during root filesystem check at boot time','off', True],
    'force.import': ['IMPORT_FORCE','If set to on the system will attempt to force import the pools. Usefull after upgrades or during Live CD sessions.','off', True],
    'default.sync.files': ['SYNC_DEF_FILES','Default files that are included in the system backup','/etc/passwd /etc/group /etc/shadow /etc/samba/ /etc/krb5.conf /etc/hosts /etc/resolv.conf /etc/nsswitch.conf /etc/security/ /etc/pam.d/system-auth /etc/tgt/ /var/lib/samba/ /etc/sysconfig/ovios.conf', False],
    'nfs.sys.log': ['NFS_LOG_SYSLOG','If set to on NFS will log to sys.log instead of console logging','off',True ],
    'files.to.sync': ['SYNC_FILES','Files to sync to the rmeote backup server or locally to the backup pool',None, False],
    'netbios.enable': ['NETBIOS_ENABLED','Enable or disable NETBIOS to be started when the SMB server starts','off', True],
    'options.coloured': ['OPT_CLRS',"If set to on the options command's output will be colourized",'off', True],
    'fcheck.rootfs': ['FORCE_CHECK','If set to on the OS will force a root filesystem check during boot','off', True],
    'sendlogs.to': ['SENDLOGS_TO','	Specify one or more email addresses to send logs to. If multiple values, enter between quotes.',None, False],
    'skip.import': ['SKIP_IMPORT_POOLS','If set to off the system will import all storage pools during boot','on', True],
    'nis.client.enable': ['NIS_CLIENT_ENABLE','Enable or disable the NIS client start option during boot','off', True],
    'os.hostname': ['HOSTNAME','Set hostname. Similar to the "hostname" command from ovios-shell or the linux shell','ovios-indt', False],
    'netbios.debug.level': ['NETBIOS_DEBUG_LEVEL','Netbios debug level: integer between 0 (disabled) and 10','Disabled',False],
    'clock.utc': [ 'CLOCK_UTC','If set to on forces hardware clock to be set to UTC. Otherwise localtime is used.','off', True],
    'snmptrapd.enable': ['SNMPTRAPD_ENABLE','Enable or disable the SNMPTRAP service start option during boot.','off', True],
    'iscsi.debug': ['ISCSI_DEBUG','Enable iSCSI debugging','off', True],
    'smb.debug.level': ['SMB_DEBUG_LEVEL','SMB Server debug level: integer between 0 (disabled) and 10','Disabled', False],
    'nfs.idmap': ['NFS_IDMAP','Enable or disable the NFS idmap service when NFS starts','off', True],
    'smtp.starttls': ['SMTP_STARTTLS','Enable STARTTLS connection to the SMTP server if required','off', True],
    'ssh.sessions': ['SSH_MAXSESSIONS','Specify number of allowed SSH sessions over a single connection. Setting to 1 will disable multiplexing',None, False],
    'smb.enable': ['SMB_ENABLE','Enable or disable the SMB server start option during boot.','off', True],
    'nscd.enable': ['NSCD_ENABLE','	Enable or disable the NSCD service start option during boot.','off', True],
    'sendlogs.from': ['SENDLOGS_FROM','Specify a custom email address logs will be sent from','ovilogs@ovios.org', False],
    'autosync.cluster': ['HAC_AUTOSYNC','Enable or disable the cluster autosync feature. If set to on the system will autosync the config between all nodes in the cluster','off', True],
    'cluster.enable': ['HAC_ENABLED','Enable or disable the Cluster services start option during boot','off',True],
    'cron.enable': ['CRON_ENABLE', 'Enable or disable the cron service start option during boot.','on', True],
    'ssh.port': ['SSH_PORT','Specify a custom port for SSH to listen to','22', False],
    'ssh.timeout': ['SSH_TIMEOUT','Sets a timeout interval in seconds after which the system will send a message to request a response from the client.',None,False],
    'system.backup.pool': ['OS_BACKUP_POOL','Specify a pool which will be used to store system configuration backups',None, False],
    'arc.size': [ 'ARC_SIZE', 'The number in percentage ARC is supposed to use. Requires reboot.', '1/2 of Physical RAM', False],
    'nfs.debug': ['NFS_DEBUG','Enable NFS server debugging','off', True],
    'winbind.debug.level':['WINBINDD_DEBUG_LEVEL','Winbind debug level: integer between 1 (disabled) and 10','Disabled', False],
    'snmpd.enable': ['SNMPD_ENABLE','Enable or disable the SNMP service start option during boot.','off', True],
    'nfs.port': ['NFS_PORT','Specify a port for the NFS Server to listen to',None,False],
    'smtp.port': ['SMTP_PORT','Specify a custom port for the SMTP service.','25',False],
    'nis.server.enable': ['NIS_SERVER_ENABLE','Enable or disable the NIS server start option during boot.','off', True],
    'import.all.read-write': ['IMPORT_ALL_RW','If set to on DEGRADED pools will also be imported in read-write mode. Otherwise DEGRADED pools are only imported read-only','off', True],
    'ssh.enable': ['SSH_ENABLE','Enable or disable the SSH server start option during boot.','on', True],
    'nfs.udp.disable': ['NFS_NO_UDP','If set to on NFS will not use UDP, only TCP','off', True],
    'iscsi.port': ['ISCSI_PORT','Change the iSCSI portal Port number','3260',False],
    'ntp.servers': ['NTP_SERVERS','Enter one or more NTP servers. If multiple values, enter between quotes.', None,False],
    'keep.tmp': ['SKIP_TMPCLEAN',"If set to on the content of the /tmp directory won't be cleared during boot",'off', True],
    'nfs.threads': ['NFS_THREADS','Specify a number of NFS threads. A larger number of threads can improve performance',None,False],
    'smtp.user': ['SMTP_USER','Specify a SMTP user if required by the server.',None, False],
    'iscsi.address': ['ISCSI_PORTAL','Specify an IP address iSCSI will accept connections on. Must be an existing IP on the system and must be up',None, False],
    'tftp.enable': ['TFTP_ENABLE','Enable or disable the TFTP server start option during boot.','off', True],
    'nfs.enable': ['NFS_ENABLE','Enable or disable the NFS server start option during boot.','off', True],
    'skipcheck.rootfs': ['SKIP_CHECK',"If set to on the root filesystem won't be checked for errors during boot",'off', True],
    'iscsi.enable': ['ISCSI_ENABLE','Enable or disable the iSCSI server start option during boot.','off', True],
    'ntp.enable': ['NTP_ENABLE','Enable or disable the NTP service start option during boot.','off', True],
    'smtp.server': ['SMTP_SERVER','Specify a SMTP server the system will connect to for sending emails',None, False],
    'ssh.allow.root': ['SSH_ROOTLOGN','If set to on the root user can also login via SSH','off',True],
    'nfs.tcp.disable': ['NFS_NO_TCP','If set to on NFS will not use TCP, only UDP','off', True],
}
hidden_opts = ['files.to.sync', 'default.sync.files']
requires_ip = ['iscsi.address']
requires_int=['nfs.port', 'nfs.threads', 'iscsi.port', 'smb.debug.level','winbind.debug.level', 'netbios.debug.level', 'ssh.port',\
'ssh.sessions', 'ssh.timeout', ]

def validate_ip(MY_IP):
    parts = MY_IP.split(".")
    if len(parts) != 4:
        return False
    for item in parts:
        try:
            int(item)
        except:
            return False
        if not 0 <= int(item) <= 255:
            return False
    return True

def handleArcsize(user_value):
    if user_value == "reset":
        pass
    elif user_value.isdigit() is not True:
        print ('Option arc.size only accepts a number between 0 and 100')
        sys.exit(1)
    elif int(user_value) > 100:
        print ('Option arc.size only accepts a number between 0 and 100')
        sys.exit(1)
    elif int(user_value) < 0:
        print ('Option arc.size only accepts a number between 0 and 100')
        sys.exit(1)

    mf='/proc/meminfo'

    if user_value == "reset":
        if os.path.isfile('/etc/modprobe.d/arc.conf'):
            os.remove('/etc/modprobe.d/arc.conf')
    else:
        if os.path.isdir('/etc/modprobe.d'):
            modfile='/etc/modprobe.d/arc.conf'
        else:
            os.mkdir('/etc/modprobe.d')
            modfile='/etc/modprobe.d/arc.conf'

        if os.path.isfile(modfile):
            pass
        else:
            open(modfile, 'a').close()

        with open(mf) as fd:
            for line in fd:
                if  'MemTotal' in line:
                    line=line
                    tm = [mem for mem in line.split() if mem.isdigit()][0]
                    fd.close()
                    break

        arc_mem=[(int(user_value) * int(tm)) / 100][0]
        arc_mem=arc_mem*1024

        fo=open(modfile, 'r')
        fd=fo.readlines()
        fo.close()

        with open(modfile, 'wb') as output:
            for line in fd:
                if 'zfs_arc_max' in line:
                    continue
                else:
                    output.write(line)
        fo=open(modfile, 'a')
        fo.write('options zfs zfs_arc_max='+str(arc_mem)+'\n')
        fo.close()
        print("Setting arc.size to %s%% OR %s KB of TotalMem: %s KB" % (user_value, arc_mem/1024, tm))
    
def run_cmd(command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    return out, err
    


def handleHostname(user_value):
    if user_value == 'reset':
        user_value = 'ovios-indt'
    cmd = "/bin/hostname %s" %user_value
    out, err= run_cmd(cmd)
    if err:
        print(err)
        sys.exit()
    else:
        print("Changed hostname to %s" %user_value)

def getOldvalue(user_op):
    fd = open(cf)
    lines = fd.readlines()
    for line in lines:
        user_os_opt = line.strip('\n').split('=')[0]
        old_value =line.strip('\n').split('=')[-1]
        old_value = old_value.strip("'").strip('"')
        if user_os_opt == options[user_op][0]:
            fd.close()
            if len(old_value.strip()) == 0:
                return None
            else:
                return old_value
    fd.close()
    return None

def cleanUPList(mylist):
    newlist = list()
    for e in mylist:
        new_e = e.strip("'").strip('"').strip(" ")
        newlist.append(new_e)
    return newlist

def handleExcludepools(user_value, option):
    print('WARNING: Pools that you define here will not be managed by ovios.')
    old_value = getOldvalue(option)
    if old_value == "None":
        old_value = None
    tmp_excluded_pools = list(user_value.split())
    tmp_excluded_pools = cleanUPList(tmp_excluded_pools)
    if old_value is not None:
        excluded_pools = list(old_value.split())
        excluded_pools = cleanUPList(excluded_pools)
    else: excluded_pools = list()

    if user_value == "reset":
        for p in excluded_pools:
            cmd = '/usr/sbin/zfs set ovios:manage=yes '+p
            out, err = run_cmd(cmd)
            if ': dataset does not exist' in err:
                print("Pool %s doesn't exist or is exported" %p)
            else:
                print("Pool %s will be managed by OviOS starting now" %p)
        return ""
    else:
        for p in tmp_excluded_pools:
            cmd = '/usr/sbin/zfs set ovios:manage=no '+p
            out, err = run_cmd(cmd)
            if ': dataset does not exist' in err:
                print "Pool %s doesn't exist or is exported" %p
                print "Removing %s from the list ..." %p
            elif p not in excluded_pools:
                excluded_pools.append(p)   
        new_value = str(' '.join(excluded_pools))
        print("Excluding the following pools from being managed by OviOS: %s" %new_value)
        return new_value
    return None

def handleSmtpUser():
    import getpass
    SMTP_PASSWORD=getpass.getpass("Enter the password. If no password required, leave empty: ")
    f = open("/etc/sysconfig/ovios/.smtp_password", "w")
    f.write(SMTP_PASSWORD)
    f.close()

def handleSkipImport(user_value, option):
    if option == 'skip.import' and user_value == 'off':
        ov = getOldvalue("cluster.enable")
        if ov.lower() == "on":
            print 'WARNING: Cluster is enabled. Disabling this option might cause split brain scenarios.'
    
def handleAutosync(user_value, option):
    if option  == 'autosync.cluster' and user_value == 'off':
        ov = getOldvalue("cluster.enable")
        if ov.lower() == "on":
            print 'WARNING: Cluster is enabled. Disabling this option will stop the cluster auto-sync functionality.'
            
def handleCluster(user_value, option):
    if option == 'cluster.enable' and user_value == 'on':
        print 'Changing option: autosync.cluster ==> on if not on already'
        command="/sbin/options autosync.cluster on"
        output, err = run_cmd(command)
        print output.strip()

        print 'Changing option: skip.import ==> on if not on already'
        command='/sbin/options skip.import on'
        output, err = run_cmd(command)
        print output.strip()

def getColorized():
    value = getOldvalue('options.coloured')
    if value.lower() == 'on':
        no_colour=0
    elif value.lower()== 'off':
        no_colour=1
    else:
        print '======================== WARNING ==============================='
        print 'Could not determine the options.coloured setting. Default is off'
        print 'Set the options.coloured to on or off to correct this'
        print '======================== WARNING ==============================='
        no_colour=1
    return no_colour

class cl:
    no_colour = getColorized()
    """
    B = Blue
    G = Green
    Y = Yellow
    R = Red
    N = No color
    """
    if no_colour == 0:
        B = '\033[94m'
        G = '\033[92m'
        Y = '\033[93m'
        R = '\033[91m'
        N = '\033[0m'
    else:
        B = ''
        G = ''
        Y = ''
        R = ''
        N = ''
    

class Option():
    def __init__(self, option, user_value, cf):
        self.option = option
        self.user_value = user_value
        self.cf = cf
    
    def runOption(self):
        if self.option == "all":
            self.printAll()
        elif self.user_value == 'reset':
            os_opt = options[self.option][0]
            if self.option == "exclude.pools": 
                handleExcludepools(self.user_value, self.option)
                new_user_value = "None"
                self.writeConf(new_user_value, os_opt)
                sys.exit()
            if self.option == "os.hostname":
                handleHostname(self.user_value)
                new_user_value = options[self.option][2]
                self.writeConf(new_user_value, os_opt)
                sys.exit()
            dv =options[self.option][2]
            if os_opt in requires_int or requires_ip:
                new_user_value = ''
            if options[self.option][3]: # if it is an on-off option set the default to on or off
                new_user_value = dv
            else:
                new_user_value = ''
            if dv is None:
                new_user_value = ''
            self.writeConf(new_user_value, os_opt)

        elif self.user_value == "help":
            self.getHelp()
        elif self.user_value in ['on', 'off', '0', '1', 0, 1]:
            self.changeOption()
        elif self.user_value == None:
            self.printOption()
        elif self.option in requires_ip:
            if not validate_ip(self.user_value):
                print(cl.R+"Option: "+cl.N+cl.Y+self.option+cl.N+cl.R+" requires an IPv4"+cl.N )
                sys.exit(1)
            else:
                self.changeOption()
        else:
            self.changeOption()

    def printOption(self):
        all_to_print = list()
        all_options = options.keys()
        for op in all_options:
            #if op.startswith(self.option): # this is stricter
            if self.option in op:
                all_to_print.append(op)
        if len(all_to_print) == 0: 
            print(cl.R+"Option: "+cl.N+cl.Y+self.option+cl.N+cl.R+" is not a valid OviOS option"+cl.N )
            sys.exit()

        for o in all_to_print:
            os_opt = options[o][0]
            fd = open(cf)
            lines = fd.readlines()
            for line in lines:
                user_os_opt = line.strip('\n').split('=')[0]
                old_value =line.strip('\n').split('=')[-1]
                if os_opt == user_os_opt:
                    print(cl.B+"option "+cl.N+"%s  %s" %(cl.Y+o+cl.N, cl.G+old_value+cl.N))

    def changeOption(self):
        os_opt = options[self.option][0]  
        if options[self.option][3]:
            if self.user_value not in ['on', 'off', '0', '1', 0, 1]:
                print("The option %s only takes on/off/1/0 as argument" %self.option)
                sys.exit(1)
            if self.user_value in [0, '0']:
                new_user_value = 'off'
            elif self.user_value in [1, '1']:
                new_user_value = 'on'
            else:
                new_user_value = self.user_value
        else:
            new_user_value = self.user_value
        ## check for options that require a number
        if self.option in requires_int and new_user_value.isdigit() is not True:
            print ("Option: %s requires an integer number" %self.option)
            sys.exit(1)
        ## handle arc.size
        if self.option == "arc.size":
            handleArcsize(self.user_value)
            new_user_value = new_user_value+"%"
        ## handle exclude.pools
        if self.option == "exclude.pools":
            new_user_value = handleExcludepools(self.user_value, self.option)
            if new_user_value is None:
                sys.exit() 
        ## handle smtp user / pw here
        if self.option == "smtp.user":
            handleSmtpUser()
        ## handle os.hostname
        if self.option == "os.hostname":
            handleHostname(self.user_value)
        ## handle skip import, autosync and cluster
        if self.option == "skip.import":
           handleSkipImport(new_user_value, self.option)
        if self.option == "autosync.cluster":
           handleAutosync(new_user_value, self.option)
        if self.option == "cluster.enable": 
           handleCluster(new_user_value, self.option)
        self.writeConf(new_user_value, os_opt)

    def writeConf(self,new_user_value, os_opt):
        # chnage options here
        fd = open(cf)
        lines = fd.readlines()
        lines_to_write = list()
        for line in lines:
            user_os_opt = line.strip('\n').split('=')[0]
            #print(user_os_opt)
            old_value =line.strip('\n').split('=')[-1]
            #print((old_value), (user_value))
            if os_opt == user_os_opt:
                if str(self.user_value) == str(old_value):
                    print("Option %s is already set to %s" %(self.option, new_user_value))
                    lines_to_write.append(line)
                else:
                    print("Setting option: %s ==> %s" %(self.option, new_user_value))
                    new_line = "%s='%s'\n" %(user_os_opt,new_user_value)
                    lines_to_write.append(new_line)
            else:
                lines_to_write.append(line)
        #print(lines_to_write)
        # close file and rewrite
        fd.close()
        with open(cf, 'w') as f:
            for line in lines_to_write:
                f.write(line)
        f.close()
        sys.exit()



    def setDefault(self):
         options[self.option][2]
         
    def defaultValue(self):
        return options[self.option][2]
    
    def getHelp(self):
        print(cl.B+"Option: "+cl.N+"%s" %cl.Y+self.option+cl.N)
        defaultvalue = self.defaultValue()
        if defaultvalue in [None,'']:
            defaultvalue = "None"
        print(cl.B+"Default value: "+"%s" %cl.G+defaultvalue+cl.N)
        print(cl.B+"Definition: "+cl.N+"%s" %cl.G+options[self.option][1]+cl.N)
     
    def printAll(self):
        fd = open(cf)
        lines = fd.readlines()
        for l in lines:
            os_opt = l.split("=")[0]
            os_value = l.split("=")[-1].strip("\n")
            for k, v in options.items():
                if os_opt in v[0]:
                    if k not in hidden_opts:
                        print(cl.B+"option "+cl.N +"%s  %s" %(cl.Y+k+cl.N, cl.G+os_value+cl.N))
       

