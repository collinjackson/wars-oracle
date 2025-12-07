# How to Connect Wars Oracle to ChatGPT

Since you are on a personal plan, you might be looking for "Custom GPTs". This feature requires **ChatGPT Plus** (the $20/mo subscription).

If you **do** have Plus, here is the hidden menu:

1.  Go to [chatgpt.com](https://chatgpt.com).
2.  Click on your name in the bottom left -> **My GPTs**. (If you don't see this, click "Explore GPTs" in the sidebar).
3.  Click **+ Create**.
4.  In the "Create" tab (split screen), switch to **Configure**.
5.  Scroll down to the bottom. You will see **"Actions"**.
6.  Click **Create new action**.
7.  **Import from URL**: Paste your OpenAPI schema (content below).

---

### OpenAPI Schema (Copy This)

```yaml
openapi: 3.1.0
info:
  title: Wars Oracle
  description: API for retrieving turn-based strategy game state and context.
  version: 1.0.0
servers:
  - url: https://wars-oracle.vercel.app
paths:
  /api/game/{gameId}/context:
    get:
      operationId: getGameContext
      summary: Get game strategy context
      parameters:
        - name: gameId
          in: path
          required: true
          schema:
            type: integer
      responses:
        '200':
          description: OK
          content:
            text/plain:
              schema:
                type: string
```

---

## Alternative: Using it WITHOUT ChatGPT Plus

If you don't have Plus, you can't create "Actions". However, you can still use your API!

1.  **Manual Mode**: Visit your API URL in a browser:
    `https://wars-oracle.vercel.app/api/game/1548776/context`
2.  **Copy-Paste**: Select All -> Copy the text response.
3.  **Paste to ChatGPT**: "Here is my game state: [Paste]. What should I do?"

It's one extra step, but it works perfectly on the free tier.
