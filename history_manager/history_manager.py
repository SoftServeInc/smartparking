"""
History manager.

Sends old images to Archive Store and removes them from Operational Store.

Run: python history_manager.py <configuration_file.json>
"""
import re
import traceback
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
from collections import namedtuple
from queue import Queue, Empty
import shutil
import json

import datetime
import os
import sys
import time

from utils.logging_utils import create_logger
from utils.mosquitto_utils import start_messages_consumption
from utils.thread_utils import StopEvent

logger = create_logger('history_manager')

STRATEGIES = {
    'REMOVE': 'rm',
    'SAVE_TO_FS': 'fs'
}

DayRange = namedtuple('DayRange', ['start_m', 'end_m'])

skipped = 0


def get_cli_configuration():
    """ Get configuration values from CLI.

    :return: dict of configuration values
    """
    parser = ArgumentParser(description='test', formatter_class=RawTextHelpFormatter)
    parser.add_argument('-i', '--input-dir', dest='images_root_directory', required=True,
                        help='Root directory with images directories')
    parser.add_argument('-o', '--output-dir', dest='output_dir', required=True,
                        help='Archive directory')
    parser.add_argument('-s', '--strategy', required=True, dest='strategy',
                        help='Historical data strategy. Options:\n'
                             ' - "rm" - removes all historical data \n'
                             ' - "fs" - saves historical data to local FS. '
                             'Use options to configure: "-f" "-ex"',
                        choices=[v.lower() for v in STRATEGIES.values()])
    parser.add_argument('-c', '--client-id', dest='client_id',
                        required=False, default='history_manager',
                        help='Client ID')
    parser.add_argument('-t', '--topic', dest='mq_topic',
                        required=False, default='/plugins/video',
                        help='Input topic name')
    parser.add_argument('-sd', '--sleep-duration', dest='sleep_duration',
                        type=int, required=False, default=1,
                        help='Sleep duration between readings from the topic')
    parser.add_argument('-se', '--save-each', dest='save_each',
                        type=int, required=False, default=1,
                        help='("fs" strategy only)\n'
                             'Save to Archive each N message, others will be skip')
    parser.add_argument('-ex', '--exclude-time',
                        dest='exclude_time', required=False,
                        help='("fs" strategy only)\n'
                             'Exclude this day time from saving to Archive. \n'
                             'Use next format: "1:00-03:00,21:00-23:30,22:0-2:0"')
    parser.add_argument('-ht', '--host', dest='mq_host',
                        required=False, default='mosquitto',
                        help='MQ host')
    parser.add_argument('-p', '--port', dest='mq_port',
                        type=int, required=False, default=1883,
                        help='MQ port')

    return vars(parser.parse_args())


def get_file_configuration():
    """ Get configuration values from the configuration file passed from CLI.

    :return: dict of configuration values
    """
    with open(sys.argv[1]) as json_config_file:
        file_options = json.load(json_config_file)

    file_options['images_root_directory'] = os.environ['IMAGES_INPUT_DIR'].rstrip('/')
    file_options['output_dir'] = os.environ['ARCHIVE_DIR'].rstrip('/')
    file_options.setdefault('client_id', 'history_manager')
    file_options.setdefault('mq_host', 'mosquitto')
    file_options.setdefault('mq_port', 1883)
    file_options.setdefault('sleep_duration', 1)
    file_options.setdefault('save_each', 1)
    file_options.setdefault('exclude_time', None)
    file_options.setdefault('mq_topic', '/plugins/video')

    return file_options


def copy_to_archive(options, data):
    """ Save a metadata file and copy the image to Archive Store.

    :param options: dict of configuration values
    :param data: json of metadata
    """
    output_file_name = data['metadata']['processing_start_time']
    image_extension = os.path.splitext(data['metadata']['source_file'])[1]

    if not os.path.exists(options['output_dir']):
        os.makedirs(options['output_dir'])

    src = os.path.join(options['images_root_directory'],
                       data['metadata']['source_folder'],
                       data['metadata']['source_file'])

    dst = os.path.join(options['output_dir'],
                       output_file_name + image_extension)
    shutil.copyfile(src, dst)

    metadata_file_name = os.path.join(options['output_dir'], output_file_name + '.json')
    with open(metadata_file_name, 'w') as metadata_file:
        json.dump(data, metadata_file)


def is_valid_day_time(exclude_time_list):
    """ Check whether current time should be accepted or not.

    :param exclude_time_list: list of time periods to exclude
    :return: True if current time should be accepted and False otherwise
    """
    if exclude_time_list:
        now = datetime.datetime.now()
        minutes = now.hour * 60 + now.minute
        for ex in exclude_time_list:
            if ex.start_m <= ex.end_m:
                if ex.start_m <= minutes <= ex.end_m:
                    return False
            else:
                if minutes >= ex.start_m or minutes <= ex.end_m:
                    return False

    return True


