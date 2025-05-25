#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "anthropic>=0.20.0", # Or a version compatible with the latest tool use features
#   "rich>=13.0.0",
#   "requests>=2.20.0" # For Ollama API calls
# ]
# ///

"""
Single-File Agent: Ollama Delegator

Purpose:
This agent uses a primary LLM (e.g., Anthropic Claude) to understand user requests 
and can delegate specific text generation or analysis tasks to a locally running 
Ollama instance using a specified model.

Example Usage:
# Make sure OLLAMA_BASE_URL is set, e.g., export OLLAMA_BASE_URL='http://localhost:11434'
# Ensure you have an Ollama model pulled, e.g., ollama pull llama3
uv run sfa_ollama_delegator_agent.py --prompt "Summarize the following text using the 'llama3' model locally: <your long text here>. Then, tell me (as Claude) if the summary is good."
"""

import os
import sys
import json
import argparse
import requests # For Ollama
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.panel import Panel
from anthropic import Anthropic

# Initialize Rich Console
console = Console()

# This global variable will be set in the main() function.
# It's used here to indicate dependency.
OLLAMA_BASE_URL = ""

def run_ollama_generate(
    model_name: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    context_window: Optional[int] = None
) -> str:
    """
    Invokes a local Ollama model for text generation using the /api/generate endpoint.
    """
    global OLLAMA_BASE_URL # Access the global variable set in main()

    if not OLLAMA_BASE_URL:
        # This case should ideally be handled before calling, or OLLAMA_BASE_URL ensured by main.
        console.log("[red]Error: OLLAMA_BASE_URL is not configured.[/red]")
        return "Error: OLLAMA_BASE_URL is not configured."

    api_url = f"{OLLAMA_BASE_URL}/api/generate"

    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False  # We want the full response at once for this tool
    }
    if system_prompt:
        payload["system"] = system_prompt

    options = {}
    if context_window:
        # Note: 'num_ctx' in Ollama's API is typically for model loading or global config.
        # Overriding per /api/generate call might have limitations or specific model support.
        options["num_ctx"] = context_window
    if options:
        payload["options"] = options

    console.log(f"[cyan]Ollama Tool:[/cyan] Sending request to {api_url} for model '{model_name}'. Payload: {payload}")

    try:
        response = requests.post(api_url, json=payload, timeout=120) # 120-second timeout
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

        response_json = response.json()
        generated_text = response_json.get("response", "")
        
        # Additional details from the response can be logged if needed
        # e.g., response_json.get("total_duration"), response_json.get("eval_count")
        console.log(f"[cyan]Ollama Tool:[/cyan] Successfully received response from model '{model_name}'. Output: '{generated_text[:100]}...'")
        return generated_text

    except requests.exceptions.Timeout:
        error_msg = f"Error: Timeout after 120s connecting to Ollama API at {api_url}."
        console.log(f"[red]Ollama Tool Error:[/red] {error_msg}")
        return error_msg
    except requests.exceptions.ConnectionError:
        error_msg = f"Error: Connection refused by Ollama API at {api_url}. Is Ollama running and accessible?"
        console.log(f"[red]Ollama Tool Error:[/red] {error_msg}")
        return error_msg
    except requests.exceptions.HTTPError as e:
        # Attempt to get more detailed error from Ollama's response if possible
        ollama_error_detail = ""
        try:
            ollama_error_detail = e.response.json().get("error", e.response.text)
        except json.JSONDecodeError:
            ollama_error_detail = e.response.text
        error_msg = f"Error: Ollama API request failed with status {e.response.status_code}. Detail: {ollama_error_detail}"
        console.log(f"[red]Ollama Tool Error:[/red] {error_msg}")
        return error_msg
    except requests.exceptions.RequestException as e:
        # Catch any other requests-related errors
        error_msg = f"Error: An unexpected error occurred with the Ollama API request: {str(e)}"
        console.log(f"[red]Ollama Tool Error:[/red] {error_msg}")
        return error_msg
    except json.JSONDecodeError:
        # This might happen if the response isn't valid JSON, despite a 200 OK status
        error_msg = "Error: Could not decode JSON response from Ollama API, even though request seemed successful."
        console.log(f"[red]Ollama Tool Error:[/red] {error_msg}")
        return error_msg

