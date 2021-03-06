# -*- coding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock
import unittest

from airflow.utils import logging
from datetime import datetime

DEFAULT_DATE = datetime(2016, 1, 1)


class TestS3Log(unittest.TestCase):

    def setUp(self):
        super(TestS3Log, self).setUp()
        self.remote_log_location = 'remote/log/location'
        self.hook_patcher = mock.patch("airflow.hooks.S3_hook.S3Hook")
        self.hook_mock = self.hook_patcher.start()
        self.hook_inst_mock = self.hook_mock.return_value
        self.hook_key_mock = self.hook_inst_mock.get_key.return_value
        self.hook_key_mock.get_contents_as_string.return_value.decode.\
            return_value = 'content'
        self.logging_patcher = mock.patch("airflow.utils.logging.logging")
        self.logging_mock = self.logging_patcher.start()

    def tearDown(self):
        self.logging_patcher.stop()
        self.hook_patcher.stop()
        super(TestS3Log, self).tearDown()

    def test_init(self):
        logging.S3Log()
        self.hook_mock.assert_called_once_with('')

    def test_init_raises(self):
        self.hook_mock.side_effect = Exception('Failed to connect')
        logging.S3Log()
        self.logging_mock.error.assert_called_once_with(
            'Could not create an S3Hook with connection id "". Please make '
            'sure that airflow[s3] is installed and the S3 connection exists.'
        )

    def test_log_exists(self):
        self.assertTrue(logging.S3Log().log_exists(self.remote_log_location))

    def test_log_exists_none(self):
        self.hook_inst_mock.get_key.return_value = None
        self.assertFalse(logging.S3Log().log_exists(self.remote_log_location))

    def test_log_exists_raises(self):
        self.hook_inst_mock.get_key.side_effect = Exception('error')
        self.assertFalse(logging.S3Log().log_exists(self.remote_log_location))

    def test_log_exists_no_hook(self):
        self.hook_mock.side_effect = Exception('Failed to connect')
        self.assertFalse(logging.S3Log().log_exists(self.remote_log_location))

    def test_read(self):
        self.assertEqual(logging.S3Log().read(self.remote_log_location),
                         'content')

    def test_read_key_empty(self):
        self.hook_inst_mock.get_key.return_value = None
        self.assertEqual(logging.S3Log().read(self.remote_log_location), '')

    def test_read_raises(self):
        self.hook_inst_mock.get_key.side_effect = Exception('error')
        self.assertEqual(logging.S3Log().read(self.remote_log_location), '')

    def test_read_raises_return_error(self):
        self.hook_inst_mock.get_key.side_effect = Exception('error')
        result = logging.S3Log().read(self.remote_log_location,
                                      return_error=True)
        msg = 'Could not read logs from %s' % self.remote_log_location
        self.assertEqual(result, msg)
        self.logging_mock.error.assert_called_once_with(msg)

    def test_write(self):
        logging.S3Log().write('text', self.remote_log_location)
        self.hook_inst_mock.load_string.assert_called_once_with(
            'content\ntext',
            key=self.remote_log_location,
            replace=True,
            encrypt=False,
        )

    def test_write_raises(self):
        self.hook_inst_mock.load_string.side_effect = Exception('error')
        logging.S3Log().write('text', self.remote_log_location)
        msg = 'Could not write logs to %s' % self.remote_log_location
        self.logging_mock.error.assert_called_once_with(msg)
