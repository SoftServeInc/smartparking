""" Helper classes and functions to deal with parking events.
"""
import logging
import time

from core_engine.parking_state import GATE_ENTERED_STATUS, PLACE_STATUS

logger = logging.getLogger('core_engine')


class Event:
    """ Base event class.
    """
    def __init__(self):
        self.time = time.time()


class GateEvent(Event):
    """ Base class for smart gate events.
    """
    def __init__(self, car_number=None):
        """
        :param car_number: car number
        """
        super(GateEvent, self).__init__()
        self.car_number = car_number

class EnteredThroughGate(GateEvent):
    """ Car entered parking through the gate.
    """

class ExitedThroughGate(GateEvent):
    """ Car exited parking through the gate.
    """


class PlaceEvent(Event):
    """ Base class for parking place events.
    """
    def __init__(self, place_id=None):
        """
        :param id: parking place ID
        """
        super(PlaceEvent, self).__init__()
        self.place_id = place_id

class EnteredParkingPlace(PlaceEvent):
    """ Car entered a parking place.
    """

class ExitedParkingPlace(PlaceEvent):
    """ Car exited a parking place.
    """


def apply_event(events, data, topic, parking_state, options):
    """ Apply parking events and update the parking state.

    :param events: list of parking events
    :param data: content of the message
    :param topic: topic name
    :param parking_state: parking state object
    :param options: dict of configuration values
    """
    if topic == options['gate_plugin_topic']:
        if data['entered'] == GATE_ENTERED_STATUS['ENTERED']:
            events.insert(0, EnteredThroughGate())
        elif data['entered'] == GATE_ENTERED_STATUS['EXITED']:
            events.insert(0, ExitedThroughGate())
        else:
            raise RuntimeError('Unsupported barrier "entered" value. MQ event - {}'.format(data))
    elif topic in options['video_plugin_topics']:
        state_diff = parking_state.state_diff(data['parking_places'])

        if state_diff:
            for place_id in state_diff:
                if parking_state.state[place_id].reservation_state is not None:
                    continue
                elif parking_state.state[place_id].state == PLACE_STATUS['FREE']:
                    events.insert(0, EnteredParkingPlace(place_id))
                else:
                    events.insert(0, ExitedParkingPlace(place_id))

        parking_state.set_parking_new_state(data)
    else:
        raise RuntimeError('Received a message from unknown topic: {}'.format(topic))


def remove_last_event(events):
    """ Remove last event from the list.

    :param events: list of parking events
    """
    latest = events[-1]
    pair_event_index = None
    if isinstance(latest, (EnteredThroughGate, ExitedParkingPlace)):
        for i, event in reversed(list(enumerate(events))):
            if isinstance(event, (ExitedThroughGate, EnteredParkingPlace)):
                pair_event_index = i
                break

    del events[-1]
    if pair_event_index:
        del events[pair_event_index]


def remove_old_events(events, event_ttl):
    """ Remove all events from the list older than a TTL value.

    :param events: list of parking events
    :param event_ttl: TTL value (in seconds)
    """
    if events:
        latest = events[-1]
        threshold = time.time() - event_ttl
        while latest.time < threshold:
            remove_last_event(events)
            if events:
                latest = events[-1]
            else:
                break
