### Heroku Setup Instructions:

1. Start by forking and starring this repository.
2. Navigate to your forked repository.
3. Access the settings.
4. Set the deploy branch as the default branch.
5. Remove all other branches.
6. Populate these secret variables in GitHub:
   
   * `BOT_TOKEN`
   * `OWNER_ID`
   * `DATABASE_URL`
   * `TELEGRAM_API`
   * `TELEGRAM_HASH`
   * `HEROKU_APP_NAME`
   * `HEROKU_EMAIL`
   * `HEROKU_API_KEY`

7. Run action workflow.
8. After the deployment is complete, finalize the remaining variables and upload sensitive files like `token.pickle` using the `bsetting` command.

[Donate](.github/donations.md)