# Copycat Slack Bot

Copycat is a Slack bot that imitates people from their slack message history.

## Setup

1. Clone this repository to your local machine.

2. Install the project dependencies:

   ```bash
   poetry install
   ```

3. Copy the `.env.example` file to a new file named `.env` and replace the placeholder values with your actual Slack/OpenAI API credentials:

   ```bash
   cp .env.example .env
   ```

4. Start the bot:

   ```bash
   poetry run start
   ```

5. Start ngrok

   ```bash
   ngrok http 3000
   ```

6. Update [Event Subscriptions URL](https://api.slack.com/apps/A05940MD2FJ/event-subscriptions?) to point to `<your-ngrok-url>/slack/events

## Developing

Copycat uses [mypy](http://mypy-lang.org/) for type checking and [yapf](https://readthedocs.org/projects/yapf/) for code formatting.
