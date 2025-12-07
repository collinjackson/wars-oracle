# Wars Oracle

**Wars Oracle** is an AI-powered strategic advisor for turn-based strategy games (specifically Advance Wars clones like AWBW). It scrapes live game data (map, units, economy) and formats it into a hallucination-free context that LLMs (like ChatGPT or Claude) can understand to provide Grandmaster-level advice.

🔮 **Live Tool**: [https://wars-oracle.vercel.app](https://wars-oracle.vercel.app)

## Features

*   **Hallucination-Free Context**: Scrapes the *actual* map terrain, unit positions, HP, fuel, and ammo.
*   **Strategic Awareness**: Understands CO matchups (e.g., Max vs Grit), property ownership, and income.
*   **ASCII Visualization**: Renders a text-based map for the AI to "see" the board.
*   **API-First**: Exposes a clean OpenAPI endpoint for Custom GPTs and MCP (Model Context Protocol).

## Usage

### 1. Web Interface (Easiest)
1.  Go to [wars-oracle.vercel.app](https://wars-oracle.vercel.app).
2.  Paste your AWBW Game Link or ID (e.g., `1548776`).
3.  Select your Username from the dropdown.
4.  Click "Generate Briefing" and paste the result into ChatGPT.

### 2. Custom GPT (Best Experience)
If you have ChatGPT Plus, you can add this as a custom Action.
1.  Create a new GPT "Wars Oracle".
2.  In "Actions", import the schema from `openapi.yaml` (in this repo).
3.  Now you can just ask: *"Analyze game 1548776 for user ridiculotron"* and it will run the analysis automatically.

### 3. Developer API
```bash
curl "https://wars-oracle.vercel.app/api/game/1548776/context?username=ridiculotron"
```

## Roadmap

- [x] **Core Analysis**: Map, Units, Funds, COs.
- [x] **Team Awareness**: Knows who is Team A vs Team B.
- [x] **Property Ownership**: Tracks captured cities/bases.
- [x] **Turn Awareness**: Knows whose turn it is.
- [ ] **Fog of War Prediction**: Guessing hidden unit locations based on value drops (ZK-style).
- [ ] **Damage Calculator Integration**: Exact damage percentages in the context.
- [ ] **Movement Heatmaps**: Visualizing threat ranges in ASCII.

## License

**GNU General Public License v3.0 (GPLv3)**. See [LICENSE](./LICENSE).
