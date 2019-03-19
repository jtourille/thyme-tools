# THYME TOOLS

This repository regroups useful modules for THYME corpus processing.

## Conversion from anafora to brat

THYME corpus annotations are encoded in anafora standoff format. The launcher ANAFORA-TO-BRAT allows to transform 
these annotations to brat format. 
* Files that are marked as 'in-progress' will be discarded.
* Some entity offsets include a leading and/or a trailing space. These will be removed 
and offsets will be corrected accordingly.

```shell
$ python main.py ANAFORA-TO-BRAT \
    --input-anafora /path/to/thymedata/coloncancer/Train \
    --input-thyme /path/to/source-data/train \
    --preproc-file /path/to/preprocessing.json \
    --output-dir /path/to/output/brat/coloncancer/train \
    [--overwrite]
    
2019-03-19 16:43:18,047 Skipping file ID090_path_266a.Temporal-Entity.gold.completed.xml. Reason: annotation in progress.
2019-03-19 16:43:19,373 Skipping file ID050_clinic_145.Temporal-Relation.gold.completed.xml. Reason: annotation in progress.
2019-03-19 16:43:20,468 Number of corrected entities: 37
2019-03-19 16:43:20,984 Done ! (Time elapsed: 0:00:03)

$ python main.py ANAFORA-TO-BRAT \
    --input-anafora /path/to/thymedata/coloncancer/Dev \
    --input-thyme /path/to/source-data/dev \
    --preproc-file /path/to/preprocessing.json \
    --output-dir /path/to/output/brat/coloncancer/dev \
    [--overwrite]
    
2019-03-19 16:43:29,688 Number of corrected entities: 17
2019-03-19 16:43:29,966 Done ! (Time elapsed: 0:00:02)

$ python main.py ANAFORA-TO-BRAT \
    --input-anafora /path/to/thymedata/coloncancer/Test \
    --input-thyme /path/to/source-data/test \
    --preproc-file /path/to/preprocessing.json \
    --output-dir /path/to/output/brat/coloncancer/test \
    [--overwrite]
    
2019-03-19 16:43:38,075 Number of corrected entities: 18
2019-03-19 16:43:38,330 Done ! (Time elapsed: 0:00:01)
```

## Conversion from brat to anafora

The reverse transformation allows to check if we did not lose information during the anafora-to-brat conversion.

```shell
$ python main.py BRAT-TO-ANAFORA \
    --input--brat /path/to/output/brat/coloncancer/train \
    --output-dir /path/to/output/brat-to-anafota/train
    [--overwrite]
    
$ python main.py BRAT-TO-ANAFORA \
    --input--brat /path/to/output/brat/coloncancer/dev \
    --output-dir /path/to/output/brat-to-anafota/dev
    [--overwrite]
$ python main.py BRAT-TO-ANAFORA \
    --input--brat /path/to/output/brat/coloncancer/test \
    --output-dir /path/to/output/brat-to-anafota/test
    [--overwrite]
```

Once you have anafora payloads, you can run the official evaluation script. Due to multiple offset correction and two 
files skipping, we do not reach a perfect f1-score for all categories. Evaluation script outputs are available within 
this repository under the `logs` directory.

```shell
$ python -m anafora.evaluate \
    -r /path/to/thymedata/coloncancer/Train \
    -p /path/to/output/brat-to-anafota/train > logs/coloncancer-train.log 2>&1
    
$ python -m anafora.evaluate \
    -r /path/to/thymedata/coloncancer/Dev \
    -p /path/to/output/brat-to-anafota/dev > logs/coloncancer-dev.log 2>&1
    
$ python -m anafora.evaluate \
    -r /path/to/thymedata/coloncancer/Test \
    -p /path/to/output/brat-to-anafota/test > logs/coloncancer-test.log 2>&1
```

