""" Script to train the model.

usage: train_model.py [-h] --input-folder INPUT_FOLDER --output-folder
                      OUTPUT_FOLDER

optional arguments:
  -h, --help            show this help message and exit
  --input-folder INPUT_FOLDER, -i INPUT_FOLDER
                        input folder with a dataset for a particular model
  --output-folder OUTPUT_FOLDER, -o OUTPUT_FOLDER
                        output folder for the model
  --model-folder MODEL_FOLDER, -m MODEL_FOLDER
                        existing model folder
"""

import argparse
import os

from model_core import train_and_save, retrain_and_save, test_model


def main():
    """ Main function.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-folder', '-i', dest='input_folder',
                        help='input folder with a dataset for a '
                             'particular model', required=True)
    parser.add_argument('--output-folder', '-o', dest='output_folder',
                        help='output folder for the model', required=True)
    parser.add_argument('--model-folder', '-m', dest='model_folder',
                        help='existing model folder', required=False)
    args = parser.parse_args()

    os.makedirs(args.output_folder, exist_ok=True)
    if args.model_folder:
        retrain_and_save(args.model_folder,
                         os.path.join(args.input_folder, 'training'),
                         os.path.join(args.input_folder, 'validation'),
                         args.output_folder)
    else:
        train_and_save(os.path.join(args.input_folder, 'training'),
                       os.path.join(args.input_folder, 'validation'),
                       args.output_folder)

    test_model(args.output_folder,
         os.path.join(args.input_folder, 'validation'),
         os.path.join(args.output_folder, 'misclassified'))


if __name__ == '__main__':
    main()
