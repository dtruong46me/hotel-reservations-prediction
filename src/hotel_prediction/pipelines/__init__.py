"""
hotel_prediction.pipelines
===========================
Orchestration modules for executing ML workflows.

This sub-package contains scripts that wire together individual
components (from :mod:`~hotel_prediction.components`) to execute
a full end-to-end process.

Pipelines are designed to be run as scripts (entry points) rather
than imported as libraries, although their main entry functions
(e.g., :func:`~hotel_prediction.pipelines.training_pipeline.run_training_pipeline`)
can be imported and triggered programmatically if needed.
"""
