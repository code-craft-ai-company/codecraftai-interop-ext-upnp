=========================================
Automation Mojo Interop Extension: UPnP
=========================================

The ``automojo-interop-ext-upnp`` package is a UPnP extension for the ``automojo-interop`` and ``automojo-landscaping`` frameworks. It plugs into the extension points exposed by ``automojo-extension``, ``automojo-interop``, and ``automojo-landscaping`` to add UPnP-aware protocol handlers, device discovery, service proxies, and landscaping coordinators without modifying the host packages.

Highlights
==========

- UPnP model under ``interop/protocols/upnp/``: ``upnpdevicebase``, ``upnprootdevice``, ``upnpembeddeddevice``, ``upnpserviceproxy``, service state tables, and action descriptions.
- Discovery and presence: ``upnppresence``, ``upnpsearchwindow``, ``devicequerymanager``, and ``devicemetadatamanager``.
- SOAP helper and DIDL-Lite content support.
- Service-proxy and device-class generator that produces typed bindings from device descriptions.
- ``UpnpCoordinatorCoupling`` under ``landscaping/`` so UPnP devices show up as first-class landscape resources, plus manufacturer-specific mappings (for example, Bose).
- ``cli/cmdtree/upnp/`` command group for operator tooling.

Repository Structure
====================

- ``development/`` - Runtime environment scripts.
- ``repository-setup/`` - Repository homing and setup scripts.
- ``source/packages/`` - Package source code.
- ``source/testroots/automojo/`` - TestBase test roots.
- ``source/examples/`` - Example UPnP usage.
- ``userguide/`` - Standards, conventions, and documentation.

Environment Setup
=================

When working in a Codex container:

.. code-block:: bash

   ./development/setup-agent-container

For local development:

.. code-block:: bash

   ./repository-setup/rehome-repository
   ./development/setup-envrionment

Running Tests
=============

Activate the virtual environment:

.. code-block:: bash

   source .venv/bin/activate

Run the single-host test suite:

.. code-block:: bash

   testbase testing run --root source/testroots/automojo --includes=automojo.tests.singlehost --output=./.output

Standards and Conventions
=========================

- Naming conventions: ``userguide/10-02-naming-conventions.rst``
- Code organization: ``userguide/10-01-code-organization.rst``
- Coding standards: ``userguide/10-00-coding-standards.rst``

Additional Resources
====================

- User guide entry point: ``userguide/userguide.rst``
