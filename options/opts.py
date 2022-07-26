#!/usr/bin/python

import sys
from options import Option, cl

def printHelp():
    print(cl.Y+"options <option name> <value>"+cl.N)
    print(cl.R+"Example:"+cl.G+"\n\toptions smb.enable on\n\t"+cl.N+cl.B+"|\n\t--> This will enable the SMB server to start at boot.")
    print("\ton / off can also be given as 1 or 0")
    print("Type "+cl.Y+"options <option name> help "+cl.B+"to get a definition of the option.") 
    print(cl.R+"Example:"+cl.G+"\n\toptions ssh.allow.root help"+cl.B+"\n\t|\n\t-->This will print the definition for ssh.allow.root")
    print("Type "+cl.Y+"options <option name> default "+cl.B+"to get the default value")
    print(cl.R+"Example:\n\t"+cl.G+"options iscsi.debug default"+cl.B+"\n\t|\n\t-->This will print the default value for iscsi.debug"+cl.N)
    sys.exit()


def main():
    try:
        option=sys.argv[1]
    except:
        option = None
    try:
        user_value = sys.argv[2]
    except:
        user_value = None
    if user_value == "--help" or option is None:
        printHelp()
    global cf
    cf = "./ovios.conf"
    opt = Option(option, user_value,cf)
    opt.runOption()

if __name__ == '__main__':
    main()

