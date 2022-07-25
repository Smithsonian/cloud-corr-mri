import paramsurvey

def sleep_worker(pset, system_kwargs, user_kwargs):
    time.sleep(pset['duration'])
    return {'slept': pset['duration']}


paramsurvey.init(backend='ray', 'ray': {'address': 'auto'})

psets = [{'duration': 0.01}] * 1000

results = paramsurvey.map(sleep_worker, psets, verbose=1)

                        
