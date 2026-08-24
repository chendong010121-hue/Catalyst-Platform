import unittest

from guard import is_valid_identifier


class GuardTests(unittest.TestCase):
    def test_invalid_input_fails_closed(self):
        self.assertFalse(is_valid_identifier(None))
        self.assertFalse(is_valid_identifier(""))
        self.assertTrue(is_valid_identifier("approved-id"))


if __name__ == "__main__":
    unittest.main()
