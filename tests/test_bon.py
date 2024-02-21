#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from unittest import TestCase

from kutil.storage.bon import load, dump, GZIP, RAW


class TestBON(TestCase):
    def test_bon(self):
        enc = RAW
        # enc = GZIP

        data = {
            "hello": "World",
            "test": {
                "int": 69,
                "float": 3.14159,
                "bytes": b'correct',
                "test": True
            },
            "list_test": [1, 2, 3, "HI", {}, []]
        }

        data["list_test"].append(data["test"])  # Test pool duplication mitigations
        data["list_test"].append(data["list_test"])  # Test infinite loops

        dump(open("test.bon", "wb+"), data, encoding=enc)

        loaded_data = load(open("test.bon", "rb"), encoding=enc)

        self.assertEqual(loaded_data["hello"], "World")
        self.assertEqual(loaded_data["test"]["int"], 69)
        self.assertEqual(loaded_data["test"]["float"], 3.14159)
        self.assertEqual(loaded_data["test"]["bytes"], b'correct')
        self.assertTrue(loaded_data["test"]["test"])
        self.assertEqual(loaded_data["list_test"][:4], [1, 2, 3, "HI"])
        self.assertEqual(loaded_data["list_test"][6], loaded_data["test"])  # Check pool duplicate
        self.assertEqual(loaded_data["list_test"][7], loaded_data["list_test"])  # Check recursion
