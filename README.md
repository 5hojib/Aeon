<p align="center">
    <a href="https://github.com/5hojib/Aeon-MLTB">
        <kbd>
            <gif width="250" src="https://github.com/jubayerprantor/designresources/blob/main/cover.gif" alt="Aeon-MLTB animation">
        </kbd>
    </a>
</p>

### Heroku Deployment Instructions

1. **Fork and Star the Repository**
   - Start by forking and starring this repository.
   - When forking, ensure that the option "Copy the default branch only" is unchecked before forking the repository.

2. **Navigate to Your Forked Repository**
   - Once the repository is forked, navigate to your forked repository.

3. **Access the Settings**
   - Go to the settings of your forked repository.
   - Enable all actions in the settings.

4. **Run Action Workflow**
   - Go to the **Actions** tab.
   - Select the `Deploy to Heroku` action from the list of workflows.
   - Click on **Run workflow**.
   - Fill in the following variables in the form:
     - `BOT_TOKEN`
     - `OWNER_ID`
     - `DATABASE_URL`
     - `TELEGRAM_API`
     - `TELEGRAM_HASH`
     - `HEROKU_APP_NAME`
     - `HEROKU_EMAIL`
     - `HEROKU_API_KEY`
   - Run the action workflow.

5. **Finalize the Deployment**
   - After the deployment is complete, finalize the remaining variables.
   - Upload sensitive files like `token.pickle` using the `/botsettings` command.