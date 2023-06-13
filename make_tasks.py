import os
import json
import math
import random
import argparse
from tqdm import tqdm




def get_captions(image_dir, human_captions_fname, model_captions_list, model_names_list):
    # no class heirarchy. flattened image folder
    images = os.listdir(image_dir)
    with open(human_captions_fname, 'r') as f:
        human_captions = json.load(f)
    human_captions = {k: v for k,v in human_captions.items() if k in images}

    model_caption_dict = {}
    for model_name, model_captions_fname in zip(model_names_list, model_captions_list):
        
        with open(model_captions_fname, 'r') as f:
            model_captions = json.load(f)
        model_captions = {k: v for k,v in model_captions.items() if k in images}

        model_caption_dict[model_name] = model_captions


    return images, human_captions, model_caption_dict


def get_comparisons(images, human_captions, model_caption_dict, num_images):
    random.shuffle(images)
    images = images[:num_images]

    comparisons = {}
    # human to human: 1
    # human to each model: 1
    for img in images:
        comparisons[img] = []
        ref_captions = human_captions[img]
        random.shuffle(ref_captions)
        # for human-human comparisons
        human1 = ref_captions[0]
        human2 = ref_captions[1]
    
        comparisons[img].append({'human1': human1, 'human2': human2})

        # for human-model comparisons
        for model, model_captions in model_caption_dict.items():
            random.shuffle(ref_captions)
            human = ref_captions[0]
            model_caption = model_captions[img]
            comparisons[img].append({'human': human, model: model_caption})

    return comparisons


def get_tasks(images, comparisons, model_caption_dict, num_trials_per_task, num_attention_checks):

    tasks = {}
    num_comparisons = sum([len(v) for v in comparisons.values()])
    num_tasks = math.ceil(num_comparisons / (num_trials_per_task - num_attention_checks))
    image_sample_list = images[:]

    for n in tqdm(range(num_tasks)):
        images_seen = set()
        length = 10
        task_id = ''.join(random.choice('0123456789abcdef') for i in range(length))
        task = [None] * num_trials_per_task
        for i in range(num_trials_per_task):
        
            if not images:
                continue
        
            img = random.choice(images)
            sample_try_count = 0
            while img in images_seen and not n == num_tasks - 1:
                img = random.choice(images)
                if sample_try_count > 10:
                    # we've sampled in an unfortunate way and there are no more
                    # unseen images. At this point, we leave the task with fewer
                    # images than the others and move on.
                    break
                sample_try_count += 1
            continue
            images_seen.add(img)

            comps = comparisons[img]
            idx = random.choice([i for i in range(len(comps))])

            if i < num_attention_checks:
                # add attention check
                distractor_img = img
                while distractor_img == img:
                    distractor_img = random.choice(image_sample_list)
                
                distractor_caption = random.choice(human_captions[distractor_img])

                comp = comps[idx] # don't remove comparison from list
                ids = list(comp.keys())

                caps = {
                    img.split('/')[-1].split('.')[0] + '_attention_check_correct': comp[ids[0]],
                    distractor_img.split('/')[-1].split('.')[0] + 'attention_check_distractor': distractor_caption,
                }

                ids = list(caps.keys())
                random.shuffle(ids)
                task[i] = {
                    'image': img,
                    'c1_id': ids[0],
                    'c1_text': caps[ids[0]],
                    'c2_id': ids[1],
                    'c2_text': caps[ids[1]],
                }
                continue
        
            # add regular comparison
            comp = comps.pop(idx) # remove comparison from list
            if not comps:
                # last comparison added
                del comparisons[img]
                images.remove(img)
            
            ids = list(comp.keys())
            random.shuffle(ids)

            for model_name in model_caption_dict.keys():
                if model_name in ids:
                    name = f'{model_name}-human'
                    break
            if 'human1' in ids:
                name = 'human-human'            

            task[i] = {
                'image': img,
                'c1_id': img.split('/')[-1].split('.')[0] + '_' + name + '_' + ids[0],
                'c1_text': comp[ids[0]],
                'c2_id': img.split('/')[-1].split('.')[0] + '_' + name + '_' + ids[1],
                'c2_text': comp[ids[1]],
            }

        task = [t for t in task if t is not None]
        random.shuffle(task)
        tasks[task_id] = task

    return tasks
        
    


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('image_dir', help="Path to flattened image directory", default="./public/images")
    parser.add_argument('--human_captions', help="Path to human caption json")
    parser.add_argument('--model_captions', help="List of paths to model caption json files", nargs="+")
    parser.add_argument('--model_names', help="List of model names corresponding to json files", nargs="+")
    parser.add_argument('--num_images', help="Number of images to sample for all tasks", default=1000, type=int)
    parser.add_argument('--num_trials_per_task', help="Number of comparisons to include in each task", type=int, default=10)
    parser.add_argument('--num_attention_checks', help="Number of attention checks to include in each task", type=int, default=1)

    args = parser.parse_args()
    assert len(set(args.model_names))  == len(args.model_names) ; "Model names should be distinct"
    assert len(args.model_captions) == len(args.model_names) ; "Should have one distinct model name for each caption"
    images, human_captions, model_caption_dict = get_captions(args.image_dir, args.human_captions, args.model_captions, args.model_names)
    comparisons = get_comparisons(images, human_captions, model_caption_dict, args.num_images)
    tasks = get_tasks(images, comparisons, model_caption_dict, args.num_trials_per_task, args.num_attention_checks)


    if os.path.exists('./server/data/comparison_tasks.json'):
        confirmed = False
        response = input('Directory ./server/data/comparison_tasks.json exists. Overwrite? (y/n)')
        while not confirmed:
            if response.lower() in ['y', 'yes']:
                confirmed = True
            elif response.lower() in ['n', 'no']:
                print('Save ./server/data/comparison_tasks.json under a different name and run again.')
                quit()
            else:
                response = input('Please answer with (y/n)')

    with open('server/data/comparison_tasks.json', 'w') as f:
        json.dump(tasks, f)

