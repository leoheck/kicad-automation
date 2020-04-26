#!/usr/bin/python3

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
import time
import re
import argparse

from contextlib import contextmanager
from junit_xml import TestSuite, TestCase

eeschema_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(eeschema_dir)

sys.path.append(repo_root)

from util import file_util
from util.ui_automation import (
    PopenContext,
    xdotool,
    wait_for_window,
    recorded_xvfb,
    clipboard_store,
    clipboard_retrieve
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def dismiss_library_warning():
    # The "Not Found" window pops up if libraries required by the schematic have
    # not been found. This can be ignored as all symbols are placed inside the
    # *-cache.lib file:
    try:
        nf_title = 'Project Rescue Helper'
        wait_for_window(nf_title, nf_title, 5)

        logger.info('Dismiss eeschema library warning window')
        xdotool(['search', '--name', nf_title, 'windowfocus'])
        xdotool(['key', 'Return'])
    except RuntimeError as e:
        print(e)

def dismiss_newer_version():
    try:
        logger.info('Dismiss schematic version notification')
        wait_for_window('Newer schematic version notification', 'Info', 3)

        xdotool(['key', 'Return'])
    except RuntimeError:
        pass

def eeschema_plot_schematic(output_directory, file_format, all_pages):
    if file_format not in ('pdf', 'svg'):
        raise ValueError("file_format should be 'pdf' or 'svg'")

    clipboard_store(output_dir)

    dismiss_library_warning()
    # dismiss_newer_version()

    wait_for_window('eeschema', '\[')

    logger.info('Focus main eeschema window')
    xdotool(['search', '--name', '\[', 'windowfocus'])

    logger.info('Open File->Plot')
    xdotool(['key', 'alt+f', 'Up', 'Up', 'Return'])

    wait_for_window('plot', 'Plot')

    logger.info('Paste output directory')
    xdotool(['key', 'ctrl+v'])

    command_list = ['key',
        'Tab',
        'Tab',
        'space'
    ]
    if file_format == 'pdf':
        logger.info('Select PDF plot format')
        for i in range(3):
            command_list.insert(3, 'Up')
    else:
        logger.info('Select SVG plot format')
        for i in range(2):
            command_list.insert(3, 'Up')

    if not all_pages:   # all pages is default option
        command_list.extend(['Tab', 'Tab', 'Tab', 'Tab', 'Tab'])
    xdotool(command_list)

    logger.info('Plot')
    xdotool(['key', 'Return'])

def set_default_plot_option():
    # eeschema saves the latest plot format, this is problematic because
    # plot_schematic() does not know which option is set (it assumes HPGL)
    opt_file_path = os.path.expanduser('~/.config/kicad/')
    in_p = os.path.join(opt_file_path, 'eeschema')
    if os.path.exists(in_p):
        out_p = os.path.join(opt_file_path, 'eeschema.new')
        in_f = open(in_p)
        out_f = open(out_p, 'w')
        for in_line in in_f:
            param, value = in_line.split('=', 1)
            if param == 'PlotFormat':
                out_line = 'PlotFormat=0\n'  # 1: ps, 4: pdf, 5:svg, 3: dxf, 0: hpgl
            else:
                out_line = in_line
            out_f.write(out_line)
        out_f.close()
        os.remove(in_p)
        os.rename(out_p, in_p)

def eeschema_export_schematic(schematic, output_dir, file_format="svg", all_pages=False):
    screencast_output_file = os.path.join(output_dir, 'export_schematic_screencast.ogv')
    file_format = file_format.lower()
    output_file = os.path.join(output_dir, os.path.splitext(os.path.basename(schematic))[0]+'.'+file_format)
    if os.path.exists(output_file):
        logging.info('Removing old file')
        os.remove(output_file)

    set_default_plot_option()
    os.path.basename('/root/dir/sub/file.ext')

    with recorded_xvfb(screencast_output_file, width=800, height=600, colordepth=24):
        with PopenContext(['eeschema-nightly', schematic], close_fds=True) as eeschema_proc:
            eeschema_plot_schematic(output_dir, file_format, all_pages)
            file_util.wait_for_file_created_by_process(eeschema_proc.pid, output_file)
            eeschema_proc.terminate()

    return output_file

def eeschema_parse_erc(erc_file, warning_as_error=False, generate_junit_xml=False):
    with open(erc_file, 'r') as f:
        lines = f.read().splitlines()
        last_line = lines[-1]

    if generate_junit_xml:
        # Build test suite per sheet. Multiple test failures per test case are
        # not supported bu junit XML.
        test_suites = []
        test_cases = []

        sheet = None

        for i in range(0, len(lines)):
            line = lines[i]
            logger.debug(line)
            if line.startswith('***** Sheet'):
                if sheet is not None:
                    # Build test suite for previous sheet
                    logger.debug('Adding test suite for {}'.format(sheet))
                    test_suites.append(TestSuite('ERC {}'.format(sheet), test_cases))

                m = re.search('^\*\*\*\*\* Sheet (.+)$', line)
                sheet = m.group(1)
                test_cases = []

            else:
                if line.startswith('ErrType'):
                    m = re.search('^ErrType\(([0-9]+)\): (.+)$', line)
                    error_type = m.group(1)
                    message = m.group(2)
                else:
                    continue
                i += 1;
                line = lines[i]

                if not line.startswith('    @'):
                    logger.error('Did not find location on line {}: {}'.format(i, line))
                    continue

                test_case = TestCase('ERC rule {}'.format(error_type), sheet)
                test_case.add_failure_info(message + ' '+line.strip(), failure_type=error_type)
                test_cases.append(test_case)
        if sheet is not None:
            # Add last sheet
            logger.debug('Adding final test suite for {}'.format(sheet))
            test_suites.append(TestSuite('ERC {}'.format(sheet), test_cases))

        output_dir = os.path.dirname(erc_file)
        with open(output_dir+'/junit.xml', 'w') as f:
            TestSuite.to_file(f, test_suites, prettyprint=False)


    logging.debug('Last line: '+last_line)
    m = re.search('^ \*\* ERC messages: ([0-9]+) +Errors ([0-9]+) +Warnings ([0-9]+)+$', last_line)
    messages = m.group(1)
    errors = m.group(2)
    warnings = m.group(3)

    if warning_as_error:
        return int(errors) + int(warnings)
    return int(errors)

def eeschema_run_erc(schematic, output_dir, warning_as_error, generate_junit_xml=False):
    screencast_output_file = os.path.join(output_dir, 'run_erc_schematic_screencast.ogv')

    with recorded_xvfb(screencast_output_file, width=1024, height=768, colordepth=24):
        with PopenContext(['eeschema-nightly', schematic], close_fds=True) as eeschema_proc:
            dismiss_library_warning()
            # dismiss_newer_version()
            logger.info('Focus main eeschema window')
            wait_for_window('eeschema', '\[')

            logger.info('Inspect->Electrical Rules Checker')
            xdotool(['key',
                'alt+i',
                'c'
            ])

            xdotool(['key', 'Return'])
            # Do this now since we have to wait for KiCad anyway
            clipboard_store(output_dir)

            logger.info('Focus Electrical Rules Checker window')
            wait_for_window('Electrical Rules Checker', 'Electrical Rules Checker')
            xdotool(['key',
                'Tab',
                'Tab',
                'Tab',
                'Tab',
                'space',
                'Return'
            ])

            wait_for_window('ERC File save dialog', 'ERC File')
            xdotool(['key', 'Home'])
            logger.info('Pasting output dir')
            xdotool(['key', 'ctrl+v'])
            logger.info('Copy full file path')
            xdotool(['key',
                'ctrl+a',
                'ctrl+c'
            ])

            erc_file = clipboard_retrieve()
            if os.path.exists(erc_file):
                os.remove(erc_file)

            logger.info('Run ERC')
            xdotool(['key', 'Return'])

            logger.info('Wait for ERC file creation')
            file_util.wait_for_file_created_by_process(eeschema_proc.pid, erc_file)

            eeschema_proc.terminate()

    return eeschema_parse_erc(erc_file, warning_as_error, generate_junit_xml)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='KiCad schematic automation')
    subparsers = parser.add_subparsers(help='Command:', dest='command')

    parser.add_argument('schematic', help='KiCad schematic file')
    parser.add_argument('output_dir', help='output directory')

    export_parser = subparsers.add_parser('export', help='Export a schematic')
    export_parser.add_argument('--file_format', '-f', help='Export file format',
        choices=['svg', 'pdf'],
        default='svg'
    )
    export_parser.add_argument('--all_pages', '-a', help='Plot all schematic pages in one file',
        action='store_true'
    )

    erc_parser = subparsers.add_parser('run_erc', help='Run Electrical Rules Checker on a schematic')
    erc_parser.add_argument('--warnings_as_errors', '-w', help='Treat warnings as errors',
        action='store_true'
    )
    erc_parser.add_argument('--junit_xml', '-x', help='Generate junit XML report',
        action='store_true'
    )

    args = parser.parse_args()

    schematic = os.path.abspath(args.schematic)
    if not os.path.isfile(schematic):
        logging.error(args.schematic+' does not exist')
        exit(-1)

    output_dir = os.path.abspath(args.output_dir)+'/'
    file_util.mkdir_p(output_dir)

    if args.command == 'export':
        eeschema_export_schematic(schematic, output_dir, args.file_format, args.all_pages)
        exit(0)
    if args.command == 'run_erc':
        errors = eeschema_run_erc(schematic, output_dir, args.warnings_as_errors, args.junit_xml)
        if errors > 0:
            logging.error('{} ERC errors detected'.format(errors))
            exit(errors)
        exit(0)
    else:
        usage()
        if sys.argv[1] == 'help':
            exit(0)
    exit(-1)
