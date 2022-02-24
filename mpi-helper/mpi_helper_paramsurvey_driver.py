import argparse

import paramsurvey


def main():
    parser = argparse.ArgumentParser(description='difx_paramsurvey_driver, run inside ray')
    parser.add_argument('--resources', action='store', default='')
    args = parser.parse_args()

    paramsurvey.init(backend='ray')

    psets = get_difx_joblists()
    add_costs(psets)
    resources = analyze_resources(args.resources)
    schedule_resources(resources, psets)

    # this is how ray backend args are specified
    for p in psets:
        if 'num_cores' in p:
            p['ray'] = {'num_cores': p.pop('num_cores')}

    # example of how to return stdout
    user_kwargs = {'run_kwargs': {'stdout': subprocess.PIPE, 'encoding': 'utf-8'}}

    results = paramsurvey.map(difx_run_worker, psets, user_kwargs=user_kwargs)

    # YYY explicitly tear down the clsuter?

    for r in results.itertuples():
        # r.cli is a subprocess.CompletedProcess object
        print(r.cli.returncode, r.cli.stdout.rstrip())


if __name__ == '__main__':
    main()
