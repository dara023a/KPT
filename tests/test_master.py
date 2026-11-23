import os
import tempfile
import unittest

import numpy as np

from src.common import checksum
from src.master_sort import Worker, build_sort_tasks, load_dataset, parse_size


class TestUtils(unittest.TestCase):
    def test_parse_size(self):
        self.assertEqual(parse_size("10m"), 10_000_000)
        self.assertEqual(parse_size("2.5k"), 2500)
        self.assertEqual(parse_size("1_000"), 1000)
        self.assertEqual(parse_size(500), 500)

    def test_build_sort_tasks_static(self):
        data = np.arange(10, dtype=np.int32)
        ws = [Worker({"host": "a", "ip": "127.0.0.1", "port": 9998, "cores": 2}),
              Worker({"host": "b", "ip": "127.0.0.1", "port": 9999, "cores": 1})]
        tasks = build_sort_tasks(data, ws, "static", 4)
        self.assertEqual(len(tasks), 2)
        self.assertEqual([t["owner"] for t in tasks], [w.key for w in ws])
        self.assertEqual([len(t["array"]) for t in tasks], [6, 4])
        np.testing.assert_array_equal(np.concatenate([t["array"] for t in tasks]), data)

    def test_build_sort_tasks_dynamic_min_chunk(self):
        n = 250_000
        data = np.arange(n, dtype=np.int32)
        ws = [Worker({"host": "a", "ip": "127.0.0.1", "port": 9998, "cores": 2}),
              Worker({"host": "b", "ip": "127.0.0.1", "port": 9999, "cores": 2})]
        tasks = build_sort_tasks(data, ws, "dynamic", 2)
        self.assertEqual(len(tasks), 3)
        self.assertEqual([len(t["array"]) for t in tasks], [100_000, 100_000, 50_000])
        self.assertTrue(all(t["owner"] is None for t in tasks))
        np.testing.assert_array_equal(np.concatenate([t["array"] for t in tasks]), data)

    def test_load_dataset_npy_shuffle_and_limit(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.npy")
            raw = np.arange(1000, dtype=np.int32)
            np.save(path, raw)
            limited = load_dataset(path, "", 100, False, 42)
            np.testing.assert_array_equal(limited, raw[:100])
            shuffled = load_dataset(path, "", 0, True, 7)
            self.assertEqual(checksum(shuffled), checksum(raw))
            self.assertFalse(np.array_equal(shuffled, raw))
            del limited, shuffled


if __name__ == "__main__":
    unittest.main()
