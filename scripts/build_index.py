#!/usr/bin/env python
"""
Standalone CLI to build/rebuild the retrieval index from the corpus
directory, without starting the API server. Useful for:

  - Verifying ingestion works after editing/adding a policy document.
  - Pre-warming a build (e.g. in a CI step or a container build stage)
    before the API server starts, so the first request isn't slow.

Usage:
    python scripts/build_index.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running this script directly (`python scripts/build_index.py`)
# without having installed the package, by adding `src/` to the path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from compliance_copilot.infrastructure.config import get_settings  # noqa: E402
from compliance_copilot.infrastructure.logging_setup import configure_logging  # noqa: E402
from compliance_copilot.service.rag_engine import RagEngine  # noqa: E402


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    engine = RagEngine(settings)
    chunk_count = engine.build()

    print(f"Indexed {chunk_count} chunks across {len(engine.corpus_metadata())} documents.")
    for doc in engine.corpus_metadata():
        print(f"  - {doc['doc_id']}: {doc['doc_title']} ({doc['chunk_count']} chunks)")


if __name__ == "__main__":
    main()
