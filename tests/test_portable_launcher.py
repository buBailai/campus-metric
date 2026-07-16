import os
import unittest
from unittest.mock import MagicMock, patch

import portable_launcher


class PortableLauncherTests(unittest.TestCase):
    def test_usable_ipv4_rejects_loopback_and_link_local(self):
        self.assertTrue(portable_launcher._usable_ipv4('192.168.1.28'))
        self.assertTrue(portable_launcher._usable_ipv4('10.0.0.8'))
        self.assertFalse(portable_launcher._usable_ipv4('127.0.0.1'))
        self.assertFalse(portable_launcher._usable_ipv4('169.254.10.2'))
        self.assertFalse(portable_launcher._usable_ipv4('not-an-ip'))

    def test_detect_lan_ipv4_uses_default_route(self):
        context = MagicMock()
        context.__enter__.return_value.getsockname.return_value = ('192.168.50.23', 50000)
        with patch('portable_launcher.socket.socket', return_value=context), patch(
            'portable_launcher.socket.getaddrinfo', return_value=[],
        ):
            self.assertEqual(portable_launcher.detect_lan_ipv4(), '192.168.50.23')

    def test_configured_port_falls_back_for_invalid_environment(self):
        with patch.dict(os.environ, {'PORT': 'invalid'}, clear=False):
            self.assertEqual(portable_launcher.configured_port(), portable_launcher.DEFAULT_PORT)


if __name__ == '__main__':
    unittest.main()
