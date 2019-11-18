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

'''
**************************DATA STRUCTURE***************************************
'''
# interface data structure profile (dictionary)
g_dictIntfProfile = {
     #static
     'networkname': 'None',
     'bootproto': 'static',
     'ipaddress': 'x.x.x.x',
     'gwaddress': 'x.x.x.x',
     'prefix': 'None',
     'onboot': 'yes',
     'mtu': '1500',
     'dns': 'None',
     'bondtype': 'active-backup', # or null for non-bond
     #dynamic 
     'bondtypebondmiimon': '100',
     'bondtypebondslaves': [], # translated for bond
     'lgdevname': 'None' # translated for bond
}

# device data structure profile (dictionary)
g_dictOSDeviceProfile = \
{
    'driveType': "none", 
    'sizeInGB': "0"
}

# UUID data structure profile (dictionary)
g_dictUUIDProfile = \
{
    'UUID': "none"
}

'''
**************************COMMON UTIL COMPONENT***************************************
'''

g_strLogfileName           = '/var/log/yacdi/yacdi.log'
g_strSysLogExecName        = 'hostvarmap'
g_strProdVer               = 'Ver 1.0.0'
g_strSysLogDebugFormat     = '[DEBUG]'
g_strSysLogInfoFormat      = '[INFO]'
g_strSysLogErrFormat       = '[ERROR]'


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
Description: utility function dumping yml config to host_vars directory
Component: utility
'''
def utilWriteHostVars(strHostVarsFile, \
                      strIntfRstrt,\
                      strLogicalDrv,\
                      strIntf,
                      strUUID):
    f = None
    try:
        if(strHostVarsFile is None):
            utilRaiseAssert('')
        if(strIntfRstrt is None):
            utilRaiseAssert('')
        if(strLogicalDrv is None):
            utilRaiseAssert('')
        if(strIntf is None):
            utilRaiseAssert('')
        if(strUUID is None):
            utilRaiseAssert('')
                               
        f = open(strHostVarsFile,'w')
        f.write("---\r\n\r\n")
        f.write(strUUID)
        f.write(strLogicalDrv)
        f.write(strIntfRstrt)
        f.write(strIntf)

    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,'error, unable to open file or file does not exists')
    finally:
        if f:
            f.close()
    
    return None

'''-------------------------------------------------------------------
Description: print help banner
Component: utility
'''
def UtilUsage():
    utilStdoutSysLogger(g_strSysLogInfoFormat,'USAGE: hostvarmap.py [-<flag> [<val>],...]')
    utilStdoutSysLogger(g_strSysLogInfoFormat,'xml to ansible host variable map'+g_strProdVer)
    utilStdoutSysLogger(g_strSysLogInfoFormat,'-u  <UI json dir>, user input hostname JSON directory')
    utilStdoutSysLogger(g_strSysLogInfoFormat,'-a  <ansible json dir>, ansible input facts JSON directory')
    utilStdoutSysLogger(g_strSysLogInfoFormat,'-i  <ansible init file>, ansible groups ini file')
    utilStdoutSysLogger(g_strSysLogInfoFormat,'-o  <host_vars outpur dir>, ansible host_vars output directory')
    utilStdoutSysLogger(g_strSysLogInfoFormat,'-f  <force intf restart>, force interface restart, no reboot')
    utilStdoutSysLogger(g_strSysLogInfoFormat,'-d  <ip addr>, dns server ip addr')
    utilStdoutSysLogger(g_strSysLogInfoFormat,'-h , help')

'''-------------------------------------------------------------------
Description: utility function parse and validate input arguments
Component: utility
'''
def UtilFparseInput(argv):
    sts = 1
    strUserInputJsonHostDir     = None
    strAnsibleJsonHostDir       = None
    strAnsibleGroupsIniFileName = None
    strHostVarsOutputDir        = None
    strDNSIPAddr                = None
    bForce = False
    try:
        opts, args = getopt.getopt(argv,'u:a:i:o:d:f',['userinputdir=','ansiblefactdir=',\
                                                       'inifile=','hostvarsout=',\
                                                       'force','help'])
        for opt, arg in opts:
            if opt == '-h':
                UtilUsage()
                sys.exit()
            elif opt in ("-u", "--userinputdir"):
                strUserInputJsonHostDir     = arg
            elif opt in ("-a", "--ansiblefactdir"):
                strAnsibleJsonHostDir       = arg
            elif opt in ("-i", "--inifile"):
                strAnsibleGroupsIniFileName = arg
            elif opt in ("-o", "--hostvarsout"):
                strHostVarsOutputDir        = arg
            elif opt in ("-d", "--dnsipaddr"):
                strDNSIPAddr                = arg
            elif opt in ("-f"," --force"):
                bForce = True
    except getopt.GetoptError:
        UtilUsage()
        
    if ((strUserInputJsonHostDir  is None) or (strAnsibleJsonHostDir is None) or \
        (strAnsibleGroupsIniFileName  is None) or (strHostVarsOutputDir is None)) or\
        (strDNSIPAddr is None):
        sts = 1
    else:
        sts = 0
        
    return sts,bForce,strAnsibleGroupsIniFileName,\
        strAnsibleJsonHostDir,strUserInputJsonHostDir,\
        strHostVarsOutputDir,strDNSIPAddr

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

'''-------------------------------------------------------------------
Description: utility function remove file if exists
Component: utility
'''
def utilFileCleanup(filename):
    if(filename is None):
        utilRaiseAssert('')
        
    if os.path.exists(filename):
        os.remove(filename)

'''-------------------------------------------------------------------
Description: utility function create directory and files if doesn't exists
Component: utility
'''
def utilCreateDirsAndFile(
                 strIniFileName,strAnsibleJsonHostDir,\
                 strUiJsonHostDir,strHostVarsOutputDir):

    uintSts = -1
    # Flush file contents and create dir if doesn't exists
    try:
        if(strIniFileName is None):
            utilRaiseAssert('')
        if(strAnsibleJsonHostDir is None):
            utilRaiseAssert('')
        if(strUiJsonHostDir is None):
            utilRaiseAssert('')
        if(strHostVarsOutputDir is None):
            utilRaiseAssert('')
        
        if not os.path.exists(strAnsibleJsonHostDir):
            os.makedirs(strAnsibleJsonHostDir)
        if not os.path.exists(strUiJsonHostDir):
            os.makedirs(strUiJsonHostDir)
        if not os.path.exists(strHostVarsOutputDir):
            os.makedirs(strHostVarsOutputDir)
        uintSts = 0
    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,\
                                'exception error, unable to open or create dir')
    return uintSts


'''-------------------------------------------------------------------
Description: convert vendor representation (base 10) to actual representation
(base 2) up to 2 unit of precision.
Component: utility
'''
def utilGetActualSize(strsize,strUnit):
    floatDriveSz = 0

    try: 
        floatSizeBTenBytes = float(strsize.split(' ')[0])*1000000000

        if(strUnit == "MB"):
            floatDriveSz = round((floatSizeBTenBytes)/(1024.0*1024.0),2)
        elif (strUnit == "GB"):
            floatDriveSz = round((floatSizeBTenBytes)/(1024.0*1024.0*1024.0),2)
        elif (strUnit == "TB"):
            floatDriveSz = round((floatSizeBTenBytes)/(1024.0*1024.0*1024.0*1024.0),2)
        else:
            utilStdoutSysLogger(g_strSysLogErrFormat,\
                                    'error, unknown drive size unit')
    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,\
                                'exception error, unable to convert drive size') 
    return floatDriveSz

'''-------------------------------------------------------------------
Description: check to see if size within range
Component: utility
'''
def utilIsSizeWithinRange(floatUiSize,floatAnsibleSize,strUnit):
    bWithinRange = False
    try: 
        if(strUnit == "MB"):
            if(floatAnsibleSize <= floatUiSize+10) and (floatAnsibleSize >= floatUiSize-10):
                bWithinRange = True
        elif (strUnit == "GB"):
            if(floatAnsibleSize <= floatUiSize+5) and (floatAnsibleSize >= floatUiSize-5):
                bWithinRange = True
        elif (strUnit == "TB"):
            if(floatAnsibleSize <= floatUiSize+0.1) and (floatAnsibleSize >= floatUiSize-0.1):
                bWithinRange = True
        else:
            utilStdoutSysLogger(g_strSysLogErrFormat,\
                                    'error, unknown drive size unit')
    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,\
                                'exception error, unable to check if size within range') 
    return bWithinRange
    
    
'''
**************************USER INPUT COMPONENT***************************************
'''

'''-------------------------------------------------------------------
Description: Get UUID hw profile from the user
Component: User input JSON processing
'''
def hvarUserInputGetHwProfileUUID(strHname,dictAnsibleJData):
    dictUUIDProfile = {}
    try:
        if(strHname is None):
            utilRaiseAssert('')
        if(not dictAnsibleJData):
            utilRaiseAssert('')
        
        if (dictAnsibleJData[strHname]):
            dictUUIDProfile['UUID'] = dictAnsibleJData[strHname]['UUID']
        else:
            utilStdoutSysLogger(g_strSysLogErrFormat,'error, unable to find UUID name from user input' )
    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,'exception error, translation of UUID name' )

    if(not dictUUIDProfile):
        utilStdoutSysLogger(g_strSysLogErrFormat,'error, get user input uuid profile' )        

    return dictUUIDProfile

'''-------------------------------------------------------------------
Description: Get OS drive hw profile from the user
Component: User input JSON processing
'''
def hvarUserInputGetHwProfileOSDrive(strHname,dictAnsibleJData):
    dictOSDeviceProfile = {}
    try:
        if(strHname is None):
            utilRaiseAssert('')
        if(not dictAnsibleJData):
            utilRaiseAssert('')
        
        if (dictAnsibleJData[strHname]) and \
        (dictAnsibleJData[strHname]['StorageProfile']) and\
        (dictAnsibleJData[strHname]['StorageProfile']['OperatingSystem']):
            dictOSDeviceProfile['driveType'] = dictAnsibleJData[strHname]['StorageProfile']['OperatingSystem']['DriveType']
            dictOSDeviceProfile['sizeInGB'] = dictAnsibleJData[strHname]['StorageProfile']['OperatingSystem']['SizeInGB']
        else:
            utilStdoutSysLogger(g_strSysLogErrFormat,'error, unable to find OS drive from user input' )
    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,'exception error, translation of OS drive name' )

    if(not dictOSDeviceProfile):
        utilStdoutSysLogger(g_strSysLogErrFormat,'error, user input get OS drive' )
        
    return dictOSDeviceProfile

'''-------------------------------------------------------------------
Description: Get interface hardware profile from the user
Component: User input JSON processing
'''
def hvarUserInputGetHwProfileIntf(strHname,dictAnsibleJData):
    lstUiIntfProfile = []
    try:
        if(strHname is None):
            utilRaiseAssert('')
        if(not dictAnsibleJData):
            utilRaiseAssert('')
        
        for strElm in dictAnsibleJData[strHname]:
            keyent = dictAnsibleJData[strHname][strElm]
            if type(keyent) is dict:
                if ('MACAddresses' in keyent) and \
                ('InterfaceName' in keyent) and \
                ('NetworkType' in keyent) and \
                ('IPAddress' in keyent):
                    dictNewIntfProfile = copy.deepcopy(g_dictIntfProfile)
                    dictNewIntfProfile['networkname'] = keyent['NetworkName']
                    dictNewIntfProfile['bootproto'] = 'static'
                    dictNewIntfProfile['ipaddress'] = keyent['IPAddress']
                    dictNewIntfProfile['gwaddress'] = keyent['Gateway']
                    dictNewIntfProfile['prefix'] = keyent['Prefix']
                    dictNewIntfProfile['onboot'] = 'yes'
                    dictNewIntfProfile['mtu'] = '1500'
                    dictNewIntfProfile['dns'] = 'None'
                    dictNewIntfProfile['bondtype'] = keyent['BondType'].lower()
                    dictNewIntfProfile['bondtypebondmiimon'] = '100'
                    for strMacAddr in dictAnsibleJData[strHname][strElm]['MACAddresses']:
                        dictNewIntfProfile['bondtypebondslaves'].append(strMacAddr)
                    lstUiIntfProfile.append(dictNewIntfProfile)
    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,'exception error, translation MAC address to interface name' )
    
    if(not lstUiIntfProfile):
        utilStdoutSysLogger(g_strSysLogErrFormat,' error, user input intf profile, translation MAC address to interface name' )
            
    return lstUiIntfProfile

'''
**************************ANSIBLE COMPONENT******************************************
'''

'''-------------------------------------------------------------------
Description: get logical interface in yml format by translating drive
type profile from JSON ansible facts to logical device
Component: Ansible JSON processing
'''
def hvarAnsibleGetLogicalDev(dictAnsibleJData,uiDrvProfile):
    strLgDrv = None
    try:
        if(not dictAnsibleJData):
            utilRaiseAssert('')
        if(not uiDrvProfile):
            utilRaiseAssert('')
            
        if ('SSD' != uiDrvProfile['driveType']) and ('HDD' != uiDrvProfile['driveType']):
            utilStdoutSysLogger(g_strSysLogErrFormat,'invalid DriveType:'+uiDrvProfile['driveType']+
                      'HDD/SDD are the only currently supported' )
        else:
            strUiSize = "0"
            charUiRotational = "0"
            if ('SSD' != uiDrvProfile['driveType']):
                charUiRotational = "1"
            strUiSize = uiDrvProfile['sizeInGB']

            for dev in dictAnsibleJData['ansible_facts']['ansible_devices']:
                charRotation = (dictAnsibleJData['ansible_facts']['ansible_devices'][dev.encode('UTF-8')]['rotational']).encode('UTF-8')
                if (charUiRotational == charRotation):
                    strsize = (dictAnsibleJData['ansible_facts']['ansible_devices'][dev.encode('UTF-8')]['size']).encode('UTF-8')
                    strUnit = strsize.split(' ')[1]
                    floatAnsibleSize    = round(float(strsize.split(' ')[0]),2)
                    floatUiSize         = utilGetActualSize(strUiSize,strUnit)
                    bWithinRange        = utilIsSizeWithinRange(floatUiSize,floatAnsibleSize,strUnit)
                    if(True == bWithinRange):
                        strLgDrv = 'StorageProfile_Drive_OperatingSystem: '+ '\"'+'/dev/'+dev.encode('UTF-8')+'\"'+"\r\n"
                        break
                    else:
                        print 'unable to match OS drive size.'
                        print 'user input xml drive size: '+strUiSize+' GB'
                        print 'user input actual drive size: '+str(floatUiSize)+' GB'
                        print 'hardware drive size: '+str(floatAnsibleSize)+' '+strUnit
                        utilStdoutSysLogger(g_strSysLogErrFormat,'error user input OS drive size in GB: ' \
                        +str(floatUiSize)+' ,node drive size in '+strUnit+': '+str(floatAnsibleSize))
                else:
                    print 'unable to match OS drive type.'
                    print 'user input drive type rotational (1-True/0-False): '+charUiRotational
                    print 'hardware drive type rotational (1-True/0-False): '+charRotation
                    utilStdoutSysLogger(g_strSysLogErrFormat,'error user input OS drive rotational: ' \
                    +charUiRotational+',node drive rotational: '+charRotation)
    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,'exception error, traversing JSON file' )

    if(strLgDrv is None):
        utilStdoutSysLogger(g_strSysLogErrFormat,'error, ansible get logical device' )
            
    return strLgDrv

def hvarUserInputSetHwProfileIntfDNS(strDnsServerIPaddr,lstAnsibleHwProfileIntf):
    lstHwProfileIntf = []
    
    try:
        for dictElm in lstAnsibleHwProfileIntf:
            if (dictElm['ipaddress'].split('.')[0] == strDnsServerIPaddr.split('.')[0]) and \
            (dictElm['ipaddress'].split('.')[1] == strDnsServerIPaddr.split('.')[1]) and \
            (dictElm['ipaddress'].split('.')[1] == strDnsServerIPaddr.split('.')[1]):
                dictElm['dns'] = strDnsServerIPaddr
                lstHwProfileIntf = lstAnsibleHwProfileIntf
                break
    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,'exception error, hw dns match failed' )
        
    return lstHwProfileIntf

'''-------------------------------------------------------------------
Description: translate MAC address to interface name
Component: Ansible JSON processing
'''
def hvarAnsibleTranslateMACToIntfName(dictAnsibleJData,lstMacAdresses):
    lstIntfNames = []
    try:
        if(not dictAnsibleJData):
            utilRaiseAssert('')
        if(not lstMacAdresses):
            utilRaiseAssert('')
        
        for strUiMacAddr in lstMacAdresses:
            for strDev in dictAnsibleJData['ansible_facts']:
                dictDev = dictAnsibleJData['ansible_facts'][strDev]
                if type(dictDev) is dict:
                    if ('macaddress' in dictDev) and ('module' in dictDev) and ('device' in dictDev) and ('mtu' in dictDev):
                        strAnsibleMacAddr = (dictAnsibleJData['ansible_facts'][strDev.encode('UTF-8')]['macaddress']).encode('UTF-8')
                        if(strUiMacAddr.lower() == strAnsibleMacAddr.lower()):
                            lstIntfNames.append(dictAnsibleJData['ansible_facts'][strDev.encode('UTF-8')]['device'])
        if len(lstMacAdresses) != len(lstIntfNames):
            lstIntfNames = []
    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,'exception error, translation MAC address to interface name' )
    
    if(not lstIntfNames):
        utilStdoutSysLogger(g_strSysLogErrFormat,'error, ansible translating MAC to interface name' )
            
    return lstIntfNames

'''-------------------------------------------------------------------
Description: get logical interface in yml format by translating MAC 
addresses from JSON ansible facts to interface names
Component: Ansible JSON processing
'''
def hvarAnsibleGetLogicalIntf(dictAnsibleJData,lstUiIntfProfile):
    strLogIntf = None
    sts = 0
    try:
        lstLogIntfEther = []
        lstLogIntfBond  = []
        
        if(not dictAnsibleJData):
            utilRaiseAssert('')
        if(not lstUiIntfProfile):
            utilRaiseAssert('')
        
        for dictElem in lstUiIntfProfile:
            lstIntf = hvarAnsibleTranslateMACToIntfName(dictAnsibleJData,dictElem['bondtypebondslaves'])
            if lstIntf:
                strIntf = ""
                if "none".lower() == dictElem['bondtype'].encode('UTF-8'):
                    strIntf += "    - NetworkName: " +lstIntf[0]+"\r\n"
                    strIntf += "      IPAddress: "   +dictElem['ipaddress']+"\r\n"
                    strIntf += "      GwAddress: "   +dictElem['gwaddress']+"\r\n"
                    strIntf += "      Prefix: "      +dictElem['prefix']+"\r\n"
                    strIntf += "      Bootproto: "   +dictElem['bootproto']+"\r\n"
                    strIntf += "      Onboot: "      +dictElem['onboot']+"\r\n"
                    strIntf += "      Mtu: "         +dictElem['mtu']+"\r\n"
                    if dictElem['dns'].lower() != 'none':
                        strIntf += "      DNS: "         +dictElem['dns']+"\r\n"
                    lstLogIntfEther.append(strIntf)
                else:
                    strIntf += "    - NetworkName: " +dictElem['networkname'] +"\r\n"
                    strIntf += "      IPAddress: "   +dictElem['ipaddress']+"\r\n"
                    strIntf += "      GwAddress: "   +dictElem['gwaddress']+"\r\n"
                    strIntf += "      Prefix: "      +dictElem['prefix']+"\r\n"
                    strIntf += "      Bootproto: "   +dictElem['bootproto']+"\r\n"
                    strIntf += "      Onboot: "      +dictElem['onboot']+"\r\n"
                    strIntf += "      Mtu: "         +dictElem['mtu']+"\r\n"
                    if dictElem['dns'].lower() != 'none'.lower():
                        strIntf += "      DNS: "         +dictElem['dns']+"\r\n"
                    strIntf += "      BondType: "    +dictElem['bondtype']+"\r\n"
                    strIntf += "      Bond_miimon: " +dictElem['bondtypebondmiimon']+"\r\n"
                    strIntf += "      BondSlaves: "+"\r\n"
                    for slv in lstIntf:
                        strIntf += "        - "  +slv.encode('UTF-8')+"\r\n"
                    lstLogIntfBond.append(strIntf)
            else:
                utilStdoutSysLogger(g_strSysLogErrFormat,' error, unable to pull mac address entry' )
                sts = -1
        #format as YAML report
        if 0 == sts: 
            if lstLogIntfEther:
                strLogIntf  = ""
                strLogIntf += "ServerConfiguration_Interface_Ether:\r\n"
                for strIntfElm in lstLogIntfEther:
                    strLogIntf += strIntfElm
            else:
                strLogIntf = "ServerConfiguration_Interface_Ether: []\r\n"
            if lstLogIntfBond:
                strLogIntf += ""
                strLogIntf += "ServerConfiguration_Interface_Bond:\r\n"
                for strIntfElm in lstLogIntfBond:
                    strLogIntf +=  strIntfElm
            else:
                strLogIntf += "ServerConfiguration_Interface_Bond: []\r\n"   
    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,'exception error, unable to get logical interface name' )
        
    if(strLogIntf is None):
        utilStdoutSysLogger(g_strSysLogErrFormat,'error, ansible get logical interface' )
    
    return strLogIntf

'''
**************************MAIN******************************************
'''

'''-------------------------------------------------------------------
Description: translate user input in JSON to ansible facts in JSON for
all hosts specified within the ini file
Component: Ansible JSON processing
'''
def hvarTranslateFacts(strHname,strDnsServerIPaddr,bForce,lstUserinputJData,lstAnsibleJData):
    strAnsibleUUIDProfile       = None
    strAnsibleLogicalDrv        = None
    strAnsibleForceIntfRstrt    = None
    strAnsibleLogicalIntf       = None
    try:
        if(strHname is None):
            utilRaiseAssert('')
        if(not lstUserinputJData):
            utilRaiseAssert('')
        if(not lstAnsibleJData):
            utilRaiseAssert('')
        if(not strDnsServerIPaddr):
            utilRaiseAssert('')
        
        dictAnsibleUUIDProfile     = hvarUserInputGetHwProfileUUID(strHname,lstUserinputJData)
        dictAnsibleHwProfileDrive  = hvarUserInputGetHwProfileOSDrive(strHname,lstUserinputJData)
        lstAnsibleHwProfileIntf    = hvarUserInputGetHwProfileIntf(strHname,lstUserinputJData)
        if (dictAnsibleHwProfileDrive is not None) and (dictAnsibleUUIDProfile is not None) and \
          lstAnsibleHwProfileIntf:
            lstAnsibleHwProfileIntf = hvarUserInputSetHwProfileIntfDNS(strDnsServerIPaddr,lstAnsibleHwProfileIntf)
            if lstAnsibleHwProfileIntf:
                strAnsibleUUIDProfile  = "ServerConfiguration_UUID: "+dictAnsibleUUIDProfile['UUID']+"\r\n"
                strAnsibleLogicalDrv   = hvarAnsibleGetLogicalDev(lstAnsibleJData,dictAnsibleHwProfileDrive)
                if (False == bForce):
                    strAnsibleForceIntfRstrt    = "ServerConfiguration_Interface_Toggle: \"no\""+"\r\n"
                else:
                    strAnsibleForceIntfRstrt    = "ServerConfiguration_Interface_Toggle: \"yes\""+"\r\n"
                strAnsibleLogicalIntf  = hvarAnsibleGetLogicalIntf(lstAnsibleJData,lstAnsibleHwProfileIntf)
        else:
            utilStdoutSysLogger(g_strSysLogErrFormat,'error, ansible get hw profile UUID/OSDRIVE/Intf' )
    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,'exception error, translating ansible facts and/or user input xml information' )
    return strAnsibleForceIntfRstrt,strAnsibleLogicalDrv,strAnsibleLogicalIntf,strAnsibleUUIDProfile

'''-------------------------------------------------------------------
Description: Iterate through all the hosts within the ini file and 
make translation of each JSON file from user input and ansible facts
folder 
Component: main function
'''
def hvarProcessHosts(bForce,strIniFileName,strAnsibleJsonHostDir,\
                 strUiJsonHostDir,strHostVarsOutputDir,\
                 strDnsServerIPaddr):
    uintSts = -1
    try: 
        utilFInitSysLog()
        if(strIniFileName is None):
            utilRaiseAssert('')
        if(strAnsibleJsonHostDir is None):
            utilRaiseAssert('')
        if(strUiJsonHostDir is None):
            utilRaiseAssert('')
        if(strHostVarsOutputDir is None):
            utilRaiseAssert('')
        if(strDnsServerIPaddr is None):
            utilRaiseAssert('')

        strAnsibleJsonHostDir   = strAnsibleJsonHostDir+'/'
        strUiJsonHostDir        = strUiJsonHostDir+'/'
        strHostVarsOutputDir    = strHostVarsOutputDir+'/'
        uintSts = utilCreateDirsAndFile(strIniFileName,\
                                        strAnsibleJsonHostDir,\
                                        strUiJsonHostDir,\
                                        strHostVarsOutputDir)
        if (0 == uintSts):      
            for strElm in fileinput.input([strIniFileName]):
                uintSts = -1  
                strHnameFull      = strElm.strip()
                strHname = (strElm.strip()).split('.')[0]
                utilFileCleanup(strHostVarsOutputDir+strHname+'.yml')
                if False == fileinput.isfirstline():
                    lstAnsibleJData     = utilParseJSONFile(strAnsibleJsonHostDir+strHname+'.json')
                    lstUserinputJData   = utilParseJSONFile(strUiJsonHostDir+strHname+'.json')
                    if lstAnsibleJData and lstUserinputJData:
                        strAnsibleForceIntfRstrt,strAnsibleLogicalDrv, \
                        strAnsibleLogicalIntf,strAnsibleUUIDProfile = \
                            hvarTranslateFacts(strHname,strDnsServerIPaddr,bForce,lstUserinputJData,lstAnsibleJData)
                        if (strAnsibleForceIntfRstrt is not None and \
                           strAnsibleLogicalDrv is not None and \
                           strAnsibleLogicalIntf is not None and
                           strAnsibleUUIDProfile is not None):
                            utilWriteHostVars(strHostVarsOutputDir+strHnameFull+'.yml',\
                                          strAnsibleForceIntfRstrt, \
                                          strAnsibleLogicalDrv, \
                                          strAnsibleLogicalIntf,
                                          strAnsibleUUIDProfile)
                            uintSts = 0
                        else:
                            utilStdoutSysLogger(g_strSysLogErrFormat,'error, unable to translate facts')
                            break
                    else:
                        utilStdoutSysLogger(g_strSysLogErrFormat,'error, unable to parse JSON files:' +\
                                            strAnsibleJsonHostDir+strHname+'.json' + ' or '+\
                                            strUiJsonHostDir+strHname+'.json')
                        break
    except:
        utilStdoutSysLogger(g_strSysLogErrFormat,'exception error, hostvarmap processing hosts')
        
    return uintSts

'''-------------------------------------------------------------------
Description: Init syslog, parse input and process all the hosts
Component: main function
'''
def main(argv):
    
    uintSts = -1
    try:
        '''
        g_strHostVarsOutputDir         = '/home/tsumardi/workspace/OSPROJ45/postvalidate/host_vars/'
        g_strAnsibleJsonHostDir        = '/home/tsumardi/workspace/OSPROJ45/postvalidate/ansible/'
        g_strUserInputJsonHostDir      = '/home/tsumardi/workspace/OSPROJ45/postvalidate/userinput/'
        g_strAnsibleGroupsIniFileName  = '/home/tsumardi/workspace/OSPROJ45/postvalidate/groups/nodes'
        '''
        utilFInitSysLog()
        uintSts,bForce,strAnsibleGroupsIniFileName, \
        strAnsibleJsonHostDir,strUserInputJsonHostDir, \
        strHostVarsOutputDir,strDnsServerIPaddr = UtilFparseInput(argv)
        if 0 == uintSts:
            uintSts = hvarProcessHosts(bForce,\
                               strAnsibleGroupsIniFileName,\
                               strAnsibleJsonHostDir,
                               strUserInputJsonHostDir,\
                               strHostVarsOutputDir,\
                               strDnsServerIPaddr)
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
    