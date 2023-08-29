# Introduction

This repo is the implementation of the caption comparison task used to
compute HUMANr in NeurIPS submission _ObjectNet Captions: Models are
not superhuman captioners_. We provide code for hosting the experiment
and preparing tasks to be run on Amazon Mechanical Turk. We do not use
the MTurk API, but rather we generate task-link CSVs that can be
uploaded to MTurk. We provide a project template but the user is
required to specify payment, time allocation, etc. themselves on [the
MTurk requester portal](requetser.mturk.com). We encourage the user to
comply with minimum wage regulation and even to be generous with the
rewards they offer.


# Pipeline

This pipeline assumes that you have started redis running on your
machine.

0. Modify the informed consent section in caption_compare/public/compare.html
replace "TODO:University X" with your institution

1. Set experiment variables

```(bash)
$ export REDIS_PORT=<redis port> COMPARISON_TASK_DATABASE=<database number> COMPARISON_TASK_HOST=<hostname> COMPARISON_TASK_PORT=<port number>
```

2. Start server

```(bash)
$ cd server
$ node server.js
```

4. Make task file by running `make_tasks.py`. This creates the
`./server/data/comparison_tasks.json` file that is used to determine
which images and captions to show workers. It requires a few
arguments:

* `image_dir`: The directory containing the images. The directory
  should be flattened, with all images in the top level. Default is `./public/images`.
  
* `--human_captions`: The human caption `.json` file. It should be a
  dictionary mapping image filenames to a list of string captions as
  follows:

```(python)
{
	image0.jpg: ['A red hat', 'A red hat on a table', ...],
	image1.jpg: ['A cat on the floor', 'A rug with a cat on
		    it',...],
	...
}
```

* `--model_captions`: A list of model caption `.json` files. At least one
  must be specified. Model caption files should be dictionaries
  mapping image filenames to one string caption as follows:

```(python)
{
	image0.jpg: 'A red silk hat',
	image1.jpg: 'A brown cat',
	...
}
```

* `--model_names`: A list of model names, one for each model caption
  file.

* `--num_images`: The number of images to use in computing
  HUMANr. Default is 1000.

* `--num_trials_per_task`: The number of comparisons to include in
  each task. Default is 10.

* `--num_attention_check`: The number of attention checks to include
  in each task. Default is 1.

Example usage of `make_tasks.py` is below.

```(bash)
$ python make_tasks.py ./public/images --human_captions human_captions.json  --model_captions model0_captions.json model1_captions.json model2_captions.json --model_names model0 model1 model2 --num_images 2000 --num_trials_per_task 20 --num_attention_checks 2
```

3. Build csv. This file uses the comparison tasks file made in the
previous step to make multiple CSV with task URLs that can be uploaded
to MTurk. Each CSV contains 500 links.

```(bash)
$ cd ../
$ python make_csv.py
```

4. Upload CSV files in `server/data/task_links` to MTurk project.
5. Collect and analyze data stored in redis. Responses are stored as
hash sets under the key with the following `key value field` triples:

* `<link_id> assignmentID <assignment_id>`: Stores the assignment ID
  of the task.
* `<link_id> hitID <hit_id>`: Stores the HIT ID
  of the task.
* `<link_id> workerID <worker_id>`: Stores the worker ID
  of the worker that is peforming the task
* `<link_id> <image_filename> <response value>`: Stores the value of
  the worker's response. Scores are between 1-9 with 1 implying
  preference for the caption on the left and 9 implying preference for
  the caption on the right. In order to determine which caption was
  preferred, find the corresponding comparison metadata in `./server/data/comparison_tasks.json`

6. Compute HUMANr. HUMANr is very simple to comute. It is the average
of the normalized scores for comparisons between a human and a
particular model. Since scores are given 1-9, the user must first
normalize the scores to [-1, 1] such that -1 means preference for the
human caption and 1 means preference for the model caption. Since the
order of the captions is randomized, the user needs to refer to the
`./server/data/comparison_tasks.json' to determine which caption is
preferred.

# Filestructure
The relevant files are:

- `mturk_landing_page.html`: Project template for MTurk web application.
- `server/server.js`: Javascript server for hosting experiments.
- `server/data/comparison_tasks.json`: JSON file containing captions
- and image paths for individual comparison tasks.
- `server/data/task_links/`: Directory containing task CSV files.
- `make_csv.py`: Script for building CSV files.
- `public/`: Frontend code for experiment. Can be left as is with the
- exception of `public/images`.
- `public/images/`: Directory containing all experiment images.

## `server/server.js`

This is the server that hosts the experiment tasks. It expects 4 OS
environment variables to be set
- `REDIS_PORT`: The port number that redis is running on
- `COMPARISON_TASK_DATABASE`: The redis database number that results
will be saved to
- `COMPARISON_TASK_PORT`: The port number that the server will be
listening to.

## `server/data/comparison_tasks.json`

This JSON file contains all the comparison tasks that will be
displayed in the experiment. The format is as follows:

```(python)
{
  <link_id_1>: [{
		  "image": <image_filepath>,
		  "c1_id": <caption1_id>,
		  "c1_text": <caption1_text>,
		  "c1_source": <caption1_source>,
		  "c2_id": <caption2_id>,
		  "c2_text": <caption2_text>,
		  "c2_source": <caption2_source>
 	        },
	        {
		  "image": <image_filepath>,
		  "c1_id": <caption1_id>,
		  "c1_text": <caption1_text>,
		  "c1_source": <caption1_source>,
		  "c2_id": <caption2_id>,
		  "c2_text": <caption2_text>,
		  "c2_source": <caption2_source>
		},
	        ...,
	       ],
  <link_id_2>: [...],
}	      
```

Each link ID is unique and maps to a list of comparison tasks that
will be shown with that particular experiment link. Caption IDs are also be unique even if the same caption is used in multiple
tasks. Each caption ID should includes  information to
unambiguosly retrieve the task information from `comparison_tasks`
even if that particular image or caption text is repeated in multiple
tasks. The caption source should indicate the source of the
caption. For the puposes of our analysis, we assume that
human-generated captions have caption source "human". We also assume
that no image appears twice in a set of tasks assigned to a given
link. If an image appears multiple times, its result will be
overwritten in the database.

## `server/data/task_links/`
This directory stores multiple CSV files which can be uploaded to an
MTurk project. Each CSV contains only one column with title `HIT_Link`
and each line in the CSV is a URL to a set of experiment
tasks described in `comparison_tasks.json`. These CSV files are
generated by `make_csv.py`.

## `make_tasks.py` Make `./server/data/comparison_tasks.json`. See
   above for usage.

## `make_csv.py`
The python script that generates the CSV files in `task_links`. It
expects two OS environment variables to be set:

- `COMPARISON_TASK_HOST`: Hostname of the server hosting the experiments.
- `COMPARISON_TASK_PORT`: Port number that the server is listening to.

It is the responsibility of the user to build a project on MTurk to
upload these CSVs to. The

## `public/`
The web code for the experiment tasks.

## `public/images/`

This is just the directory containing all experiment images. Image
filepaths in `comparison_tasks.json` will be relative to this
directory.
