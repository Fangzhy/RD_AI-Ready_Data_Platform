"""Run the fixed evaluation locally or explicitly exercise one live free-model call."""
import argparse
import json

from src.evaluation import evaluate
from src.openrouter import GenerationError, generate
from src.retrieval import retrieve, supported
from src.workspace import build


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Send one synthetic lookup to the configured free model.")
    args = parser.parse_args()
    db = build()
    try:
        if args.live:
            question = "What measurement was recorded in EXP-A001?"
            answer, model = generate(question,supported(question,retrieve(db,question)))
            print(json.dumps({"model":model,**answer},indent=2))
        else:
            print(json.dumps(evaluate(db)[0],indent=2))
    except GenerationError as error:
        raise SystemExit(str(error)) from None
    finally:
        db.close()


if __name__ == "__main__":
    main()
