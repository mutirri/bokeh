
from __future__ import absolute_import, print_function

import os
import sys
import unittest

from selenium.common.exceptions import NoSuchElementException

from bokeh.tests.selenium.fixtures import BasicSeleniumTestFixture
from bokeh.tests.selenium.utils import look_for_element, check_if_images_are_the_same


class TestSample(BasicSeleniumTestFixture):
    """
    Sample test - just to check if basic selenium environment works as it is expected.
    """

    @unittest.skip("Just a simple test - only for internal testing purposes.")
    def test_sample(self):
        """Check if we are able to load basic document to bokeh server."""

        doc_name = 'simple_line'
        ref_file = self.test_settings.screenshot_dir+'/ref-screenshot-01.png'
        gen_file = self.test_settings.screenshot_dir+'/gen-screenshot-01.png'

        document_url = self.load_document(doc_name)

        plot = look_for_element(self.driver, "div.bk-canvas-events")