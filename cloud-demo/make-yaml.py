#!/usr/bin/env python

import sys
import json
import os.path

import yaml
import mergedeep


def load_one_line(existing, k, v):
    things = k.split('.')
    partial = existing
    for k2 in things[:-1]:
        if isinstance(partial, dict):
            if k2.startswith('[') and k2.endswith(']'):
                if len(partial) == 0:
                    print('I do not know how to replace this empty dict with a list')
                raise ValueError('list syntax seen but this is a dict: '+k2)
            if k2 not in partial:
                partial[k2] = dict()
            partial = partial[k2]
            continue
        elif isinstance(partial, list):
            if k2.startswith('[') and k2.endswith(']'):
                i = int(k2[1:-1])
                if i < len(partial):
                    partial = partial[i]
                    continue
                else:
                    raise ValueError('list too short for '+k2)
            raise ValueError('dict syntax seen but this is a list: '+k2)
        else:
            raise ValueError('partial is type', type(partial))

    final = things[-1]
    if not isinstance(partial, dict):
        raise ValueError('last partial must be a dict, but is instead '+type(partial))
    partial[final] = v


def load_one_thing(existing, thing):
    if ':' in thing:
        load_one_line(existing, *thing.split(':', 1))
        return

    if os.path.isfile(thing):
        with open(thing) as fd:
            f = yaml.safe_load(fd)
        count = sum([1 for x in f.keys() if '.' in x])
        if count > 0:
            for k, v in f.items():
                load_one_line(existing, k, v)
            return
        else:
            mergedeep.merge(existing, f)
            return

    raise ValueError('{} does not appear to be a thing or a file'.format(thing))


aliases = {
    'workers': [
        'max_workers:',
        'available_node_types.ray_worker.min_workers:',
        'available_node_types.ray_worker.max_workers:',
    ],
    'max_workers': [
        'max_workers:',
        'available_node_types.ray_worker.max_workers:',
    ],
    'min_workers': [
        'available_node_types.ray_worker.min_workers:',
    ],
    'machineType': [
        'available_node_types.ray_head.node_config.machineType:',
        'available_node_types.ray_worker.node_config.machineType:',
    ],
    'resources': [
    ],
    'sourceImage': [
        'available_node_types.ray_head.node_config.disks.[0].initializeParams.sourceImage:',
        'available_node_types.ray_worker.node_config.disks.[0].initializeParams.sourceImage:',
    ],
    'preemptible': [
        'available_node_types.ray_worker.node_config.schedulingConfig.preemptible:',
    ],
}

existing = {}
args = sys.argv[1:]
while args:
    verb = args.pop(0)
    if verb in aliases:
        arg = args.pop(0)
        for v in aliases[verb]:
            load_one_thing(existing, v + arg)
    elif verb.endswith(':'):
        arg = args.pop(0)
        if verb[:-1] in aliases:
            for v in aliases[verb[:-1]]:
                load_one_thing(existing, v + arg)
        else:
            load_one_thing(existing, verb + arg)
    else:
        load_one_thing(existing, verb)

print(yaml.dump(existing))
