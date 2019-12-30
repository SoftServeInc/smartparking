""" Script to test the model.

usage: test_model.py [-h] --input-folder INPUT_FOLDER --output-folder
                     OUTPUT_FOLDER --model-folder MODEL_FOLDER

optional arguments:
  -h, --help            show this help message and exit
  --input-folder INPUT_FOLDER, -i INPUT_FOLDER
                        input folder with classified images
  --output-folder OUTPUT_FOLDER, -o OUTPUT_FOLDER
                        output folder for misclassified images
  --model-folder MODEL_FOLDER, -m MODEL_FOLDER
                        model folder
"""

import argparse

from model_core import test


def main():
    """ Main function.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-folder', '-i', dest='input_folder',
                        help='input folder with classified images',
                        required=True)
    parser.add_argument('--output-folder', '-o', dest='output_folder',
                        help='output folder for misclassified images',
                        required=True)
    parser.add_argument('--model-folder', '-m', dest='model_folder',
                        help='model folder', required=True)
    args = parser.parse_args()

    test(args.model_folder, args.input_folder, args.output_folder)


if __name__ == '__main__':
    main()
