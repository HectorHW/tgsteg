# Telegram image steganography bot

This repo contains code of a simple bot that can be used to store simple steganographic data into images. Data should be somewhat JPEG compression-resistant (but not resize-resistant) because of BCH codes used for redundancy.

## How to setup

Install dependecies with poetry: `poetry install`. Create a telegram bot via BotFather and pass it as environment variable `TOKEN` or write to `.env` file. Run bot with `poetry run bot`.
