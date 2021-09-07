import time
import subprocess
from collections import defaultdict

def parse_netstat_s(s):
    ret = defaultdict(dict)

    for line in s.splitlines():
        if not line.startswith(' ') and ':' in line:
            section = line.split(':', 1)[0]
            continue
        if line.startswith('    '):
            #print(line)
            #print(line[4:])
            count, message = line[4:].split(' ', 1)
            if not count.isdigit():
                # example: ICMP output histogram
                continue
            count = int(count)
            ret[section][message] = count

    ret['time'] = time.time()
    return ret


def measure_netstat_s():
    completed = subprocess.run(('netstat', '-s'), stdout=subprocess.PIPE)
    return parse_netstat_s(completed.stdout.decode())


def print_one(stat, data, previous_data, delta_t, strict=False):
    section, thing = stat
    if strict and thing not in data[section]:
        print('{} {} appears to not be a valid thing'.format(section, thing))
        print(data[section])
        return
    if thing not in data[section]:
        return
    delta = data[section][thing] - previous_data[section][thing]
    if delta > 0:
        print(delta, section, thing)


def loop():
    previous_data = None
    while True:
        data = measure_netstat_s()
        if previous_data:
            delta_t = data['time'] - previous_data['time']
            for stat in (
                    # not errors
                    ('Udp', 'packets received'),
                    ('Udp', 'packets sent'),
                    # errors
                    ('Udp', 'packet receive errors'),
                    ('Udp', 'receive buffer errors'),
                    ('Udp', 'send buffer errors'),

                    ('Ip', 'dropped because of missing route'),  # RHEL
                    ('Ip', 'packets reassembled ok'),
                    ('Ip', 'incoming packets discarded'),
                    ('Ip', 'outgoing packets dropped'),  # ubuntu 20.4
            ):
                print_one(stat, data, previous_data, delta_t)
        previous_data = data
        time.sleep(1.0)
        print('')
        continue


if __name__ == '__main__':
    loop()
