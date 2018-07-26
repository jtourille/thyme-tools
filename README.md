# THYME TOOLS

This repository regroups useful modules for THYME corpus processing.

## Conversion from anafora to brat

THYME corpus annotations are encoded in anafora standoff format. The launcher ANAFORA-TO-BRAT allows to transform 
these annotation to brat format

```shell
python launcher.py ANAFORA-TO-BRAT \
  --input-anafora /path/to/thymedata/coloncancer/Train \
  --input-thyme /path/to/source-data/train \
  --preproc-file /path/to/preprocessing.json \
  --output-dir /path/to/output/brat/coloncancer/train \
  [--overwrite]
  
 python launcher.py ANAFORA-TO-BRAT \
  --input-anafora /path/to/thymedata/coloncancer/Dev \
  --input-thyme /path/to/source-data/dev \
  --preproc-file /path/to/preprocessing.json \
  --output-dir /path/to/output/brat/coloncancer/dev \
  [--overwrite]

python launcher.py ANAFORA-TO-BRAT \
  --input-anafora /path/to/thymedata/coloncancer/Test \
  --input-thyme /path/to/source-data/test \
  --preproc-file /path/to/preprocessing.json \
  --output-dir /path/to/output/brat/coloncancer/test \
  [--overwrite]
```
