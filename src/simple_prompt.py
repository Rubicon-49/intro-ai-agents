"""
simple_prompt.py

An interactive CLI assistant for financial analysts.

This script builds on `simple_llm.py` and extends it into a more complete agentic workflow: the analyst can describe a task (e.g., analyzing a balance sheet, income statement, cash flow or share price series), and the LLM will:

    1. Write a clean, documented Python function to perform the requested analysis.
    2. Generate a short README.md section explaining what the function does.
    3. Produce unit tests verifying correctness of the implementation.

The tool uses the `click`library for a command-line interface and configuration from `config.toml` for model, temperature, and system prompts.
"""

from pathlib import Path
import click
from llmutils import generate_response, extract_code_block, CFG


# ------------------------------------------------------------------
# CLI definition
# ------------------------------------------------------------------
@click.group()
def cli():
    """A command-line assistant for financial analysts."""
    pass


# ----------------------------------------------------------------------
# CLI command: analyze
# ----------------------------------------------------------------------
@cli.command()
@click.argument("task", required=False)
@click.option("--output", "-o", type=click.Path(), help="Output file name (optional)")
@click.option(
    "--model", default=CFG["general"]["model"], show_default=True, help="Model to use."
)
@click.option(
    "--temperature",
    default=CFG["general"]["temperature"],
    show_default=True,
    help="Sampling temperature for generation.",
)
def analyze(task, output, model, temperature):
    """
    Ask the LLM to generate analytical Python code for a given financial dataset.

    The financial analyst can describe a task such as:
      - "Analyze the balance sheet and compute the debt-to-equity ratio."
      - "Analyze income statement trends for the last two years."
      - "Write code to visualize closing prices and volatility of AAPL and TSLA."
      - "Summarize key liquidity and profitability ratios from cash flows."

    Example:
      $ python simple_prompt.py analyze
    """

    # ------------------------------------------------------------------
    # Step 1: Collect analyst request
    # ------------------------------------------------------------------
    if not task:
        description = click.prompt(
            "Please describe the function you want to create (e.g., 'analyze the income statement for profitability ratios')"
        )
    else:
        description = task

    click.echo("\n=== Building your request to the LLM ===\n")

    # Base message context

    user_prompt = (
        f"Please write a clean Python function that {description}.\n"
        + CFG["prompt"]["user_prompt1"]
    )

    messages = [
        {"role": "system", "content": CFG["prompt"]["system_prompt"]},
        {"role": "system", "content": user_prompt},
    ]

    # ------------------------------------------------------------------
    # Step 2: Ask the model to generate the full response
    # ------------------------------------------------------------------

    base_response = generate_response(messages, model=model, temperature=temperature)

    # Extract Python code and documentation from the LLM output
    base_function = extract_code_block(base_response)

    click.echo("\n=== Generated Function ===\n")
    click.echo(base_function or base_response)

    # ------------------------------------------------------------------
    # Step 3: Generate a README.md summary
    # ------------------------------------------------------------------

    messages.append(
        {
            "role": "assistant",
            "content": base_function
        }
    )
    messages.append({"role": "user", "content": CFG["prompt"]["user_prompt2"]})

    readme_response = generate_response(messages, model=model, temperature=temperature)
    readme_content = extract_code_block(readme_response) or readme_response

    click.echo("\n=== README Summary ===\n)")
    click.echo(readme_content)

    # ------------------------------------------------------------------
    # Step 4: Ask for test cases
    # ------------------------------------------------------------------
    messages.append({"role": "assistant", "content": readme_content})
    messages.append({"role": "user", "content": CFG["prompt"]["user_prompt3"]})

    test_response = generate_response(messages, model=model, temperature=temperature)
    test_code = extract_code_block(test_response)

    click.echo("\n=== Unit Tests ===\n")
    click.echo(test_code)

    # ------------------------------------------------------------------
    # Step 5: Save outputs to files
    # ------------------------------------------------------------------
    if not output:
        safe_name = "".join(
            c for c in description.lower() if c.isalnum() or c.isspace()
        )
        base_filename = safe_name.replace(" ", "_")[:30]
        output_dir = Path.cwd()
        output_code = output_dir / f"{base_filename}.py"
        output_readme = output_dir / f"README_{base_filename}.md"
    else:
        output_code = Path(output)
        output_readme = output_code.with_suffix(".md")

    with open(output_code, "w", encoding="utf-8") as f:
        f.write(base_function + "\n\n" + test_code)

    with open(output_readme, "w", encoding="utf-8") as f:
        f.write(readme_content)

    click.echo(f"\nCode saved to: {output_code}")
    click.echo(f"Documentation saved to: {output_readme}")


# ----------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------

if __name__ == "__main__":
    cli()
