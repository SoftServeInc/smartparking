""" Script to split classified images into a training and validation sets.

usage: split_dataset.py [-h] --input-folder INPUT_FOLDER --output-folder
                        OUTPUT_FOLDER [--auto-oversampling]

optional arguments:
  -h, --help            show this help message and exit
  --input-folder INPUT_FOLDER, -i INPUT_FOLDER
                        input folder with classified images for a particular
                        model
  --output-folder OUTPUT_FOLDER, -o OUTPUT_FOLDER
                        output folder for the model
  --auto-oversampling, -a
                        do automatic oversampling if needed
"""

import argparse
import math
import random
import os

from shutil import copyfile
from duplicate_images import duplicate_file

VALIDATION = 0.1
MIN_TRAINING = 0.175
MIN_OVERSAMPLING = 0.02
THRESHOLD_1 = VALIDATION + (1 - VALIDATION * 2) * MIN_TRAINING
THRESHOLD_2 = VALIDATION + MIN_OVERSAMPLING
THRESHOLD_3 = MIN_OVERSAMPLING * 2


class DatasetException(Exception):
    """ Dataset exception.
    """


def create_output_folders(output_folder):
    """ Create output folders.

    :param output_folder: absolute path to an output folder
    """
    for subfolder_1 in ('training', 'validation'):
        for subfolder_2 in ('free', 'occupied'):
            os.makedirs(os.path.join(output_folder, subfolder_1, subfolder_2),
                        exist_ok=True)


def list_images(folder):
    """ List images in a folder.

    :param folder: absolute path to a folder
    :return: list of images
    """
    res = [os.path.join(folder, f) for f in os.listdir(folder)
           if f.endswith('.png')]
    return res


def analyze_dataset(num_free, num_occupied):
    """ Check whether input folder contains enough free and occupied images.

    :param num_free: number of free images
    :param num_occupied: number of occupied images
    :return: results:
        {'free': {'add_manually': <number of images to add manually>,
                   'oversample': <number of images to oversample>},
         'occupied': {'add_manually': <number of images to add manually>,
                      'oversample': <number of images to oversample>}
         'validation': <number of images in validation set of each type>
        }
    """
    num_total = num_free + num_occupied
    num_validation = math.ceil(num_total * VALIDATION)
    num_current = {'free': num_free, 'occupied': num_occupied}
    res = {}
    for img_type in ('free', 'occupied'):
        res[img_type] = {'add_manually': 0,
                         'oversample': 0}
        img_pct = num_current[img_type] / num_total
        if img_pct < THRESHOLD_1:
            res[img_type]['add_manually'] = math.ceil(
                (num_total * THRESHOLD_1 - num_current[img_type]) /
                (1 - THRESHOLD_1))

            if img_pct < THRESHOLD_3:
                num_validation = math.ceil(num_current[img_type] / 2)
            elif THRESHOLD_3 <= img_pct < THRESHOLD_2:
                num_validation = math.ceil(
                    num_total * (img_pct - MIN_OVERSAMPLING))

            res[img_type]['oversample'] = math.ceil(
                (MIN_TRAINING * num_total +
                 (1 - 2 * MIN_TRAINING) * num_validation -
                 num_current[img_type]) / (1 - MIN_TRAINING))

    res['validation'] = num_validation

    return res


def oversample_images(img_list, num):
    """ Oversample existing images and add new files to the list.

    :param img_list: list of existing images
    :param num: number of images to add
    """
    choices = {}
    for _ in range(num):
        img = random.choice(img_list)
        choices[img] = choices.get(img, 0) + 1

    for img, cnt in choices.items():
        img_list.extend(duplicate_file(img, cnt))


def copy_to_validation(img_list, img_type, num, output_folder):
    """ Copy images to validation folder and remove them from the list.

    :param img_list: list of images
    :param img_type: either "free" or "occupied"
    :param num: number of images to copy
    :param output_folder: absolute path to an output folder
    """
    for _ in range(num):
        img = random.choice(img_list)
        dest_file = os.path.join(output_folder, 'validation', img_type,
                                 os.path.basename(os.path.normpath(img)))
        copyfile(img, dest_file)
        img_list.remove(img)


def copy_to_training(img_list, img_type, output_folder):
    """ Copy images to training folder.

    :param img_list: list of images
    :param img_type: either "free" or "occupied"
    :param output_folder: absolute path to an output folder
    """
    for img in img_list:
        dest_file = os.path.join(output_folder, 'training', img_type,
                                 img.split('/')[-1].split('\\')[-1])
        copyfile(img, dest_file)


def main():
    """ Main function.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-folder', '-i', dest='input_folder',
                        help='input folder with classified images for a '
                             'particular model', required=True)
    parser.add_argument('--output-folder', '-o', dest='output_folder',
                        help='output folder for the model', required=True)
    parser.add_argument('--auto-oversampling', '-a', dest='auto_oversampling',
                        help='do automatic oversampling if needed',
                        default=False, action='store_true')
    args = parser.parse_args()

    img_free = list_images(os.path.join(args.input_folder, 'free'))
    if not img_free:
        raise DatasetException('No free images found')
    elif len(img_free) < 10:
        raise DatasetException('At least 10 free images needed')

    img_occupied = list_images(os.path.join(args.input_folder, 'occupied'))
    if not img_occupied:
        raise DatasetException('No occupied images found')
    elif len(img_occupied) < 10:
        raise DatasetException('At least 10 occupied images needed')

    res = analyze_dataset(len(img_free), len(img_occupied))
    if not args.auto_oversampling:
        if res['free']['add_manually']:
            raise DatasetException(
                'Not enough free images: either add {} images manually or '
                'pass --auto-oversampling argument'
                .format(res['free']['add_manually']))

        if res['occupied']['add_manually']:
            raise DatasetException(
                'Not enough occupied images: either add {} images manually or '
                'pass --auto-oversampling argument'
                .format(res['occupied']['add_manually']))

    create_output_folders(args.output_folder)
    copy_to_validation(img_free, 'free', res['validation'],
                       args.output_folder)
    copy_to_validation(img_occupied, 'occupied', res['validation'],
                       args.output_folder)

    if res['free']['oversample']:
        oversample_images(img_free, res['free']['oversample'])

    if res['occupied']['oversample']:
        oversample_images(img_occupied, res['occupied']['oversample'])

    copy_to_training(img_free, 'free', args.output_folder)
    copy_to_training(img_occupied, 'occupied', args.output_folder)


if __name__ == '__main__':
    main()