# --- Agent Prompt (Placeholder for Step 4) ---
AGENT_SYSTEM_PROMPT = """
You are a sophisticated AI assistant named 'Ollama Delegator'. Your primary LLM is Anthropic Claude.
Your core function is to accurately interpret user requests and achieve them by leveraging available tools, including a specialized tool for interacting with local Ollama instances.

<purpose>
Your main goal is to fulfill user requests effectively. You can respond directly using your own (Claude's) knowledge and reasoning capabilities, or you can delegate specific text generation, analysis, or coding tasks to a locally hosted Ollama model via the `run_ollama_generate` tool.
</purpose>

<instructions>
1.  **Analyze the Request:** Carefully understand the user's needs. Determine if the task is best handled by your internal Claude capabilities or if it should be delegated to a local Ollama model.
2.  **Tool Usage - `run_ollama_generate`:**
    *   **When to Use:**
        *   When the user explicitly requests the use of a local model or mentions a specific Ollama model name (e.g., "llama3", "mistral", "codellama").
        *   For tasks that benefit from local processing, such as operating on sensitive data that shouldn't leave the user's environment (if the user indicates this preference).
        *   When the user wants to leverage the specific capabilities of a fine-tuned local model.
        *   For computationally intensive generation tasks where offloading to a local Ollama instance is desirable.
    *   **Tool Parameters:**
        *   `model_name` (str, required): The exact name of the model hosted in the local Ollama instance (e.g., "llama3", "mistral"). You should ask the user for this if it's not specified and you deem the tool necessary. If the user mentions a generic type like "a local summarizer model," ask for a specific model name available in their Ollama setup.
        *   `prompt` (str, required): The specific prompt to be sent to the Ollama model. Craft this prompt carefully based on the user's request for the sub-task.
        *   `system_prompt` (Optional[str]): A system prompt to guide the behavior of the chosen Ollama model for the delegated task.
        *   `context_window` (Optional[int]): Specify if the user provides a particular context window size they wish the local model to adhere to. Be aware that not all models or the Ollama API might support overriding this on a per-call basis effectively.
    *   **Confirmation:** Before using the `run_ollama_generate` tool, if there's any ambiguity about the model name or the suitability of using a local model, confirm with the user. For example: "I can use a local Ollama model for this. Which model would you like to use (e.g., llama3, mistral)?"
3.  **Combining Capabilities:**
    *   Do not just return the raw output from `run_ollama_generate`.
    *   After receiving a response from the Ollama tool, integrate it into your response. You (Claude) should provide context, analysis, or further processing of the Ollama model's output. For example, if Ollama summarizes a text, you might then analyze the quality of the summary or answer questions about it.
    *   If the `run_ollama_generate` tool returns an error, inform the user about the error and do not attempt to re-run the tool with the exact same parameters without addressing the cause or explicit user instruction.
4.  **Clarity and Conciseness:** Provide clear, concise, and helpful responses.
5.  **Efficiency:** Use tools only when necessary. If a request can be handled directly by you (Claude) efficiently and effectively, do so.
</instructions>

<user_interaction>
- If the user's request is vague regarding the use of a local model, ask clarifying questions.
- Clearly state when you are about to use the `run_ollama_generate` tool and which model you intend to use.
- Present the results from the local model clearly, often quoting or summarizing its output, before adding your own insights.
</user_interaction>

Remember, you are the primary interface to the user. The `run_ollama_generate` tool is a powerful capability for you to draw upon.
"""

    # --- Main Agent Logic ---
