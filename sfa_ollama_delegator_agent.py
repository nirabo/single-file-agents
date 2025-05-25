#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "anthropic>=0.20.0", # Or a version compatible with the latest tool use features
#   "rich>=13.0.0",
#   "requests>=2.20.0", # For Ollama API calls
#   "python-dotenv>=0.20.0"
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

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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

# --- New Ollama Chat Completion Function ---
def get_ollama_chat_completion(
    messages: List[Dict[str, Any]],
    model_name: str,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: Optional[str] = "auto" # Can also be a dict for specific function
) -> Dict[str, Any]:
    """
    Makes a request to the Ollama /api/chat endpoint.
    Handles basic tool calling parameters if the model supports them.
    """
    global OLLAMA_BASE_URL

    if not OLLAMA_BASE_URL:
        console.log("[red]Error: OLLAMA_BASE_URL is not configured for get_ollama_chat_completion.[/red]")
        return {"error": "OLLAMA_BASE_URL is not configured."}

    api_url = f"{OLLAMA_BASE_URL}/api/chat"
    headers = {"Content-Type": "application/json"}

    payload: Dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "stream": False,
        "options": { # Example options, can be parameterized later
            "temperature": 0.7,
            # "num_ctx": 4096 # Context window, model-dependent
        }
    }

    if tools:
        # Assuming Ollama uses OpenAI-like schema for tools if supported
        formatted_tools = []
        for tool_spec in tools:
            # This is a common way to structure tools for models that support OpenAI's schema
            # The 'input_schema' from Anthropic's format needs to map to 'parameters'
            if "input_schema" in tool_spec:
                 formatted_tools.append({
                    "type": "function", # Assuming 'function' type, could be other types
                    "function": {
                        "name": tool_spec["name"],
                        "description": tool_spec.get("description", ""),
                        "parameters": tool_spec["input_schema"]
                    }
                })
            else: # If no input_schema, maybe it's a simpler tool definition
                formatted_tools.append(tool_spec)


        if formatted_tools: # Only add if tools were successfully formatted
            payload["tools"] = formatted_tools
            if tool_choice: # tool_choice can be "auto", "none", "any", or specific like {"type": "function", "function": {"name": "my_func"}}
                payload["tool_choice"] = tool_choice
        else:
            console.log(f"[yellow]Warning: Tools provided to get_ollama_chat_completion but could not be formatted correctly. Sending request without tools.[/yellow]")


    console.log(f"[cyan]Ollama Chat:[/cyan] Sending request to {api_url} for model '{model_name}'. Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=180) # 180-second timeout

        if response.status_code >= 400:
            try:
                error_detail = response.json().get("error", response.text)
            except json.JSONDecodeError:
                error_detail = response.text
            error_msg = f"Error: Ollama /api/chat request failed with status {response.status_code}. Detail: {error_detail}"
            console.log(f"[red]Ollama Chat Error:[/red] {error_msg}")
            return {"error": error_msg, "status_code": response.status_code}

        response_json = response.json()
        
        # Log the full response for debugging if needed
        # console.log(f"[grey]Ollama Chat Full Response:[/grey] {json.dumps(response_json, indent=2)}")

        if "message" in response_json:
            console.log(f"[cyan]Ollama Chat:[/cyan] Successfully received response from model '{model_name}'.")
            return response_json["message"] # Return the message object
        elif "error" in response_json: # Some Ollama versions might return 200 OK but with an error in JSON
            console.log(f"[red]Ollama Chat Error (in 200 OK response):[/red] {response_json['error']}")
            return {"error": response_json['error']}
        else:
            # If no 'message' and no explicit 'error', return the whole JSON, but log a warning
            console.log(f"[yellow]Warning: Ollama /api/chat response for '{model_name}' did not contain a 'message' field. Returning full response.[/yellow]")
            return response_json

    except requests.exceptions.Timeout:
        error_msg = f"Error: Timeout after 180s connecting to Ollama /api/chat at {api_url}."
        console.log(f"[red]Ollama Chat Error:[/red] {error_msg}")
        return {"error": error_msg}
    except requests.exceptions.ConnectionError:
        error_msg = f"Error: Connection refused by Ollama /api/chat at {api_url}. Is Ollama running and accessible?"
        console.log(f"[red]Ollama Chat Error:[/red] {error_msg}")
        return {"error": error_msg}
    except requests.exceptions.RequestException as e:
        error_msg = f"Error: An unexpected error occurred with the Ollama /api/chat request: {str(e)}"
        console.log(f"[red]Ollama Chat Error:[/red] {error_msg}")
        return {"error": error_msg}
    except json.JSONDecodeError:
        error_msg = "Error: Could not decode JSON response from Ollama /api/chat."
        console.log(f"[red]Ollama Chat Error:[/red] {error_msg}")
        return {"error": error_msg}


# --- Agent Prompt (Placeholder for Step 4) ---
AGENT_SYSTEM_PROMPT = """
You are a sophisticated AI assistant named 'Ollama Delegator', equipped with advanced reasoning capabilities.
Your core function is to accurately interpret user requests and achieve them by leveraging available tools, including a specialized tool for interacting with local Ollama instances.

<purpose>
Your main goal is to fulfill user requests effectively. You can respond directly using your own core knowledge and advanced reasoning capabilities, or you can delegate specific text generation, analysis, or coding tasks to a locally hosted Ollama model via the `run_ollama_generate` tool.
</purpose>

<instructions>
1.  **Analyze the Request:** Carefully understand the user's needs. Determine if the task is best handled by your primary intelligence or if it should be delegated to a local Ollama model.
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
    *   After receiving a response from the Ollama tool, integrate it into your response. Your primary intelligence should provide context, analysis, or further processing of the Ollama model's output. For example, if Ollama summarizes a text, you might then analyze the quality of the summary or answer questions about it.
    *   If the `run_ollama_generate` tool returns an error, inform the user about the error and do not attempt to re-run the tool with the exact same parameters without addressing the cause or explicit user instruction.
4.  **Clarity and Conciseness:** Provide clear, concise, and helpful responses.
5.  **Efficiency:** Use tools only when necessary. If a request can be handled directly by your own advanced reasoning capabilities efficiently and effectively, do so.
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
    parser = argparse.ArgumentParser(description="SFA Ollama Delegator Agent. Config can be set via .env or CLI args (CLI overrides .env).")

    default_provider = os.getenv("PRIMARY_LLM_PROVIDER", "ollama")
    parser.add_argument(
        "--primary-provider",
        default=default_provider,
        choices=["ollama", "anthropic"],
        help=f"Primary LLM provider. Env: PRIMARY_LLM_PROVIDER, Default: '{default_provider}'."
    )

    # --primary-model default is determined after args are parsed, based on the provider.
    parser.add_argument(
        "--primary-model",
        default=None, 
        help="Primary LLM model name. Default from OLLAMA_PRIMARY_MODEL_NAME or ANTHROPIC_MODEL_NAME."
    )
    
    default_ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    parser.add_argument(
        "--ollama-base-url",
        default=default_ollama_url,
        help=f"Ollama API base URL. Env: OLLAMA_BASE_URL, Default: '{default_ollama_url}'."
    )
    
    default_compute_loops = int(os.getenv("DEFAULT_MAX_COMPUTE_LOOPS", "7"))
    parser.add_argument(
        "-c", "--compute",
        type=int,
        default=default_compute_loops,
        help=f"Max agent loops. Env: DEFAULT_MAX_COMPUTE_LOOPS, Default: {default_compute_loops}."
    )
    
    parser.add_argument("-p", "--prompt", required=True, help="User's request to the agent.")
    
    args = parser.parse_args()

    # Determine effective primary model after parsing, so we know the provider
    effective_provider = args.primary_provider
    effective_primary_model = args.primary_model # Will be updated below

    if effective_provider == 'ollama':
        effective_primary_model = args.primary_model or os.getenv("OLLAMA_PRIMARY_MODEL_NAME", "gemma2:9b")
        if not args.ollama_base_url: # Should be set by default, but good to check
            console.print("[red]Error: Ollama provider selected, but OLLAMA_BASE_URL is not set.[/red]")
            sys.exit(1)
    elif effective_provider == 'anthropic':
        effective_primary_model = args.primary_model or os.getenv("ANTHROPIC_MODEL_NAME", "claude-3-haiku-20240307")
        ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
        if not ANTHROPIC_API_KEY:
            console.print("[red]Error: Anthropic provider selected, but ANTHROPIC_API_KEY environment variable not set.[/red]")
            sys.exit(1)
    else:
        console.print(f"[red]Error: Unknown primary provider '{effective_provider}'. Choose 'ollama' or 'anthropic'.[/red]")
        sys.exit(1)
    
    args.primary_model = effective_primary_model # Update args with the determined model

    console.print(Panel(f"User Prompt: {args.prompt}", title="[bold blue]Request[/bold blue]", expand=False))
    console.print(f"Effective Provider: {effective_provider}, Primary Model: {args.primary_model}, Ollama URL: {args.ollama_base_url}, Max Loops: {args.compute}")

    # Initialize Anthropic client only if needed
    anthropic_client = None
    if effective_provider == 'anthropic':
        anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    global OLLAMA_BASE_URL 
    OLLAMA_BASE_URL = args.ollama_base_url # Set for run_ollama_generate and get_ollama_chat_completion

    messages = [{"role": "user", "content": args.prompt}]
    
    # Tool definition (same for both providers, but how it's passed differs)
    # The `run_ollama_generate` tool itself uses the global OLLAMA_BASE_URL
    ollama_tool_def = {
        "name": "run_ollama_generate",
        "description": "Delegates text generation to a specific local Ollama model (e.g., for specialized tasks). The primary LLM will then analyze or use this output.",
        "input_schema": {
            "type": "object",
            "properties": {
                "model_name": {
                    "type": "string",
                    "description": f"The name of the Ollama model to use for this specific task (e.g., '{os.getenv('OLLAMA_DEFAULT_DELEGATE_MODEL_NAME', 'gemma2:2b')}'). Must be available in the local Ollama instance."
                },
                "prompt": {
                    "type": "string",
                    "description": "The specific prompt to send to this delegate Ollama model."
                },
                "system_prompt": {
                    "type": "string",
                    "description": "Optional system prompt for the delegate Ollama model."
                },
                "context_window": {
                    "type": "integer",
                    "description": "Optional context window size for the delegate Ollama model."
                }
            },
            "required": ["model_name", "prompt"]
        }
    }
    tools_for_llm = [ollama_tool_def]


    final_answer_delivered = False
    loop_count = 0
    max_loops = args.compute

    for i in range(max_loops):
        loop_count = i + 1
        console.rule(f"[yellow]Agent Loop {loop_count}/{max_loops} (Provider: {effective_provider})[/yellow]")

        assistant_response_content_blocks = [] # Parsed from LLM response
        llm_error = None

        if effective_provider == 'anthropic':
            try:
                response = anthropic_client.messages.create(
                    model=args.primary_model,
                    max_tokens=2048, 
                    system=AGENT_SYSTEM_PROMPT, 
                    messages=messages,
                    tools=tools_for_llm,
                    tool_choice={"type": "auto"}
                )
                assistant_response_content_blocks = response.content
                messages.append({"role": "assistant", "content": assistant_response_content_blocks})
            except Exception as e:
                llm_error = f"Error calling Anthropic API: {str(e)}"
        
        elif effective_provider == 'ollama':
            # For Ollama, we pass the tools in its specific format (if supported)
            # The get_ollama_chat_completion function handles the formatting.
            ollama_response = get_ollama_chat_completion(
                messages=messages,
                model_name=args.primary_model,
                tools=tools_for_llm, # Pass Anthropic-style tool schema
                tool_choice="auto" # Or other strategy like "required" if needed
            )
            if ollama_response.get("error"):
                llm_error = f"Error from Ollama API: {ollama_response['error']}"
            else:
                # Adapt Ollama's response to Anthropic's MessageContentBlock structure
                # Ollama's response (ollama_response) is the "message" object:
                # {'role': 'assistant', 'content': 'text', 'tool_calls': [{'id': ..., 'type': 'function', 'function': {'name': ..., 'arguments': '...'}}]}
                
                assistant_content_for_history = []
                if ollama_response.get("content"):
                    assistant_content_for_history.append({"type": "text", "text": ollama_response["content"]})
                
                if ollama_response.get("tool_calls"):
                    for tc in ollama_response["tool_calls"]:
                        # Ensure arguments is a string, as per Anthropic's tool_use block
                        if isinstance(tc["function"].get("arguments"), dict):
                            tc["function"]["arguments"] = json.dumps(tc["function"]["arguments"])
                        
                        assistant_content_for_history.append({
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["function"]["name"],
                            "input": json.loads(tc["function"]["arguments"]) # input for anthropic is dict
                        })
                
                assistant_response_content_blocks = assistant_content_for_history
                # Append the structured response to messages history for Ollama
                messages.append({"role": "assistant", "content": assistant_content_for_history})


        if llm_error:
            console.print(f"[red]{llm_error}[/red]")
            break # Exit loop on API error

        has_text_response = False
        tool_calls_to_fulfill_from_llm = [] # Parsed tool calls for this turn

        for content_block in assistant_response_content_blocks:
            if content_block["type"] == "text":
                text_content = content_block.get("text", "")
                if text_content.strip():
                    console.print(Panel(text_content, title=f"[bold green]Agent ({effective_provider} - {args.primary_model})[/bold green]", expand=False))
                    has_text_response = True
            elif content_block["type"] == "tool_use":
                 # Structure for Anthropic: content_block is a ToolUseBlock object
                 # Structure for adapted Ollama: content_block is a dict like
                 # {"type": "tool_use", "id": ..., "name": ..., "input": {...}}
                tool_calls_to_fulfill_from_llm.append(content_block)
        
        if not tool_calls_to_fulfill_from_llm and has_text_response:
            console.print("[bold blue]--- Agent delivered final text response. ---[/bold blue]")
            final_answer_delivered = True
            break

        if tool_calls_to_fulfill_from_llm:
            tool_results_for_next_user_message = []
            for tool_call_block in tool_calls_to_fulfill_from_llm:
                # For Anthropic, tool_call_block is ToolUseBlock (has .id, .name, .input)
                # For Ollama (adapted), tool_call_block is a dict (has ["id"], ["name"], ["input"])
                tool_name = tool_call_block["name"] if isinstance(tool_call_block, dict) else tool_call_block.name
                tool_input = tool_call_block["input"] if isinstance(tool_call_block, dict) else tool_call_block.input
                tool_use_id = tool_call_block["id"] if isinstance(tool_call_block, dict) else tool_call_block.id

                console.log(f"[cyan]LLM Requested Tool Call:[/cyan] ID: {tool_use_id} Tool: {tool_name}({json.dumps(tool_input)})")
                
                tool_output_content_str = "" 

                if tool_name == "run_ollama_generate":
                    # Tool input is already a dict here for both providers
                    model_name_arg = tool_input.get("model_name")
                    prompt_arg = tool_input.get("prompt")

                    if not model_name_arg or not prompt_arg:
                        tool_output_content_str = f"Error: 'model_name' and 'prompt' are required for {tool_name}."
                        console.print(f"[red]{tool_output_content_str}[/red]")
                    else:
                        try:
                            # run_ollama_generate expects kwargs, tool_input is a dict
                            tool_output_content_str = run_ollama_generate(
                                model_name=model_name_arg,
                                prompt=prompt_arg,
                                system_prompt=tool_input.get("system_prompt"),
                                context_window=tool_input.get("context_window")
                            )
                            console.print(Panel(tool_output_content_str, title=f"[bold purple]Tool Output (Ollama: {model_name_arg})[/bold purple]", expand=False))
                        except Exception as e: 
                            tool_output_content_str = f"Error executing tool {tool_name} internally: {str(e)}"
                            console.print(f"[red]{tool_output_content_str}[/red]")
                else:
                    tool_output_content_str = f"Error: Unknown tool '{tool_name}' called by LLM."
                    console.log(f"[red]{tool_output_content_str}[/red]")
                
                # Construct tool_result content block for the next "user" message
                tool_results_for_next_user_message.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": tool_output_content_str 
                })
            
            if tool_results_for_next_user_message:
                 messages.append({"role": "user", "content": tool_results_for_next_user_message})
                 
        elif not has_text_response: 
            console.print("[yellow]Warning: LLM did not provide text or call a tool in this turn. Ending loop.[/yellow]")
            break
    
    if final_answer_delivered:
        console.print("[bold green]Agent run completed successfully.[/bold green]")
    elif loop_count == max_loops and not final_answer_delivered:
        console.print(f"[yellow]Warning: Reached maximum agent loops ({max_loops}) without a definitive final text response.[/yellow]")
    elif not final_answer_delivered:
        console.print("[red]Agent run concluded without delivering a final answer due to errors or unexpected LLM behavior.[/red]")

if __name__ == "__main__":
    main()
