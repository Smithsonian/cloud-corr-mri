import time
import datetime
import subprocess
import math
from argparse import ArgumentParser


FAILED_TIME = 86400*365 + 42


def extract_delta_seconds(s):
    if ' to start at ' in s:
        tstring = s.split(' to start at ', 1)[1].split(' ')[0]
    else:
        raise ValueError('no time found in: '+s)

    now = int(time.time())

    utc = datetime.timezone.utc
    timestamp = '%Y-%m-%dT%H:%M:%S'
    start = datetime.datetime.strptime(tstring, timestamp).replace(tzinfo=utc).timestamp()
    delta_seconds = int(start - now)
    if delta_seconds <= 1:
        delta_seconds = 0
    return delta_seconds


def get_delay(cmd, value, verbose=False):
    cmd = cmd.format(value)
    completed = subprocess.run(cmd.split(), encoding='utf-8',
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if completed.returncode:
        if 'allocation failure: Invalid partition' in completed.stderr:
            raise ValueError('invalid partition')
        if verbose and 'Requested node configuration is not available' not in completed.stderr:
            print('cmd', cmd)
            for line in completed.stderr.splitlines():
                print(' stderr', line)
            print(' exited', completed.returncode)
        return FAILED_TIME
    out = completed.stderr

    return extract_delta_seconds(out)


def binary_search(cmd, bottom, top, tol=None, verbose=False):
    '''
    Search for the largest value that gives the smallest delay.
    '''

    if top < bottom:
        # can happen if user specifies memmemory/maxmemory
        top = bottom

    smallest = get_delay(cmd, bottom, verbose=verbose)
    if verbose:
        print('starting:', bottom, smallest)

    while True:
        if tol is None:
            middle = (bottom + top)//2  # an integer, rounds down
        else:
            middle = (bottom + top)/2
            middle = middle - math.fmod(middle, tol)  # round down
        if middle == bottom:
            return middle, smallest

        delay = get_delay(cmd, middle, verbose=verbose)
        if verbose:
            print('step:', middle, delay)

        if delay > smallest:
            top = middle
        else:
            smallest = delay
            bottom = middle


def main(verbose=0, minmemory=100, maxmemory=4000, partition=None):

    cmd = 'srun --pty -p {} --cpus-per-task 1 --mem-per-cpu {} -N {} -n {} --test-only'.format(partition, minmemory, '1', '{}')
    # specify --pty to avoid needing a script
    cores, value = binary_search(cmd, 1, 49, verbose=verbose)
    print('largest -N 1 core count available is -n', cores, 'starting in', value, 'seconds')

    cmd = 'srun --pty -p {} --cpus-per-task 1 --mem-per-cpu {} -N 1 -n {} --test-only'.format(partition, '{:.0f}', cores)
    gigs, value = binary_search(cmd, minmemory, max(minmemory, maxmemory), tol=100, verbose=verbose)
    print('-p {} -N 1 -n {} --mem-per-cpu {:.0f} (megabytes) starting in'.format(partition, cores, gigs), value, 'seconds')

# does not work because srun --pty --array is not a valid combination
#    cmd = 'srun --pty -p {} --cpus-per-task 1 --mem-per-cpu {} -N 1 -n {} --array 0-{} --test-only'.format(partition, int(gigs), cores, '{}')
#    array, value = binary_search(cmd, 0, 100, verbose=verbose)
#    print('array of length {} starting in {} seconds'.format(array, value))

'''
(eht38v2) [glindahl@holylogin03 ~]$ python ./squeeze.py
largest -N 1 core count available is -n 22 starting in 0 seconds
-p blackhole -N 1 -n 22 --cpus-per-task 1 --mem-per-cpu 3900 (megabytes) starting in 0 seconds

SLURM_SQUEEZE_DEFAULT_PARTITIONS=blackhole
SLURM_SQUEEZE_ALL_PARTITIONS=backhole,unrestricted,serial_requeue

$ scontrol show config blackhole | grep MaxArraySize
DefMemPerCPU is set for blackhole and bigmem
MaxMemPerCPU is not set for blackhole and bigmem
'''

if __name__ == '__main__':
    parser = ArgumentParser(description='disingenuous command line tool')
    parser.add_argument('--verbose', '-v', action='count', help='increase debugging output')
    parser.add_argument('--minmemory', action='store', type=int, default=100, help='minimum memory-per-cpu in megabytes')
    parser.add_argument('--maxmemory', action='store', type=int, default=4000, help='maximum memory-per-cpu in megabytes')
    parser.add_argument('--partition', '-p', action='store', default=['blackhole'], nargs='*', help='SLURM partition to examine')
    args = parser.parse_args()

    for p in args.partition:
        main(verbose=args.verbose,  minmemory=args.minmemory, maxmemory=args.maxmemory, partition=p)
