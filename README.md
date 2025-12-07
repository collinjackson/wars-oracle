# Wars Oracle

An AI-powered strategic advisor for turn-based strategy games (specifically Advance Wars clones like AWBW).

This project exposes a Vercel-hosted API that:
1.  Scrapes public game state (Map, Units, Teams, Economy).
2.  Translates it into a clean, hallucination-free "Context" blob.
3.  Serves it to LLMs (like ChatGPT) via an OpenAPI schema.

## Usage

### As a ChatGPT Action
Import the `openapi.yaml` into your Custom GPT to enable the `getGameContext` action.

### As a Developer API
```bash
curl https://wars-oracle.vercel.app/api/game/<GAME_ID>/context
```

## License

**GNU General Public License v3.0 (GPLv3)**

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

See `LICENSE` for details.

