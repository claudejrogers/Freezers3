"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from freezers.utilities import getposition, getaddress, get_bounding_addresses
from view_helper import get_redirect_url


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

    def test_bounds_with_all(self):
        pos1 = (3, 4, 1, 2, 7)
        self.assertTupleEqual(get_bounding_addresses(pos1),
                              (0x0304010207, 0x0304010300))

    def test_bounds_to_box(self):
        con = (3, 2, 1, 3)
        self.assertTupleEqual(get_bounding_addresses(con),
                              (0x0302010300, 0x0302010400))

    def test_bounds_to_drawer(self):
        con = (1, 2, 3)
        self.assertTupleEqual(get_bounding_addresses(con),
                              (0x0102030000, 0x0102040000))

    def test_bounds_to_rack(self):
        con = (3, 5)
        self.assertTupleEqual(get_bounding_addresses(con),
                              (0x0305000000, 0x0306000000))

    def test_bounds_to_shelf(self):
        con = [5]
        self.assertTupleEqual(get_bounding_addresses(con),
                              (0x0500000000, 0x0600000000))

    def test_bounds_all_freezer(self):
        self.assertTupleEqual(get_bounding_addresses([], 6),
                              (0x0, 0x0600000000))


class RedirectURLTest(TestCase):
    """
    Test redirect url function.
    """
    def test_link_with_prefix(self):
        addr = 0x0102030405
        containers = getposition(addr)
        self.assertEqual(
            get_redirect_url(1, containers, prefix='freezers'),
            '/freezers/%d/%d/%d/%d/%d/' % (1, 1, 2, 3, 4)
        )

    def test_link_with_str_fid(self):
        addr = 0x0102030405
        containers = getposition(addr)
        self.assertEqual(
            get_redirect_url('1', containers, prefix='freezers'),
            '/freezers/%s/%d/%d/%d/%d/' % ('1', 1, 2, 3, 4)
        )

    def test_link_with_suffix(self):
        addr = 0x0102030405
        containers = getposition(addr)
        self.assertEqual(
            get_redirect_url(1, containers, prefix='freezers',
                             suffix='rearrange-samples'),
            '/freezers/1/1/2/3/4/rearrange-samples/'
        )

    def test_conditional_suffix(self):
        addr = 0x0102030405
        box_id = '4'
        containers = getposition(addr)
        r1 = get_redirect_url(1, containers, prefix='freezers',
                              suffix='samples' if not box_id else None)
        box_id = None
        r2 = get_redirect_url(1, containers[:3], prefix='freezers',
                              suffix='samples' if not box_id else None)
        self.assertEqual(r1, '/freezers/1/1/2/3/4/')
        self.assertEqual(r2, '/freezers/1/1/2/3/samples/')

    def test_containers_is_empty(self):
        r = get_redirect_url(1, [], prefix='freezers', suffix='samples')
        self.assertEqual(r, '/freezers/1/samples/')

    def test_include_cell(self):
        r = get_redirect_url(1, (1, 2, 3, 4, 5), prefix="freezers",
                             suffix="add-samples", include_cell=True)
        self.assertEqual(r, "/freezers/1/1/2/3/4/5/add-samples/")
