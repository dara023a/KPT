import socket
import unittest

import numpy as np

from common import (ALGOS, checksum, is_sorted, merge_many, merge_two,
                    recv_frame, send_frame, sort_part)


class TestSorting(unittest.TestCase):
    def setUp(self):
        self.arr = np.array([5, -3, 5, 0, -7, 2, -3], dtype=np.int32)

    def test_sort_part_all_algorithms(self):
        expected = np.sort(self.arr)
        for algo in ALGOS:
            with self.subTest(algo=algo):
                out = sort_part((self.arr, algo))
                np.testing.assert_array_equal(out, expected)
                self.assertEqual(out.dtype, self.arr.dtype)

    def test_merge_two_with_duplicates_and_empty(self):
        a = np.array([1, 2, 2, 5], dtype=np.int32)
        b = np.array([2, 3, 5, 5], dtype=np.int32)
        expected = np.sort(np.concatenate([a, b]))
        np.testing.assert_array_equal(merge_two(a, b), expected)
        np.testing.assert_array_equal(merge_two(a, np.empty(0, dtype=a.dtype)), a)
        np.testing.assert_array_equal(merge_two(np.empty(0, dtype=a.dtype), b), b)

    def test_merge_many(self):
        runs = [np.array([4, 8]), np.array([1, 3]),
                np.array([2, 2, 9]), np.empty(0, dtype=np.int32)]
        expected = np.sort(np.concatenate([r for r in runs if len(r)]))
        np.testing.assert_array_equal(merge_many(runs), expected)

    def test_is_sorted(self):
        self.assertTrue(is_sorted(np.array([1, 1, 2, 3], dtype=np.int32)))
        self.assertFalse(is_sorted(np.array([1, 3, 2], dtype=np.int32)))

    def test_checksum_perm_invariant_and_detects_change(self):
        a = np.array([1, 2, 3, 3], dtype=np.int32)
        b = np.random.default_rng(0).permutation(a)
        self.assertEqual(checksum(a), checksum(b))
        changed = np.append(a[:-1], 99)
        self.assertNotEqual(checksum(a), checksum(changed))


class TestFraming(unittest.TestCase):
    def test_frame_roundtrip(self):
        a, b = socket.socketpair()
        try:
            arr = np.arange(12, dtype=np.int64)
            hdr = {"action": "sort", "task_id": "T0000", "dtype": str(arr.dtype)}
            send_frame(a, hdr, arr)
            got_hdr, payload = recv_frame(b)
            self.assertEqual(got_hdr["action"], "sort")
            self.assertEqual(got_hdr["task_id"], "T0000")
            got = np.frombuffer(payload, dtype=np.dtype(got_hdr["dtype"]))
            np.testing.assert_array_equal(got, arr)
        finally:
            a.close()
            b.close()

    def test_empty_payload(self):
        a, b = socket.socketpair()
        try:
            send_frame(a, {"type": "heartbeat"})
            hdr, payload = recv_frame(b)
            self.assertEqual(hdr["payload_len"], 0)
            self.assertEqual(len(payload), 0)
        finally:
            a.close()
            b.close()


if __name__ == "__main__":
    unittest.main()
