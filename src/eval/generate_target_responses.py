import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from openai import OpenAI
from tqdm import tqdm

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.harness.runtime import load_harness_env


def main():
    load_harness_env(Path.cwd())

    parser = argparse.ArgumentParser(description="Generate target model responses for FinRED prompts.")
    parser.add_argument("-i", "--input_csv", required=True, help="Step2 prompts_all CSV path")
    parser.add_argument("-o", "--output_csv", required=True, help="Output CSV path for judge_finred.py")
    parser.add_argument("--model", default="gpt-4.1-mini", help="OpenAI-compatible target model name")
    parser.add_argument("--prompt_column", default="prompt_1", help="Prompt column to send to target model")
    parser.add_argument("--category_column", default="category_prefix", help="Category column name")
    parser.add_argument("--max_rows", type=int, default=None, help="Optional row limit for a quick test")
    parser.add_argument("--temperature", type=float, default=0.0)
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required.")

    input_path = Path(args.input_csv)
    output_path = Path(args.output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path, keep_default_na=False)
    if args.prompt_column not in df.columns:
        raise ValueError(f"Prompt column not found: {args.prompt_column}")
    if args.category_column not in df.columns:
        raise ValueError(f"Category column not found: {args.category_column}")

    if args.max_rows is not None:
        df = df.head(args.max_rows).copy()

    client = OpenAI(api_key=api_key)
    rows = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Generating responses"):
        attack_prompt = row[args.prompt_column]
        response = client.chat.completions.create(
            model=args.model,
            messages=[{"role": "user", "content": attack_prompt}],
            temperature=args.temperature,
        )
        rows.append({
            "category_prefix": row[args.category_column],
            "attack_prompt": attack_prompt,
            "response": response.choices[0].message.content or "",
        })

    pd.DataFrame(rows).to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Saved target responses: {output_path}")


if __name__ == "__main__":
    main()
