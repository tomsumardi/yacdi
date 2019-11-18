#!/usr/bin/python
import os
import sys, getopt
import subprocess
import time,atexit
import json
from pprint import pprint
import logging,signal,atexit
import logging.handlers
import fileinput
import traceback
import copy

g_strHostIndexFname         = 'host_index.json'

'''
**************************DATA STRUCTURE***************************************
'''

g_dictHostsFileProfile  = {\
'ipaddress': 'x.x.x.x',
'hostname':'None'
}

'''
**************************COMMON UTIL COMPONENT***************************************
'''

g_strLogfileName           = '/var/log/yacdi/yacdi.log'
g_strSysLogExecName        = 'hostsgen'
g_strProdVer               = 'Ver 1.0.0'
g_strSysLogDebugFormat     = '[DEBUG] '
g_strSysLogInfoFormat      = '[INFO] '
g_strSysLogErrFormat       = '[ERROR] '

'''-------------------------------------------------------------------
Description: utility function raise exception assertion
Component: utility
'''
def utilRaiseAssert(strx):
    strErr = 'illegal function input '+strx
    utilStdoutSysLogger(g_strSysLogErrFormat,strErr)
    raise ValueError(strErr)

'''-------------------------------------------------------------------
Description: utility function wrapper around syslog ouput
Component: utility
'''
def utilStdoutSysLogger(strLvl,strMsg):
    if g_strSysLogErrFormat == strLvl:
        tb = traceback.format_exc()
        logging.error('['+g_strSysLogExecName+']:'+strMsg)
        if tb:
            strTrcBk = "Trace: "+tb
            logging.error(strTrcBk)
    elif g_strSysLogDebugFormat == strLvl:
        logging.debug('['+g_strSysLogExecName+']:'+strMsg)
    else:
        logging.info('['+g_strSysLogExecName+']:'+strMsg)

'''-------------------------------------------------------------------
Description: utility function Initializing syslog
Component: utility
'''
def utilFInitSysLog():
    logging.basicConfig(filename=g_strLogfileName, level=logging.INFO)
    return 0

'''-------------------------------------------------------------------
Description: utility function parsing JSON file
Component: utility
'''
def utilParseJSONFile(strfileloc):
    lstAnsibleJData = []
    try:
        if(strfileloc is None):
            utilRaiseAssert('')
        
        with open(strfileloc) as f:    
            lstAnsibleJData = json.load(f)
    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,'invalid JSON file: '+strfileloc)
        
    if (not lstAnsibleJData):
        utilStdoutSysLogger(g_strSysLogErrFormat,'error, unable to parse JSON file: '+strfileloc)
        
    return lstAnsibleJData

'''
**************************Host Generation COMPONENT***************************************
'''

def hgGetNetworkNameLstDict(strHostName,lstUserInputJData):
    lstNetworkNameDict = []
    try:
        for strElm in lstUserInputJData[strHostName]:
            keyent = lstUserInputJData[strHostName][strElm]
            if type(keyent) is dict:
                if ('MACAddresses' in keyent) and \
                ('InterfaceName' in keyent) and \
                ('NetworkType' in keyent) and \
                ('IPAddress' in keyent):
                    lstNetworkNameDict.append(lstUserInputJData[strHostName][strElm])
    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,'exception error, getting Network Name' )
        
    if not lstNetworkNameDict:
        utilStdoutSysLogger(g_strSysLogErrFormat,'error, getting Network Name' )
        
    return lstNetworkNameDict
        
