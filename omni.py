#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "requests>=2.25.0"  # For Ollama communication
# ]
# ///
import argparse
import datetime
import json
import sys # To capture raw user input
import requests # For Ollama integration

# TMS Configuration
TRANSACTIONS_LOG = [] # In-memory log

# Ollama Configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_ERROR_CONNECT = "Error: Could not connect to Ollama. Ensure Ollama is running."
OLLAMA_ERROR_REQUEST_FAILED = "Error: Ollama request failed with status code {status_code}."
OLLAMA_ERROR_RESPONSE_FORMAT = "Error: Unexpected response format from Ollama."
OLLAMA_MODEL = "qwen3"

# Added Capabilities Configuration
ADDED_CAPABILITIES = [] # In-memory list of added capabilities

DESIGN_WORKFLOW_DOCS = """\
# Omni Agent: Add Capability Workflow Design

This document outlines the conceptual workflow for the `omni add <capability_name> <description>` command, which enables the Omni agent to dynamically acquire new capabilities.

## 1. Command Invocation

*   **User Invocation:** The user invokes the command via the CLI, providing a name for the new capability and a textual description of its functionality.
    *   Example: `omni add minio_browser "A tool to browse MinIO server contents"`
    *   Alternative: `omni add new_feature "A short description of what new_feature does"`

*   **Initial Parsing and Validation:**
    *   `omni.py`'s main argument parser will be extended to recognize the `add` command.
    *   A subparser for `add` will expect two arguments: `<capability_name>` (string, no spaces, snake_case preferred) and `<description>` (a string, likely quoted).
    *   **Validation:**
        *   Check if both arguments are provided.
        *   `<capability_name>` should be a valid identifier (e.g., alphanumeric, underscores).
        *   Check for potential conflicts with existing commands or capability names.
        *   The description should be non-empty.
    *   An entry is made in the TMS log for the `add` command invocation.

## 2. Understanding the Capability (Phase 1 - LLM-assisted Planning)

This phase is for **immediate conceptualization**.

*   **Using User Input:** The `<capability_name>` and `<description>` are the primary inputs for this phase.

*   **Prompting `qwen3` (or a similar LLM) for a Plan:**
    *   **Prompt Design:** A detailed prompt will be constructed to guide the LLM in generating a high-level plan.
        ```
        You are an expert Python software architect assisting the 'omni' agent in integrating a new capability.
        The user wants to add a capability named "<capability_name>" with the following description: "<description>".

        Your task is to generate a detailed plan for implementing this capability within the 'omni' agent's existing Python framework (`omni.py`). The plan should be structured (e.g., JSON or YAML) and include the following sections:

        1.  **CapabilityPurpose:** Briefly re-state the core purpose of the new capability based on the user's description.
        2.  **ProposedFunctions/Classes:**
            *   Suggest necessary new Python functions or classes.
            *   For each, provide a name, a brief description of its role, expected input parameters (with types), and expected return values (with types).
        3.  **CLIIntegration:**
            *   Suggest how the new capability should be invoked via the `omni` CLI (e.g., `omni <capability_name> [sub_commands] [options]`).
            *   Define any necessary sub-commands or command-line arguments.
        4.  **ModificationsToOmniPy:**
            *   Identify parts of `omni.py` that need modification (e.g., the main argument parser, command dispatch logic).
            *   Describe the nature of these modifications.
        5.  **RequiredLibraries:** List any external Python libraries or modules required for this capability (e.g., `requests`, `boto3`).
        6.  **BasicErrorHandling:** Outline key error conditions to consider and how they might be handled (e.g., invalid input, network errors, missing dependencies).
        7.  **StorageConsiderations (if any):** If the capability requires persistent storage (e.g., configuration, data), suggest how this might be managed.
        8.  **SecurityConsiderations (if any):** Highlight any potential security implications (e.g., handling API keys, external process execution).
        9.  **TestingSuggestions:** Briefly suggest what aspects should be tested.

        Output the plan in JSON format.
        Example for a simple "greet" capability:
        {
          "CapabilityPurpose": "To allow omni to greet a user.",
          "ProposedFunctions/Classes": [
            {
              "name": "greet_user",
              "role": "Constructs a greeting message.",
              "parameters": [{"name": "user_name", "type": "str"}],
              "returns": {"type": "str"}
            }
          ],
          "CLIIntegration": {
            "command": "omni greet <name>",
            "arguments": [{"name": "name", "description": "The name of the user to greet."}]
          },
          "ModificationsToOmniPy": [
            "Add 'greet' subparser to main ArgumentParser.",
            "Update command dispatcher to call a new 'handle_greet_command' function."
          ],
          "RequiredLibraries": [],
          "BasicErrorHandling": ["Handle missing name argument."],
          "StorageConsiderations": [],
          "SecurityConsiderations": [],
          "TestingSuggestions": ["Test with name, without name."]
        }
        ```
    *   The actual `<capability_name>` and `<description>` from the user are injected into this prompt.

*   **Storing the Plan:**
    *   The LLM's response (ideally structured JSON as requested) will be captured.
    *   This plan will be saved to a file, associated with the `<capability_name>`.
        *   Example: `capabilities/plans/<capability_name>_plan.json`
    *   The TMS log entry for the `add` command will be updated to reference this stored plan.

## 3. Code Generation (Phase 2 - LLM-assisted Coding - Future)

This phase is designated as **Future Work**.

*   **Using the Plan:** `omni` would read the stored plan (e.g., `<capability_name>_plan.json`).
*   **Prompting for Code:** For each function/class outlined in the plan, `omni` would generate a new, more specific prompt for `qwen3`.
    *   Example prompt snippet:
        ```
        Based on the following specification from a development plan:
        Function Name: <function_name>
        Role: <role_description>
        Parameters: <parameters_from_plan>
        Returns: <return_type_from_plan>

        Generate the Python code for this function. Ensure it includes basic error handling as previously suggested (if applicable) and comments explaining the logic. Only output the raw Python code for the function.
        ```
*   **Code Validation (Conceptual):**
    *   Basic static analysis (linting, syntax checking).
    *   Potentially use the LLM again for a review step: "Review this generated code for correctness, security, and adherence to the plan."
*   **Sandboxing (Conceptual):** For security, especially if the capability involves external interactions, executing the generated code in a restricted environment during testing would be ideal, though complex to implement.
*   **Testing (Conceptual):**
    *   Use the "TestingSuggestions" from the plan to prompt the LLM to generate basic unit tests.
    *   Run these tests against the generated code.

## 4. Code Integration and Storage (Future)

This phase is designated as **Future Work**.

*   **Storage:**
    *   Generated Python code for the capability could be stored as a new file: `capabilities/modules/<capability_name>_module.py`.
    *   If the capability is very simple, it might be (less ideally) appended to a generic "custom_capabilities.py" file or even (least ideally) `omni.py`. A modular approach with separate files is preferred.
*   **Modification of `omni.py`:**
    *   `omni.py` would need to be updated to dynamically load and integrate the new module.
    *   This involves:
        *   Updating the main argument parser (`argparse`) to include the new command structure defined in the plan's `CLIIntegration` section.
        *   Modifying the command dispatch logic in `main()` to call the appropriate function from the newly added module.
        *   This modification itself could potentially be assisted by the LLM, by providing the relevant sections of `omni.py` and asking the LLM to generate the diff/patch for adding the new command hooks.

## 5. Self-Documentation (Future)

This phase is designated as **Future Work**.

*   **Generating Documentation:**
    *   `omni` could use `qwen3` to generate user-facing documentation for the new capability.
    *   Prompt:
        ```
        You are 'omni', a self-improving agent. You have just successfully integrated a new capability called '<capability_name>'.
        The initial description was: "<description>".
        The implemented code is:
        ```python
        <generated_python_code_for_the_module>
        ```
        The CLI usage is: <cli_usage_from_plan>.

        Generate a concise help document for this new capability. Explain its purpose, how to use it (CLI commands, options), and provide a simple example.
        ```
*   **Storage:**
    *   Documentation could be stored in a `docs/capabilities/<capability_name>.md` file.
    *   A reference to this doc file could be added to the TMS log.
*   **Updating Main Help:**
    *   The main `omni help` message (currently generated by `qwen3` by describing `omni` itself) would need to be updated.
    *   This could be done by modifying the prompt to `qwen3` for the main help message to include a list of available capabilities, perhaps by reading from a central registry or by scanning the `capabilities/modules` directory.
    *   Alternatively, `omni help` could list static commands and then have a separate section like "Learned Capabilities:" followed by dynamically discovered ones.

## 6. Versioning (Future)

This phase is designated as **Future Work**.

*   **Creating a New Version:**
    *   **Simple Versioning:** Increment a version number (e.g., `omni_version.txt`) after a capability is successfully added and integrated.
    *   **Git-based Snapshotting:** If `omni` operates within a Git repository, successfully adding a capability could trigger an automated `git commit` with a standardized message (e.g., "Feat: Added capability '<capability_name>'") and then a `git tag vX.Y.Z`. This is more robust.
*   **TMS and Versioning:** TMS logs should ideally include the `omni` agent version active during that transaction. This helps in debugging and tracking when capabilities were added or modified.

## 7. Error Handling and Rollback (Conceptual)

This section is for **immediate conceptualization** regarding error handling during the `add` process, though full rollback is **Future Work**.

*   **Planning Phase Failure:**
    *   If `qwen3` fails to generate a plan or the plan is malformed: Log error in TMS, report to user. No code changes made.
*   **Code Generation Failure (Future):**
    *   If `qwen3` fails to generate code for a function: Log, potentially try again, or report failure to user.
*   **Integration Failure (Future):**
    *   If generated code fails tests or breaks `omni.py` during modification:
        *   **Rollback (Ideal):** If using Git, `git reset --hard HEAD` could revert changes. For file-based changes, backup original files before modification and restore them.
        *   **Manual Intervention:** Log detailed errors. Alert the user that integration failed and manual review might be needed. The capability would be marked as "disabled" or "incomplete."
*   **Dependency Issues:** If required libraries cannot be installed, the capability cannot be enabled. Report to user.

The TMS is crucial for tracking the success or failure of each step in the `add` capability workflow.

## 8. MinIO Example Application: `omni add minio_browser "A tool to browse MinIO server contents"`

*   **Command Invocation:**
    *   User types: `omni add minio_browser "A tool to browse MinIO server contents"`
    *   `omni.py` validates command, logs invocation to TMS.

*   **Understanding the Capability (Phase 1 - LLM-assisted Planning):**
    *   `omni` sends a prompt to `qwen3` with `capability_name = "minio_browser"` and the description.
    *   **`qwen3` Plan (Conceptual):**
        *   `CapabilityPurpose`: "To provide CLI-based browsing of MinIO server buckets and objects."
        *   `ProposedFunctions/Classes`:
            *   `minio_connect(host, access_key, secret_key)`: returns MinIO client.
            *   `list_buckets(client)`: returns list of bucket names.
            *   `list_objects(client, bucket_name, prefix)`: returns list of objects in a bucket.
            *   `get_object_details(client, bucket_name, object_name)`: returns object metadata.
        *   `CLIIntegration`:
            *   `omni minio_browser list-buckets --host <h> --access-key <ak> --secret-key <sk>`
            *   `omni minio_browser list-objects <bucket_name> --prefix <p> --host <h> ...`
        *   `ModificationsToOmniPy`: Add `minio_browser` subparser, route to `handle_minio_browser_command`.
        *   `RequiredLibraries`: `minio` (official MinIO Python SDK).
        *   `BasicErrorHandling`: Invalid credentials, bucket not found, network errors.
        *   `SecurityConsiderations`: Secure handling/prompting for MinIO credentials. Avoid storing them plaintext if possible (maybe use environment variables or prompt each time).
        *   `TestingSuggestions`: Test bucket listing, object listing with/without prefix, connection errors.
    *   **Storing the Plan:** The JSON output from `qwen3` is saved to `capabilities/plans/minio_browser_plan.json`. TMS updated.

*   **Code Generation (Phase 2 - Future):**
    *   `omni` would prompt `qwen3` for each function (e.g., "Generate Python code for `list_buckets(client)` using the `minio` library...").

*   **Code Integration and Storage (Future):**
    *   Generated code saved to `capabilities/modules/minio_browser_module.py`.
    *   `omni.py`'s argument parser and command dispatcher updated to handle `omni minio_browser ...` commands, importing and calling functions from `minio_browser_module.py`.

*   **Self-Documentation (Future):**
    *   `qwen3` generates `docs/capabilities/minio_browser.md` explaining how to use the `omni minio_browser` commands.
    *   `omni help` might list `minio_browser` as an available capability.

*   **Versioning (Future):**
    *   After successful integration and testing, `omni` might commit changes and tag a new version (e.g., `v0.2.0`).

*   **Error Handling:** If the `minio` library installation fails, or `qwen3`'s plan is unusable, the process halts, logs the error, and informs the user. If code integration fails tests, changes are ideally reverted.

## 9. Adding MCP Tool Integration (Conceptual)

This section outlines a conceptual approach for extending Omni to interact with existing tools or agents that expose a Multi-Agent Communication Protocol (MCP) interface. This allows Omni to delegate tasks or retrieve information from specialized external services. This is distinct from the `omni add` command which is for more general Python-based capabilities.

**Command Structure Proposal:**

`omni add_mcp_tool <tool_name> <mcp_config_json> "<description>"`

*   `<tool_name>`: A unique, local name for Omni to refer to this MCP tool (e.g., `external_knowledge_base_v1`, `image_analysis_service`). This name will be used for subsequent commands to interact with the tool.
*   `<mcp_config_json>`: A JSON string containing the necessary details for Omni to connect to and interact with the MCP tool. This could include:
    *   `endpoint_url`: The URL of the MCP tool.
    *   `protocol_version`: The specific MCP version the tool uses (e.g., "1.0", "2.0-draft").
    *   `authentication_method`: (e.g., "bearer_token", "api_key_header").
    *   `auth_details`: The actual token or key.
    *   `message_schemas`: (Optional) JSON schemas for expected request and response message formats.
    *   Example: `'{"url": "http://mcp.example.com/query", "protocol_version": "1.1", "auth_method": "bearer", "token": "abcdef12345"}'`
*   `<description>`: A natural language description provided by the user, explaining what the tool does, what kind of requests it can handle, and how Omni should utilize it. This description is crucial for the LLM to generate a relevant interaction plan.

**LLM-Assisted Planning & Code Structure Generation:**

When the `add_mcp_tool` command is invoked, Omni will use its LLM (qwen3) to perform the following:

1.  **Parse Inputs:** Extract and understand the `<tool_name>`, `<mcp_config_json>`, and `<description>`.
2.  **Generate Interaction Plan:** Based on the description and MCP config, the LLM will be prompted to create a high-level plan for interaction. This plan should cover:
    *   Connection strategy (e.g., persistent connection if applicable, or per-request).
    *   Typical message exchange sequences for common tasks the tool might perform (based on the user's description).
    *   Key data elements to extract from responses.
    *   Basic error handling strategies for MCP communication (e.g., connection errors, timeout, invalid responses).
3.  **Generate Placeholder Python Functions/Classes:** The LLM will be asked to generate Python function skeletons or class structures that would be integrated into Omni. These act as placeholders for the actual MCP communication logic.
    *   Example:
        ```python
        # Placeholder for MCP tool: <tool_name>
        # Description: <description from user>
        # MCP Config: <mcp_config_json from user>

        def call_mcp_<tool_name>(params: dict) -> dict:
            """
            Sends a request to the <tool_name> MCP tool and returns its response.
            (This is a placeholder - actual MCP communication logic to be implemented here based on the interaction plan)
            
            MCP Endpoint: <parsed_url_from_config>
            Expected params based on description: ...
            """
            # 1. Construct MCP message from params based on interaction plan
            # 2. Establish connection (if needed) using details from mcp_config_json
            # 3. Send message
            # 4. Receive response
            # 5. Parse response and extract relevant data
            # 6. Handle MCP-specific errors
            print(f"Simulating call to MCP tool '<tool_name>' with params: {params}")
            return {"status": "success_placeholder", "data": "simulated data from <tool_name>"}
        ```
4.  **Define CLI Usage for the Tool:** The LLM will propose a command structure for users to invoke this newly defined MCP tool capability through Omni's CLI.
    *   Example: `omni use_tool <tool_name> --param1 <value1> --json_payload <json_string>`
    *   Or: `omni <tool_name> <sub_command_for_tool> [options]` (if the tool has distinct actions)

**Storage and Scope:**

*   The `<mcp_config_json>` and the LLM-generated interaction plan and placeholder code structure would be associated with the `<tool_name>`.
*   Currently, similar to other "added capabilities", this information would be stored in-memory for the session.
*   **Important Scope Note:** This `add_mcp_tool` workflow is designed for Omni to *act as a client* to existing, external MCP-enabled tools or agents. It is not about transforming Omni itself into an MCP server or enabling it to host MCP endpoints, which would be a significantly more complex capability.

**Future Work:**
The actual implementation of sending/receiving MCP messages, handling asynchronous communication if needed, and fully integrating the generated placeholder code into a live system are designated as future work. This conceptual phase focuses on the initial planning, user interface, and code structure generation with LLM assistance.
"""

