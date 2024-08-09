# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Conftest."""

import pytest
from invenio_access.permissions import system_identity
from invenio_app.factory import create_app as _create_app
from invenio_records_resources.proxies import current_service_registry


@pytest.fixture(scope='module')
def app_config(app_config):
    """Override pytest-invenio app_config fixture.

    For test purposes we need to explicitly set these configuration variables
    above any other module's config.py potential clashes.
    """
    app_config.update({
        # Variable not used. We set it to silent warnings
        'JSONSCHEMAS_HOST': 'not-used',
        # Disable DATACITE.
        'DATACITE_ENABLED': False,
        'RECORDS_REFRESOLVER_CLS': (
            "invenio_records.resolver.InvenioRefResolver"
        ),
        'RECORDS_REFRESOLVER_STORE': (
            "invenio_jsonschemas.proxies.current_refresolver_store"
        ),
        'MAIL_DEFAULT_SENDER': ('Prism', 'no-reply@localhost'),
        # Uncomment to investigate SQL queries
        # 'SQLALCHEMY_ECHO': True,
    })

    return app_config


@pytest.fixture(scope='module')
def create_app():
    """Create app fixture for UI+API app."""
    return _create_app


# Plethora of required pre-existing data to create a record


def create_vocabulary_type(id_, pid):
    """Create vocabulary type."""
    vocabulary_service = current_service_registry.get("vocabularies")
    return vocabulary_service.create_type(system_identity, id_, pid)


@pytest.fixture(scope="module")
def resourcetypes_type(app):
    """Resource type vocabulary type."""
    return create_vocabulary_type("resourcetypes", "rsrct")


@pytest.fixture(scope="module")
def resourcetypes(app, resourcetypes_type):
    """Resource type vocabulary record."""
    vocabulary_service = current_service_registry.get("vocabularies")
    vocabulary_service.create(
        system_identity,
        {  # create parent resource type
            "id": "text",
            "title": {
                "en": "Text Resources"
            },
            "type": "resourcetypes"
        }
    )
    program = vocabulary_service.create(
        system_identity,
        {
            "icon": "file alternate",
            "id": "text-program",
            "props": {
                "coar": "text",
                "csl": "",
                "datacite_general": "Text",
                "datacite_type": "Program",
                "eurepo": "info:eu-repo/semantics/other",
                "openaire_resourceType": "",
                "openaire_type": "Text",
                "schema.org": "https://schema.org/TextDigitalDocument",
                "subtype": "text-program",
                "type": "text",
            },
            "title": {
                "en": "Program"
            },
            "tags": ["depositable", "linkable"],
            "type": "resourcetypes"
        }
    )
    return [program]


@pytest.fixture(scope="module")
def running_app(app, location, resourcetypes):
    """Running app."""
    return app


@pytest.fixture(scope="module")
def minimal_record_input():
    """Record input dict."""
    return {
        "pids": {},
        "access": {
            "record": "public",
            "files": "public",
        },
        "files": {
            "enabled": False,  # Most tests don't care about files
        },
        "metadata": {
            "creators": [
                {
                    "person_or_org": {
                        "family_name": "Brown",
                        "given_name": "Troy",
                        "type": "personal",
                    }
                },
                {
                    "person_or_org": {
                        "name": "Troy Inc.",
                        "type": "organizational",
                    },
                },
            ],
            "publication_date": "2020-06-01",
            # because DATACITE_ENABLED is True, this field is required
            "publisher": "Acme Inc",
            "resource_type": {"id": "text-program"},
            "title": "A Romans story",
        },
    }


@pytest.fixture(scope="module")
def create_draft_data(running_app, minimal_record_input):
    """Draft data-layer fixture."""
    records_service = current_service_registry.get("records")

    def _create_draft_data(
        identity=None,
        record_input=minimal_record_input,
    ):
        """Create a data-layer draft record."""
        identity = identity or system_identity
        draft_data = records_service.create(identity, record_input)._record
        return draft_data

    return _create_draft_data


@pytest.fixture(scope="module")
def create_record_data(create_draft_data, minimal_record_input):
    """Record data-layer fixture."""
    record_service = current_service_registry.get("records")

    def _create_record_data(
        identity=None,
        record_input=minimal_record_input,
    ):
        """Create a data-layer record."""
        identity = identity or system_identity
        draft_data = create_draft_data(identity, record_input)
        record_result = record_service.publish(
            identity, draft_data.pid.pid_value
        )
        return record_result._record

    return _create_record_data


@pytest.fixture(scope="function")
def create_record_data_fn(create_record_data, db, search):
    """Function scoped record creation fixture."""

    def _create_record_data(identity, record_input):
        """Create a data-layer record."""
        return create_record_data(identity, record_input)

    return _create_record_data


@pytest.fixture(scope="function")
def minimal_subject_input():
    """Minimal subject input dict."""
    return {
        "id": "http://example.org/foo/0",
        "scheme": "foo",
        "subject": "0",
    }


@pytest.fixture(scope="function")
def create_subject_data(running_app, db, search, minimal_subject_input):
    """Create data-layer subjects."""
    subjects_service = current_service_registry.get("subjects")

    def _create_subject_data(
        identity=None,
        input_=None
    ):
        """Create a data-layer subject."""
        identity = identity or system_identity
        input_ = input_ or minimal_subject_input
        result = subjects_service.create(
            identity,
            input_
        )
        return result._record

    return _create_subject_data
