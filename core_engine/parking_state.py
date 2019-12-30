""" Helper classes for parking state.
"""

import time
import logging

from core_engine.windowing import create_windowing_manager

PLACE_STATUS = {
    'FREE': 0,
    'OCCUPIED': 1,
    'DYNAMIC_RESERVATION': 2,
    'STATIC_RESERVATION': 3,
    'RESERVATION_FOR_DISABLED': 4,
}

GATE_ENTERED_STATUS = {
    'ENTERED': 0,
    'EXITED': 1
}

logger = logging.getLogger('core_engine')


class ParkingPlace:
    """ Individual parking place.
    """
    def __init__(self, state, sigmoid, windowing_options,
                 reservation_state=None):
        """
        :param state: parking state (0 or 1 - see PLACE_STATUS values)
        :param sigmoid: occupied probability in range 0..1
        :param windowing_options: dict of windowing configuration
        :param reservation_state: reservation state (2, 3 or 4 - see
            PLACE_STATUS values) or None
        """
        self.state = state
        self.windowing_strategy = create_windowing_manager(windowing_options)
        self.reservation_state = reservation_state
        self.sigmoid_value = sigmoid

    def set_new_state(self, state, sigmoid, reservation_state=None):
        """ Set new parking state.

        :param state: parking state (0 or 1 - see PLACE_STATUS values)
        :param sigmoid: occupied probability in range 0..1
        :param reservation_state: reservation state (2, 3 or 4 - see
            PLACE_STATUS values) or None
        """
        self.state = state
        if reservation_state:
            self.reservation_state = reservation_state

        fixed_state = self.windowing_strategy.apply(sigmoid)

        if fixed_state == 1:
            self.sigmoid_value = 0.0
        elif fixed_state == 2:
            self.sigmoid_value = 1.0
        else:
            self.sigmoid_value = 0.5

        if self.sigmoid_value > 0.5:
            self.state = PLACE_STATUS['OCCUPIED']
        else:
            self.state = PLACE_STATUS['FREE']


class ParkingState:
    """ Overall parking state.
    """
    def __init__(self, data, reservations, windowing_options):
        """
        :param data: content of the message from Model Engine
        :param reservations: dict of reservations
        :param windowing_options: dict of windowing configuration
        """
        self.video_plugin_data = data
        self.reservations = reservations
        self.windowing_options = windowing_options
        self.update_time = time.time()
        self.state = {}
        self.__init_parking_state(data['parking_places'].copy())

    def __init_parking_state(self, video_plugin_parking_places):
        start_time = time.time()
        self.general_purpose_places = 0
        for place_id in video_plugin_parking_places:
            if place_id in self.reservations:
                reservation_state = self.reservations[place_id]
                state = video_plugin_parking_places[place_id][0]
                prob = video_plugin_parking_places[place_id][1]
                self.update_or_create_parking_place(place_id, state, prob, reservation_state)
            else:
                model_state = video_plugin_parking_places[place_id][0]
                model_prob = video_plugin_parking_places[place_id][1]
                self.update_or_create_parking_place(place_id, model_state, model_prob)
                self.general_purpose_places += 1
        logger.info('Parking state and Windows calculation took %f sec', time.time() - start_time)

    def set_parking_new_state(self, data):
        """ Set new parking state.

        :param data: content of the message from Model Engine
        """
        self.video_plugin_data = data
        self.update_time = time.time()
        self.__init_parking_state(data['parking_places'].copy())

    def update_or_create_parking_place(self, place_id, state, prob, reservation_state=None):
        """ Update or create new parking place.

        :param place_id: parking place ID
        :param state: new parking state (0 or 1 - see PLACE_STATUS values)
        :param prob: occupied probability in range 0..1
        :param reservation_state: reservation state (2, 3 or 4 - see
            PLACE_STATUS values) or None
        """
        if place_id in self.state:
            self.state[place_id].set_new_state(state, prob, reservation_state)
        else:
            self.state[place_id] = ParkingPlace(state,
                                                prob,
                                                self.windowing_options,
                                                reservation_state)

    def state_diff(self, new_state):
        """ Analyze differences between old and new states.

        :param new_state: dict of new parking states
        :return: set of parking place IDs where parking state changed
        """
        return set(k for k in new_state if k in self.state
                   and new_state[k][0] != self.state[k].state)