def handle_add_capability(capability_name, description):
    """
    Handles the 'add' command: gets a plan from qwen3, prints it, 
    and logs it. Updates the in-memory ADDED_CAPABILITIES list on success.
    Returns the agent_response string for TMS.
    """
    global ADDED_CAPABILITIES
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
        
        # Check if capability already exists by name to avoid duplicates
        if not any(cap['name'] == capability_name for cap in ADDED_CAPABILITIES):
            ADDED_CAPABILITIES.append({
                "name": capability_name, 
                "type": "general_capability", # Distinguish from MCP tools
                "description": description,
                "plan": plan_text # For general capabilities, the plan is the main artifact
            })
            print(f"Capability '{capability_name}' added to in-memory planned capabilities list for this session.")
        else:
            print(f"Capability '{capability_name}' already exists in in-memory planned capabilities list. Plan displayed but list not updated.")

        return f"Placeholder for add capability '{capability_name}': qwen3 generated the following plan: {plan_text}"

def handle_add_mcp_tool(tool_name, mcp_config_json, description):
    """
    Handles the 'add_mcp_tool' command: parses JSON config, gets a plan from qwen3, 
    prints it, and logs it. Updates ADDED_CAPABILITIES on success.
    Returns the agent_response string for TMS.
    """
    global ADDED_CAPABILITIES
    
    try:
        mcp_config_details = json.loads(mcp_config_json)
    except json.JSONDecodeError as e:
        error_msg = f"Failed to add MCP tool '{tool_name}': Invalid JSON in configuration. Error: {e}"
        print(error_msg)
        return error_msg

    # Prompt for qwen3
    prompt = (
        f"You are an expert Python software architect assisting the 'omni' agent. "
        f"The user wants to integrate an existing external MCP (Multi-Agent Communication Protocol) tool named '{tool_name}'.\n"
        f"The tool's MCP configuration is: {json.dumps(mcp_config_details, indent=2)}\n"
        f"The user's description of this tool and its purpose is: '{description}'.\n\n"
        f"Your task is to generate a high-level plan and Python placeholder function(s) for integrating this MCP tool with the 'omni' agent. "
        f"The plan should outline:\n"
        f"1. Connection Strategy: How omni should connect to the MCP tool.\n"
        f"2. Data Exchange: Typical message patterns or data to send/receive, based on the description.\n"
        f"3. Error Handling: Key MCP-related errors to consider (e.g., connection, timeout, invalid response).\n"
        f"4. CLI Usage Suggestion: How a user might invoke this tool via omni's CLI (e.g., `omni call {tool_name} <payload_or_args>`).\n"
        f"5. Placeholder Python Function(s): Define a skeleton function, like `call_mcp_{tool_name}(payload)` or similar, "
        f"that would encapsulate the logic for interacting with this MCP tool. Include comments indicating where MCP communication logic would go.\n\n"
        f"Output the plan and placeholder code as clear, structured text."
    )

    print(f"Attempting to generate integration plan for MCP tool: '{tool_name}'...")
    plan_text = get_qwen3_response(prompt)

    if plan_text.startswith("Error:"):
        error_message = plan_text
        print(f"Failed to generate plan for MCP tool: {error_message}")
        return f"Failed to get plan for MCP tool '{tool_name}'. Error: {error_message}"
    else:
        print("\n--- Generated MCP Tool Integration Plan & Placeholders ---")
        print(plan_text)
        print("--- End of MCP Tool Plan ---\n")

        if not any(cap['name'] == tool_name for cap in ADDED_CAPABILITIES):
            ADDED_CAPABILITIES.append({
                "name": tool_name,
                "type": "mcp_tool",
                "config": mcp_config_details,
                "description": description,
                "plan": plan_text
            })
            print(f"MCP tool '{tool_name}' added to in-memory planned capabilities list for this session.")
        else:
            print(f"A capability or MCP tool named '{tool_name}' already exists. Plan displayed but list not updated.")
        
        return f"Placeholder for MCP tool '{tool_name}': qwen3 generated the following plan/code: {plan_text}"

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
    """Appends the given transaction to the in-memory TRANSACTIONS_LOG."""
    global TRANSACTIONS_LOG
    TRANSACTIONS_LOG.append(transaction_data_dict)

