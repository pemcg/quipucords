#
# Copyright (c) 2018 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 3 (GPLv3). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv3
# along with this software; if not, see
# https://www.gnu.org/licenses/gpl-3.0.txt.
#
"""ScanTask used for satellite connection task."""
import logging
from requests import exceptions
from django.db import transaction
from api.models import (ScanTask, ConnectionResult, SourceOptions)
from scanner.task import ScanTaskRunner
from scanner.satellite import utils
from scanner.satellite.api import SatelliteException
from scanner.satellite.factory import create

# Get an instance of a logger
logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class ConnectTaskRunner(ScanTaskRunner):
    """ConnectTaskRunner satellite connection capabilities.

    Attempts connections to a source using a credential
    and gathers the set of available systems.
    """

    def __init__(self, scan_job, scan_task, conn_results):
        """Set context for task execution.

        :param scan_job: the scan job that contains this task
        :param scan_task: the scan task model for this task
        :param prerequisite_tasks: An array of scan task model objects
        that were execute prior to running this task.
        """
        super().__init__(scan_job, scan_task)
        self.conn_results = conn_results
        self.source = scan_task.source
        with transaction.atomic():
            conn_result = conn_results.results.filter(
                source__id=self.source.id).first()
            if conn_result is None:
                conn_result = ConnectionResult(
                    scan_task=scan_task, source=self.source)
                conn_result.save()
                conn_results.results.add(conn_result)
                conn_results.save()
        self.conn_result = conn_result
        # If we're restarting the scan after a pause, systems that
        # were previously up might be down. So we throw out any
        # partial results and start over.
        conn_result.systems.all().delete()

    def run(self):
        """Scan network range ang attempt connections."""
        logger.info('Connect scan started for %s.', self.scan_task)

        satellite_version = None
        options = self.source.options
        if options:
            satellite_version = options.satellite_version

        if (satellite_version is None or
                satellite_version == SourceOptions.SATELLITE_VERSION_5):
            logger.error('Satellite version %s is not yet supported.',
                         SourceOptions.SATELLITE_VERSION_5)
            logger.error('Connect scan failed for %s.', self.scan_task)
            return ScanTask.FAILED

        try:
            status_code, api_version = utils.status(self.scan_task)
            if status_code == 200:
                api = create(satellite_version, api_version,
                             self.scan_task, self.conn_result)
                if not api:
                    logger.error('Satellite version %s with '
                                 'api version %s is not supported.',
                                 satellite_version, api_version)
                    logger.error('Connect scan failed for %s.', self.scan_task)
                    return ScanTask.FAILED
                api.host_count()
                api.hosts()
            else:
                logger.error('Connect scan failed for %s.', self.scan_task)
                return ScanTask.FAILED
        except SatelliteException as sat_error:
            logger.error('Satellite error encountered: %s', sat_error)
            logger.error('Connect scan failed for %s.', self.scan_task)
            return ScanTask.FAILED
        except exceptions.ConnectionError as conn_error:
            logger.error('Satellite error encountered: %s', conn_error)
            logger.error('Connect scan failed for %s.', self.scan_task)
            return ScanTask.FAILED

        logger.info('Connect scan completed for %s.', self.scan_task)
        return ScanTask.COMPLETED