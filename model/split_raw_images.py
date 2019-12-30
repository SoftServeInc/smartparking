""" Script to split raw images to individual parking slots.

usage: split_raw_images.py [-h] --input-folder INPUT_FOLDER --output-folder
                           OUTPUT_FOLDER --conf CONF

optional arguments:
  -h, --help            show this help message and exit
  --input-folder INPUT_FOLDER, -i INPUT_FOLDER
                        input folder with raw images
  --output-folder OUTPUT_FOLDER, -o OUTPUT_FOLDER
                        output folder with cropped slot images
  --conf CONF, -c CONF  parking configuration json
"""

import argparse
import json
import os

from crop_helpers import verify_conf, create_output_folder, extract_and_save


def main():
    """ Main function.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-folder', '-i', dest='input_folder',
                        help='input folder with raw images', required=True)
    parser.add_argument('--output-folder', '-o', dest='output_folder',
                        help='output folder with cropped slot images',
                        required=True)
    parser.add_argument('--conf', '-c', dest='conf',
                        help='parking configuration json', required=True)
    args = parser.parse_args()
    with open(args.conf) as f_conf:
        conf = json.load(f_conf)

    verify_conf(conf)
    create_output_folder(args.output_folder, conf)
    for filename in os.listdir(args.input_folder):
        if filename.endswith('.jpg'):
            extract_and_save(os.path.join(args.input_folder, filename),
                             args.output_folder,
                             conf)


if __name__ == '__main__':
    main()