def main():
    parser = argparse.ArgumentParser(description="SFA Ollama Delegator Agent")
    parser.add_argument("-p", "--prompt", required=True, help="User's request to the agent")
    parser.add_argument(
        "-m", 
        "--model", 
        default="claude-3-haiku-20240307", 
        help="Primary LLM model for the agent (default: claude-3-haiku-20240307)" 
    )
    parser.add_argument(
        "-c",
        "--compute",
        type=int,
        default=7, 
        help="Maximum number of agent loops (default: 7)",
    )
    parser.add_argument(
        "--ollama-base-url",
        default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        help="Base URL for the Ollama API (defaults to env OLLAMA_BASE_URL or http://localhost:11434)"
    )

    args = parser.parse_args()

    console.print(Panel(f"User Prompt: {args.prompt}", title="[bold blue]Request[/bold blue]", expand=False))
    console.print(f"Primary LLM: {args.model}, Ollama URL: {args.ollama_base_url}, Max Loops: {args.compute}")

    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    if not ANTHROPIC_API_KEY:
        console.print("[red]Error: ANTHROPIC_API_KEY environment variable not set.[/red]")
        sys.exit(1)
    
    client = Anthropic(api_key=ANTHROPIC_API_KEY) 
    
    global OLLAMA_BASE_URL 
    OLLAMA_BASE_URL = args.ollama_base_url
    # No need to log OLLAMA_BASE_URL here, it's logged by the tool if used, or above as part of args.

    messages = [{"role": "user", "content": args.prompt}]
    
    tools = [
        {
            "name": "run_ollama_generate",
            "description": "Delegates text generation to a local Ollama model. Use this for specific local models or tasks requiring local processing.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": "The name of the Ollama model (e.g., 'llama3', 'mistral'). Must be available in the local Ollama instance."
                    },
                    "prompt": {
                        "type": "string",
                        "description": "The prompt to send to the Ollama model."
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "Optional system prompt for the Ollama model."
                    },
                    "context_window": {
                        "type": "integer",
                        "description": "Optional context window size for the Ollama model."
                    }
                },
                "required": ["model_name", "prompt"]
            }
        }
    ]

    final_answer_delivered = False
    loop_count = 0
    max_loops = args.compute

    for i in range(max_loops):
        loop_count = i + 1
        console.rule(f"[yellow]Agent Loop {loop_count}/{max_loops}[/yellow]")

        try:
            response = client.messages.create(
                model=args.model,
                max_tokens=2048, 
                system=AGENT_SYSTEM_PROMPT, 
                messages=messages,
                tools=tools,
                tool_choice={"type": "auto"}
            )
        except Exception as e:
            console.print(f"[red]Error calling Anthropic API: {str(e)}[/red]")
            break # Exit loop on API error

        # Append assistant's entire response (raw, including potential tool calls)
        messages.append({"role": "assistant", "content": response.content})

        has_text_response = False
        tool_calls_to_fulfill = [] # Tool calls from this specific response

        for content_block in response.content:
            if content_block.type == "text":
                if content_block.text.strip():
                    console.print(Panel(content_block.text, title="[bold green]Ollama Delegator Agent (Claude)[/bold green]", expand=False))
                    has_text_response = True
            elif content_block.type == "tool_use":
                tool_calls_to_fulfill.append(content_block)
        
        if not tool_calls_to_fulfill and has_text_response:
            console.print("[bold blue]--- Agent delivered final text response. ---[/bold blue]")
            final_answer_delivered = True
            break # Exit loop as agent has responded with text and no further tools.

        if tool_calls_to_fulfill:
            tool_results_content_blocks = [] # Content blocks for the next user message
            for tool_call in tool_calls_to_fulfill:
                tool_name = tool_call.name
                tool_input = tool_call.input
                tool_use_id = tool_call.id

                console.log(f"[cyan]LLM Requested Tool Call:[/cyan] ID: {tool_use_id} Tool: {tool_name}({json.dumps(tool_input)})")

                tool_output_content = "" # This will be a string

                if tool_name == "run_ollama_generate":
                    model_name_arg = tool_input.get("model_name")
                    prompt_arg = tool_input.get("prompt")

                    if not model_name_arg or not prompt_arg:
                        tool_output_content = f"Error: 'model_name' and 'prompt' are required for {tool_name}."
                        console.print(f"[red]{tool_output_content}[/red]")
                    else:
                        try:
                            tool_output_content = run_ollama_generate(
                                model_name=model_name_arg,
                                prompt=prompt_arg,
                                system_prompt=tool_input.get("system_prompt"),
                                context_window=tool_input.get("context_window")
                            )
                            console.print(Panel(tool_output_content, title=f"[bold purple]Ollama ({model_name_arg}) Direct Output[/bold purple]", expand=False))
                        except Exception as e: # Should be rare if run_ollama_generate handles its own errors
                            tool_output_content = f"Error executing tool {tool_name} internally: {str(e)}"
                            console.print(f"[red]{tool_output_content}[/red]")
                else:
                    tool_output_content = f"Error: Unknown tool '{tool_name}' called by LLM."
                    console.log(f"[red]{tool_output_content}[/red]")
                
                tool_results_content_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": tool_output_content # Content is a string
                })
            
            if tool_results_content_blocks:
                 messages.append({"role": "user", "content": tool_results_content_blocks})
            # else: No explicit warning if tool_results_content_blocks is empty, as this means no valid tools were called.
                 
        elif not has_text_response: # No tool calls and no text response from LLM
            console.print("[yellow]Warning: LLM did not provide text or call a tool in this turn. Ending loop.[/yellow]")
            break # Exit loop as LLM didn't give text or tools
    
    # After loop finishes or breaks
    if final_answer_delivered:
        console.print("[bold green]Agent run completed successfully.[/bold green]")
    elif loop_count == max_loops and not final_answer_delivered:
        console.print(f"[yellow]Warning: Reached maximum agent loops ({max_loops}) without a definitive final text response.[/yellow]")
    elif not final_answer_delivered: # Loop broke for other reasons (API error, LLM no-op)
        console.print("[red]Agent run concluded without delivering a final answer due to errors or unexpected LLM behavior.[/red]")


if __name__ == "__main__":
    main()
