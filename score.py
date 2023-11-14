import os
import time
import redis
import json
import argparse
import itertools
import threading
import traceback
import subprocess
import pandas as pd
from tqdm import tqdm
from scipy import stats
from mturk import deploy_hits, check_hits, expire_hits
from make_tasks import get_captions, get_comparisons, get_tasks, build_experiment_links


class server(threading.Thread):
    def __init__(self, thread_name, thread_ID):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.thread_ID = thread_ID
 
    def run(self):
        proc = subprocess.Popen(['node', 'server.js'])
        self.pid = proc.pid

    def kill(self):
        os.system(f'kill {self.pid}')
        
        
def repl(question, yes_response, no_response):
    confirmed = False
    response = input(question)
    while not confirmed:
        if response.lower() in ['y', 'yes']:
            confirmed = True
            print(yes_response)
        elif response.lower() in ['n', 'no']:
            print(no_response)
            quit()
        else:
            response = input('Please answer with (y/n)')

            
def get_results(hit_ids, link_ids, tasks):
    client = redis.Redis(
        host=os.environ.get('REDIS_HOST'),
        port=os.environ.get('REDIS_PORT'),
        password=os.environ.get('REDIS_PASSWORD'),
        db=os.environ.get('COMPARISON_TASK_DATABASE')
    )

    results_dict = {}
    for key in client.scan_iter():
        key = key.decode()
        if key not in link_ids:
            continue


        results_dict[key] = []
        
        results = client.hgetall(key)
        results = {k.decode(): v.decode() for k,v in results.items()}
        hit_id = results['hitID']
        
        if hit_id not in hit_ids:
            continue
        
        assignment_id = results['assignmentID']
        worker_id = results['workerID']

        del results['hitID']
        del results['assignmentID']
        del results['workerID']

        task_images = [t["image"] for t in tasks[key]]
        for image in results:
            idx = task_images.index(image)
            results_dict[key].append({k:v for k,v in tasks[key][idx].items()})
            
            source_1 = tasks[key][idx]['c1_source']
            source_2 = tasks[key][idx]['c2_source']

            sources = (source_1, source_2)
            flip = False
            if sources[0] not in ["human1", "human", "correct"]:
                flip = True

            raw_score = int(results[image])
            if flip:
                score = 10 - raw_score
            else:
                score = raw_score

            if "correct" in sources:
                comparison_type = "attention_check"
            elif "human1" in sources:
                comparison_type = "human"
            else:
                if source_1 == "human":
                    comparison_type = source_2
                else:
                    comparison_type = source_1
                    
            results_dict[key][-1]['type'] = comparison_type
            results_dict[key][-1]['raw_score'] = raw_score
            results_dict[key][-1]['score'] = score
            results_dict[key][-1]['assignmentID'] = assignment_id
            results_dict[key][-1]['hitID'] = hit_id
            results_dict[key][-1]['workerID'] = worker_id

    results_df = pd.DataFrame(list(itertools.chain(*[results_dict[x] for x in results_dict])))    
    return results_df


def compute_humanr(results_df):
    failed_attention_checks = results_df[(results_df['type'] == 'attention_check') & (results_df['score'] >= 5)]
    failed_assignments = failed_attention_checks['assignmentID'].unique().tolist()

    # remove assignments with failed attention checks
    results_df = results_df[~results_df['assignmentID'].isin(failed_assignments)]
    results_df = results_df[results_df['type'] != 'attention_check']
    print(f'==> Ignoring {len(failed_assignments)} tasks for failed attention checks')

    # TODO more strict option: remove work from all workers who fail attention checks

    results_df['HUMANr'] = (results_df['score'] - 5) / 4

    model_scores = {}
    model_ci = {}
    confidence = 0.95
    for model in results_df['type'].unique():
        model_df = results_df[results_df['type'] == model]
        score = model_df['HUMANr'].mean()
        sem = model_df['HUMANr'].sem()
        if sem:
            ci = stats.t.interval(confidence, len(model_df['HUMANr'])-1, loc=score, scale=sem)
        else:
            ci = (score, score)

        model_scores[model] = score
        model_ci[model] = score - max(ci[0], -1)

    return model_scores, model_ci
    
    

