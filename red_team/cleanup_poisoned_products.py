"""Remove poisoned PI-indirect products from ChromaDB.

Run ONLY after Fase 9 (defenses) is complete.
Do NOT run before merging Fase 7 — products must remain for Fase 9 re-execution.

Usage:
    python -m red_team.cleanup_poisoned_products [--chroma-url http://localhost:8000] [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import sys

import chromadb

from red_team.payloads.prompt_injection_indirect import remove_poisoned_products


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove red-team poisoned products from ChromaDB (run after Fase 9)"
    )
    parser.add_argument(
        "--chroma-url",
        default=os.environ.get("CHROMA_URL", "http://localhost:8000"),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be removed without deleting",
    )
    args = parser.parse_args()

    url = args.chroma_url
    without_scheme = url.split("//", 1)[-1].rstrip("/")
    if ":" in without_scheme:
        host, port_str = without_scheme.rsplit(":", 1)
    else:
        host, port_str = without_scheme, "8000"
    client = chromadb.HttpClient(host=host, port=int(port_str))

    from red_team.payloads.prompt_injection_indirect import PI_INDIRECT_PAYLOADS

    if args.dry_run:
        print(f"[dry-run] Would remove {len(PI_INDIRECT_PAYLOADS)} poisoned product(s):")
        for p in PI_INDIRECT_PAYLOADS:
            print(f"  - {p.chroma_id}  ({p.technique})")
        sys.exit(0)

    removed = remove_poisoned_products(client)
    print(f"Removed {removed} poisoned product(s) from ChromaDB.")


if __name__ == "__main__":
    main()
