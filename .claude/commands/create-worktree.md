You are automating the creation of a git worktree.
The input argument is the worktree name. Let: WORKTREE_NAME = $ARGUMENTS

Execute the following steps in order. Stop immediately if any step fails.

1. **Update Refs:**
   Run `git fetch origin main` to ensure we have the latest code.

2. **Create Worktree:**
   Run `git worktree add .trees/{WORKTREE_NAME} -b {WORKTREE_NAME} origin/main`

3. **Link Environment Config:**
   Create a symbolic link for the dev environment file. Use the absolute path to avoid relative linking errors.
   Run `ln -s "$(pwd)/.env.dev" ".trees/{WORKTREE_NAME}/.env.dev"`

**Error Handling Rules:**
If any command returns a non-zero exit code:
1. Print the specific error message.
2. Analyze why it failed (e.g., check if the directory exists, if the branch name is taken, or if .env.dev is missing).
3. Propose a specific fix command and wait for my confirmation to proceed.