def handle_show_transactions():
    """Handles the 'show_transactions' command."""
    global TRANSACTIONS_LOG
    if not TRANSACTIONS_LOG:
        print("No transactions recorded in this session.")
        return "No transactions to display for this session."
    
    print("\n--- Transaction Log (In-Memory for this Session) ---")
    for transaction in TRANSACTIONS_LOG:
        print(json.dumps(transaction, indent=2))
    print("--- End of Transaction Log ---\n")
    return "Displayed in-memory transaction log."


def display_help():
    """
    Displays the help message for the omni agent by calling get_qwen3_response and printing its output.
    """
    global ADDED_CAPABILITIES
    
    base_prompt = (
        "You are the omni agent. Describe yourself and your purpose. "
        "Mention that you are a self-improving agent capable of learning new capabilities. "
        "Explain that typing 'omni help' displays this information and lists available commands. "
        "The current commands are 'help', 'add', 'add_mcp_tool', 'show_transactions', and 'show_design_workflow'.\n\n"
        "When you list the 'add' command, explain it's for adding general Python-based capabilities, where Omni (with your help as qwen3) generates a conceptual plan and placeholder code for new features.\n\n"
        "When you list the `add_mcp_tool` command, clearly explain that this command is used to define a conceptual integration with an external MCP-compliant tool or agent. "
        "Mention that Omni, with your help (qwen3), will generate a high-level plan, placeholder Python code structures for this interaction, and suggest how the user might eventually call this tool via a new `omni` command (e.g., `omni call <tool_name> ...` or `omni use_tool <tool_name> ...`). "
        "Emphasize that the full implementation of actually calling these external MCP tools is future work, and `add_mcp_tool` sets up the design and placeholder structure.\n\n"
        "Also, please state that transaction logs (viewable with `show_transactions`) are currently stored in-memory for this session and will be cleared when the agent exits. "
        "Furthermore, state that any newly added capabilities (via the 'add' or 'add_mcp_tool' commands) are registered for the current session only and will also be cleared when the agent exits. "
        "Keep the overall description concise and informative."
    )
    
    if ADDED_CAPABILITIES:
        capabilities_intro = (
            "\n\nAdditionally, the following capabilities have been planned for this session (these are placeholders awaiting full implementation and are session-specific):\n"
        )
        capabilities_list_str = capabilities_intro
        for cap in ADDED_CAPABILITIES:
            cap_type = cap.get('type', 'general_capability')
            if cap_type == "mcp_tool":
                type_explanation = "(Type: MCP Tool Integration Definition - a plan for interacting with an external MCP-compliant tool)"
            else: # general_capability
                type_explanation = "(Type: General Capability Plan - a plan for a new Python-based feature)"
            capabilities_list_str += f"- {cap['name']} {type_explanation}: {cap['description']}\n"
        
        prompt = f"{base_prompt}\n{capabilities_list_str}"
    else:
        prompt = f"{base_prompt}\n\nYou can add new capabilities for this session using the 'omni add <name> \"<description>\"' command for general Python features, or 'omni add_mcp_tool <name> <json_config> \"<description>\"' to define integrations with external MCP tools."

    # display_help directly prints the message.
    # The success/failure for logging will be determined by a separate call in main().
    print(get_qwen3_response(prompt))


