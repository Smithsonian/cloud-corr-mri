import os
import os.path
import sys
from collections import defaultdict

import baseband.vdif as vdif
from pandas_appender import DF_Appender


def index(f, limit=None, only_seconds=False, verbose=False, force_equal_length=True):
    '''Index a vdif file, returning a DataFrame
    '''
    metadata = defaultdict(int)
    metadata['threads'] = set()
    metadata['stations'] = set()

    if verbose:
        print(f)
    with vdif.open(f, 'rb') as fr:
        count = 0
        last_second = 0
        last_frame_nr = 0  # should be per-thread
        first_frame_nbytes = 0  # should be per-thread
        first = True

        dtypes = dict([(k, 'category') for k in ('invalid', 'edv', 'sync_pattern', 'frame_nbytes', 'station', 'thread', 'seconds')])  # pandas
        dfa = DF_Appender(ignore_index=True, dtypes=dtypes)

        while True:
            offset = fr.tell()
            try:
                frame = fr.read_frame(verify=False)
            except Exception as e:
                # if you read garbage, you get things like ValueError: multi-channel VDIF data requires bits per sample that is a power of two
                print('got exception {} reading frame offset={}, skipping'.format(str(e), offset), file=sys.stderr)
                # try to fix the file offset, assuming packets are all the same length
                if first_frame_nbytes:
                    metadata['read_frame exception offset fixup attempt'] += 1
                    fr.seek(offset + first_frame_nbytes, 0)
                else:
                    raise ValueError('the first frame in the file was corrupt, cannot fix up') from e

            invalid = frame.header['invalid_data']

            try:
                frame.verify()
            except Exception as e:
                print('got exception {} verifying frame offset={} invalid={}'.format(str(e), offset, invalid))
                metadata['frame verify exception'] += 1
                continue

            kind = type(frame.header)
            edv = frame.header['edv']
            if edv > 160:
                edv = hex(edv)  # 0xab ... probably bad that edv is either an int or str
            if 'sync_pattern' in frame.header:
                sync_pattern = hex(frame.header['sync_pattern'])  # should be present for edv=2
            else:
                sync_pattern = None
            frame_nbytes = frame.header.frame_nbytes
            station = frame.header.station  # ok to be a str because it is a category
            metadata['stations'].add(station)
            thread = frame.header['thread_id']
            metadata['threads'].add(thread)
            seconds = frame.header['seconds']  # XXX add in the ref_epoch so that this is a unixtime?
            # XXX some kind of check that the ref_epoch does not change -- apparently EVN 2014 screwed this up? XXX baseband fix
            frame_nr = frame.header['frame_nr']

            if first and not invalid:
                first = False
                metadata['kind'] = kind
                metadata['edv'] = edv
                metadata['frame_nbytes'] = frame_nbytes
                metadata['sync_pattern'] = sync_pattern
                metadata['start_seconds'] = seconds  # XXX make sure disorders don't make this wrong
                metadata['end_seconds'] = seconds  # XXX make sure the last packet is this seconds value

                first_frame_nbytes = frame_nbytes
                file_length = os.stat(f).st_size
                if file_length % first_frame_nbytes != 0:
                    print('GREG filesize is not a multiple of the first frame length')
                print('file start, kind={} file_length={} frame_nbytes={} sync_pattern={}'.format(kind, file_length, frame_nbytes, sync_pattern))

            disordered = seconds < last_second
            disordered = disordered or frame_nr < last_frame_nr

            wrong_nbytes = first_frame_nbytes != frame_nbytes
            if wrong_nbytes:
                frame_nbytes_str = ' frame_nbytes={} first_frame_nbytes={}'.format(frame_nbytes, first_frame_nbytes)
                print('GREG quirk frame_length={} frame_nbytes={}'.format(frame.header['frame_length'], frame_nbytes))
                if force_equal_length:
                    # if invalid, this frame's length can be incorrect.
                    # mark6 recorder quirk: it emits a nbytes=10032 filler header but the length is really nbytes=8224
                    # XXX confirm that the bytes really say 1254 is the length
                    # XXX limit this quirk fixup to the exact quirk
                    correct = offset + first_frame_nbytes
                    delta = correct - fr.tell()
                    print('GREG seeking to the usual length, delta={}'.format(delta))
                    fr.seek(correct, 0)
            else:
                frame_nbytes_str = ''

            if invalid or disordered or wrong_nbytes:
                print('bad frame: invalid={} disordered={}{}'.format(invalid, disordered, frame_nbytes_str))
                print(' kind={} edv={} sync_pattern={} offset={} last_second={} second={} last_frame_nr={} frame_nr={}'.format(
                    kind, edv, sync_pattern, offset, last_second, seconds, last_frame_nr, frame_nr))

            if only_seconds and (invalid or seconds == last_second):
                continue

            if verbose:
                print('.', end='')

            if not (invalid or disordered):
                last_second = seconds
                last_frame_nr = frame_nr

            dfa = dfa.append({'invalid': invalid, 'edv': edv, 'sync_pattern': sync_pattern, 'frame_nbytes': frame_nbytes,
                              'offset': offset, 'station': station,
                              'thread': thread, 'seconds': seconds, 'frame_nr': frame_nr})
            if verbose:
                df = dfa.finalize()
                print(df)
            count = count + 1
            if limit and count >= limit:
                break

    if verbose:
        print()
    return dfa.finalize()


def write_ordered(fin, df, fout):
    '''Writes out a vdif file according to the order of DataFrame df
    '''
    with vdif.open(fin, 'rb') as fr, vdif.open(fout, 'wb') as fw:
        for r in df.itertuples():
            fr.seek(r.offset)
            frame = fr.read_frame(edv=2, verify=False)
            fw.write_frame(frame)


def split(f, delta_t=1, nfiles=None):
    with vdif.open(f, 'rb') as fr:
        fw = None
        previous_second = None
        starting_second = None
        basename = None
        while True:
            try:
                frame = fr.read_frame(edv=2, verify=False)
            except EOFError as e:
                print('saw exception {} in {}, terminating'.format(e, basename), file=sys.stderr)
                return
            except Exception as e:
                print('saw exception {}, skipping frame'.format(e), file=sys.stderr)
                continue
            seconds = frame.header['seconds']

            if frame.header['invalid_data']:
                fw.write_frame(frame)
                continue

            if starting_second is None:
                starting_second = seconds

            if previous_second is None or seconds >= previous_second + delta_t:
                if nfiles is not None:
                    if nfiles == 0:
                        break
                    nfiles -= 1
                previous_second = seconds

                #head, tail = os.path.split(f)
                #basename, ext = os.path.splitext(tail)
                basename, ext = os.path.splitext(f)  # write output in the same directory as input

                new = basename + '-' + str(seconds - starting_second) + ext

                if os.path.isfile(new):
                    raise ValueError(new+' already exists')
                fw = vdif.open(new, 'wb')
                print('t={} file {}'.format(seconds, new))

            if seconds < previous_second:
                print('input was not strictly sorted by time: saw {} after {}'.format(seconds, previous_second), file=sys.stderr)

            fw.write_frame(frame)
