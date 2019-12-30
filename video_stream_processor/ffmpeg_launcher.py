"""
FFmpeg launcher/wrapper.

Runs FFmpeg command to consume a video stream and break it to images.
"""

import datetime
import json
import logging
import os
import subprocess
import sys

from utils.logging_utils import create_logger

logger = create_logger('ffmpeg_launcher')


def init_logger():
    """ Initialize a logger.
    """
    fh = logging.FileHandler('ffmpeg_launcher.log')
    fh.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)


def get_frame_rate(interval):
    """ Convert interval into frame rate.

    :param interval: interval between shots (seconds)
    :return: frame rate for that interval
    """
    return 1.0 / interval


def init_configuration():
    """ Initialize configuration values.

    :return: dict of configuration values
    """
    if len(sys.argv) == 2:
        config_file = sys.argv[1]
    else:
        raise RuntimeError('Path to configuration file is not specified. '
                           'Set it as first argument of script')

    with open(config_file) as json_config_file:
        json_config = json.load(json_config_file)

    json_config['frame_rate'] = get_frame_rate(json_config['interval'])
    logger.info('Frame rate - %s', json_config['frame_rate'])

    json_config['output_dir'] = os.environ['IMAGES_OUTPUT_DIR'].rstrip('/')
    if not json_config['output_dir']:
        raise RuntimeError('Output dir is not specified. Define '
                           'IMAGES_OUTPUT_DIR environment variable')

    json_config['output_sub_dir'] = datetime.datetime.now().isoformat()
    os.mkdir('{}/{}'.format(json_config['output_dir'], json_config['output_sub_dir']))
    logger.info('Images output dir - %s/%s',
                json_config['output_dir'], json_config['output_sub_dir'])

    json_config['quality'] = ('-qscale:v {}'.format(json_config['quality'])
                              if 'quality' in json_config else '')
    logger.info('Images quality (in range 2-31) - %s', json_config['quality'])

    return json_config


def run_ffmpeg(config):
    """ Start extracting images from a stream.

    :param config: dict of configuration values
    """
    cli = ('ffmpeg -loglevel info {ffmpeg_configurations} -i "{video_url}" '
           '-map 0:0 -r {frame_rate} {quality} {output_dir}/{output_sub_dir}/'
           'out_%05d.{image_format}'.format(
               ffmpeg_configurations=config.get('ffmpeg_configurations', ''),
               video_url=config['video_url'], frame_rate=config['frame_rate'],
               output_dir=config['output_dir'], quality=config['quality'],
               image_format=config['image_format'], output_sub_dir=config['output_sub_dir']))

    subprocess.call(cli, shell=True)


def main():
    """ Entry point.
    """
    init_logger()
    config = init_configuration()
    run_ffmpeg(config)


if __name__ == '__main__':
    main()
