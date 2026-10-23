from backend.agents.groq_evaluator import GroqEvaluator


def main():
    print("Starting Groq evaluator test...")

    evaluator = GroqEvaluator()

    result = evaluator.evaluate(
        evidence=(
            "We collect personal information to provide our services. "
            "Users may contact privacy@example.com for privacy questions."
        ),
        indicator_id="A1",
        indicator_description=(
            "Basic privacy policy information and contact details."
        ),
    )

    print("\n--- Groq Evaluator Result ---")
    print(result.to_dict())


if __name__ == "__main__":
    main()
    