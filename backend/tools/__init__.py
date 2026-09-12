"""Placeholder package for real specialist tools (Phase 2+).

This package must never import backend.store / store — the single-writer test
(tests/test_single_writer.py, REC-03/D-05) AST-scans every module here and
fails the suite if it finds a store import. Only FastAPI merges typed agent
output into the EngagementStore.
"""
