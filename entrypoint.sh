#!/bin/bash
set -e

# GitHub Action entrypoint for GitLab Ticker

# Build command arguments
ARGS=()

# Repository path (default to /github/workspace which is where GitHub mounts the repo)
REPO_PATH="${INPUT_REPO_PATH:-/github/workspace}"
ARGS+=("$REPO_PATH")

# Main branch
ARGS+=("${INPUT_MAIN_BRANCH:-main}")

# Mode-specific arguments
if [ "$INPUT_MODE" = "dev-branch" ]; then
    # Dev-branch mode
    if [ -z "$INPUT_DEV_BRANCH" ]; then
        echo "::error::dev_branch input is required when mode is 'dev-branch'"
        exit 1
    fi
    ARGS+=("--dev-branch" "$INPUT_DEV_BRANCH")
    
    # Max diff size
    if [ -n "$INPUT_MAX_DIFF_SIZE" ]; then
        ARGS+=("--max-diff-size" "$INPUT_MAX_DIFF_SIZE")
    fi
    
    # Slack integration
    if [ "$INPUT_SEND_TO_SLACK" = "true" ]; then
        if [ -z "$INPUT_SLACK_CHANNEL" ]; then
            echo "::error::slack_channel is required when send_to_slack is true"
            exit 1
        fi
        if [ -z "$SLACK_TOKEN" ]; then
            echo "::error::slack_token is required when send_to_slack is true"
            exit 1
        fi
        ARGS+=("--send-to-slack" "--slack-channel" "$INPUT_SLACK_CHANNEL")
    fi
else
    # Commit-range mode
    if [ -z "$INPUT_COMMIT_A" ]; then
        echo "::error::commit_a input is required when mode is 'commit-range'"
        exit 1
    fi
    ARGS+=("$INPUT_COMMIT_A")
    
    # Optional commit_b
    if [ -n "$INPUT_COMMIT_B" ]; then
        ARGS+=("$INPUT_COMMIT_B")
    fi
    
    # Output directory
    ARGS+=("--output" "${INPUT_OUTPUT_DIR:-./output}")
    
    # Skip empty merges
    if [ "$INPUT_SKIP_EMPTY_MERGES" = "true" ]; then
        ARGS+=("--skip-empty-merges")
    fi
    
    # Max diff size
    if [ -n "$INPUT_MAX_DIFF_SIZE" ]; then
        ARGS+=("--max-diff-size" "$INPUT_MAX_DIFF_SIZE")
    fi
fi

# Validate LLM provider configuration
if [ "$LLM_PROVIDER" = "anthropic" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "::error::anthropic_api_key is required when llm_provider is 'anthropic'"
    exit 1
fi

if [ "$LLM_PROVIDER" = "openai" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "::error::openai_api_key is required when llm_provider is 'openai'"
    exit 1
fi

echo "Running GitLab Ticker with arguments: ${ARGS[*]}"

# Capture output for dev-branch mode to set as action output
if [ "$INPUT_MODE" = "dev-branch" ]; then
    OUTPUT=$(python /app/validate_commits.py "${ARGS[@]}" 2>&1) || {
        echo "$OUTPUT"
        exit 1
    }
    echo "$OUTPUT"
    
    # Extract summary between the separator lines for the output
    SUMMARY=$(echo "$OUTPUT" | sed -n '/^=\{80\}$/,/^=\{80\}$/p' | sed '1d;$d' | sed '1d')
    
    # Set output (handle multiline)
    {
        echo "summary<<EOF"
        echo "$SUMMARY"
        echo "EOF"
    } >> "$GITHUB_OUTPUT"
else
    python /app/validate_commits.py "${ARGS[@]}"
    
    # Set output path
    echo "output_path=${INPUT_OUTPUT_DIR:-./output}" >> "$GITHUB_OUTPUT"
fi

echo "::notice::GitLab Ticker completed successfully!"

