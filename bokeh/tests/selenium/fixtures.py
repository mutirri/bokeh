
from __future__ import absolute_import, print_function

import os
import re
import sys
import time
import subprocess
import requests
from requests.exceptions import ConnectionError
from unittest import TestCase
from urllib2 import urlopen, URLError

from selenium import webdriver

from .utils import initialize_standalone_testing_env, initialize_distributive_testing_env, look_for_element
from .run_selenium_tests import settings as test_settings


BOKEH_SERVER_PORT = 5006


def get_server_url(port):
    return "http://localhost:%s/" % (str(port))


def start_bokeh_server(port):

    cmd = ["python", "-c", "import bokeh.server; bokeh.server.run()"]
    argv = ["--bokeh-port=%s" % str(port), "--backend=memory"]
    full_cmd = cmd + argv

    try:
        proc = subprocess.Popen(full_cmd)
    except OSError:
        print("Failed to run: %s" % " ".join(full_cmd))
        sys.exit(1)

    return proc


def stop_bokeh_server(bokeh_server):
    if bokeh_server is not None:
        print("Shutting down bokeh-server ...")
        bokeh_server.kill()


class RawSeleniumTestFixture(TestCase):
    """
    Raw basic fixture which initialize bokeh server and selenium environment as well.
    """

    def setUp(self):

        self.test_settings = test_settings

        # TODO:
        # - The use case with LiveServerTestCase doesn't seem to work with bokeh.
        # - Right now it is overcome by using externally launched bokeh server.
        # - This approach forces to install bokeh in current evnironment before launing selenium tests.
        self.bokeh_server_url = self.test_settings.get_remote_bokeh_server_url()
        self.bokeh_server_instance = start_bokeh_server(self.test_settings.remote_bokeh_server_port)

        self.addCleanup(stop_bokeh_server, self.bokeh_server_instance)

        if not self.check_if_server_is_up_and_running():
            print("Bokeh server is NOT running!")
            return False

        if self.test_settings.headless_mode:
            if 'DISPLAY' in os.environ:
                os.environ['OLD_DISPLAY'] = os.environ['DISPLAY']
            os.environ['DISPLAY'] = self.test_settings.headless_mode_display

        if self.test_settings.env_mode == 'standalone':
            os.environ['SELENIUM_SERVER_JAR'] = self.test_settings.selenium_server_jar_path

            self.driver = initialize_standalone_testing_env(self.test_settings.browser_engine,
                self.test_settings.get_browser_bin(self.test_settings.browser_engine))
        elif self.test_settings.env_mode == 'distributive':
            self.driver = initialize_distributive_testing_env(self.test_settings.browser_engine,
                self.test_settings.browser_caps, self.test_settings.selenium_hub_address)
        else:
            print("Unsupported mode of testing environment: %s" % (self.test_settings.env_mode))
            return False

        self.driver.set_window_size(self.test_settings.window_width, self.test_settings.window_height)
        self.driver.start_client()

        self.actions = webdriver.common.action_chains.ActionChains(self.driver)
        self.touch = webdriver.common.touch_actions.TouchActions(self.driver)

        self.addCleanup(self.driver.quit)

    def check_if_server_is_up_and_running(self):
        tries = 20
        try_num = 0

        while try_num <= tries:
            ret = 0

            try:
                response = urlopen(self.bokeh_server_url+'bokeh/ping')
                ret = response.code
            except URLError:
                pass

            if ret == 200:
                return True
            else:
                try_num += 1
                time.sleep(1)

        return False

    def tearDown(self):
        if self.test_settings.headless_mode:
            if 'OLD_DISPLAY' in os.environ:
                os.environ['DISPLAY'] = os.environ['OLD_DISPLAY']
                del os.environ['DISPLAY']


class BasicSeleniumTestFixture(RawSeleniumTestFixture):
    """
    Basic fixture which guarantee clean testing environment.
    """

    def setUp(self):
        RawSeleniumTestFixture.setUp(self)

        self.driver.get(self.bokeh_server_url)
        self.assertEqual(self.driver.title, 'Bokeh Plot Server')

        msg = self.driver.find_element_by_css_selector("div.container a.navbar-brand")
        self.assertRegexpMatches(msg.text, "Bokeh Documents for defaultuser")

        self.unload_all_documents()

    def load_document(self, document_file_name):
        url = None

        document_file = self.test_settings.documents_dir+'/'+document_file_name+'.py'
        output = subprocess.check_output(['python', document_file])

        for line in output.splitlines():
            match = re.compile(r"^URL of this document: (?P<url>.+)$").match(line)

            if match:
                raw = match.groupdict()
                url = raw.get('url', None)

        if not url:
            raise Exception("Document {} is not producing required URL!".format(document_file))

        self.driver.get(url)

        return url

    def unload_document(self, document_name):
        delete_button = self.driver.find_element_by_css_selector("a.bokehdoclabel span.bokehdelete.glyphicon.glyphicon-trash")
        delete_button.click()

    def unload_all_documents(self):
        delete_buttons = self.driver.find_elements_by_css_selector("a.bokehdoclabel span.bokehdelete.glyphicon.glyphicon-trash")

        for button in delete_buttons:
            button.click()

    def tearDown(self):
        RawSeleniumTestFixture.tearDown(self)
