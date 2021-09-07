import time
import re
#import subprocess
#from collections import defaultdict


def parse_proc_interrupts(grep):
    fields = []
    ret = {}

    with open('/proc/interrupts', 'r') as f:
        for line in f:
            if not fields:
                fields = line.split()  # CPU0 CPU1 etc
                continue

            if grep not in line:
                continue

            #   0:         46          0          0          0   IO-APIC-edge      timer
            # no tabs, but there are multiple spaces
            line = re.sub(r'\s{2,}', '  ', line.strip())
            counter, rest = line.split(':', 1)
            parts = rest.strip().split('  ')

            # collect the ones on the end
            name, kind = parts[len(fields):]
            ret[name] = {}
            ret[name]['kind'] = kind
    
            # this doesn't process the parts on the end
            for k, v in zip(fields, parts):
                ret[name][k] = int(v)  # all of the CPUn values are ints

    ret['time'] = time.time()
    return ret


def print_one(data, previous_data, delta_t):
    for name in data:
        if name == 'time':
            continue
        my_line = {}
        for k in data[name]:
            if k == 'kind':
                continue
            count = data[name][k] - previous_data[name][k]
            if count > 0:
                my_line[k] = count
        if my_line:
            print(name, *['{}: {}'.format(k, v) for k, v in my_line.items()])


def loop(grep):
    previous_data = None
    while True:
        data = parse_proc_interrupts(grep)
        if previous_data:
            delta_t = data['time'] - previous_data['time']
            print_one(data, previous_data, delta_t)
        previous_data = data
        time.sleep(1.0)
        print('')
        continue


if __name__ == '__main__':
    loop('mlx')
