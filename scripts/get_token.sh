#!/bin/bash
# This script generates and prints an Apigee OAuth2 token.
# It prompts for credentials if they are not provided as environment variables.

# --- Use existing credentials or prompt if missing ---
if [ -z "$APIGEE_USERNAME" ]; then
    read -p "Enter your Apigee Username (email): " APIGEE_USERNAME
fi
if [ -z "$APIGEE_PASSWORD" ]; then
    read -s -p "Enter your Apigee Password: " APIGEE_PASSWORD
    echo "" >&2
fi

# --- Handle MFA code based on MFA_REQUIRED setting ---
if [ -z "$MFA_CODE" ]; then
    if [ -z "$MFA_REQUIRED" ]; then
        # MFA_REQUIRED not set, prompt user and save their preference
        read -p "Please enter your 6-digit MFA code (or press Enter if MFA is not required): " MFA_CODE >&2
        echo "" >&2 # Add a newline after the prompt
        
        # Update .env file with MFA_REQUIRED setting
        if [ -n "$MFA_CODE" ]; then
            # User entered MFA code, set MFA_REQUIRED=true
            if grep -q "MFA_REQUIRED" .env 2>/dev/null; then
                sed -i 's/MFA_REQUIRED=.*/MFA_REQUIRED=true/' .env
            else
                echo "MFA_REQUIRED=true" >> .env
            fi
        else
            # User pressed Enter, set MFA_REQUIRED=false
            if grep -q "MFA_REQUIRED" .env 2>/dev/null; then
                sed -i 's/MFA_REQUIRED=.*/MFA_REQUIRED=false/' .env
            else
                echo "MFA_REQUIRED=false" >> .env
            fi
        fi
    elif [ "$MFA_REQUIRED" = "true" ]; then
        # MFA is required, but we're in non-interactive mode
        # Check if we're running in a non-interactive environment
        if [ -t 0 ]; then
            # Interactive mode - prompt for code
            read -p "Please enter your 6-digit MFA code: " -s MFA_CODE >&2
            echo "" >&2 # Add a newline after the prompt
        else
            # Non-interactive mode - MFA_CODE should be provided via environment
            if [ -z "$MFA_CODE" ]; then
                echo "Error: MFA is required but MFA_CODE is not set. Please provide MFA_CODE environment variable." >&2
                exit 1
            fi
        fi
    else
        # MFA not required, set empty code
        MFA_CODE=""
    fi
fi

# --- Generate the token using curl and parse it ---
TOKEN_RESPONSE=$(curl -s -H "Content-Type:application/x-www-form-urlencoded;charset=utf-8" \
  -H "Accept: application/json;charset=utf-8" \
  -H "Authorization: Basic ZWRnZWNsaTplZGdlY2xpc2VjcmV0" \
  -X POST https://login.apigee.com/oauth/token \
  -d "username=$APIGEE_USERNAME&password=$APIGEE_PASSWORD&mfa_token=$MFA_CODE&grant_type=password")

ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')

if [ -z "$ACCESS_TOKEN" ]; then
    echo "Error: Failed to get access token. Please check your credentials and MFA code." >&2
    echo "API Response: $TOKEN_RESPONSE" >&2
    exit 1
fi

# --- Print ONLY the token to stdout ---
echo $ACCESS_TOKEN