def main():
    """Main function for the omni agent."""
    global ADDED_CAPABILITIES # Ensure main can access the global list if needed for logging help

    user_input = " ".join(sys.argv) # Capture the full user input
    agent_response = "" # Initialize agent_response

    parser = argparse.ArgumentParser(
        description="Omni - A dynamic agent.",
        add_help=False # Disable default help to handle it customly
    )
    # Using subparsers to handle commands like "help"
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Help command
    help_parser = subparsers.add_parser('help', help='Displays the help message and lists planned capabilities for the session.')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='(Placeholder) Adds a new general Python capability for the current session by generating a plan.')
    add_parser.add_argument('capability_name', type=str, help='The name for the new general capability (e.g., minio_browser).')
    add_parser.add_argument('description', type=str, help='A short description of what the general capability should do.')

    # Add MCP Tool command
    add_mcp_tool_parser = subparsers.add_parser('add_mcp_tool', help='(Placeholder) Adds an MCP tool integration for the current session by generating a plan.')
    add_mcp_tool_parser.add_argument('tool_name', type=str, help='A unique local name for the MCP tool.')
    add_mcp_tool_parser.add_argument('mcp_config_json', type=str, help='JSON string with MCP connection details (e.g., \'{"url": "...", "token": "..."}\').')
    add_mcp_tool_parser.add_argument('description', type=str, help='Description of the MCP tool and its purpose.')

    # Show Transactions command
    show_transactions_parser = subparsers.add_parser('show_transactions', help='Displays all transactions for the current session.')

    # Show Design Workflow command
    show_design_workflow_parser = subparsers.add_parser('show_design_workflow', help='Displays the embedded design workflow documentation.')

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
        # Directly use the global ADDED_CAPABILITIES list
        base_help_prompt_for_log = (
            "You are the omni agent. Describe yourself and your purpose. "
            "Mention that you are a self-improving agent capable of learning new capabilities. "
            "Explain that typing 'omni help' displays this information and lists available commands. "
            "The current commands are 'help', 'add', 'add_mcp_tool', 'show_transactions', and 'show_design_workflow'.\n\n"
            "When you list the 'add' command, explain it's for adding general Python-based capabilities, where Omni (with your help as qwen3) generates a conceptual plan and placeholder code for new features.\n\n"
            "When you list the `add_mcp_tool` command, clearly explain that this command is used to define a conceptual integration with an external MCP-compliant tool or agent. "
            "Mention that Omni, with your help (qwen3), will generate a high-level plan, placeholder Python code structures for this interaction, and suggest how the user might eventually call this tool via a new `omni` command (e.g., `omni call <tool_name> ...` or `omni use_tool <tool_name> ...`). "
            "Emphasize that the full implementation of actually calling these external MCP tools is future work, and `add_mcp_tool` sets up the design and placeholder structure.\n\n"
            "Also, please state that transaction logs (viewable with `show_transactions`) are currently stored in-memory for this session and will be cleared when the agent exits. "
            "Furthermore, state that any newly added capabilities (via the 'add' or 'add_mcp_tool' commands) are registered for the current session only and will also be cleared when the agent exits. "
            "Keep the overall description concise and informative."
        )
        if ADDED_CAPABILITIES:
            capabilities_intro_log = (
                "\n\nAdditionally, the following capabilities have been planned for this session (these are placeholders awaiting full implementation and are session-specific):\n"
            )
            capabilities_list_str_for_log = capabilities_intro_log
            for cap in ADDED_CAPABILITIES:
                cap_type_log = cap.get('type', 'general_capability')
                if cap_type_log == "mcp_tool":
                    type_explanation_log = "(Type: MCP Tool Integration Definition - a plan for interacting with an external MCP-compliant tool)"
                else: # general_capability
                    type_explanation_log = "(Type: General Capability Plan - a plan for a new Python-based feature)"
                capabilities_list_str_for_log += f"- {cap['name']} {type_explanation_log}: {cap['description']}\n"
            
            help_prompt_for_log = f"{base_help_prompt_for_log}\n{capabilities_list_str_for_log}"
        else:
            help_prompt_for_log = f"{base_help_prompt_for_log}\n\nYou can add new capabilities for this session using the 'omni add <name> \"<description>\"' command for general Python features, or 'omni add_mcp_tool <name> <json_config> \"<description>\"' to define integrations with external MCP tools."

        ollama_outcome_for_log = get_qwen3_response(help_prompt_for_log)

        if ollama_outcome_for_log.startswith("Error:"):
            agent_response = f"Attempted to display help via qwen3 (with session-only capabilities list and disclaimers), but encountered an error: {ollama_outcome_for_log}"
        else:
            agent_response = "Displayed help message generated by qwen3 (with session-only capabilities list and disclaimers)."
        
        display_help() # display_help makes its own call to get_qwen3_response and prints
    
    elif args.command == 'add':
        if args.capability_name and args.description:
            agent_response = handle_add_capability(args.capability_name, args.description)
        else:
            # This case should be caught by argparse if arguments are mandatory
            print("Error: 'add' command requires capability_name and description.")
            agent_response = "Error: Missing arguments for 'add' command."

    elif args.command == 'add_mcp_tool':
        if args.tool_name and args.mcp_config_json and args.description:
            agent_response = handle_add_mcp_tool(args.tool_name, args.mcp_config_json, args.description)
        else:
            # This case should be caught by argparse if arguments are mandatory
            print("Error: 'add_mcp_tool' command requires tool_name, mcp_config_json, and description.")
            agent_response = "Error: Missing arguments for 'add_mcp_tool' command."
            
    elif args.command == 'show_transactions':
        agent_response = handle_show_transactions()

    elif args.command == 'show_design_workflow':
        agent_response = handle_show_design_workflow()

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

[end of omni.py]
