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

"""Ingests raw facts to determine the status of JBoss Fuse for a system."""

import logging
from api.models import Product, Source
from fingerprinter.utils import (product_entitlement_found,
                                 generate_raw_fact_members)

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

PRODUCT = 'JBoss Fuse'
PRESENCE_KEY = 'presence'
VERSION_KEY = 'version'
RAW_FACT_KEY = 'raw_fact_key'
META_DATA_KEY = 'metadata'
JBOSS_FUSE_FUSE_ON_EAP = 'eap_home_bin'
JBOSS_FUSE_ON_KARAF_KARAF_HOME = 'karaf_home_bin_fuse'
JBOSS_FUSE_SYSTEMCTL_FILES = 'jboss_fuse_systemctl_unit_files'
JBOSS_FUSE_CHKCONFIG = 'jboss_fuse_chkconfig'
JBOSS_ACTIVEMQ_VER = 'jboss_activemq_ver'
JBOSS_CAMEL_VER = 'jboss_camel_ver'
JBOSS_CXF_VER = 'jboss_cxf_ver'
SUBMAN_CONSUMED = 'subman_consumed'
ENTITLEMENTS = 'entitlements'

FUSE_CLASSIFICATIONS = {
    'redhat-630187': 'Fuse-6.3.0',
    'redhat-621084': 'Fuse-6.2.1',
    'redhat-620133': 'Fuse-6.2.0',
    'redhat-611412': 'Fuse-6.1.1',
    'redhat-610379': 'Fuse-6.1.0',
    'redhat-60024': 'Fuse-6.0.0',
}


# pylint: disable=R0914
def detect_jboss_fuse(source, facts):
    """Detect if JBoss Fuse is present based on system facts.

    :param source: The source of the facts
    :param facts: facts for a system
    :returns: dictionary defining the product presence
    """
    fuse_on_eap = facts.get(JBOSS_FUSE_FUSE_ON_EAP)
    fuse_on_karaf = facts.get(JBOSS_FUSE_ON_KARAF_KARAF_HOME)
    systemctl_files = facts.get(JBOSS_FUSE_SYSTEMCTL_FILES)
    chkconfig = facts.get(JBOSS_FUSE_CHKCONFIG)
    fuse_activemq = facts.get(JBOSS_ACTIVEMQ_VER, [])
    fuse_camel = facts.get(JBOSS_CAMEL_VER, [])
    fuse_cxf = facts.get(JBOSS_CXF_VER, [])
    subman_consumed = facts.get(SUBMAN_CONSUMED, [])
    entitlements = facts.get(ENTITLEMENTS, [])
    fuse_versions = list(set(fuse_activemq + fuse_camel + fuse_cxf))

    source_object = Source.objects.filter(id=source.get('source_id')).first()
    if source_object:
        source_name = source_object.name
    else:
        source_name = None

    metadata = {
        'source_id': source['source_id'],
        'source_name': source_name,
        'source_type': source['source_type'],
    }
    product_dict = {'name': PRODUCT}
    raw_facts = None
    is_fuse_on_eap = (fuse_on_eap and any(fuse_on_eap.values()))
    is_fuse_on_karaf = (fuse_on_karaf and any(fuse_on_karaf.values()))
    if is_fuse_on_eap or is_fuse_on_karaf or fuse_versions:
        raw_facts_dict = {JBOSS_FUSE_FUSE_ON_EAP: is_fuse_on_eap,
                          JBOSS_FUSE_ON_KARAF_KARAF_HOME: is_fuse_on_karaf,
                          JBOSS_ACTIVEMQ_VER: fuse_activemq,
                          JBOSS_CAMEL_VER: fuse_camel,
                          JBOSS_CXF_VER: fuse_cxf}
        raw_facts = generate_raw_fact_members(raw_facts_dict)
        product_dict[PRESENCE_KEY] = Product.PRESENT
        versions = []
        if fuse_versions:
            for version_data in fuse_versions:
                unknown_release = 'Unknown-Release: ' + version_data
                versions.append(FUSE_CLASSIFICATIONS.get(version_data,
                                                         unknown_release))
            if versions:
                product_dict[VERSION_KEY] = versions
    elif systemctl_files or chkconfig:
        raw_facts_dict = {JBOSS_FUSE_SYSTEMCTL_FILES: systemctl_files,
                          JBOSS_FUSE_CHKCONFIG: chkconfig}
        raw_facts = generate_raw_fact_members(raw_facts_dict)
        product_dict[PRESENCE_KEY] = Product.POTENTIAL
    elif product_entitlement_found(subman_consumed, PRODUCT):
        raw_facts = SUBMAN_CONSUMED
        product_dict[PRESENCE_KEY] = Product.POTENTIAL
    elif product_entitlement_found(entitlements, PRODUCT):
        raw_facts = ENTITLEMENTS
        product_dict[PRESENCE_KEY] = Product.POTENTIAL
    else:
        product_dict[PRESENCE_KEY] = Product.ABSENT

    metadata[RAW_FACT_KEY] = raw_facts
    product_dict[META_DATA_KEY] = metadata
    return product_dict
