#!/usr/bin/env python3
import argparse
import datetime
import json
import sys # To capture raw user input
import requests # For Ollama integration

# TMS Functions
LOG_FILE = "tms_log.json"

# Ollama Configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_ERROR_CONNECT = "Error: Could not connect to Ollama. Ensure Ollama is running."
OLLAMA_ERROR_REQUEST_FAILED = "Error: Ollama request failed with status code {status_code}."
OLLAMA_ERROR_RESPONSE_FORMAT = "Error: Unexpected response format from Ollama."
OLLAMA_MODEL = "qwen3"

# Added Capabilities Configuration
ADDED_CAPABILITIES_FILE = "added_capabilities.json"

def load_added_capabilities():
    """Loads the list of added capabilities from JSON file."""
    try:
        with open(ADDED_CAPABILITIES_FILE, 'r') as f:
            content = f.read()
            if content:
                capabilities = json.loads(content)
                if isinstance(capabilities, list):
                    return capabilities
                else: # If not a list, return empty and let it be overwritten
                    return [] 
            return [] # If content is empty
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_added_capabilities(capabilities_list):
    """Saves the list of added capabilities to JSON file."""
    with open(ADDED_CAPABILITIES_FILE, 'w') as f:
        json.dump(capabilities_list, f, indent=2)

def handle_add_capability(capability_name, description):
    """
    Handles the 'add' command: gets a plan from qwen3, prints it, 
    and logs it. Updates added_capabilities.json on success.
    Returns the agent_response string for TMS.
    """
    prompt = (
        f"You are an expert Python software architect assisting the 'omni' agent. "
        f"The user wants to add a new capability named '{capability_name}' with the following description: '{description}'.\n\n"
        f"Your task is to generate a high-level plan for implementing this capability within the 'omni' agent's existing Python framework (`omni.py`). "
        f"The plan should be conceptual and outline necessary new Python functions or classes, how the capability might be invoked via CLI "
        f"(e.g., `omni {capability_name} [sub_commands] [options]`), potential modifications to `omni.py` (like adding subparsers), "
        f"any external Python libraries that might be needed, and basic error handling considerations.\n\n"
        f"Output the plan as a clear, structured text. For example:\n"
        f"1. Capability Purpose: [Brief restatement]\n"
        f"2. Proposed Functions/Classes: [List with descriptions]\n"
        f"3. CLI Integration: [Example command structure]\n"
        f"4. Modifications to omni.py: [Summary of changes]\n"
        f"5. Required Libraries: [List of libraries]\n"
        f"6. Error Handling: [Key considerations]\n"
    )
    
    print(f"Attempting to generate plan for new capability: '{capability_name}'...")
    plan_text = get_qwen3_response(prompt)

    if plan_text.startswith("Error:"):
        error_message = plan_text
        print(f"Failed to generate plan: {error_message}")
        return f"Failed to get plan for capability '{capability_name}'. Error: {error_message}"
    else:
        print("\n--- Generated Capability Plan ---")
        print(plan_text)
        print("--- End of Plan ---\n")
        
        capabilities = load_added_capabilities()
        # Check if capability already exists by name to avoid duplicates
        if not any(cap['name'] == capability_name for cap in capabilities):
            capabilities.append({"name": capability_name, "description": description})
            save_added_capabilities(capabilities)
            print(f"Capability '{capability_name}' added to planned capabilities list.")
        else:
            print(f"Capability '{capability_name}' already exists in planned capabilities list. Plan displayed but list not updated.")

        return f"Placeholder for add capability '{capability_name}': qwen3 generated the following plan: {plan_text}"

def get_qwen3_response(prompt_text):
    """
    Gets a response from the qwen3 model via Ollama.
    Returns the generated text or an error message string.
    """
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt_text,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=20) # Added timeout
        if response.status_code == 200:
            try:
                return response.json().get('response', OLLAMA_ERROR_RESPONSE_FORMAT)
            except json.JSONDecodeError:
                return OLLAMA_ERROR_RESPONSE_FORMAT
        else:
            return OLLAMA_ERROR_REQUEST_FAILED.format(status_code=response.status_code)
    except requests.exceptions.ConnectionError:
        return OLLAMA_ERROR_CONNECT
    except requests.exceptions.Timeout:
        return "Error: Ollama request timed out."
    except requests.exceptions.RequestException as e:
        return f"Error: An unexpected error occurred with Ollama request: {e}"

