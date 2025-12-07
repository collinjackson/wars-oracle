# Contributing to Wars Oracle

We welcome contributions! Whether you're fixing a bug, adding a new CO definition, or improving the ASCII renderer, here is how to get started.

## How to Contribute

1.  **Fork the Repo**: Create your own fork on GitHub.
2.  **Clone Locally**: `git clone ...`
3.  **Install Dependencies**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```
4.  **Run Locally**:
    You can run the debug script to test scraping:
    ```bash
    python3 debug_api.py
    ```
    (Note: You might need to adjust imports if running scripts directly vs as a module).

5.  **Submit a PR**: Push your branch and open a Pull Request against `main`.

## Project Structure

*   `api/index.py`: The Vercel Serverless Function entry point.
*   `fetch_*.py`: Scrapers for AWBW data.
*   `map_converter.py`: Translates CSV map data to JSON.
*   `context_generator.py`: The brain. Assembles the text prompt for the AI.
*   `rules.json`: Hardcoded CO stats and unit costs.

## License

By contributing, you agree that your contributions will be licensed under the GPLv3.

