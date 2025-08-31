#!/bin/bash

# Build notification script with pleasant audio feedback
# Usage: ./notify_build.sh [success|fail] [optional_message]

set -e

# Array to track background process PIDs for cleanup
BACKGROUND_PIDS=()

# Cleanup function to kill any remaining background processes
cleanup() {
    if [ ${#BACKGROUND_PIDS[@]} -gt 0 ]; then
        echo -e "\n🧹 Cleaning up background processes..."
        for pid in "${BACKGROUND_PIDS[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
            fi
        done
        BACKGROUND_PIDS=()
    fi
}

# Set up trap to cleanup on script exit or interruption
trap cleanup EXIT INT TERM

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to play success tones (ascending pleasant chord)
play_success_tones() {
    echo -e "${GREEN}🎵 Playing success notification...${NC}"
    
    # Pleasant ascending chord progression
    speaker-test -t sine -f 523 -l 1 -s 1 >/dev/null 2>&1 &  # C5
    BACKGROUND_PIDS+=($!)
    sleep 0.15
    speaker-test -t sine -f 659 -l 1 -s 1 >/dev/null 2>&1 &  # E5
    BACKGROUND_PIDS+=($!)
    sleep 0.15
    speaker-test -t sine -f 784 -l 1 -s 1 >/dev/null 2>&1 &  # G5
    BACKGROUND_PIDS+=($!)
    sleep 0.2
    speaker-test -t sine -f 1047 -l 1 -s 1 >/dev/null 2>&1 & # C6 (octave)
    BACKGROUND_PIDS+=($!)
    sleep 0.3
}

# Function to play failure tones (descending minor progression)
play_failure_tones() {
    echo -e "${RED}🔔 Playing failure notification...${NC}"
    
    # Descending minor progression to indicate failure
    speaker-test -t sine -f 440 -l 1 -s 1 >/dev/null 2>&1 &  # A4
    BACKGROUND_PIDS+=($!)
    sleep 0.2
    speaker-test -t sine -f 392 -l 1 -s 1 >/dev/null 2>&1 &  # G4
    BACKGROUND_PIDS+=($!)
    sleep 0.2
    speaker-test -t sine -f 349 -l 1 -s 1 >/dev/null 2>&1 &  # F4
    BACKGROUND_PIDS+=($!)
    sleep 0.3
    speaker-test -t sine -f 294 -l 1 -s 1 >/dev/null 2>&1 &  # D4
    BACKGROUND_PIDS+=($!)
    sleep 0.4
}

# Function to try system sounds as fallback
try_system_sounds() {
    local sound_type="$1"
    
    if [ "$sound_type" = "success" ]; then
        # Try common success sound files
        for sound_file in \
            "/usr/share/sounds/freedesktop/stereo/complete.oga" \
            "/usr/share/sounds/alsa/Front_Left.wav" \
            "/usr/share/sounds/ubuntu/stereo/desktop-login.ogg"; do
            if [ -f "$sound_file" ]; then
                paplay "$sound_file" 2>/dev/null && return 0
            fi
        done
    else
        # Try common error sound files
        for sound_file in \
            "/usr/share/sounds/freedesktop/stereo/dialog-error.oga" \
            "/usr/share/sounds/ubuntu/stereo/dialog-error.ogg" \
            "/usr/share/sounds/alsa/Side_Left.wav"; do
            if [ -f "$sound_file" ]; then
                paplay "$sound_file" 2>/dev/null && return 0
            fi
        done
    fi
    return 1
}

# Main notification function
notify_build() {
    local status="$1"
    local message="${2:-Build notification}"
    
    case "$status" in
        "success")
            echo -e "${GREEN}✅ SUCCESS: $message${NC}"
            if ! try_system_sounds "success"; then
                play_success_tones
            fi
            ;;
        "fail"|"failure"|"error")
            echo -e "${RED}❌ FAILURE: $message${NC}"
            if ! try_system_sounds "failure"; then
                play_failure_tones
            fi
            ;;
        *)
            echo -e "${BLUE}ℹ️  NOTIFICATION: $message${NC}"
            # Default neutral tone
            speaker-test -t sine -f 800 -l 1 -s 1 >/dev/null 2>&1 &
            BACKGROUND_PIDS+=($!)
            sleep 0.3
            ;;
    esac
}

# Script usage
show_usage() {
    echo "Usage: $0 [success|fail] [optional_message]"
    echo ""
    echo "Examples:"
    echo "  $0 success \"Frontend build completed\""
    echo "  $0 fail \"Backend tests failed\""
    echo "  $0 success"
    echo ""
    echo "Audio methods used (in order of preference):"
    echo "  1. System sound files via paplay"
    echo "  2. Generated tones via speaker-test"
}

# Main script logic
main() {
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi
    
    local status="$1"
    local message="$2"
    
    # Check if required tools are available
    if ! command -v speaker-test >/dev/null 2>&1; then
        echo -e "${RED}Warning: speaker-test not found. Audio notifications may not work.${NC}"
    fi
    
    if ! command -v paplay >/dev/null 2>&1; then
        echo -e "${RED}Warning: paplay not found. System sound fallback unavailable.${NC}"
    fi
    
    notify_build "$status" "$message"
}

# Run main function with all arguments
main "$@"