def create_transaction_data(user_input_str, agent_response_str):
    """Creates a transaction dictionary."""
    return {
        "timestamp": datetime.datetime.now().isoformat(),
        "user_input": user_input_str,
        "agent_response": agent_response_str,
    }

def log_transaction(transaction_data_dict):
    """Appends the given transaction to tms_log.json."""
    transactions = []
    try:
        with open(LOG_FILE, 'r') as f:
            content = f.read()
            if content: # Ensure content is not empty before trying to load json
                transactions = json.loads(content)
                if not isinstance(transactions, list): # Ensure it's a list
                    transactions = [] # Reset if not a list
    except (FileNotFoundError, json.JSONDecodeError):
        # If file not found or content is not valid JSON, start with an empty list
        transactions = []
    
    transactions.append(transaction_data_dict)
    
    with open(LOG_FILE, 'w') as f:
        json.dump(transactions, f, indent=2)


def display_help():
    """
    Displays the help message for the omni agent by calling get_qwen3_response and printing its output.
    """
    added_capabilities = load_added_capabilities()
    
    base_prompt = (
        "You are the omni agent. Describe yourself and your purpose. "
        "Mention that you are a self-improving agent capable of learning new capabilities. "
        "Also, explain that typing 'omni help' displays this information and lists available commands (currently 'help' and 'add'). "
        "Keep the description concise and informative."
    )
    
    if added_capabilities:
        capabilities_list_str = "\nPlanned (but not yet fully implemented) capabilities:\n"
        for cap in added_capabilities:
            capabilities_list_str += f"- {cap['name']}: {cap['description']}\n"
        capabilities_list_str += "\nBriefly mention that these are placeholders awaiting full implementation and testing."
        prompt = f"{base_prompt}\n\n{capabilities_list_str}"
    else:
        prompt = f"{base_prompt}\n\nYou can add new capabilities using the 'omni add <name> \"<description>\"' command."

    # display_help directly prints the message.
    # The success/failure for logging will be determined by a separate call in main().
    print(get_qwen3_response(prompt))


