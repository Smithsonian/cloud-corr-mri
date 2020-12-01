import os.path

import baseband.vdif as vdif
from pandas_appender import DF_Appender


def index(f, limit=None):
    '''Index a vdif file, returning a DataFrame
    '''
    with vdif.open(f, 'rb') as fr:
        count = 0
        dtypes = {'station': 'category', 'thread': 'category', 'seconds': 'category'}
        dfa = DF_Appender(ignore_index=True, dtypes=dtypes)

        while True:
            offset = fr.tell()
            frame = fr.read_frame()
            station = frame.header.station  # ok to be a str because it is a category
            thread = frame.header['thread_id']
            seconds = frame.header['seconds']
            frame_nr = frame.header['frame_nr']

            dfa = dfa.append({'offset': offset, 'station': station,
                              'thread': thread, 'seconds': seconds, 'frame_nr': frame_nr})
            count = count + 1
            if limit and count >= limit:
                break

    return dfa.finalize()


def write_ordered(fin, df, fout):
    '''Writes out a vdif file according to the order of DataFrame df
    '''
    with vdif.open(fin, 'rb') as fr, vdif.open(fout, 'wb') as fw:
        for r in df.itertuples():
            fr.seek(r.offset)
            frame = fr.read_frame()
            fw.write_frame(frame)


def split(f, delta_t=1, nfiles=None):
    with vdif.open(f, 'rb') as fr:
        fw = None
        previous_second = None
        while True:
            frame = fr.read_frame()
            seconds = frame.header['seconds']

            if previous_second is None or seconds >= previous_second + delta_t:
                if nfiles is not None:
                    if nfiles == 0:
                        break
                    nfiles -= 1
                previous_second = seconds
                head, tail = os.path.split(f)
                basename, ext = os.path.splitext(tail)
                new = basename + '-' + str(seconds) + ext
                if os.path.isfile(new):
                    raise ValueError(new+' already exists')
                fw = vdif.open(new, 'wb')
                print('t={} file {}'.format(seconds, new))

            if seconds < previous_second:
                raise ValueError('input was not strictly sorted by time')

            fw.write_frame(frame)
