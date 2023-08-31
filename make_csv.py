import os
import json
import math


def build_experiment_links():
    comparison_task_json = 'public/data/comparison_tasks.json'
    comparison_task_host = os.environ.get('COMPARISON_TASK_HOST', 'localhost')
    comparison_task_port = os.environ.get('COMPARISON_TASK_PORT', '8087')
    with open(comparison_task_json, 'r') as f:
        tasks = json.load(f)


    max_size = 500 # sets the number of links to include in each csv
    task_ids = list(tasks.keys())
    batches = math.ceil(len(task_ids) / max_size)

    if not os.path.exists('task_links/'):
        os.makedirs('task_links/')

    for i in range(batches):
        with open(f'task_links/hit_links_{i}.csv', 'w') as f:
            f.write('HIT_Link\n')
            for task in task_ids[i * max_size : (i + 1) * max_size]:
                f.write(f'http://{comparison_task_host}:{comparison_task_port}/compare.html?link=' + task)
                f.write('\n')
