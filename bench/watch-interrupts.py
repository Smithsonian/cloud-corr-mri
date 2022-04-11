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
            line = re.sub(r'\s+', '  ', line.strip())
            counter, rest = line.split(':', 1)
            parts = rest.strip().split('  ')
            for k, v in zip(fields, parts):  # this doesn't process the parts on the end
                ret[k] = int(v)  # all of the CPUn values are ints
            # collect the ones on the end
            rest = parts[len(fields):]
            for r in rest:
                ret[r] = True
    
    ret['time'] = time.time()
    return ret


def print_one(data, previous_data, delta_t):
    for k, v in data.items():
        if isinstance(v, bool):
            continue
        count = data[k] - previous_data[k]
        if count > 0:
            print(k, count)


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
