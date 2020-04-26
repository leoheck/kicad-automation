#!/usr/bin/env python
#
# Utility functions for UI automation with xdotool in a virtual framebuffer
# with XVFB. Also includes utilities for accessing the clipboard for easily
# and efficiently copy-pasting strings in the UI
# Based on splitflap/electronics/scripts/export_util.py by Scott Bezek
#
#   Copyright 2019 Productize SPRL
#   Copyright 2015-2016 Scott Bezek and the splitflap contributors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import os
import subprocess
import sys
import tempfile
import time
import shutil

from contextlib import contextmanager

# python3-xvfbwrapper
from xvfbwrapper import Xvfb
from kicad_auto import file_util

from kicad_auto import log
logger = log.get_logger(__name__)

class PopenContext(subprocess.Popen):
    def __enter__(self):
        return self
    def __exit__(self, type, value, traceback):
        if self.stdout:
            self.stdout.close()
        if self.stderr:
            self.stderr.close()
        if self.stdin:
            self.stdin.close()
        if type:
            self.terminate()
        # Wait for the process to terminate, to avoid zombies.
        self.wait()

def wait_xserver():
    timeout = 10
    DELAY = 0.5
    logger.debug('Waiting for virtual X server ...')
    if shutil.which('setxkbmap'):
       cmd = ['setxkbmap', '-query']
    elif shutil.which('setxkbmap'):
       cmd = ['xset', 'q']
    else:
       cmd = ['ls']
       logger.warning('No setxkbmap nor xset available, unable to verify if X is running')
    for i in range(int(timeout/DELAY)):
        with open(os.devnull, 'w') as fnull:
             logger.debug('Checking using '+str(cmd))
             ret = subprocess.call(cmd,stdout=fnull,stderr=subprocess.STDOUT,close_fds=True)
             #ret = subprocess.call(['xset', 'q'])
        if not ret:
           return
        logger.debug('   Retry')
        time.sleep(DELAY)
    raise RuntimeError('Timed out waiting for virtual X server')

@contextmanager
def recorded_xvfb(video_dir, video_name, **xvfb_args):
    if video_dir:
       video_filename = os.path.join(video_dir, video_name)
       with Xvfb(**xvfb_args):
           wait_xserver()
           fnull = open(os.devnull, 'w')
           logger.debug('Recording session to %s', video_filename)
           with PopenContext([
                   'recordmydesktop',
                   '--overwrite',
                   '--no-sound',
                   '--no-frame',
                   '--on-the-fly-encoding',
                   '-o', video_filename],
                   stdout=fnull,
                   stderr=subprocess.STDOUT,
                   close_fds=True) as screencast_proc:
               yield
               screencast_proc.terminate()
    else:
       with Xvfb(**xvfb_args):
           wait_xserver()
           yield


def xdotool(command):
    return subprocess.check_output(['xdotool'] + command)

def clipboard_store(string):
    # I don't know how to use Popen/run to make it run with pipes without
    # either blocking or losing the messages.
    # Using files works really well.
    logger.debug('Clipboard store "'+string+'"')
    # Write the text to a file
    fd_in, temp_in = tempfile.mkstemp(text=True)
    os.write(fd_in, string.encode())
    os.close(fd_in)
    # Capture output
    fd_out, temp_out = tempfile.mkstemp(text=True)
    process = subprocess.Popen(['xclip', '-selection', 'clipboard', temp_in],
                               stdout=fd_out, stderr=subprocess.STDOUT)
    ret_code = process.wait()
    os.remove(temp_in)
    os.lseek(fd_out, 0, os.SEEK_SET)
    ret_text = os.read(fd_out,1000)
    os.close(fd_out)
    os.remove(temp_out)
    ret_text = ret_text.decode()
    if ret_text:
       logger.error('Failed to store string in clipboard')
       logger.error(ret_text)
       raise
    if ret_code:
       logger.error('Failed to store string in clipboard')
       logger.error('xclip returned %d' % ret_code)
       raise

def clipboard_retrieve():
    p = subprocess.Popen(['xclip', '-o', '-selection', 'clipboard'], stdout=subprocess.PIPE)
    output = '';
    for line in p.stdout:
        output += line.decode()
    logger.debug('Clipboard retrieve "'+output+'"')
    return output;


def wait_focused(id, timeout=10):
    DELAY = 0.5
    logger.debug('Waiting for %s window to get focus...', id)
    for i in range(int(timeout/DELAY)):
        cur_id = xdotool(['getwindowfocus']).rstrip()
        logger.debug('Currently focused id: %s', cur_id)
        if cur_id==id:
           return
        time.sleep(DELAY)
    raise RuntimeError('Timed out waiting for %s window to get focus' % id)

def wait_not_focused(id, timeout=10):
    DELAY = 0.5
    logger.debug('Waiting for %s window to lose focus...', id)
    for i in range(int(timeout/DELAY)):
        cur_id = xdotool(['getwindowfocus']).rstrip()
        logger.debug('Currently focused id: %s', cur_id)
        if cur_id!=id:
           return
        time.sleep(DELAY)
    raise RuntimeError('Timed out waiting for %s window to lose focus' % id)

def wait_for_window(name, window_regex, timeout=10, focus=True, skip_id=0):
    DELAY = 0.5
    logger.info('Waiting for "%s" ...', name)
    if skip_id: logger.debug('Will skip %s', skip_id)
    xdotool_command = ['search', '--onlyvisible', '--name', window_regex]

    for i in range(int(timeout/DELAY)):
        try:
            window_id = xdotool(xdotool_command).splitlines()
            logger.debug('Found %s window (%d)', name, len(window_id))
            if len(window_id)==1:
               id = window_id[0]
            if len(window_id)>1:
               id = window_id[1]
            logger.debug('Window id: %s', id)
            if id!=skip_id:
               if focus:
                  xdotool_command = ['windowfocus', '--sync', id ]
                  xdotool(xdotool_command)
                  wait_focused(id,timeout)
               return window_id
            else:
               logger.debug('Skipped')
        except subprocess.CalledProcessError:
            pass
        time.sleep(DELAY)
    raise RuntimeError('Timed out waiting for %s window' % name)
