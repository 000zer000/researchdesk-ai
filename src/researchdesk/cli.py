import argparse
import json

from .db import Session


def main():
    parser = argparse.ArgumentParser(
        description="Local ResearchDesk administration; never exposed as HTTP"
    )
    parser.add_argument("command", choices=["models", "ingest", "stats", "evaluate"])
    parser.add_argument("--split", choices=["dev", "final"], default="final")
    args = parser.parse_args()
    if args.command == "models":
        from .embeddings import download_embeddings
        from .provider import download_llm

        print(download_embeddings())
        print(download_llm())
    elif args.command == "ingest":
        from .ingestion import ingest

        with Session() as session:
            print(json.dumps(ingest(session), indent=2))
    elif args.command == "evaluate":
        from .evaluation_v12 import evaluate

        evaluate(split=args.split)
    else:
        from .db import Document, Fact, Passage

        with Session() as session:
            print(
                {
                    "documents": session.query(Document).count(),
                    "passages": session.query(Passage).count(),
                    "facts": session.query(Fact).count(),
                }
            )
