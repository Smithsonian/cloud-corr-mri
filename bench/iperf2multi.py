#!/usr/bin/env python

import sys

ip = sys.argv[1]
procs = int(sys.argv[2])

bw_per_proc = 100 / procs  # not an integer

buffer_per_proc = 0.01 * 100000 / procs // 8  # 10 milliseconds of 100 gigabit, in megabytes
buffer_per_proc *= 10

for port in range(procs):
    print('iperf -s -P{} --udp -l 8200 -w {}M -p {} &'.format(procs, buffer_per_proc, port+5000))

print('')

for port in range(procs):
    print('iperf -c {} -P{} --udp -l 8200 -w {}M -b {}G -p {} &'.format(ip, procs, buffer_per_proc, bw_per_proc, port+5000))
