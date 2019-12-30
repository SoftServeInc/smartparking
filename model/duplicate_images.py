""" Script to duplicate specified images.

usage: duplicate_images.py [-h] --number NUM --files FILES [FILES ...]

optional arguments:
  -h, --help            show this help message and exit
  --number NUM, -n NUM  number of copies
  --files FILES [FILES ...], -f FILES [FILES ...]
                        list of files
"""

import argparse
from shutil import copyfile


def duplicate_file(src_file, num):
    """ Duplicate a file a specified number of times.

    :param src_file: path to a file
    :param num: number of copies
    :return: list of new files
    """
    new_files = []
    for i in range(1, num + 1):
        parts = src_file.split('.')
        dest_file = '{}_copy_{}.{}'.format('.'.join(parts[:-1]),
                                           i, parts[-1])
        copyfile(src_file, dest_file)
        new_files.append(dest_file)

    return new_files


def main():
    """ Main function.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--number', '-n', dest='num',
                        help='number of copies', required=True)
    parser.add_argument('--files', '-f', nargs='+', dest='files',
                        help='list of files', required=True)
    args = parser.parse_args()

    for src_file in args.files:
        new_files = duplicate_file(src_file, int(args.num))
        for new_file in new_files:
            print('Created {}'.format(new_file))


if __name__ == '__main__':
    main()
