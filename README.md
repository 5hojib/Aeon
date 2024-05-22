### Heroku Deployment Instructions

1. **Fork and Star the Repository**
   - Start by forking and starring this repository.
   - When forking, ensure that the option "Copy the default branch only" is unchecked before forking the repository.

2. **Navigate to Your Forked Repository**
   - Once the repository is forked, navigate to your forked repository.

3. **Access the Settings**
   - Access the settings of your forked repository.

4. **Populate Secret Variables in GitHub**
   - Find "Secrets and Variables" in the repository settings and access "Actions."
   - Populate the following secret variables in GitHub:
     * `BOT_TOKEN`
     * `OWNER_ID`
     * `DATABASE_URL`
     * `TELEGRAM_API`
     * `TELEGRAM_HASH`
     * `HEROKU_APP_NAME`
     * `HEROKU_EMAIL`
     * `HEROKU_API_KEY`

5. **Run Action Workflow**
   - Run the action workflow but with the deploy branch.

6. **Finalize the Deployment**
   - After the deployment is complete, finalize the remaining variables and upload sensitive files like `token.pickle` using the `/botsettings` command.
