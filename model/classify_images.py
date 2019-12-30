""" Script to classify parking slots as free or occupied.

usage: classify_images.py [-h] --input-folder INPUT_FOLDER --output-folder
                          OUTPUT_FOLDER --model-folder MODEL_FOLDER
                          --model-name MODEL_NAME

optional arguments:
  -h, --help            show this help message and exit
  --input-folder INPUT_FOLDER, -i INPUT_FOLDER
                        input folder with cropped images for a particular
                        model
  --output-folder OUTPUT_FOLDER, -o OUTPUT_FOLDER
                        output folder with classified images for the model
  --model-folder MODEL_FOLDER, -m MODEL_FOLDER
                        model folder
"""

import argparse
import os

from model_core import load_parking_model, classify


def create_output_folders(output_folder):
    """ Create output folders.

    :param output_folder: absolute path to an output folder
    """
    for subfolder in ('free', 'occupied'):
        os.makedirs(os.path.join(output_folder, subfolder), exist_ok=True)


def main():
    """ Main function.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-folder', '-i', dest='input_folder',
                        help='input folder with cropped images for a '
                             'particular model', required=True)
    parser.add_argument('--output-folder', '-o', dest='output_folder',
                        help='output folder with classified images for the '
                             'model', required=True)
    parser.add_argument('--model-folder', '-m', dest='model_folder',
                        help='model folder', required=True)
    args = parser.parse_args()

    load_parking_model(args.model_folder)
    create_output_folders(args.output_folder)
    classify(args.input_folder, args.output_folder,
             os.path.basename(os.path.normpath(args.model_folder)))


if __name__ == '__main__':
    main()
