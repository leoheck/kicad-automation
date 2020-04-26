#!/usr/bin/python3

#
#   UI automation script to run DRC on a KiCad PCBNew layout
#   Sadly it is not possible to run DRC with the PCBNew Python API since the
#   code is to tied in to the UI. Might change in the future.
#
#   Copyright 2019 Productize SPRL
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

import sys
import os
import logging
import argparse
from xvfbwrapper import Xvfb

pcbnew_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(pcbnew_dir)

sys.path.append(repo_root)

from util import file_util
from util.ui_automation import (
    PopenContext,
    xdotool,
    wait_for_window,
    recorded_xvfb,
    clipboard_store
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def run_export_step(pcb_file, output_dir, record=True):

    file_util.mkdir_p(output_dir)

    recording_file = os.path.join(output_dir, 'run_export_step.ogv')
    
    board = ''.join(map(str, pcb_file.split('.')[0:-1]))
    step_file = os.path.join(os.path.abspath(output_dir), board + ".step")

    xvfb_kwargs = {
	    'width': 800,
	    'height': 600,
	    'colordepth': 24,
    }

    with recorded_xvfb(recording_file, **xvfb_kwargs) if record else Xvfb(**xvfb_kwargs):
        with PopenContext(['pcbnew', pcb_file], close_fds=True) as pcbnew_proc:

            print(step_file)
            clipboard_store(step_file.encode())

            window = wait_for_window('pcbnew', 'Pcbnew', 10, False)

            logger.info('Focus main pcbnew window')
            wait_for_window('pcbnew', 'Pcbnew')

            # Needed to rebuild the menu, making sure it is actually built
            xdotool(['windowsize', '--sync', window, '750', '600'])
            wait_for_window('pcbnew', 'Pcbnew')

            logger.info('Open File->Export->Step')
            xdotool(['key',
                'alt+f',
                'Down', 'Down', 'Down', 'Down', 'Down', 'Down', 'Down', 'Down', 'Down',
                'Right',
                'Down', 'Down', 'Down', 'Down',
                'Return'
            ])

            logger.info('Focus Export STEP modal window')
            wait_for_window('Export STEP modal window', 'Export STEP')

            logger.info('Pasting output file')
            logger.info(step_file)
            xdotool(['key', 'ctrl+v'])

            xdotool(['key',
                'Tab',
                'Tab',
                'Down', 'Down', 'Down', 'Down', # Board center origin
                'Tab','Tab','Tab','Tab','Tab','Tab','Tab','Tab','Tab','Tab',
                'Return'
            ])

            try:
                wait_for_window('STEP Export override dialog', 'STEP Export')
                xdotool(['key', 'Return'])
            except:
                print("Timeout")

            logger.info('Close Export STEP modal window')
            xdotool(['key', 'Tab','Tab','Tab','Tab','Tab', 'Return'])

            pcbnew_proc.terminate()

    return step_file


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='KiCad Step exporter')

    parser.add_argument('kicad_pcb_file', help='KiCad layout file')
    parser.add_argument('output_dir', help='Output directory')
    parser.add_argument('--record', help='Record the UI automation',
        action='store_true'
    )

    args = parser.parse_args()

    export_result = run_export_step(args.kicad_pcb_file, args.output_dir, args.record)
