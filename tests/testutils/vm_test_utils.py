# Copyright (C) 2017 Codethink Limited
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

'''
Utilities to test a bootable image in QEMU.

Based on the `test-minimal-system` python script at freedesktop-sdk, see the
original source here[0]

[0]: https://gitlab.com/freedesktop-sdk/freedesktop-sdk/blob/master/utils/test-minimal-system
'''

import asyncio
import asyncio.subprocess
import locale
import logging
import sys
import time
import os
import signal


QEMU = 'qemu-system-x86_64'
QEMU_EXTRA_ARGS = ['-m', '256']

FAILURE_TIMEOUT = 300   # seconds
BUFFER_SIZE = 80 # how many characters to read at once

DIALOGS = {
    'minimal':
    [
        "Started '/init' script from initramfs.",
        '\nuname -a',
        "Linux"
    ],
    'systemd-firstboot':
    [
        '-- Press any key to proceed --',
        '',
        'Please enter system locale name or number',
        '1',
        'Please enter system message locale name or number',
        '',
        'Please enter timezone name or number',
        '1',
        'Please enter a new root password',
        'root',
        'Please enter new root password again',
        'root',
        'localhost login',
        'root',
        'Password',
        'root',
        'sh',
        'uname -a',
        'Linux',
        'systemctl poweroff',
        'Power down'
    ],
    'root-login':
    [
        'localhost login',
        'root',
        'Password',
        'root',
        'sh',
        'uname -a',
        'Linux',
        'systemctl poweroff',
        'Power down'
    ]
}


def build_qemu_image_command(image):
    return [QEMU, '-drive', 'file=%s,format=raw' % image, '-nographic'] + QEMU_EXTRA_ARGS


buf = b''

async def await_line(stream, marker):
    '''Read from 'stream' until a line appears that starts with 'marker'.'''
    marker = marker
    global buf

    while not stream.at_eof():
        buf += await stream.read(BUFFER_SIZE)

        lineend = buf.find(b'\n')
        if lineend >= 0:
            line = buf[:lineend+1]
            buf = buf[lineend+1:]

            decoded_line = line.decode('unicode-escape')
            sys.stdout.write(decoded_line)
            if marker in decoded_line.strip():
                logging.debug("Matched line with marker: %s", decoded_line)
                return decoded_line
        else:
            try:
                decoded_buf = buf.decode('unicode-escape')
                if marker in decoded_buf.strip():
                    logging.debug("Matched incomplete line with marker: %s", decoded_buf)
                    sys.stdout.write(decoded_buf)
                    buf = b''
                    return decoded_buf
            except UnicodeDecodeError:
                # we read part of a unicode char
                continue


async def run_test(command, dialog):
    dialog = DIALOGS[dialog]

    logging.debug("Starting process: %s", command)
    process = await asyncio.create_subprocess_exec(
        *command, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        start_new_session=True)

    success = False
    try:
        while dialog:
            prompt = await await_line(process.stdout, dialog.pop(0))
            print("Got:", prompt)
            assert prompt != None

            if dialog:
                process.stdin.write(dialog.pop(0).encode('ascii') + b'\n')

        print("Test successful")
        success = True
    except asyncio.CancelledError:
        # Move straight to killing the process group
        pass
    finally:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass

    await process.communicate()
    await process.wait()
    return success


def fail_timeout(qemu_task):
    sys.stderr.write("Test failed as timeout of %i seconds was reached.\n" %
                     FAILURE_TIMEOUT)
    qemu_task.cancel()


def vm_test(image, *, dialog='root-login'):
    command = build_qemu_image_command(image)

    # TODO: Use asyncio.run() rather than using low level event loop API
    #       asyncio.run() is only provisional API at the moment

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    qemu_task = loop.create_task(run_test(command, dialog))
    loop.call_later(FAILURE_TIMEOUT, fail_timeout, qemu_task)
    loop.run_until_complete(qemu_task)
    loop.close()

    if qemu_task.result():
        return 0
    else:
        return 1
