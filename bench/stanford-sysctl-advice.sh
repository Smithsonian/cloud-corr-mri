#!/bin/sh

# https://srcc.stanford.edu/100g-network-adapter-tuning#Point3

sysctl -w net.core.rmem_max = 268435456
sysctl -w net.core.wmem_max = 268435456
sysctl -w net.ipv4.tcp_rmem = 4096 87380 134217728
sysctl -w net.ipv4.tcp_wmem = 4096 65536 134217728
sysctl -w net.core.netdev_max_backlog = 250000
sysctl -w net.ipv4.tcp_no_metrics_save = 1

# Explicitly set htcp as the congestion control: cubic buggy in older 2.6 kernels
#sysctl -w net.ipv4.tcp_congestion_control = htcp

# If you are using Jumbo Frames, also set this
sysctl -w net.ipv4.tcp_mtu_probing = 1

# recommended for CentOS7/Debian8 hosts
#sysctl -w net.core.default_qdisc = fq

