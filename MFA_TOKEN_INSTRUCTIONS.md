# Apigee Migration Assessment Tool - MFA Token Generation Instructions

## Option 1: Using the Enhanced Scripts Branch (Recommended)

This option uses the improved automation scripts that make token generation much easier.

### Prerequisites
- Docker installed and running
- Git installed
- Access to your Apigee organization with MFA enabled

### Steps

1. **Clone the repository with the scripts branch:**
   ```bash
   git clone https://github.com/krisrowe/apigee-migration-assessment-tool.git
   cd apigee-migration-assessment-tool
   git checkout feat/scripts
   ```

2. **Set up your environment:**
   ```bash
   make setup SOURCE_ORG="your-org-name"
   ```

3. **Build the Docker image:**
   ```bash
   make build
   ```

4. **Generate your MFA token:**
   ```bash
   export SOURCE_AUTH_TOKEN=$(make token APIGEE_USERNAME="your-email@domain.com" APIGEE_PASSWORD="your-password" MFA_CODE="123456")
   ```
   
   **Note:** Replace:
   - `your-email@domain.com` with your Apigee username
   - `your-password` with your Apigee password  
   - `123456` with your current 6-digit MFA code

5. **Run the assessment:**
   ```bash
   make run
   ```

### Alternative: Using .env file for easier management

You can create a `.env` file to avoid typing credentials repeatedly:

1. **Create a .env file:**
   ```bash
   cat > .env << EOF
   APIGEE_USERNAME=your-email@domain.com
   APIGEE_PASSWORD=your-password
   EOF
   ```

2. **Generate token with MFA:**
   ```bash
   export SOURCE_AUTH_TOKEN=$(make token MFA_CODE="123456")
   ```

3. **Run the assessment:**
   ```bash
   make run
   ```

---

## Option 2: Manual Token Generation (Upstream Main Branch)

This option shows how to generate tokens manually if you're using the upstream main branch without the automation scripts.

### Prerequisites
- Docker installed and running
- Git installed
- Access to your Apigee organization with MFA enabled
- curl command available

### Steps

1. **Clone the upstream repository:**
   ```bash
   git clone https://github.com/apigee/apigee-migration-assessment-tool.git
   cd apigee-migration-assessment-tool
   ```

2. **Set up your environment manually:**
   ```bash
   # Copy the sample input file
   cp sample/inputs/saas.input.properties input.properties
   
   # Edit input.properties to set your organization
   # Change SOURCE_ORG=sample-saas-project-1 to your actual org name
   nano input.properties
   
   # Create output directory
   mkdir -p output
   chmod 777 output
   ```

3. **Build the Docker image:**
   ```bash
   docker build -t apigee-migration-assessment-tool:latest .
   ```

4. **Generate your MFA token manually:**
   ```bash
   # Replace the values below with your actual credentials
   APIGEE_USERNAME="your-email@domain.com"
   APIGEE_PASSWORD="your-password"
   MFA_CODE="123456"  # Your current 6-digit MFA code
   
   # Generate the token
   TOKEN_RESPONSE=$(curl -s -H "Content-Type:application/x-www-form-urlencoded;charset=utf-8" \
     -H "Accept: application/json;charset=utf-8" \
     -H "Authorization: Basic ZWRnZWNsaTplZGdlY2xpc2VjcmV0" \
     -X POST https://login.apigee.com/oauth/token \
     -d "username=$APIGEE_USERNAME&password=$APIGEE_PASSWORD&mfa_token=$MFA_CODE&grant_type=password")
   
   # Extract the access token
   SOURCE_AUTH_TOKEN=$(echo $TOKEN_RESPONSE | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')
   
   # Verify the token was generated
   if [ -z "$SOURCE_AUTH_TOKEN" ]; then
     echo "Error: Failed to get access token. Please check your credentials and MFA code."
     echo "API Response: $TOKEN_RESPONSE"
     exit 1
   fi
   
   echo "Token generated successfully!"
   ```

5. **Run the assessment:**
   ```bash
   docker run --rm \
     -v "$(pwd)/output:/app/target" \
     -v "$(pwd)/input.properties:/app/input.properties" \
     -e SOURCE_AUTH_TOKEN="$SOURCE_AUTH_TOKEN" \
     apigee-migration-assessment-tool:latest \
     --resources all --skip-target-validation
   ```

---

## Troubleshooting

### Common Issues

1. **Permission denied on Docker:**
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker
   ```

2. **MFA code expired:**
   - MFA codes are time-sensitive (usually 30-60 seconds)
   - Generate a fresh code from your authenticator app
   - Run the token generation command again

3. **Invalid credentials:**
   - Double-check your username (usually your email)
   - Ensure your password is correct
   - Verify your organization name matches exactly

4. **Token generation fails:**
   - Check your internet connection
   - Verify you have access to login.apigee.com
   - Ensure MFA is properly configured on your account

### Getting Help

- Check the tool's output in the `output/` directory
- Review the Docker logs if the container fails to start
- Ensure all prerequisites are installed and configured correctly

---

## Security Notes

- Never commit your `.env` file or credentials to version control
- The `.env` file is already included in `.gitignore` in the scripts branch
- Tokens are temporary and will expire - you may need to regenerate them
- Keep your MFA device secure and accessible during the assessment process