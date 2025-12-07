import { openai } from '@ai-sdk/openai';
import { streamText } from 'ai';

export const maxDuration = 30;

export async function POST(req: Request) {
  const { messages, data } = await req.json();
  
  const analysis = data?.analysis;
  const username = data?.username || 'Commander';

  let systemMessage = `You are the Wars Oracle, an advanced strategic AI for Advance Wars By Web.
Your goal is to provide actionable, high-level strategic advice based on the game state.
Be concise, tactical, and direct. Focus on threats, economy, and key moves.
Analyze the provided game state data to justify your advice.
Do not hallucinate rules or units that are not present.`;

  if (analysis) {
    systemMessage += `\n\n=== CURRENT GAME STATE ANALYSIS for ${username} ===\n${JSON.stringify(analysis, null, 2)}\n=====================================`;
  }

  const result = await streamText({
    model: openai('gpt-4o'),
    system: systemMessage,
    messages,
  });

  return result.toDataStreamResponse();
}