def hgGetNetworkProf(strHostName,lstNetworkNameDict):
    strHostsText = ''
    bFirstPublic = False
    try:
        for dictNetworkName in lstNetworkNameDict:
            dictHostsFileProfile = g_dictHostsFileProfile; 
            dictHostsFileProfile['ipaddress']       = dictNetworkName['IPAddress']
            dictHostsFileProfile['hostname']        = strHostName.lower()+'.'+dictNetworkName['NetworkName'].lower()
            if (False == bFirstPublic) and (dictNetworkName['NetworkName'].lower() == 'public'):
                strHostsText += dictHostsFileProfile['ipaddress']+'        '+\
                                dictHostsFileProfile['hostname']+'        '+\
                                strHostName.lower()+'\n'
                bFirstPublic = True
            else:
                strHostsText += dictHostsFileProfile['ipaddress']+'        '+\
                                dictHostsFileProfile['hostname']+'        '+'\n'
    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,'exception error, getting Network Profile' )
        
    if strHostsText == '':
        utilStdoutSysLogger(g_strSysLogErrFormat,'error, getting Network Profile' )
        strHostsText = None
        
    return strHostsText
        
def hgWriteHostsFile(strHostsText,strOutputHostsFileLocation):
    f = None
    try:
        if(strHostsText is None):
            utilRaiseAssert('')
        if(strOutputHostsFileLocation is None):
            utilRaiseAssert('')
                               
        f = open(strOutputHostsFileLocation,'w')
        if f:
            f.write(strHostsText)
    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,'exception error, writing host file' )
    finally:
        if f:
            f.close()

def hgGenHostFileProcess(strInputUserInputJsonDir):
    strHostsText = ''
    try:
        if(strInputUserInputJsonDir is None):
            utilRaiseAssert('')
        
        lstHostIndex = utilParseJSONFile(strInputUserInputJsonDir+'/'+g_strHostIndexFname)
        for strJsonFname in lstHostIndex['hosts']:
            strJsonFname +='.json'
            lstUserInputJData = utilParseJSONFile(strInputUserInputJsonDir+'/'+strJsonFname)
            if lstUserInputJData:
                strHostName = strJsonFname.split('.')[0]
                if lstUserInputJData and strHostName:
                    lstNetworkNameDict = hgGetNetworkNameLstDict(strHostName,lstUserInputJData)
                    if lstNetworkNameDict:
                        strHostsText += hgGetNetworkProf(strHostName,lstNetworkNameDict)+'\n'
                else:
                    utilStdoutSysLogger(g_strSysLogErrFormat,'error, parsing file: '+\
                                        strInputUserInputJsonDir+'/'+strJsonFname )
            else:
                utilStdoutSysLogger(g_strSysLogErrFormat,'error, file not found' )       
    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,'exception error, generating hosts file' )

    if strHostsText == '':
        utilStdoutSysLogger(g_strSysLogErrFormat,'error, generating host file' )
        strHostsText = None
        
    return strHostsText

'''
**************************Nodes ini file COMPONENT***************************************
'''

'''
**************************Add cobbler profile COMPONENT***************************************
'''
        
''' generate hosts file 
'''
def hgHostsGen(strInputUserInputJsonDir,
               strOutputHostsFileLocation):
    uintSts = -1
    try:
        if(strInputUserInputJsonDir is None):
            utilRaiseAssert('')
        if(strOutputHostsFileLocation is None):
            utilRaiseAssert('')
        strHostsText = hgGenHostFileProcess(strInputUserInputJsonDir)
        if strHostsText is not None:
            hgWriteHostsFile(strHostsText,strOutputHostsFileLocation)
            uintSts = 0
    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,'error, generating host file' )
    
    return uintSts

'''-------------------------------------------------------------------
Description: Init syslog, parse input and process all the hosts
Component: main function
'''
def main(argv):
    
    #test input
    g_strInputUserInputJsonDir  = '/var/yacdi/data/userinput'
    g_strOutputHostsFile        = '/etc/yacdi/conf.d/hosts'
    
    uintSts = -1
    try:
        uintSts = hgHostsGen(g_strInputUserInputJsonDir,\
                   g_strOutputHostsFile)
    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,\
                                'exception error, main function')
        
    return uintSts
                
'''-------------------------------------------------------------------
Description:
'''
if __name__ == "__main__":
    sts = main(sys.argv[1:])
    sys.exit(sts)
    