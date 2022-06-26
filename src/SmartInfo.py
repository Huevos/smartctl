# -*- coding: utf-8 -*-
# Depends: smartctl

from __future__ import print_function

try:
    from . import Helper
except:
    import Helper

import os
import stat
import re
import sys

class SmartInfo(object):

    def __init__(self, device):
        self.device = None
        self.information = []
        self.attributes = []
        self.selftests = []
        self.errors = []
        self.capabilities = {}
        device = "/dev/" + device
        
        if self.__canUseSmartctl():
            # sicher stellen, dass device ein Block-Device ist
            if self.__isBlockDevice(device):
                self.device = device
            else:
                self.information.append( ("Achtung!", "%s ist keine Festplatte" % (device,)) )
        
    def __parseInformationSection(self):
        if self.device:
            cmd = [ "/usr/sbin/smartctl", "-i", self.device ]
            lsblkOutput = Helper.sub_process(cmd)
            
            inSection = False
            self.information = []
            for line in lsblkOutput.splitlines():
                if inSection:
                    try:
                        key, val = line.split(':',1)
                        self.information.append( (key.strip(), val.strip()) )
                    except:
                        pass
                if line == '=== START OF INFORMATION SECTION ===':
                    inSection = True
            
            self.__parseCapabilities()
    
    def __parseAttributesBlock(self):
        if self.device:
            cmd = [ "/usr/sbin/smartctl", "-Aj", self.device ]
            out = Helper.sub_process(cmd)
            attributes = Helper.json_loads(out)

            if attributes and "ata_smart_attributes" in attributes:
                table = attributes["ata_smart_attributes"]["table"]
                self.attributes = []
                for attr in table:
                    failed = 'ok'
                    if 'when_failed' in attr and attr['when_failed'] != '':
                        failed = attr["when_failed"]
                    thresh = ''
                    if 'tresh' in attr:
                        tresh = str(attr[thresh])
                    line = ( str(attr['id']), attr['name'].replace("_", " "), failed, str(attr["value"]), str(attr["worst"]), thresh,  attr['raw']['string'] )
                    self.attributes.append(line)
    
    def __parseSelftestsLog(self):
        if self.device:
            cmd = [ "/usr/sbin/smartctl", "-jl", "selftest", self.device ]
            out = Helper.sub_process(cmd)
            try:
                selftests = Helper.json_loads(out)
                logged = selftests["ata_smart_self_test_log"]["standard"]["table"]
                for item in logged:
                    self.selftests.append((item["type"]["string"].encode("ascii").decode(), item["status"]["string"].encode("ascii").decode()))
            except:
                pass
    
    def __parseErrorLog(self):
        if self.device:
            cmd = [ "/usr/sbin/smartctl", "-jl", "error", self.device ]
            out = Helper.sub_process(cmd)
            try:
                selftests = Helper.json_loads(out)
                logged = selftests["ata_smart_error_log"]["summary"]["table"]
                for item in logged:
                    self.selftests.append((item["type"]["string"].encode("ascii").decode(), item["status"]["string"].encode("ascii").decode()))
            except:
                pass
    
    def __parseCapabilities(self):
        if self.device:
            cmd = [ "/usr/sbin/smartctl", "-jc", self.device ]
            out = Helper.sub_process(cmd)
            try:
                cap = Helper.json_loads(out)
                for c in cap["ata_smart_data"]["capabilities"]:
                    self.capabilities[c] = cap["ata_smart_data"]["capabilities"][c]
            except:
                pass
            
            try:
                self.capabilities["poll_short_test"] = cap["ata_smart_data"]["self_test"]["polling_minutes"]["short"]
            except:
                self.capabilities["poll_short_test"] = None
    
    def __isBlockDevice(self, device):
        mode = os.stat(device).st_mode
        return stat.S_ISBLK(mode)
    
    # Versuch sicherzustellen, dass smartctl installiert und neu genug ist.
    # Das Plugin benutzt das JSON-Interface, um Parsing-Aufwand zu vermeiden.
    # Wenn keine passende Version gefunden wird, wird dies über die Informationen
    # zurückgeliefert und angezeigt.
    def __canUseSmartctl(self):
        try:
            cmd = [ "/usr/sbin/smartctl", "-V", ]
            out = Helper.sub_process(cmd)
        except:
            self.information.append( ("Achtung!", '"smartmontools" ist nicht installiert oder defekt.') )
            return False
        
        match = re.search("smartmontools release (.*?) ", out, re.MULTILINE)
        if match:
            version = match.group(1)
            if version < "7.0":
                self.information.append( ("Achtung!", '"smartmontools" sind zu alt (< 7.0)') )
                return False
        else:
            self.information.append( ("Achtung!", '"smartmontools" Version kann nicht ermittelt werden.') )
            return False

        return True
    
    def startShortSelftest(self):
        if self.device:
            cmd = [ "/usr/sbin/smartctl", "-t", "short", self.device ]
            out = Helper.sub_process(cmd)
            print("[SmartControl]", out)
            self.selftests = []
    
    def getDeviceInformation(self):
        if not self.information:
            self.__parseInformationSection()
        return self.information

    def getCapabilities(self):
        if not self.capabilities:
            self.__parseCapabilities()
        return self.capabilities

    # returns list of ascii tuples (id, name, failed, value, worst, thresh, raw)
    def getAttributes(self):
        if not self.attributes:
            self.__parseAttributesBlock()
        return self.attributes

    # returns list of ascii tuples (type, status)
    def getSelftestsLog(self):
        if not self.selftests:
            self.__parseSelftestsLog()
        return self.selftests

    # returns list of ascii tuples (type, status)
    def getErrorLog(self):
        if not self.errors:
            self.__parseErrorLog()
        return self.errors

if __name__ == "__main__":
    import Helper
    d = SmartInfo("sda")
    # print(d.getDeviceInformation())
    print(d.getAttributes())
