
import json
import sys
from pathlib import Path
from collections import defaultdict

# --------------------------------------------------
# PATH CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_FILE = PROJECT_ROOT / "evaluation" / "evaluation_dataset.json"
REPORT_FILE = PROJECT_ROOT / "evaluation" / "indicator_evaluation_report.json"

# Allow importing the existing backend indicator engine.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.indicators.indicator_engine import IndicatorEngine


# --------------------------------------------------
# METRICS
# --------------------------------------------------

def calculate_metrics(tp, fp, tn, fn):
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )

    accuracy = (
        (tp + tn) / (tp + fp + tn + fn)
        if tp + fp + tn + fn
        else 0.0
    )

    return {
        "true_positive": tp,
        "false_positive": fp,
        "true_negative": tn,
        "false_negative": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "evaluated_cases": tp + fp + tn + fn,
    }


# --------------------------------------------------
# EVALUATION
# --------------------------------------------------

def main():
    with DATASET_FILE.open("r", encoding="utf-8") as file:
        dataset = json.load(file)

    samples = dataset["samples"]
    target_indicators = dataset["target_indicators"]

    engine = IndicatorEngine()

    counts = {
        indicator_id: {
            "tp": 0,
            "fp": 0,
            "tn": 0,
            "fn": 0,
        }
        for indicator_id in target_indicators
    }

    detailed_results = []
    unlabeled_cases = 0

    for sample in samples:
        text = sample.get("text", "")
        annotations = sample.get("annotations", {})

        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                f"Sample {sample.get('sample_id')} has empty policy text."
            )

        analysis = engine.analyze_policy(text)

        predictions = {
            result["id"]: bool(result["matched"])
            for result in analysis["results"]
        }

        for indicator_id in target_indicators:
            annotation = annotations.get(indicator_id, {})

            # Unlabeled cases must not be treated as negatives.
            if annotation.get("labeled") is not True:
                unlabeled_cases += 1
                continue

            if "ground_truth" not in annotation:
                raise ValueError(
                    f"Missing ground_truth for "
                    f"{sample.get('sample_id')} / {indicator_id}"
                )

            if indicator_id not in predictions:
                raise ValueError(
                    f"Indicator {indicator_id} was not returned by the engine."
                )

            actual = annotation["ground_truth"]
            predicted = predictions[indicator_id]

            if not isinstance(actual, bool):
                raise ValueError(
                    f"ground_truth must be boolean for "
                    f"{sample.get('sample_id')} / {indicator_id}"
                )

            metric = counts[indicator_id]

            if actual and predicted:
                metric["tp"] += 1
                outcome = "TP"
            elif not actual and predicted:
                metric["fp"] += 1
                outcome = "FP"
            elif not actual and not predicted:
                metric["tn"] += 1
                outcome = "TN"
            else:
                metric["fn"] += 1
                outcome = "FN"

            detailed_results.append({
                "sample_id": sample.get("sample_id"),
                "indicator_id": indicator_id,
                "ground_truth": actual,
                "prediction": predicted,
                "outcome": outcome,
            })

    # Per-indicator metrics.
    per_indicator = {}

    for indicator_id, metric in counts.items():
        per_indicator[indicator_id] = calculate_metrics(
            metric["tp"],
            metric["fp"],
            metric["tn"],
            metric["fn"],
        )

    # Aggregate confusion counts across all labeled cases.
    total_tp = sum(item["tp"] for item in counts.values())
    total_fp = sum(item["fp"] for item in counts.values())
    total_tn = sum(item["tn"] for item in counts.values())
    total_fn = sum(item["fn"] for item in counts.values())

    overall = calculate_metrics(
        total_tp,
        total_fp,
        total_tn,
        total_fn,
    )

    report = {
        "dataset_schema_version": dataset.get("schema_version"),
        "total_samples": len(samples),
        "target_indicators": target_indicators,
        "labeled_cases_evaluated": len(detailed_results),
        "unlabeled_cases_excluded": unlabeled_cases,
        "overall": overall,
        "per_indicator": per_indicator,
        "details": detailed_results,
    }

    with REPORT_FILE.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    # --------------------------------------------------
    # CONSOLE SUMMARY
    # --------------------------------------------------

    print("=" * 76)
    print("PRIVACY COMPLIANCE AI — INDICATOR EVALUATION")
    print("=" * 76)

    print(f"Dataset samples:       {len(samples)}")
    print(f"Labeled cases tested:  {len(detailed_results)}")
    print(f"Unlabeled cases skipped: {unlabeled_cases}")

    print("\nPER-INDICATOR METRICS")
    print("-" * 76)
    print(
        f"{'ID':<8}{'Cases':>8}{'Precision':>13}"
        f"{'Recall':>12}{'F1-score':>12}{'Accuracy':>12}"
    )

    for indicator_id, metrics in per_indicator.items():
        print(
            f"{indicator_id:<8}"
            f"{metrics['evaluated_cases']:>8}"
            f"{metrics['precision']:>13.4f}"
            f"{metrics['recall']:>12.4f}"
            f"{metrics['f1_score']:>12.4f}"
            f"{metrics['accuracy']:>12.4f}"
        )

    print("\nOVERALL METRICS")
    print("-" * 76)
    print(f"Precision: {overall['precision']:.4f}")
    print(f"Recall:    {overall['recall']:.4f}")
    print(f"F1-score:  {overall['f1_score']:.4f}")
    print(f"Accuracy:  {overall['accuracy']:.4f}")

    print("\nOVERALL CONFUSION COUNTS")
    print(f"True positives:  {overall['true_positive']}")
    print(f"False positives: {overall['false_positive']}")
    print(f"True negatives:  {overall['true_negative']}")
    print(f"False negatives: {overall['false_negative']}")

    print(f"\nReport saved to: {REPORT_FILE}")


if __name__ == "__main__":
    main()

