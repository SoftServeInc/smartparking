""" Helper classes and functions for windowing functionality.
"""
import logging
import numpy as np

logger = logging.getLogger('core_engine')


def create_windowing_manager(windowing_options):
    if windowing_options['strategy'] == 'most_freq':
        return MostFreqStrategy(windowing_options)

    if windowing_options['strategy'] == 'most_freq_of_max':
        return MostFreqOfMaxStrategy(windowing_options)

    if windowing_options['strategy'] == 'none':
        return NoneStrategy(windowing_options)

    raise ValueError(
        'Wrong windowing strategy "{}" in "windowing.strategy" option from '
        'config file. Should be one of values: "most_freq", '
        '"most_freq_of_max", "none"'.format(windowing_options['strategy']))


class WindowingManager:
    def __init__(self, options):
        self.window_size = options['window_size']
        self.defined_min = options['defined_min']
        self.defined_max = options['defined_max']
        self.sigmoid_list = []
        self.medians = []
        self.batch_class = []

    def apply(self, sigmoid):
        if len(self.sigmoid_list) < self.window_size:
            self.sigmoid_list = np.append(self.sigmoid_list, float(sigmoid))
        else:
            self.sigmoid_list = np.insert(self.sigmoid_list[1:],
                                          len(self.sigmoid_list) - 1,
                                          float(sigmoid))

        self._modify_medians()
        self._modify_batch_class()

        return self._apply_strategy()

    def _apply_strategy(self):
        """Called after apply, should be implemented in subclasses"""

    def _modify_medians(self):
        median = np.median(self.sigmoid_list)
        if len(self.medians) < self.window_size:
            self.medians = np.append(self.medians, median)
        else:
            self.medians = np.insert(self.medians[1:], len(self.medians) - 1, median)

    def _modify_batch_class(self):
        """
        Define classes, class values: 1 - place is free, 2 - place is occupied,
        0 - place is undefined
        """
        self.batch_class = \
            [1 if x < self.defined_min else (2 if x > self.defined_max else 0)
             for x in self.medians]


class MostFreqStrategy(WindowingManager):
    def _apply_strategy(self):
        return np.argmax(np.bincount(self.batch_class))


class MostFreqOfMaxStrategy(WindowingManager):
    def __init__(self, options):
        super(MostFreqOfMaxStrategy, self).__init__(options)
        self.batch_class_max = np.array([]).astype(int)

    def _apply_strategy(self):
        max_v = np.max(self.batch_class)
        if np.size(self.batch_class_max) < self.window_size:
            self.batch_class_max = np.append(self.batch_class_max, max_v)
        else:
            self.batch_class_max = np.insert(self.batch_class_max[1:],
                                             len(self.batch_class_max) - 1,
                                             max_v)

        return np.argmax(np.bincount(self.batch_class_max))


class NoneStrategy(WindowingManager):
    def apply(self, sigmoid):
        if sigmoid < self.defined_min:
            return 1

        if sigmoid > self.defined_max:
            return 2

        return 0
