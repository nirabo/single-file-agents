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
```
