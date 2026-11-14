# Moving `ANTHROPIC_*` Environment Variables to `~/.claude/settings.json`

Claude Code and VSCode can both read environment variables from its user settings file. On Windows, the file is typically located at %USERPROFILE%\.claude\settings.json, which is represented as ~/.claude/settings.json.

1. Find your current environment variables

   - Go to _System Properties > Advanced > Environment Variables_
   - Find each `ANTHROPIC_*` or `CLAUDE_` variable
   - You will need to refer to these later, so either copy each one to a file you can copy from, or leave this dialog open until you are finished so you can copy from it.
2. Put the deleted settings into your `settings.json` file.

   - In VSCode, open `C:\Users\<username>\.claude\settings.json`. The start of my `settings.json` file appears below, for reference.

     ```JSON
     {
       "permissions": {
         "defaultMode": "auto"
       },
       "model": "opus[1m]",
       ... etc ...
     }
     ```

3. Look to see if your file already has an `env` section. If it does, please go to step 5.

4. If your `settings.json` has no `env` section, you will simply add one at the very top of the `settings.json` file, right after the first left brace. You add one entry for each environment variable you found in Step 1.

   For example, if my file above needed to have an `env` section added, and if I needed to add the environment variables `ANTHROPIC_AUTH_TOKEN` and `ANTHROPIC_BASE_URL`, I would edit it to look like the JSON seen below.

   Note where the commas are (after the `ANTHROPIC_AUTH_TOKEN` entry and after the `env` section), and where they are not (after the last entry, which is after the `ANTHROPIC_BASE_URL` entry). Commas matter in JSON.

   Replace `<your-auth-token>` with your real API key and `<your-gateway-url>` with the base URL your organization gave you (leave out `ANTHROPIC_BASE_URL` entirely if you talk to Anthropic directly). You should also add any other environment variables you saved earlier, if applicable.

   ```JSON
   {
     "env": {
       "ANTHROPIC_AUTH_TOKEN": "<your-auth-token>",
       "ANTHROPIC_BASE_URL": "https://<your-gateway-url>"
     },
     "permissions": {
       "defaultMode": "auto"
     },
     "model": "opus[1m]",
     ... etc ...
   }
   ```

   At this point, please go to step 6.

5. If your `settings.json` already has an `env` section, you will simply add one line to it for every environment variable you want to set.

   IF you only need to set `ANTHROPIC_AUTH_TOKEN` and `ANTHROPIC_BASE_URL`, you would add the two lines shown below to your `env` section.

   Remember that every entry in a section needs a comma after it, except the last entry. In the example, I'm putting the new lines at the end of the `env` section. This meant I had to add the comma after `SOME_EXISTING_VARIABLE`'s entry - it did not have one before because it used to be the last entry. I also had to make sure there was a comma after `ANTHROPIC_AUTH_TOKEN` but not after`ANTHROPIC_BASE_URL`.

   Replace `<your-auth-token>` with your real API key and `<your-gateway-url>` with the base URL your organization gave you (leave out `ANTHROPIC_BASE_URL` entirely if you talk to Anthropic directly). You should also add any other environment variables you saved earlier, if applicable.

   ```JSON
   {
     ...
     "env": {
       "SOME_EXISTING_VARIABLE": "SOME_EXISTING_VALUE",
       "ANTHROPIC_AUTH_TOKEN": "<your-auth-token>",
       "ANTHROPIC_BASE_URL": "https://<your-gateway-url>"
     },
     ... etc ...
   }
   ```

6. Verify the JSON syntax

   Before deleting the environment variables defined in Windows, we want to make sure that the syntax of this file is valid. To do this, run the following command in PowerShell. You should get back output similar to what is shown.

   If an error message is returned, your JSON syntax is wrong. If you remove your auth token (mask it with some asterisks) then you can go to gemini.google.com and just ask it what's wrong with your JSON, since nothing else in the file should be sensitive.

   ```PowerShell
   > ConvertFrom-Json $(Get-Content $HOME\.claude\settings.json -Raw)

   env                      : @{ANTHROPIC_AUTH_TOKEN=<your-auth-token>;  ANTHROPIC_BASE_URL=https://<your-gateway-url>}
   permissions              : @{defaultMode=auto}
   model                    : opus[1m]
   cleanupPeriodDays        : 365
   hooks                    : @{SessionEnd=System.Object[]; SessionStart=System.Object[]}
   statusLine               : @{type=command; command=bash ~/.claude/statusline-command.sh}
   effortLevel              : medium
   skipAutoPermissionPrompt : True
   ```

   > NOTE: your API key will be in plaintext in this output. Do not let others see it.

   After you have verified that your JSON is valid, continue to step 7.

7. Delete (or rename) your environment variables

   It's time to delete your environment variables. If you want to back them up first, this is an easy way:

   ```PowerShell
   > dir env:\ > "your-backup-file.txt"
   ```

   Look at the file after you create it. It should have a listing of all environment variables and their values.

   > NOTE: your API key will be in plaintext in this backup file. Do not let others see it.

   Now you should delete or rename the environment variables. You can do this through the _System Properties > Advanced > Environment Variables_ GUI you opened earlier. After you do this, just restart PowerShell, cmd, VSCode, or anyplace else that is using Claude. Any of those clients should find the credentials in their new location.
