#!/usr/bin/env python3

import subprocess
import json
import re
import time
import threading
import http.server
import socketserver

ALLOWED_IPS = [
    '116.203.81.167',  # tools-vm-he-de
    '3.211.80.200',    # infra-reporting-ec2-va
]


def gather_stats():
    """Gathers stats via qshape"""
    while True:
        real_now = time.time()
        now = real_now - (real_now % 300)
        recipient_data = subprocess.check_output(
            '/usr/sbin/qshape | /usr/bin/head -n 25',
            shell=True,
            stderr=subprocess.DEVNULL
        ).decode('ascii')
        sender_data = subprocess.check_output(
            '/usr/sbin/qshape -s | /usr/bin/head -n 25',
            shell=True,
            stderr=subprocess.DEVNULL
        ).decode('ascii')
        recipients = {}
        senders = {}
        for match in re.finditer(r"^\s+([^\s.]+\.\S+)\s+(\d+)((\s+\d+)+)\n", recipient_data, re.MULTILINE):
            domain = match.group(1)
            pending = int(match.group(2))
            times = [int(x) for x in match.group(3).split(' ') if x]
            recipients[domain] = {
                'pending': pending,
                'times': times,
            }
        for match in re.finditer(r"^\s+([^\s.]+\.\S+)\s+(\d+)((\s+\d+)+)\n", sender_data, re.MULTILINE):
            domain = match.group(1)
            pending = int(match.group(2))
            times = [int(x) for x in match.group(3).split(' ') if x]
            senders[domain] = {
                'pending': pending,
                'times': times,
            }

        try:
            file_json = json.loads(open('qshape.json', 'r').read())
        except:
            file_json = []
        while len(file_json) > 288:
            file_json.pop(0)
        file_json.append({
            'timestamp': int(now),
            'recipients': recipients,
            'senders': senders,
        })
        with open('qshape.json', 'w') as f:
            json.dump(file_json, f, indent=2)
            f.close()

        then = time.time()
        diff = then - real_now
        print("Sleeping for %u seconds now.." % (300-diff))
        time.sleep(300 - diff)


class StatsHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.client_address[0] in ALLOWED_IPS:
            print("%s is allowed, handing JSON.." % self.client_address[0])
            self.path = './qshape.json'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        else:
            return None


def main():
    print("Starting stats collector")
    gs = threading.Thread(target=gather_stats)
    gs.start()
    server = socketserver.ThreadingTCPServer(("0.0.0.0", 8083), StatsHttpRequestHandler)
    print("Started json server at 8083...")
    server.serve_forever()


if __name__ == '__main__':
    main()
