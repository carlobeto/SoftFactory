#!/bin/bash

# @yaml
# signature: open <path> [<line_number>]
# docstring: Opens the file at the given path in the editor. If line_number is provided, the window will center around that line.
# arguments:
#   path:
#     type: string
#     description: The path to the file to open.
#     required: true
#   line_number:
#     type: integer
#     description: The line number to move the window to.
#     required: false
open() {
    local file_path="$1"
    local target_line="${2:-1}"

    if [ ! -f "$file_path" ]; then
        echo "Error: File '$file_path' not found."
        return 1
    fi

    export CURRENT_FILE="$(realpath "$file_path")"
    goto "$target_line"
}

# @yaml
# signature: goto <line_number>
# docstring: Moves the window to show <line_number> positioned 1/6 of the way down the 100-line window (~17 lines of preceding context).
# arguments:
#   line_number:
#     type: integer
#     description: The line number to navigate to.
#     required: true
goto() {
    if [ "$CURRENT_FILE" = "none" ] || [ ! -f "$CURRENT_FILE" ]; then
        echo "Error: No file is currently open. Use 'open <path>' first."
        return 1
    fi

    local target=$1
    local offset=$(( WINDOW_SIZE / 6 )) # ~17 líneas de contexto previo
    local start_line=$(( target - offset ))
    if [ "$start_line" -lt 1 ]; then start_line=1; fi

    export CURRENT_LINE=$start_line
    _print_window
}

# @yaml
# signature: scroll_down
# docstring: Moves the window down by 98 lines (WINDOW_SIZE 100 minus OVERLAP 2).
scroll_down() {
    local step=$(( WINDOW_SIZE - OVERLAP ))
    export CURRENT_LINE=$(( CURRENT_LINE + step ))
    _print_window
}

# @yaml
# signature: scroll_up
# docstring: Moves the window up by 98 lines (WINDOW_SIZE 100 minus OVERLAP 2).
scroll_up() {
    local step=$(( WINDOW_SIZE - OVERLAP ))
    local new_line=$(( CURRENT_LINE - step ))
    if [ "$new_line" -lt 1 ]; then new_line=1; fi
    export CURRENT_LINE=$new_line
    _print_window
}

_print_window() {
    local total_lines=$(wc -l < "$CURRENT_FILE")
    local end_line=$(( CURRENT_LINE + WINDOW_SIZE - 1 ))
    if [ "$end_line" -gt "$total_lines" ]; then end_line=$total_lines; fi

    local lines_above=$(( CURRENT_LINE - 1 ))
    local lines_below=$(( total_lines - end_line ))

    echo "[File: $CURRENT_FILE ($total_lines lines total)]"
    [ "$lines_above" -gt 0 ] && echo "($lines_above more lines above)"
    awk -v s="$CURRENT_LINE" -v e="$end_line" 'NR>=s && NR<=e {print NR ":" $0}' "$CURRENT_FILE"
    [ "$lines_below" -gt 0 ] && echo "($lines_below more lines below)"
}
