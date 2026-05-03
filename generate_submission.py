import argparse
import json
from pathlib import Path

from submission_core import compose


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_dataset(dataset_dir: Path) -> tuple[dict, dict, dict, dict]:
    categories = {}
    for path in (dataset_dir / "categories").glob("*.json"):
        payload = load_json(path)
        categories[payload["slug"]] = payload

    merchants = {m["merchant_id"]: m for m in load_json(dataset_dir / "merchants_seed.json")["merchants"]}
    customers = {c["customer_id"]: c for c in load_json(dataset_dir / "customers_seed.json")["customers"]}
    triggers = {t["id"]: t for t in load_json(dataset_dir / "triggers_seed.json")["triggers"]}
    return categories, merchants, customers, triggers


def build_record(test_id: str, category: dict, merchant: dict, trigger: dict, customer: dict | None) -> dict:
    composed = compose(category, merchant, trigger, customer)
    return {"test_id": test_id, **composed}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", default="dataset")
    parser.add_argument("--pairs", help="JSONL file with lines containing test_id, trigger_id")
    parser.add_argument("--output", default="submission.jsonl")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    categories, merchants, customers, triggers = load_dataset(dataset_dir)

    rows = []
    if args.pairs:
        pairs_path = Path(args.pairs)
        for line in pairs_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            pair = json.loads(line)
            trigger = triggers[pair["trigger_id"]]
            merchant = merchants[trigger["merchant_id"]]
            category = categories[merchant["category_slug"]]
            customer = customers.get(trigger.get("customer_id")) if trigger.get("customer_id") else None
            rows.append(build_record(pair["test_id"], category, merchant, trigger, customer))
    else:
        for index, trigger in enumerate(triggers.values(), start=1):
            merchant = merchants[trigger["merchant_id"]]
            category = categories[merchant["category_slug"]]
            customer = customers.get(trigger.get("customer_id")) if trigger.get("customer_id") else None
            rows.append(build_record(f"T{index:02d}", category, merchant, trigger, customer))

    output_path = Path(args.output)
    output_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} records to {output_path}")


if __name__ == "__main__":
    main()