def main():
    """Main function for the omni agent."""
    user_input = " ".join(sys.argv) # Capture the full user input
    agent_response = "" # Initialize agent_response

    parser = argparse.ArgumentParser(
        description="Omni - A dynamic agent.",
        add_help=False # Disable default help to handle it customly
    )
    # Using subparsers to handle commands like "help"
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Help command
    help_parser = subparsers.add_parser('help', help='Displays the help message and lists planned capabilities.')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='(Placeholder) Adds a new capability by generating a plan.')
    add_parser.add_argument('capability_name', type=str, help='The name for the new capability (e.g., minio_browser).')
    add_parser.add_argument('description', type=str, help='A short description of what the capability should do.')

    # Capture all other inputs as a potential command
    # This allows us to check if it's 'help' or something else.
    # Using parse_known_args to allow for future expansion with more commands/args
    # We need to handle the case where sys.argv might be just ['omni.py']
    # or ['omni.py', 'help'], etc.
    # parse_known_args() will parse arguments it recognizes and leave the rest in 'unknown'.
    # If only 'omni.py' is passed, args.command will be None and unknown will be empty.
    # If 'omni.py help' is passed, args.command will be 'help' and unknown will be empty.
    # If 'omni.py foobar' is passed, args.command will be None (if foobar is not a defined command)
    # and 'foobar' will be in unknown.

    parsed_args = sys.argv[1:] # Exclude the script name itself for parsing

    args, unknown = parser.parse_known_args(parsed_args)


    if args.command == 'help' or (args.command is None and not unknown):
        # For logging the help action accurately, construct the same prompt display_help will use.
        added_capabilities = load_added_capabilities()
        base_help_prompt_for_log = (
            "You are the omni agent. Describe yourself and your purpose. "
            "Mention that you are a self-improving agent capable of learning new capabilities. "
            "Also, explain that typing 'omni help' displays this information and lists available commands (currently 'help' and 'add'). "
            "Keep the description concise and informative."
        )
        if added_capabilities:
            capabilities_list_str_for_log = "\nPlanned (but not yet fully implemented) capabilities:\n"
            for cap in added_capabilities:
                capabilities_list_str_for_log += f"- {cap['name']}: {cap['description']}\n"
            capabilities_list_str_for_log += "\nBriefly mention that these are placeholders awaiting full implementation and testing."
            help_prompt_for_log = f"{base_help_prompt_for_log}\n\n{capabilities_list_str_for_log}"
        else:
            help_prompt_for_log = f"{base_help_prompt_for_log}\n\nYou can add new capabilities using the 'omni add <name> \"<description>\"' command."

        ollama_outcome_for_log = get_qwen3_response(help_prompt_for_log)

        if ollama_outcome_for_log.startswith("Error:"):
            agent_response = f"Attempted to display help via qwen3 (with added capabilities list), but encountered an error: {ollama_outcome_for_log}"
        else:
            agent_response = "Displayed help message generated by qwen3 (including added capabilities list)."
        
        display_help() # display_help makes its own call to get_qwen3_response and prints
    
    elif args.command == 'add':
        if args.capability_name and args.description:
            agent_response = handle_add_capability(args.capability_name, args.description)
        else:
            # This case should be caught by argparse if arguments are mandatory
            print("Error: 'add' command requires capability_name and description.")
            agent_response = "Error: Missing arguments for 'add' command."

    elif unknown: # Catches commands not explicitly defined by add_parser
        # The first element in 'unknown' would be the unrecognized command
        # This assumes the unknown part is the command itself.
        # If there were options like `omni --option unknown_command`, unknown could be more complex.
        # For now, it's simple: `omni unknown_command` -> unknown = ['unknown_command']
        unknown_command_str = unknown[0] if unknown else "unknown"
        # Ensure agent_response is set if it falls through previous conditions
        # (e.g. if args.command was None but unknown was also empty - though covered by the first branch)
        current_agent_response = f"Reported unknown command: {unknown_command_str}"
        print(f"Unknown command: '{unknown_command_str}'. Use 'omni help' for available commands.")
        agent_response = current_agent_response
    else: # This case should ideally not be reached if all inputs are handled
        # For example, if a subparser was defined but no action taken
        # Or if args.command is set but it's not 'help' (future commands)
        # For now, treat as unknown or provide a generic message
        # This might happen if a known command is called that doesn't have specific handling here
        # (which isn't the case currently as only 'help' is defined).
        # Let's assume any other case is an "unhandled known command" for future-proofing
        # or simply default to help/error.
        # For this iteration, if it's not 'help' and not 'unknown', it's likely an issue
        # or a path that shouldn't be hit with current parser setup.
        # Let's make it explicit what happens.
        # If args.command is not None (so it's a recognized command by a subparser)
        # but it's not 'help', and 'unknown' is empty.
        # This means a future command was added to subparsers but not handled in the if/elif chain.
        # For now, this path means something is amiss or it's an undefined known command.
        # Let's default to an error message and log it.
        unhandled_command_str = args.command if args.command else "undefined"
        current_agent_response = f"Error: Command '{unhandled_command_str}' is recognized but not handled."
        print(current_agent_response) # Print the error to the user
        agent_response = current_agent_response


    # Log the transaction
    # Ensure agent_response has been set in all branches.
    # If logic is complex, initialize agent_response to a default error/unknown state first.
    if not agent_response: # Should not happen if all branches set it.
        agent_response = "Error: Agent response not set for this interaction."
        # This indicates a logic flaw in the command handling above.

    transaction = create_transaction_data(user_input, agent_response)
    log_transaction(transaction)

if __name__ == "__main__":
    main()
