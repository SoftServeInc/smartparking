""" Thread utils.
"""
class StopEvent:
    """ Class to identify a "stop" event.
    """


def is_stop_event(event):
    """ Check whether an event is a "stop" event or not.

    :param event: event object
    :return: True if the event is a "stop" event and False otherwise
    """
    res = isinstance(event, StopEvent) or event is StopEvent
    return res
