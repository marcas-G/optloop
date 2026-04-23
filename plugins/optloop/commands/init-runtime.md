Initialize the outer runtime bootstrap for optloop.

Use Bash to run the bundled initializer below. Do not reimplement the logic inline.

Command:
bash "${CLAUDE_PLUGIN_ROOT}/bin/optloop-init"

What this initializer must do:
1. Repair execute permissions for bundled scripts in `${CLAUDE_PLUGIN_ROOT}/bin`.
2. Create persistent plugin data directories under `${CLAUDE_PLUGIN_DATA}`.
3. Write a path/env config file for later commands and hooks.
4. Detect a Dockerfile in `$CLAUDE_PROJECT_DIR`.
5. Build the Docker image if it does not already exist.
6. Create the runtime container if it does not already exist.
7. Start the container if it is stopped.
8. Print a compact status summary at the end.

Constraints:
- Do not run benchmark logic here.
- Do not enter the inner optimization loop here.
- Do not modify project source code except files under the runtime data directory or user-approved config files.
- Fail with a clear error if Docker is missing or no Dockerfile can be found.

Output requirements:
- Print the resolved project dir, plugin root, plugin data dir, image tag, and container name.
- Print whether image was reused or built.
- Print whether container was reused, created, or started.