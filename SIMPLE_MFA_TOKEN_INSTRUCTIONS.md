# Simple MFA Token Generation for Apigee Migration Assessment Tool

## Quick Token Generation with MFA

Here's the simple curl command to generate your Apigee token with MFA:

### Step 1: Set your credentials
```bash
export APIGEE_USERNAME="your-email@domain.com"
export APIGEE_PASSWORD="your-password"
export MFA_CODE="123456"  # Your current 6-digit MFA code
```

### Step 2: Generate the token
```bash
curl -s -H "Content-Type:application/x-www-form-urlencoded;charset=utf-8" \
  -H "Accept: application/json;charset=utf-8" \
  -H "Authorization: Basic ZWRnZWNsaTplZGdlY2xpc2VjcmV0" \
  -X POST https://login.apigee.com/oauth/token \
  -d "username=$APIGEE_USERNAME&password=$APIGEE_PASSWORD&mfa_token=$MFA_CODE&grant_type=password"
```

### Step 3: Extract and use the token
```bash
# Generate token and extract access_token
TOKEN_RESPONSE=$(curl -s -H "Content-Type:application/x-www-form-urlencoded;charset=utf-8" \
  -H "Accept: application/json;charset=utf-8" \
  -H "Authorization: Basic ZWRnZWNsaTplZGdlY2xpc2VjcmV0" \
  -X POST https://login.apigee.com/oauth/token \
  -d "username=$APIGEE_USERNAME&password=$APIGEE_PASSWORD&mfa_token=$MFA_CODE&grant_type=password")

# Extract the access token
SOURCE_AUTH_TOKEN=$(echo $TOKEN_RESPONSE | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')

# Verify token was generated
if [ -z "$SOURCE_AUTH_TOKEN" ]; then
  echo "Error: Failed to get access token. Please check your credentials and MFA code."
  echo "API Response: $TOKEN_RESPONSE"
  exit 1
fi

echo "Token generated successfully: $SOURCE_AUTH_TOKEN"
```

### Step 4: Run the assessment tool
```bash
# Build the Docker image (if not already built)
docker build -t apigee-migration-assessment-tool:latest .

# Run the assessment
docker run --rm \
  -v "$(pwd)/output:/app/target" \
  -v "$(pwd)/input.properties:/app/input.properties" \
  -e SOURCE_AUTH_TOKEN="$SOURCE_AUTH_TOKEN" \
  apigee-migration-assessment-tool:latest \
  --resources all --skip-target-validation
```

## One-Liner Version

If you prefer a single command that does everything:

```bash
export APIGEE_USERNAME="your-email@domain.com" && \
export APIGEE_PASSWORD="your-password" && \
export MFA_CODE="123456" && \
SOURCE_AUTH_TOKEN=$(curl -s -H "Content-Type:application/x-www-form-urlencoded;charset=utf-8" -H "Accept: application/json;charset=utf-8" -H "Authorization: Basic ZWRnZWNsaTplZGdlY2xpc2VjcmV0" -X POST https://login.apigee.com/oauth/token -d "username=$APIGEE_USERNAME&password=$APIGEE_PASSWORD&mfa_token=$MFA_CODE&grant_type=password" | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//') && \
echo "Token: $SOURCE_AUTH_TOKEN"
```

## Important Notes

- **MFA Code**: Must be your current 6-digit code from your authenticator app (expires in 30-60 seconds)
- **Credentials**: Use your actual Apigee username (usually your email) and password
- **Token Expiry**: Tokens are temporary and will expire - regenerate as needed
- **Security**: Never commit credentials to version control

## Troubleshooting

- **Invalid credentials**: Double-check username/password
- **MFA expired**: Generate a fresh code from your authenticator
- **Network issues**: Ensure you can reach login.apigee.com
- **Permission denied**: Make sure you have Docker permissions (`sudo usermod -aG docker $USER`)