def save_to_fs(options, data):
    """ Check current time and save the data to Archive Store if needed.

    :param options: dict of configuration values
    :param data: json of metadata
    """
    global skipped
    if is_valid_day_time(options['exclude_time_list']):
        if skipped >= (options['save_each'] - 1):
            copy_to_archive(options, data)
            skipped = 0
        else:
            skipped += 1


def remove_old_dirs(options, data):
    """ Remove old (expired) directories from the file system.

    :param options: dict of configuration values
    :param data: json of metadata
    """
    root_path = options['images_root_directory']
    input_dir = data['metadata']['source_folder']

    input_dir_mtime = os.path.getmtime(
        os.path.join(root_path, input_dir)
    )

    for directory in os.listdir(options['images_root_directory']):
        path = os.path.join(root_path, directory)
        if os.path.getmtime(path) < input_dir_mtime and directory != '.DS_Store':
            shutil.rmtree(path)


def remove_old_files(options, data):
    """ Remove old (expired) files from the file system.

    :param options: dict of configuration values
    :param data: json of metadata
    """
    input_dir = os.path.join(options['images_root_directory'], data['metadata']['source_folder'])
    processed_file = os.path.join(input_dir, data['metadata']['source_file'])

    input_file_mtime = os.path.getmtime(processed_file)

    for file in os.listdir(input_dir):
        path = os.path.join(input_dir, file)
        if os.path.getmtime(path) < input_file_mtime:
            os.remove(path)

    os.remove(processed_file)


def file_is_present(options, data):
    """ Check whether the file exists in Operational Store or not.

    :param options: dict of configuration values
    :param data: json of metadata
    :return: True if the file exists and False otherwise
    """
    file = os.path.join(options['images_root_directory'],
                        data['metadata']['source_folder'],
                        data['metadata']['source_file'])
    return os.path.isfile(file)


def process(options, data):
    """ Process a file to archive.

    :param options: dict of configuration values
    :param data: json of metadata
    """
    if file_is_present(options, data):
        if options['strategy'] == STRATEGIES['SAVE_TO_FS']:
            save_to_fs(options, data)
        elif options['strategy'] == STRATEGIES['REMOVE']:
            pass
        else:
            raise RuntimeError('Unknown strategy - {}'.format(options['strategy']))

        remove_old_dirs(options, data)
        remove_old_files(options, data)


def stop_worker(worker, events, message):
    """ Stop a Mosquitto worker.

    :param worker: Thread object
    :param events: Queue of worker events
    :param message: Reason to stop the worker
    """
    if worker.is_alive():
        logger.warning(message)
        events.put(StopEvent)
        events.join()


def run(options):
    """ Read messages from the queue in a loop and process them.

    :param options: dict of configuration values
    """
    messages = Queue(maxsize=0)
    worker_events = Queue(maxsize=0)
    worker = start_messages_consumption(
        options['client_id'], options['mq_topic'], messages, worker_events,
        clean_session=False, host=options['mq_host'], port=options['mq_port'])

    while True:
        try:
            logger.info('Trying to get message from MQ')
            message = messages.get_nowait()

            try:
                logger.info('Received message from MQ')
                data = json.loads(message.payload)
                logger.info('Starting processing')
                process(options, data)
                logger.info('Finished processing')
            except ValueError as exc:
                logger.warning('Not valid message format from MQ, topic - %s, '
                               'message - %s, error - %s, %s',
                               message.topic, message.payload, type(exc), exc)

            messages.task_done()
        except Empty:
            logger.info('Waiting. MQ is empty')
            time.sleep(options['sleep_duration'])
        except Exception:
            traceback.print_tb(sys.exc_info())
            logger.info('Stopping. Exception occurred')
            stop_worker(worker, worker_events,
                        'Stopping MQ Client thread because exception occurred in main thread')
            raise
        if not worker.is_alive():
            raise RuntimeError('MQ client thread is dead')


def prepare_exclude_time(exclude_time):
    """ Parse string of time periods to exclude.

    :param exclude_time: raw string of time periods to exclude
    :return: list of time periods to exclude
    """
    if exclude_time:
        pattern = re.compile(r'([0-2]?\d):([0-5]?\d)-([0-2]?\d):([0-5]?\d)')
        ranges = []
        for value in exclude_time.split(','):
            time_range = pattern.match(value)
            ranges.append(DayRange(int(time_range.group(1)) * 60 + int(time_range.group(2)),
                                   int(time_range.group(3)) * 60 + int(time_range.group(4))))
        return ranges

    return None


def main():
    """ Entry point.
    """
    if len(sys.argv) == 2:
        options = get_file_configuration()
    else:
        options = get_cli_configuration()
    options['exclude_time_list'] = prepare_exclude_time(options['exclude_time'])
    run(options)


if __name__ == '__main__':
    main()
