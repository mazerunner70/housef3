# Test User Management Scripts

This directory contains scripts for managing test users in AWS Cognito User Pool.

## Files

### `add_cognito_test_user.sh`
Creates new test users in Cognito User Pool.

**Usage:**
```bash
./scripts/test-users/add_cognito_test_user.sh
```

**Features:**
- Reads accounts from `test-accounts.env` at project root
- Creates users with permanent passwords (no forced change on first login)
- Shows comprehensive error reporting
- Continues processing all accounts even if some fail
- Provides detailed summary at the end

**Behavior:**
- Skips users that already exist
- Exits with code 1 if any accounts failed
- Exits with code 0 if all accounts succeeded

### `update_cognito_test_user_passwords.sh`
Updates passwords for existing test users in Cognito User Pool.

**Usage:**
```bash
./scripts/test-users/update_cognito_test_user_passwords.sh
```

**Features:**
- Reads accounts from `test-accounts.env` at project root
- Updates passwords for existing users to match the file
- Sets all passwords as permanent (no forced change on first login)
- Shows comprehensive error reporting
- Continues processing all accounts even if some fail
- Provides detailed summary at the end

**Behavior:**
- Skips users that don't exist
- Exits with code 1 if any updates failed
- Exits with code 0 if all updates succeeded

## Account File Format

Both scripts read from `test-accounts.env` at the project root. Format:

```
# Comments start with #
# Format: email password (space or comma separated)

testuser1@example.com Password123!
testuser2@example.com AnotherPass456!

# Comma separation also works:
# admin@example.com,AdminPassword789!
```

## Prerequisites

1. AWS CLI configured with appropriate permissions
2. Terraform outputs available in `infrastructure/terraform/`
3. `test-accounts.env` file exists at project root
4. Execute from project root directory

## Examples

### Create new users:
```bash
./scripts/test-users/add_cognito_test_user.sh
```

### Update existing user passwords:
```bash
./scripts/test-users/update_cognito_test_user_passwords.sh
```

### Typical workflow:
1. Update `test-accounts.env` with desired accounts
2. Run `add_cognito_test_user.sh` to create new accounts
3. Run `update_cognito_test_user_passwords.sh` to update existing passwords
