# Repository Description

This repository contains a Telegram bot written in Python that allows access to Instagram (with support for saved sessions, two-factor authentication, and challenge/approval flows) and manage Instagram live streams directly from Telegram. Features include creating, starting, and stopping live streams, viewing live information, retrieving comments, and listing viewers.

# Telegram-Instagram Live Bot

A Telegram bot written in Python that allows you to:

* **Access Instagram** (including two-factor authentication and challenge/approval flows).
* **Manage Instagram live streams**: create, start, and stop a live stream, retrieve the viewer list, view comments, and more.
* **Optionally save the session** for faster access in the future.

---

## Index

1. [Overview](#overview)  
2. [Requirements](#requirements)  
3. [Installation](#installation)  
4. [Configuration](#configuration)  
5. [Usage](#usage)  
6. [How it Works](#how-it-works)  
7. [2FA and Challenge Handling](#2fa-and-challenge-handling)  
8. [Detailed Steps](#detailed-steps)  
9. [Troubleshooting](#troubleshooting)  
10. [Contributing](#contributing)  

---

## Overview

* **Telegram Bot** to control Instagram actions via chat commands.
* **Access to Instagram** using username/password, with support for two-factor authentication and challenge/approval flows.
* **Live Stream Management**: create a broadcast, start it, stop it, retrieve comments, view viewers, etc.
* **Session Saving**: avoid re-entering credentials in the future if you choose to save the session on first access.

---

## Requirements

1. **Python 3.9 or later**  
   Ensure you have Python version 3.9 or higher.
2. **Telegram Bot Token**  
   * Create a Telegram bot via [BotFather](https://t.me/BotFather).  
   * Get the **token** (something like `12345678:ABCDEF...`).
3. **An Instagram Account**  
   * Must be valid to access and use live features.
   * If you wish to test 2FA or challenges, enable them in your Instagram account settings.
4. **Ability to Install Python Packages**  
   * Typically done via `pip install...`.

---

## Installation

1. **Clone this repository** (or download the files):
   ```bash
   git clone https://github.com/PsyMan47/InstaLive-bot.git
   cd InstaLive-bot

   (Optional) Create a virtual environment:

   python -m venv venv
   source venv/bin/activate  # or.\venv\Scripts\activate on Windows

   Install dependencies:

   pip install -r requirements.txt

## Configuration

* **Insert the Telegram Bot Token**
   * Open the `bot.py` file (or any file that contains `TOKEN`) and replace the placeholder token with your real one.
   * Example: `TOKEN = "123456:ABC-XYZ"`
* **Optionally Handle Saved Sessions**
   * After a successful Instagram login, you can choose to save the session to a JSON file (e.g., `username_session.json`) so future logins won't require the password.
   * If you don't want to save the session, simply dismiss it when prompted by the bot.
* **Confirm Python Version**
   * Run `python --version` to verify you have Python 3.9+.

## Usage

* **Run the Bot**:

   python bot.py

   * You should see a message like:

     "Telegram Bot is running..."

* **Open Telegram**:
  * Find the bot by its username.
  * Type `/start` or press Start.

* **Commands / Flow**:
  * The main menu offers "Login" and "Start Live".
  * The login flow will ask for Instagram credentials (username, password).
    * If 2FA or challenges are needed, the bot will guide you accordingly.
    * Optionally save the session thereafter.
  * The "Start Live" flow: enter a title, the bot creates the broadcast, shows streaming info, and you can start or stop the live stream, check viewers, and read comments.

## How it Works

* **Login Flow**:

  * The bot uses states of the `ConversationHandler`:
    * `ASK_USERNAME` → ask for the username
    * `ASK_PASSWORD` → ask for the password
    * `ASK_2FA` → handle the 2FA code
    * `ASK_CHALLENGE` → handle the approval or resolution of a challenge
    * `ASK_SAVE_SESSION` → decide if you want to save the session
  * Upon success, an instance of `instagrapi.Client` is saved in memory for that user.

* **Live Stream Management**:

  * `create_broadcast(title)`: sets up the live broadcast on the Instagram side.
  * `start_broadcast()`: actually starts the live broadcast, allowing you to stream from an encoder or external app.
  * `end_broadcast()`: stops the active live broadcast.

## 2FA and Challenge Handling

* **Two-Factor Authentication**: if Instagram requires 2FA, the bot moves into the 2FA state and asks for the code.
* **Challenge Requested**: if a challenge is triggered, you can either manually approve it via the IG app or website or attempt automatic resolution. The bot will guide you through the process.

## Detailed Steps

Here is a step-by-step tutorial to run the bot from scratch:

* Install Python 3.9+ if you haven't already.
* Clone or download the repository.
* (Optional) Create a virtual environment to isolate dependencies.
* Run `pip install -r requirements.txt` to install necessary libraries.
* Open `bot.py` (or any relevant file) and replace `TOKEN` with your BotFather token.
* Run the bot:

  python bot.py

  * If everything is correct, you'll see "Telegram Bot is running...."
* Open Telegram and find the bot:
  * If you forgot the bot's username, go back to BotFather or your notes.
  * Press Start in the chat.
* Log in to Instagram:
  * Choose "Login" from the menu.
  * Enter your Instagram username and password when prompted.
  * If 2FA or a challenge is required, follow the instructions in the chat.
* Start a live stream:
  * Once logged in, press "Start Live".
  * Provide a title for the live stream.
  * The bot responds with streaming information (stream URL and stream key).
  * You can use commands like "Live Info", "Stop Live", "Get Comments", etc.
* Stop or end the live stream:
  * Use "Stop Live" from the menu to terminate the broadcast.
* Saved Sessions:
  * After a successful Instagram login, the bot might ask to save the session (e.g., `username_session.json`) so future logins won't require the password.
  * If you choose to save it, the next time you type "Login", the bot will try to load that session first.

## Troubleshooting

* **Invalid Credentials**
  * If the username/password is incorrect, the bot displays "Error logging in, please try again."
* **2FA Code Not Accepted**
  * Check that the 2FA code hasn't expired.
  * Ensure you're using the 6-digit code from the authenticator app or the SMS code from IG.
* **Challenge Requested**
  * If the bot says "challenge requested", you can either manually resolve it via IG or attempt automatic resolution.
  * Sometimes the challenge may require phone/email verification or entering a code in the Instagram app.
* **Live Stream Creation Error**
  * If the bot fails to create the live stream, it displays "Error creating live stream" and presents the "Start Live" button again.
* **Live Stream Start Error**
  * If the live stream cannot be started, you'll see an error and the "Start Live" button again.
* **Session Issues**
  * If you save a session but it's somehow invalid, the bot might say "Session is invalid or expired." Then it removes the old session file and asks you to log in again.

## Contributing

Contributions are welcome! To contribute:

* Fork this repository.
* Create a new branch for the feature/fix.
* Commit and push to your fork.
* Create a pull request describing the changes.
