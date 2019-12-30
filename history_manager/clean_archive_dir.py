""" Script to clean up the archive directory on the host.
"""
import os
import sys
import time

PATH = '/opt/data/images_archive'
DEFAULT_HOURS = 192


def clean_folder(path, oldest_timestamp):
    """ Recursively clean a given folder.

    :param path: path to a folder (string)
    :param oldest_timestamp: oldest timestamp to keep (int)
    """
    for entry in os.listdir(path):
        entry_path = os.path.join(path, entry)
        if (os.path.isfile(entry_path) and
                os.stat(entry_path).st_mtime < oldest_timestamp):
            os.remove(entry_path)
        elif not os.path.isfile(entry_path):
            clean_folder(entry_path, oldest_timestamp)


def main():
    """ Main function.
    """
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_HOURS
    now = time.time()
    oldest_timestamp = now - hours * 3600
    clean_folder(PATH, oldest_timestamp)


if __name__ == '__main__':
    main()
