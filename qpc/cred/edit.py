#!/usr/bin/env python
#
# Copyright (c) 2017 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 3 (GPLv3). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv3
# along with this software; if not, see
# https://www.gnu.org/licenses/gpl-3.0.txt.
#
"""CredEditCommand is used to edit credentials."""

from __future__ import print_function
import sys
from requests import codes
from qpc.request import PATCH, GET, request
from qpc.clicommand import CliCommand
import qpc.cred as credential
from qpc.cred.utils import validate_sshkeyfile, build_credential_payload
from qpc.translation import _
import qpc.messages as messages


# pylint: disable=too-few-public-methods
class CredEditCommand(CliCommand):
    """Defines the edit command.

    This command is for editing existing credentials
    which can be later associated with sources to gather facts.
    """

    SUBCOMMAND = credential.SUBCOMMAND
    ACTION = credential.EDIT

    def __init__(self, subparsers):
        """Create command."""
        # pylint: disable=no-member
        CliCommand.__init__(self, self.SUBCOMMAND, self.ACTION,
                            subparsers.add_parser(self.ACTION), PATCH,
                            credential.CREDENTIAL_URI, [codes.ok])
        self.parser.add_argument('--name', dest='name', metavar='NAME',
                                 help=_(messages.CRED_NAME_HELP),
                                 required=True)
        self.parser.add_argument('--username', dest='username',
                                 metavar='USERNAME',
                                 help=_(messages.CRED_USER_HELP),
                                 required=False)
        group = self.parser.add_mutually_exclusive_group(required=False)
        group.add_argument('--password', dest='password',
                           action='store_true',
                           help=_(messages.CRED_PWD_HELP))
        group.add_argument('--sshkeyfile', dest='filename',
                           metavar='FILENAME',
                           help=_(messages.CRED_SSH_HELP))
        self.parser.add_argument('--sshpassphrase', dest='ssh_passphrase',
                                 action='store_true',
                                 help=_(messages.CRED_SSH_PSPH_HELP))
        self.parser.add_argument('--sudo-password', dest='sudo_password',
                                 action='store_true',
                                 help=_(messages.CRED_SUDO_HELP))
        self.cred_type = None

    def _validate_args(self):
        CliCommand._validate_args(self)

        if not(self.args.username or self.args.password or
               self.args.sudo_password or self.args.filename or
               self.args.ssh_passphrase):
            print(_(messages.CRED_EDIT_NO_ARGS % (self.args.name)))
            self.parser.print_help()
            sys.exit(1)

        if 'filename' in self.args and self.args.filename:
            # check for file existence on system
            self.args.filename = validate_sshkeyfile(self.args.filename,
                                                     self.parser)

        # check for existence of credential
        response = request(parser=self.parser, method=GET,
                           path=credential.CREDENTIAL_URI,
                           params={'name': self.args.name},
                           payload=None)
        if response.status_code == codes.ok:  # pylint: disable=no-member
            json_data = response.json()
            if len(json_data) == 1:
                cred_entry = json_data[0]
                self.cred_type = cred_entry['cred_type']
                self.req_path = self.req_path + str(cred_entry['id']) + '/'
            else:
                print(_(messages.CRED_DOES_NOT_EXIST % self.args.name))
                sys.exit(1)
        else:
            print(_(messages.CRED_DOES_NOT_EXIST % self.args.name))
            sys.exit(1)

    def _build_data(self):
        """Construct the dictionary credential given our arguments.

        :returns: a dictionary representing the credential being added
        """
        self.req_payload = build_credential_payload(
            self.args, self.cred_type, add_none=False)

    def _handle_response_success(self):
        print(_(messages.CRED_UPDATED % self.args.name))