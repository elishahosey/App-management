import unittest

from roku_blocker.roku import _parse_ssdp_headers


class RokuTests(unittest.TestCase):
    def test_ssdp_headers_are_case_insensitive(self):
        payload = (
            b"HTTP/1.1 200 OK\r\n"
            b"LOCATION: http://192.168.1.10:8060/\r\n"
            b"UsN: uuid:roku:ecp:123\r\n\r\n"
        )
        headers = _parse_ssdp_headers(payload)
        self.assertEqual(headers["location"], "http://192.168.1.10:8060/")
        self.assertEqual(headers["usn"], "uuid:roku:ecp:123")
