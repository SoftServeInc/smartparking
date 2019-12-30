import unittest

import core_engine.windowing as windowing

window_options = {
    # "strategy": "<most_freq>, <most_freq_of_max>, <none>",
    "window_size": 8,
    "defined_min": 0.3,
    "defined_max": 0.7
}


class MostFreqOfMaxStrategyTest(unittest.TestCase):
    def test_max(self):
        input_data = [0.1, 0.2, 0.1, 0.9, 0.6,
                      0.98, 0.8, 0.75, 0.8, 0.9,
                      0.9, 0.8, 0.6, 0.9, 0.5,
                      0.9, 0.8, 0.1, 0.9, 0.4]

        st = windowing.MostFreqOfMaxStrategy(window_options)
        res = []
        for v in input_data:
            res.append(st.apply(v))

        expected = [1, 1, 1, 1, 1,
                    1, 1, 1, 1, 1,
                    1, 1, 2, 2, 2,
                    2, 2, 2, 2, 2]
        self.assertEqual(expected, res)


class MostFreqStrategyTest(unittest.TestCase):
    def test_max(self):
        input_data = [0.1, 0.2, 0.1, 0.9, 0.6,
                      0.98, 0.8, 0.75, 0.8, 0.9,
                      0.9, 0.8, 0.6, 0.9, 0.5,
                      0.9, 0.8, 0.1, 0.9, 0.4]

        st = windowing.MostFreqStrategy(window_options)
        res = []
        for v in input_data:
            res.append(st.apply(v))

        expected = [1, 1, 1, 1, 1,
                    1, 1, 1, 1, 0,
                    0, 2, 2, 2, 2,
                    2, 2, 2, 2, 2]
        self.assertEqual(expected, res)


class NoneStrategyTest(unittest.TestCase):
    def test_max(self):
        input_data = [0.1, 0.2, 0.1, 0.9, 0.6,
                      0.98, 0.8, 0.75, 0.8, 0.9,
                      0.9, 0.8, 0.6, 0.9, 0.5,
                      0.9, 0.8, 0.1, 0.9, 0.4]

        st = windowing.NoneStrategy(window_options)
        res = []
        for v in input_data:
            res.append(st.apply(v))

        expected = [1, 1, 1, 2, 0,
                    2, 2, 2, 2, 2,
                    2, 2, 0, 2, 0,
                    2, 2, 1, 2, 0]
        self.assertEqual(expected, res)
