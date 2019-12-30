""" Rules manager helper class.
"""
import json
import logging
import time

from paho.mqtt.publish import single

from core_engine.events import (EnteredThroughGate,
                                EnteredParkingPlace)
from core_engine.parking_state import PLACE_STATUS


CLIENT_ID = 'history-manager-publisher'

logger = logging.getLogger('core_engine')


class RulesManager:
    """ Rules manager.
    """
    def __init__(self, options):
        self.topic = options['output_topic']
        self.host = options['mq_host']
        self.port = options['mq_port']
        self.static_metadata = options['static_metadata']

    def calculate_and_send_state(self, events, parking_state):
        """ Calculate the state and publish it into Mosquito topic.

        :param events: list of parking events
        :param parking_state: parking state object
        """
        in_movement_cars = self._calculate_in_movement_cars(events)
        reserved_places = self._calculate_reserved_places(parking_state)
        message = parking_state.video_plugin_data.copy()
        message['parking_places'] = RulesManager.get_formatted_parking_state(parking_state.state)
        free = len([1 for v in parking_state.state.values()
                    if v.state == PLACE_STATUS['FREE']])
        message['parking']['free'] = free
        message['parking']['occupied'] = len(
            [1 for v in parking_state.state.values()
             if v.state != PLACE_STATUS['FREE']])
        message['parking']['in_movement'] = in_movement_cars
        message['parking']['free_to_display'] = free - in_movement_cars - reserved_places
        message['metadata']['core_engine_activation_time'] = time.time()
        message['metadata']['static_metadata'] = self.static_metadata

        single(self.topic, payload=json.dumps(message), qos=0, retain=False,
               hostname=self.host, port=self.port,
               client_id=CLIENT_ID, keepalive=60)

    @staticmethod
    def get_formatted_parking_state(state):
        """ Transform internal parking state into the output format.

        :param state: internal parking state
        :return: parking state in the output format
        """
        f_state = []
        for p_id in state:
            arr = [state[p_id].state, state[p_id].sigmoid_value]
            if state[p_id].reservation_state:
                arr.append(state[p_id].reservation_state)
            f_state.append({'id': p_id, 'status': arr})
        return f_state

    @staticmethod
    def _calculate_in_movement_cars(events):
        """ Calculates amount of cars in movement.

        :param events: list of parking events
        :return: number of cars in movement
        """
        in_movement_cars = 0
        for event in events:
            if isinstance(event, EnteredThroughGate):
                in_movement_cars += 1
            elif isinstance(event, EnteredParkingPlace):
                in_movement_cars -= 1
        if in_movement_cars < 0:
            in_movement_cars = 0
        return in_movement_cars

    @staticmethod
    def _calculate_reserved_places(parking_state):
        """ Calculates amount of free reserved places.

        :param parking_state: internal parking state
        :return: number of unoccupied reserved places
        """
        reserved_places = 0
        for place_id in parking_state.reservations:
            if (place_id in parking_state.state and
                    parking_state.state[place_id].state == PLACE_STATUS['FREE']):
                reserved_places += 1
        return reserved_places
