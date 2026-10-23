#!/bin/bash

# @yaml
# signature: search_dir <search_term> [<dir>]
# docstring: Searches for search_term in all files in dir. Rejects queries with more than 50 matches to prevent context overflow.
# arguments:
#   search_term:
#     type: string
#     description: The term to search for.
#     required: true
#   dir:
#     type: string
#     description: The directory to search in (defaults to current directory).
#     required: false
search_dir() {
    local term="$1"
    local dir="${2:-.}"
    local max_results="${MAX_SEARCH_RESULTS:-50}"

    local matches=$(grep -rnI "$term" "$dir" 2>/dev/null)
    if [ -z "$matches" ]; then
        echo "No matches found for \"$term\" in $dir"
        return 0
    fi

    local count=$(echo "$matches" | wc -l)
    if [ "$count" -gt "$max_results" ]; then
        echo "More than $max_results matches found ($count matches) for \"$term\" in $dir. Please narrow your query or specify a subdirectory."
        return 1
    fi

    echo "Found $count matches for \"$term\" in $dir:"
    echo "$matches"
    echo "End of matches for \"$term\" in $dir"
}

# @yaml
# signature: find_file <file_name> [<dir>]
# docstring: Finds all files with a given name or pattern in the specified directory.
# arguments:
#   file_name:
#     type: string
#     description: The file name or pattern to find.
#     required: true
#   dir:
#     type: string
#     description: The directory to search in.
#     required: false
find_file() {
    local name="$1"
    local dir="${2:-.}"
    find "$dir" -name "*$name*" -not -path '*/.*'
}