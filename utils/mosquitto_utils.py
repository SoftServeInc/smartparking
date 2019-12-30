""" Mosquitto utils.
"""
from queue import Empty
from threading import Thread

import paho.mqtt.client as mqtt

from utils.logging_utils import create_logger
from utils.thread_utils import is_stop_event

logger = create_logger('mosquitto')


def __on_connect(client, userdata, _flags, code):
    if code != 0:
        logger.info('Connection failed. Not valid return code %s', code)
    else:
        logger.info('Connected. Subscribing to topic(s): %s', userdata['topic'])

    if isinstance(userdata['topic'], list):
        client.subscribe([(t, 0) for t in userdata['topic']])
    else:
        client.subscribe(userdata['topic'], 0)


def __on_message(_client, userdata, msg):
    userdata['queue'].put(msg)


def __on_disconnect(_client, userdata, code):
    logger.info('Disconnection with return code %s, for topic(s): %s',
                code, userdata['topic'])


def __consume(client_id, topic, out_queue, event_queue, clean_session, host, port):
    client = mqtt.Client(client_id=client_id, clean_session=clean_session,
                         userdata={'topic': topic, 'queue': out_queue})
    client.on_connect = __on_connect
    client.on_message = __on_message
    client.on_disconnect = __on_disconnect

    client.reconnect_delay_set(min_delay=3, max_delay=300)
    client.connect(host, port, 60)

    while True:
        try:
            message = event_queue.get_nowait()
            event_queue.task_done()
            if is_stop_event(message):
                break
        except Empty:
            pass
        client.loop(timeout=1.0)


def start_messages_consumption(client_id, topic, out_queue, event_queue,
                               clean_session=True, host='localhost', port=1883):
    """ Start reading messages from the topic(s) and return the worker thread.
    :param client_id: client id (string)
    :param topic: either a single or a list of topic names
    :param out_queue: Queue of output messages
    :param event_queue: Queue of worker events
    :param clean_session: whether to clean a session or not (boolean)
    :param host: Mosquitto host
    :param port: Mosquitto port
    :return: Thread object
    """
    worker = Thread(target=__consume, args=(client_id, topic, out_queue,
                                            event_queue, clean_session, host,
                                            port))
    worker.setDaemon(True)
    worker.start()
    return worker
