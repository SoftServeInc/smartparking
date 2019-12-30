""" Core Engine.

Read inputs from Model Engine and Smart Gate (optionally) and generate the outputs.

Run: python core_engine_launcher.py <configuration_file.json> <reservation_file.json>
"""

import json
import logging
import sys
import threading
import time
from queue import Queue, Empty

from core_engine.events import apply_event, remove_old_events
from core_engine.parking_state import ParkingState
from core_engine.rules import RulesManager
from utils.mosquitto_utils import start_messages_consumption
from utils.thread_utils import StopEvent

logger = logging.getLogger('core_engine')


def get_file_configuration():
    """ Get configuration values from the configuration file passed from CLI.

    :return: dict of configuration values
    """
    with open(sys.argv[1]) as json_config_file:
        file_options = json.load(json_config_file)

    file_options.setdefault('mq_host', 'mosquitto')
    file_options.setdefault('mq_port', 1883)
    file_options.setdefault('video_plugin_topics', ['/plugins/video'])
    file_options.setdefault('gate_plugin_topic', '/plugins/gate')
    file_options.setdefault('output_topic', '/engine')
    file_options.setdefault('static_metadata', {})

    return file_options


def get_reservations():
    """ Get reservations from the configuration file passed from CLI.

    :return: dict of reservations in the form:
            {<place id>: <reservation type>}
    """
    with open(sys.argv[2]) as json_reservation_file:
        return json.load(json_reservation_file)


def main():
    """ Entry point.
    """
    options = get_file_configuration()
    messages = Queue(maxsize=0)
    video_plugin_workers_events = Queue(maxsize=0)
    video_plugin_worker = start_messages_consumption(
        'history_manager-video_plugin_client',
        options['video_plugin_topics'],
        messages,
        video_plugin_workers_events,
        clean_session=False,
        host=options['mq_host'],
        port=options['mq_port'])
    gate_plugin_workers_events = Queue(maxsize=0)
    gate_plugin_worker = start_messages_consumption(
        'history_manager-gate_plugin_client',
        options['gate_plugin_topic'],
        messages,
        gate_plugin_workers_events,
        clean_session=False,
        host=options['mq_host'],
        port=options['mq_port'])
    stop_event = threading.Event()
    rules_manager = RulesManager(options)

    parking_state = None
    events = []  # sorted by time, first element of list should be the newest
    reservations = {}
    reservations_refresh_time = 0

    while True:
        start_time = time.time()
        if (start_time - reservations_refresh_time >
                options['reservations_refresh_duration']):
            reservations = get_reservations()
            reservations_refresh_time = start_time

        try:
            logger.debug('Trying to get a message from MQ')
            message = messages.get_nowait()

            try:
                logger.debug('Received a message from MQ: %s', message.payload)
                data = json.loads(message.payload)

                if (not parking_state and
                        message.topic in options['video_plugin_topics']):
                    logger.info('Initialising parking state')
                    parking_state = ParkingState(data, reservations,
                                                 options['windowing'])
                if parking_state:
                    logger.debug('Applying event')
                    apply_event(events, data, message.topic, parking_state,
                                options)
                    logger.debug('Removing old event')
                    remove_old_events(events, options['event_ttl'])
                    logger.debug('Calculating and sending new event')
                    rules_manager.calculate_and_send_state(events,
                                                           parking_state)
                    logger.debug('Finished processing event')
            except ValueError as exc:
                logger.warning('Received an invalid message format from MQ. '
                               'Topic: %s, message: %s, error: %s, %s',
                               message.topic, message.payload, type(exc), exc)

            messages.task_done()
        except Empty:
            logger.debug('MQ is empty, sleeping')
            time.sleep(options['sleep_duration'])

        if (not video_plugin_worker.is_alive() or
                not gate_plugin_worker.is_alive()):
            raise RuntimeError('One or more MQ client threads are dead. '
                               'Video plugin worker: {}. Gate plugin worker: {}'
                               .format(video_plugin_worker.is_alive(),
                                       gate_plugin_worker.is_alive()))

        if stop_event.is_set():
            gate_plugin_workers_events.put(StopEvent())
            video_plugin_workers_events.put(StopEvent())
            break


if __name__ == '__main__':
    main()