def compute_humanr_from_redis(hit_ids, link_ids, tasks):
    results_df = get_results(hit_ids, link_ids, tasks)
    return compute_humanr(results_df), results_df
    
    

            
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--experiment_name', help="Experiment name", default="humanr")
    parser.add_argument('--human_captions', help="Path to human caption json")
    parser.add_argument('--model_captions', help="List of paths to model caption json files", nargs="+")
    parser.add_argument('--model_names', help="List of model names corresponding to json files", nargs="+")
    parser.add_argument('--num_images', help="Number of images to sample for all tasks", default=1000, type=int)
    parser.add_argument('--num_trials_per_task', help="Number of comparisons to include in each task", type=int, default=10)
    parser.add_argument('--num_attention_checks', help="Number of attention checks to include in each task", type=int, default=1)
    parser.add_argument('--reward_per_task', help="Worker reward for completing tasks", type=float)
    parser.add_argument('--sandbox', help="Post hits to MTurk sandbox rather than production environment", action='store_true')
    parser.add_argument('--human_human', help="Include comparisons between human captions for baseline variance", action='store_true')


    args = parser.parse_args()
    assert len(set(args.model_names))  == len(args.model_names) ; "Model names should be distinct"
    assert len(args.model_captions) == len(args.model_names) ; "Should have one distinct model name for each caption"
    images, human_captions, model_caption_dict = get_captions('./public/images', args.human_captions, args.model_captions, args.model_names)
    comparisons = get_comparisons(images, human_captions, model_caption_dict, args.num_images, human_human=args.human_human)
    tasks = get_tasks(images, comparisons, human_captions, model_caption_dict, args.num_trials_per_task, args.num_attention_checks)


    if os.path.exists('./public/data/comparison_tasks.json'):
        repl(
            question='Directory ./public/data/comparison_tasks.json exists. Overwrite? (y/n)',
            yes_response='Task file saved to public/data/comparison_tasks.json',
            no_response='Save ./public/data/comparison_tasks.json under a different name and run again.',
        )

    with open('public/data/comparison_tasks.json', 'w') as f:
        json.dump(tasks, f)

        
    link_ids = list(tasks.keys())
    links = build_experiment_links(link_ids)
    print('Experiment links saved to task_links/')

    print('Starting HUMANr collection server...')
    server_thread = server('humanr_server', 0)
    server_thread.start()
    time.sleep(3)

    mturk_fee_factor = 1.2
    total_reward = args.reward_per_task * len(links) * mturk_fee_factor
    if not args.sandbox:
        repl(
            question=f'Estimated cost (including MTurk fees): ${total_reward}. Proceed? (y/n)',
            yes_response='Proceeding...',
            no_response='Quitting...',
        )

    try:
        preview_url, hit_type_id, hit_ids = deploy_hits(links, args.reward_per_task, args.sandbox)
    except Exception as e:
        print('Killing server and exiting')
        print(traceback.format_exc())
        server_thread.kill()
        os._exit(os.EX_OK)


        

    last_completed = 0
    completed = []

    with open('latest_run.json', 'w') as f:
        json.dump({'hit_ids': hit_ids, 'link_ids': link_ids, 'tasks': tasks}, f)

    results_df = None
    try:
        while len(completed) != len(hit_ids):
            time.sleep(10)
            completed = check_hits(hit_ids)

            if len(completed) != last_completed:
                print()
                print(f'==> {len(completed)} / {len(hit_ids)} tasks completed')
                humanr_stats, results_df = compute_humanr_from_redis(hit_ids, link_ids, tasks)
                humanr_scores, humanr_ci = humanr_stats
                print('==> Preliminary HUMANr results:')
                for model in humanr_scores:
                    print(f'\t ==> {model}: {humanr_scores[model]} +/- {humanr_ci[model]}')
                    
                print(f'==> Saving results to {args.experiment_name}_humanr_results.csv...')
                results_df.to_csv(f'{args.experiment_name}_humanr_results.csv')
                print()
                print('Press CTRL-C at any time to stop collection and cancel remaining MTurk tasks...')

            last_completed = len(completed)

    except KeyboardInterrupt:
        print('Stopping collection and canceling tasks...')
        expire_hits(hit_ids)

    except Exception as e:
        print('Something went wrong. Canceling all tasks and exiting...\n')
        expire_hits(hit_ids)
        print(e)
        print(traceback.format_exc())

    if results_df is None:
        print('No results to save. Exiting...\n')
        server_thread.kill()
        os._exit(os.EX_OK)
        
    humanr_stats, results_df = compute_humanr_from_redis(hit_ids, link_ids, tasks)
    humanr_scores, humanr_ci = humanr_stats
    print('==> Final HUMANr results:')
    for model in humanr_scores:
        print(f'\t ==> {model}: {humanr_scores[model]} +/- {humanr_ci[model]}')
                    
    print(f'==> Saving results to {args.experiment_name}_humanr_results.csv...')
    results_df.to_csv(f'{args.experiment_name}_humanr_results.csv')
    print('==> Terminating server and exiting...')
    server_thread.kill()
    os._exit(os.EX_OK)






