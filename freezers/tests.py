"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from freezers.models import *


class UtilitiesTest(TestCase):
    """
    Test the utilities module. Simple.
    """

    def test_address_conversion(self):
        """
        Tests that an address is converted to the correct position
        """
        addr1 = 0x0102030405
        pos1 = getposition(addr1)
        self.assertEqual(pos1, (1, 2, 3, 4, 5))

    def test_position_conversion(self):
        """
        Tests that a position becomes the correct address
        """
        pos1 = (3, 4, 1, 2, 81)
        addr1 = getaddress(pos1)
        self.assertEqual(addr1, 0x0304010251)
