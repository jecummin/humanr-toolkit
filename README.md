# Introduction

This repo is the implementation of  HUMANr scoring in NeurIPS submission _ObjectNet Captions: Models are
not superhuman captioners_. HUMANr can be collected using a single
command that will launch caption comparison tasks on Amazon Mechanical
Turk and process results as they come in. We encourage the user to
comply with minimum wage regulation and even to be generous with the
rewards they offer. **This toolkit will always explicitly request your permission before incurring costs on your AWS account.**

# How to run HUMANr

```(bash)
$ git clone https://github.com/jecummin/humanr-toolkit.git && cd humanr-toolkit
$ pip install -r requirement.txt
$ aws configure
$ emacs set_environment.sh
$ source set_environment.sh
$ mv /path/to/image/directory ./public/images
$ python score.py <arguments> ...
```


# Detailed instructions

This pipeline assumes that you have started redis running on your
machine.

1. Clone the repo and install requirements

```(bash)
$ git clone https://github.com/jecummin/humanr-toolkit.git && cd humanr-toolkit
$ pip install -r requirement.txt
```

2. Configure your AWS credentials on your machine if you do not already have AWS configured.

```(bash)
$ aws configure
```

3. Set experiment variables by editing and running `set_environment.sh`

```(bash)
$ emacs set_environment.sh
$ source set_environment.sh
```

4. Move experiment images to `public/images/`. This directory should
be a flattened directory with all images at the top level. The images
must be in this directory so that they can be displayed in the web app
workers use to do the comparison tasks.

```(bash)
$ mv /path/to/image/directory ./public/images/
```

5. Compute HUMANr. You can compute HUMANr from the command line but it
will likely take a few hours depending on how many images and models
you are computing it for. We highly recommend you run it in a separate
terminal session that you can leave running. The command for computing
HUMANr ill look something like this

```(bash)
$ python score.py --experiment_name <experiment_name>
--human_captions <human captions file> --model_captions <model 1
caption file> <model 2 caption file> ...  --model_names <model 1 name> <model 2
name> ... --num_images <number of images> --num_trials_per_task <number of
trials> --num_attention_checks <number of checks> --reward_per_task
<reward> [--sandbox --human_human]
```

The arguments take the following forms:

* `experiment_name`: The name you would like to give this round of
  collection. Should be unique.
  
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
  file. Each should be unique.

* `--num_images`: The number of images to use in computing
  HUMANr. Default is 1000.

* `--num_trials_per_task`: The number of comparisons to include in
  each task. Default is 10.

* `--num_attention_check`: The number of attention checks to include
  in each task. Default is 1.

* `--reward_per_task`: The reward to be given for each task. Please
  comply with wage and ethics standards.

* `--sandbox`: Run tasks in the sandbox development
  environment. Without this flag, tasks will be posted to the
  production environment.

* `--human_human`: Whether to include comparisons between two human
  captions. Without this flag, only model-human comparisons are posted.

The following example runs computes HUMANr for two models (`model0`
and `model1`) without human-human comparisons on the MTurk production
environment using 300 images.

```(bash)
$ python score.py public/images --experiment_name sandbox_model0__model1_human
--human_captions human_captions.json --model_captions model0_captions.json model1_captions.json  --model_names model0 model1 --num_images 300 --num_trials_per_task 10 --num_attention_checks 1 --reward_per_task 0.25

```

4. Wait for collection to finish. The script will periodically compute
HUMANr on the results collected thus far and display them to the
terminal so you can see results as they come in. When the script
terminates (or exits due to an exception or keyboard interrupt), it
will print final HUMANr results and save results as a csv.
