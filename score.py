import os
import time
import redis
import argparse
import itertools
import threading
import traceback
import pandas as pd
from make_csv import build_experiment_links
from make_tasks import get_comparisons, get_tasks
from mturk import deploy_hits, check_hits, expire_hits


class server(threading.Thread):
    def __init__(self, thread_name, thread_ID):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.thread_ID = thread_ID
 
    def run(self):
        os.system('node server.js');

        
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
        db=os.environ.get('COMPARISON_TASK_DB')
    )

    results_dict = {}
    for key in client.scan_iter():
        if key not in link_ids:
            coninue

        results_dict[key] = []
        
        results = client.hgetall(key)
        hit_id = results['hitID']
        if hit_id not in link_ids:
            continue
        assignment_id = results['assignmentID']
        worker_id = results['workerID']

        del results['hitID']
        del results['assignmentID']
        del results['workerID']

        task_images = [t["image"] for t in tasks[key]]

        for image in results:
            idx = task_images.index(image)
            results_dict[key].append(task_images[key][idx][:])
            
            source_1 = tasks[key][idx]['c1_source']
            source_2 = tasks[key][idx]['c2_source']

            sources = (source_1, source_2)
            flip = False
            if sources[0] not in ["human1", "human", "correct"]:
                flip = True

            raw_score = int(results[image])
            if flip:
                score = 10 - raw_score

            if "correct" in sources:
                comparison_type == "attention_check"
            elif "human1" in sources:
                comparison_type == "human"
            else:
                if source_1 == "human":
                    comparison_type == source_2
                else:
                    comparison_type == source_1
                    
            results_dict[key][idx]['type'] = comparison_type
            results_dict[key][idx]['raw_score'] = raw_score
            results_dict[key][idx]['score'] = score
            results_dict[key][idx]['assignmentID'] = assignment_id
            results_dict[key][idx]['hitID'] = hit_id
            results_dict[key][idx]['workerID'] = worker_id

    results_df = pd.DataFrame(list(itertools.chain(*[results_dict[x] for x in results_dict])))    
    return results_df


def compute_humanr(results_df):
    failed_attention_checks = results_df[(results_df['type'] == 'attention_check') & (results_df['score'] >= 5)]
    failed_assignments = failed_attention_checks['assignmentID'].unique().tolist()

    # remove assignments with failed attention checks
    results_df = results_df[~results_df['assignmentID'].isin(failed_assignments)]
    results_df = result_df[results_df['type'] != 'attention_check']
    print(f'==> Ignoring {len(failed_assignments)} tasks for failed attention checks')

    # TODO more strict option: remove work from all workers who fail attention checks

    results_df['HUMANr'] = (results_df['score'] - 5) / 4

    model_scores = {}
    model_ci = {}
    for model in results_df['type'].unique():
        model_df = results_df[results_df['type'] == model]
        score = model_df['HUMANr'].mean()
        sem = model_df['HUMANr'].sem()
        ci = stats.t.interval(confidence, len(model_df['HUMANr'])-1, loc=score, scale=sem)

        model_scores['model'] = score
        model_ci['model'] = score - ci.low

    return model_scores, model_ci
    
    

def compute_humanr_from_redis(hit_ids, link_ids, tasks):
    results_df = get_results(hit_ids, link_ids, tasks)
    return compute_humanr(results_df), results_df
    
    

            
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('image_dir', help="Path to flattened image directory", default="./public/images")
    parser.add_argument('--experiment_name', help="Experiment name", default="humanr")
    parser.add_argument('--human_captions', help="Path to human caption json")
    parser.add_argument('--model_captions', help="List of paths to model caption json files", nargs="+")
    parser.add_argument('--model_names', help="List of model names corresponding to json files", nargs="+")
    parser.add_argument('--num_images', help="Number of images to sample for all tasks", default=1000, type=int)
    parser.add_argument('--num_trials_per_task', help="Number of comparisons to include in each task", type=int, default=10)
    parser.add_argument('--num_attention_checks', help="Number of attention checks to include in each task", type=int, default=1)
    parser.add_argument('--reward_per_task', help="Worker reward for completing tasks", type=float, default=0.25)
    parser.add_argument('--sandbox', help="Post hits to MTurk sandbox rather than production environment", action='store_true')
    parser.add_argument('--human_human', help="Include comparisons between human captions for baseline variance", action='store_true')


    args = parser.parse_args()
    assert len(set(args.model_names))  == len(args.model_names) ; "Model names should be distinct"
    assert len(args.model_captions) == len(args.model_names) ; "Should have one distinct model name for each caption"
    images, human_captions, model_caption_dict = get_captions(args.image_dir, args.human_captions, args.model_captions, args.model_names)
    comparisons = get_comparisons(images, human_captions, model_caption_dict, args.num_images, human_human=args.human_human)
    tasks = get_tasks(images, comparisons, model_caption_dict, args.num_trials_per_task, args.num_attention_checks)


    if os.path.exists('./public/data/comparison_tasks.json'):
        repl(
            question='Directory ./public/data/comparison_tasks.json exists. Overwrite? (y/n)',
            yes_response='Task file saved to public/data/comparison_tasks.json',
            no_response='Save ./public/data/comparison_tasks.json under a different name and run again.',
        )

    with open('public/data/comparison_tasks.json', 'w') as f:
        json.dump(tasks, f)

        
    link_ids = tasks.keys()
    links = build_experiment_links()
    print('Experiment links saved to task_links/')

    print('Starting HUMANr collection server...')
    server_thread = server('humanr_server', 0)
    server_thread.start()

    mturk_fee_factor = 1.2
    total_reward = args.reward_per_task * len(links) * mturk_fee_factor
    if not args.sandbox:
        repl(
            question=f'Estimated cost (including MTurk fees): ${total_reward}. Proceed? (y/n)',
            yes_response='Proceeding...',
            no_response='Quitting...',
        )

    preview_url, hit_type_id, hit_ids = deploy_hits(links, args.reward, args.sandbox)

    last_completed = 0
    completed = []
    
    try:
        while len(completed) != len(hit_ids):
            completed = check_hits(hit_ids)

            if len(completed) != last_completed:
                print(f'==> {len(completed)} / {len(hit_ids)} tasks completed')
                humanr_stats, results_df = compute_humanr_from_redis(hit_ids, link_ids, tasks)
                humanr_scores, humanr_ci = humanr_stats
                print('==> Preliminary HUMANr results:')
                for model in humanr_scores:
                    print(f'\t ==> {model}: {humanr_scores[model]} +/- {humanr_ci[model]}')
                    
                print(f'==> Saving results to {args.experiment_name}_humanr_results.csv...')
                print()
                print('Press CTRL-C at any time to stop collection and cancel remaining MTurk tasks...')

            last_completed = len(completed)

    except KeyboardInterrupt:
        print('Stopping collection and canceling tasks...')
        expire_hits(hit_ids)

    except Exception as e:
        print('Something went wrong. Canceling all tasks and exiting...')
        expire_hits(hit_ids)
        print(e)
        print(traceback.format_exc())

    humanr_stats, results_df = compute_humanr_from_redis(hit_ids, link_ids, tasks)
    humanr_scores, humanr_ci = humanr_stats
    print('==> Final HUMANr results:')
    for model in humanr_scores:
        print(f'\t ==> {model}: {humanr_scores[model]} +/- {humanr_ci[model]}')
                    
    print(f'==> Saving results to {args.experiment_name}_humanr_results.csv...')
    print('==> Terminating server and exiting...')
    os._exit(os.EX_OK)






