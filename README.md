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

## Developing

Copycat uses [mypy](http://mypy-lang.org/) for type checking and [yapf](https://readthedocs.org/projects/yapf/) for code formatting.
