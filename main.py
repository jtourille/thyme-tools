import argparse
import logging
import os
import shutil
import sys
import time
from datetime import timedelta

from thyme.anafora import anafora_to_brat, brat_to_anafora
from thyme.utils import ensure_dir

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(title="Sub-commands", description="Valid sub-commands",
                                       help="Valid sub-commands", dest="subparser_name")

    # Thyme corpus conversion from anafora to brat.
    parser_brat_conversion = subparsers.add_parser('ANAFORA-TO-BRAT', help="Anafora to brat conversion")

    parser_brat_conversion.add_argument("--input-anafora",
                                        help="Input anafora annotation directory",
                                        dest="input_anafora", type=str, required=True)
    parser_brat_conversion.add_argument("--input-thyme",
                                        help="Input THYME corpus (text version) directory",
                                        dest="input_thyme", type=str, required=True)
    parser_brat_conversion.add_argument("--preproc-file",
                                        help="Preprocessing json file",
                                        dest="preproc_file", type=str, required=True)
    parser_brat_conversion.add_argument("--output-dir",
                                        help="Output directory where brat files will be stored",
                                        dest="output_dir", type=str, required=True)
    parser_brat_conversion.add_argument("--overwrite",
                                        help="Overwrite existing documents",
                                        dest="overwrite", action="store_true")

    parser_anafora_conversion = subparsers.add_parser('BRAT-TO-ANAFORA', help="Brat to anafora conversion")

    parser_anafora_conversion.add_argument("--input-brat",
                                           help="Input brat annotation directory",
                                           dest="input_brat", type=str, required=True)
    parser_anafora_conversion.add_argument("--output-dir",
                                           help="Output directory where anafora files will be stored",
                                           dest="output_dir", type=str, required=True)
    parser_anafora_conversion.add_argument("--overwrite",
                                           help="Overwrite existing documents",
                                           dest="overwrite", action="store_true")

    args = parser.parse_args()

    timestamp = time.strftime("%Y%m%d-%H%M%S")

    start = time.time()

    if args.subparser_name == "ANAFORA-TO-BRAT":

        # Logging to stdout
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s %(message)s')

        # Checking if input anafora directory exists
        if not os.path.isdir(os.path.abspath(args.input_anafora)):
            raise NotADirectoryError("The input anafora directory does not exist: {}".format(
                os.path.abspath(args.input_anafora)
            ))

        # Checking if input THYME text directory exists
        if not os.path.isdir(os.path.abspath(args.input_thyme)):
            raise NotADirectoryError("The input text directory does not exist: {}".format(
                os.path.abspath(args.input_thyme)
            ))

        if not args.overwrite:
            if os.path.isdir(os.path.abspath(args.output_dir)):
                logging.info("The output directory already exists, use the appropriate launcher flag to overwrite")
                raise IsADirectoryError("The output directory already exists: {}".format(
                    os.path.abspath(args.output_dir)
                ))

        # Checking if preprocessing file exists
        if not os.path.isfile(os.path.abspath(args.preproc_file)):
            raise FileNotFoundError("The preprocessing file does not exists: {}".format(
                os.path.abspath(args.preproc_file)
            ))

        if os.path.isdir(os.path.abspath(args.output_dir)):
            shutil.rmtree(os.path.abspath(args.output_dir))

        ensure_dir(args.output_dir)

        # Starting conversion
        anafora_to_brat(
            os.path.abspath(args.input_anafora),
            os.path.abspath(args.input_thyme),
            os.path.abspath(args.output_dir),
            os.path.abspath(args.preproc_file)
        )

    if args.subparser_name == "BRAT-TO-ANAFORA":

        # Logging to stdout
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s %(message)s')

        # Checking if input brat directory exists
        if not os.path.isdir(os.path.abspath(args.input_brat)):
            raise NotADirectoryError("The input brat directory does not exist: {}".format(
                os.path.abspath(args.input_brat)
            ))

        if not args.overwrite:
            if os.path.isdir(os.path.abspath(args.output_dir)):
                logging.info("The output directory already exists, use the appropriate launcher flag to overwrite")
                raise IsADirectoryError("The output directory already exists: {}".format(
                    os.path.abspath(args.output_dir)
                ))

        brat_to_anafora(input_brat_dir=os.path.abspath(args.input_brat),
                        output_anafora_dir=os.path.abspath(args.output_dir))

    end = time.time()

    logging.info("Done ! (Time elapsed: {})".format(timedelta(seconds=round(end - start))))
