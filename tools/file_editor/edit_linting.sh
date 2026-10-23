#!/bin/bash

# @yaml
# signature: edit <start_line>:<end_line>\n<replacement_text>\nend_of_edit
# end_name: end_of_edit
# docstring: Replaces lines <start_line> through <end_line> (inclusive) with the given text in the currently open file. Automatically runs the project linter and reverts on syntax errors.
# arguments:
#   start_line:
#     type: integer
#     description: The first line to replace.
#     required: true
#   end_line:
#     type: integer
#     description: The last line to replace.
#     required: true
#   replacement_text:
#     type: string
#     description: The new code to insert, terminated by end_of_edit on its own line.
#     required: true
edit() {
    if [ "$CURRENT_FILE" = "none" ] || [ ! -f "$CURRENT_FILE" ]; then
        echo "Error: No file is currently open. Use 'open <path>' first."
        return 1
    fi

    local range="$1"
    local start_line=$(echo "$range" | cut -d: -f1)
    local end_line=$(echo "$range" | cut -d: -f2)
    shift
    local replacement="$*"

    # 1. Crear copia de respaldo para rollback automático si falla el linter
    local backup_file="/tmp/aci_backup_$(basename "$CURRENT_FILE")"
    cp "$CURRENT_FILE" "$backup_file"

    # 2. Aplicar el reemplazo de líneas
    python3 - "$CURRENT_FILE" "$start_line" "$end_line" "$replacement" << 'EOF'
import sys
file_path, start, end, replacement = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
with open(file_path, 'r') as f:
    lines = f.readlines()
new_lines = [line + '\n' for line in replacement.split('\n')] if replacement else []
lines[start-1:end] = new_lines
with open(file_path, 'w') as f:
    f.writelines(lines)
EOF

    # 3. Leer el comando de linter desde workflow_context.json (o usar flake8 por defecto para Python)
    local lint_errors=""
    if [[ "$CURRENT_FILE" == *.py ]]; then
        lint_errors=$(flake8 --isolated --select=F821,F822,F831,E111,E112,E113,E999,E902 "$CURRENT_FILE" 2>&1)
    elif [[ "$CURRENT_FILE" == *.go ]]; then
        lint_errors=$(gofmt -e "$CURRENT_FILE" >/dev/null 2>&1 || go vet "$CURRENT_FILE" 2>&1)
    fi

    # 4. Si hay errores de sintaxis, mostrar las 3 secciones y revertir (Rollback)
    if [ -n "$lint_errors" ]; then
        echo "Your proposed edit has introduced new syntax error(s). Please understand the fixes and retry your edit command."
        echo ""
        echo "ERRORS:"
        echo "$lint_errors"
        echo ""
        echo "This is how your edit would have looked if applied"
        echo "-------------------------------------------------"
        goto "$start_line"
        echo "-------------------------------------------------"
        echo ""
        # Revertir al archivo original
        cp "$backup_file" "$CURRENT_FILE"
        echo "This is the original code before your edit"
        echo "-------------------------------------------------"
        goto "$start_line"
        echo "-------------------------------------------------"
        echo "Your changes have NOT been applied. Please fix your edit command and try again."
        rm -f "$backup_file"
        return 1
    fi

    rm -f "$backup_file"
    echo "File updated successfully. Reviewing changes:"
    goto "$start_line"
}

# @yaml
# signature: submit
# docstring: Submits the current code changes by generating model.patch via git diff and signaling completion.
submit() {
    git status --porcelain
    git diff > "../../shared_pool/03_code_patches/model.patch"
    echo "<<SWE_AGENT_SUBMISSION>>"
}
