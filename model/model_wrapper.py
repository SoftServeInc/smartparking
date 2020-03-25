""" Simple wrapper for the model.
Designed to work inside Docker container.
Here what it does:

1. Loads config (model_config.json) - this file contains such settings as MQ topic to publish,
   MQ host and port, delay in seconds between recognitions, etc.
2. Looks for the latest file inside parking configurations folder (path was loaded at step 1),
   reads it. This is a json file, made via Sloth. We are going to use it as a grid to cut individual
   parking spaces from camera frame.
3. Using OpenCV, reads in the latest frame from camera.
4. Using config from step 2, crops, transforms and saves small images of individual parking spaces.
5. Using trained models classifies all images from step 4 into free or occupied.
6. Measures some additional information (like execution time), publishes it as a json to MQ topic.
7. Waits given in the config file delay before next execution loop. The loop is infinite.
"""
import json
import ntpath
import os
import os.path
import time
from datetime import datetime

from paho.mqtt.publish import single
from model_core import ParkingInference
from utils.logging_utils import create_logger

logger = create_logger('model')


def execute(config_json):
    """ Execute full cycle in a loop. Single cycle ends with publishing result json.

    :param config_json: model config json
    """
    with open(config_json, 'r') as stream:
        config = json.load(stream)

    img_config_refresh_duration = config.get('camera_img_config_refresh_duration')
    delay = config.get('sleep_duration')
    client_id = config.get('client_id')
    topic = config.get('mq_topic')
    host = config.get('mq_host')
    port = config.get('mq_port')
    loop_counter = 0
    last_modified = 0
    parking_coords_refresh_time = 0

    while True:
        logger.debug('Iteration started')
        start_time = time.time()
        if start_time - parking_coords_refresh_time > img_config_refresh_duration:
            logger.debug('Reloading parking configuration')
            parking_coords = get_latest_config(os.environ['CAMERA_IMG_CONFIG_FOLDER'])
            if not parking_coords:
                logger.debug('Found no parking configuration file')
                time.sleep(delay)
                continue

            parking_coords_refresh_time = start_time

        logger.debug('Looking for a new file')
        processing_start_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        (current_img_path, source_folder, current_img_last_modified
        ) = get_latest_img_and_folder(os.environ['SOURCE_IMG_FOLDER'])
        if not current_img_path:
            logger.debug('No images were found. Waiting...')
            time.sleep(delay)
            logger.debug('Iteration finished')
            continue

        if current_img_last_modified > last_modified:
            last_modified = current_img_last_modified
        else:
            logger.debug('Got image that is older than the previous. Skipping iteration...')
            time.sleep(delay)
            logger.debug('Iteration finished')
            continue

        logger.debug('Processing file %s', current_img_path)
        inference = ParkingInference(inference_config=os.environ['INFERENCE_CONFIG'],
                                     parking_coords=parking_coords,
                                     model_path=os.environ['MODEL_PATH'])
        pklot_map = inference.predict(current_img_path)
        logger.debug('Prediction for file %s finished', current_img_path)

        number_of_free_places = 0
        number_of_occupied_places = 0
        for _, state_and_prob in pklot_map.items():
            if state_and_prob[0] == 1:
                number_of_occupied_places += 1
            elif state_and_prob[0] == 0:
                number_of_free_places += 1

        parking_map = {
            'free': number_of_free_places,
            'occupied': number_of_occupied_places
        }
        processing_time = '{0:.2f} ms'.format((time.time() - start_time) * 1000)
        metadata_map = {
            'source_folder': os.path.basename(os.path.normpath(source_folder)),
            'source_file': ntpath.basename(current_img_path),
            'processing_time': processing_time,
            'processing_start_time': processing_start_time
        }
        json_response = {'parking_places': pklot_map,
                         'parking': parking_map,
                         'metadata': metadata_map}

        logger.debug('model output: %s', json_response)
        logger.debug('Preparing results finished')
        single(topic, payload=json.dumps(json_response), qos=0, retain=False,
               hostname=host, port=port, client_id=client_id,
               keepalive=60)
        logger.debug('Posting into topic finished')
        if loop_counter % 100 == 0:
            logger.info('Finished a sequence of 100 iterations: %s, model output: %s',
                        loop_counter, json_response)
        loop_counter += 1
        logger.debug('Iteration finished')


def get_latest_img_and_folder(img_folder):
    """ Get the latest image and its source folder.

    :param img_folder: path to a folder with camera images
    :return: (path to the image, path to its source folder,
              image modification time)
    """
    subdirs = [os.path.join(img_folder, o) for o in os.listdir(img_folder)
               if os.path.isdir(os.path.join(img_folder, o))]
    if not subdirs:
        return None, None, None

    latest_subdir = max(subdirs, key=os.path.getmtime)
    latest_img = None
    last_modified = None
    for file in os.listdir(latest_subdir):
        if file.endswith(('.jpg', '.png', '.bmp')):
            img = os.path.join(latest_subdir, file)
            try:
                modified = os.path.getmtime(img)
                if modified > (last_modified or 0):
                    latest_img = img
                    last_modified = modified
            except FileNotFoundError:
                pass

    return latest_img, latest_subdir, last_modified


def get_latest_config(config_folder):
    """ Get the latest parking configuration.

    :param config_folder: path to a folder parking configuration files
    :return: parking configuration json
    """
    json_config_list = []
    for file in os.listdir(config_folder):
        if file.endswith('.json'):
            json_config_list.append(os.path.join(config_folder, file))

    if not json_config_list:
        return None

    conf_path = max(json_config_list, key=os.path.getmtime)
    with open(conf_path) as f_conf:
        conf = json.load(f_conf)

    return conf


if __name__ == '__main__':
    logger.info('Started model wrapper')
    execute(os.environ['MODEL_CONFIG'])
