"""Concrete implementations of notification repositories."""

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from gitlab_ticker.notifications.domain.value_objects import SlackChannel, SlackMessage


class SlackNotificationRepositoryImpl:
    """Implementation of Slack notification repository using Slack SDK."""

    def __init__(self, token: str) -> None:
        """Initialize the Slack client with token.

        Args:
            token: The Slack Bot User OAuth Token

        Raises:
            ValueError: If token is empty or None
        """
        if not token:
            raise ValueError(
                "Slack token is required. "
                "Get your token from https://api.slack.com/apps"
            )

        self._client = WebClient(token=token)

    def send_message(self, channel: SlackChannel, message: SlackMessage) -> bool:
        """Send a message to a Slack channel.

        Args:
            channel: The Slack channel to send the message to
            message: The message to send

        Returns:
            True if the message was sent successfully, False otherwise

        Raises:
            RuntimeError: If there's an error communicating with Slack
        """
        try:
            # Build the message blocks for better formatting
            blocks = []

            if message.title:
                blocks.append(
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": message.title, "emoji": True},
                    }
                )

            # Split text into chunks if it's too long (Slack has a 3000 char limit per block)
            MAX_BLOCK_SIZE = 2900  # Leave some margin
            text_chunks = self._split_text(message.text, MAX_BLOCK_SIZE)

            for chunk in text_chunks:
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": chunk}})

            # Send the message
            response = self._client.chat_postMessage(
                channel=channel.name,
                blocks=blocks,
                text=message.title or "GitLab Ticker Summary",  # Fallback for notifications
            )

            # Extract the 'ok' field from response and ensure it's a boolean
            ok_value = response.get("ok", False)
            return bool(ok_value)

        except SlackApiError as e:
            error_msg = e.response.get("error", "unknown error")
            if error_msg == "channel_not_found":
                raise RuntimeError(
                    f"Channel '{channel.name}' not found. "
                    "Make sure the bot is invited to the channel."
                ) from e
            elif error_msg == "not_in_channel":
                raise RuntimeError(
                    f"Bot is not a member of channel '{channel.name}'. "
                    "Please invite the bot to the channel first."
                ) from e
            elif error_msg == "invalid_auth":
                raise RuntimeError(
                    "Invalid Slack token. Please check your token configuration."
                ) from e
            else:
                raise RuntimeError(f"Slack API error: {error_msg}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to send Slack message: {e}") from e

    def _split_text(self, text: str, max_size: int) -> list[str]:
        """Split text into chunks that fit within Slack's block size limit.

        Args:
            text: Text to split
            max_size: Maximum size per chunk

        Returns:
            List of text chunks
        """
        if len(text) <= max_size:
            return [text]

        chunks = []
        current_chunk = ""

        # Split by lines to avoid breaking in the middle of a line
        lines = text.split("\n")

        for line in lines:
            # If adding this line would exceed the limit, save current chunk and start new one
            if len(current_chunk) + len(line) + 1 > max_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                # If a single line is too long, split it by words
                if len(line) > max_size:
                    words = line.split(" ")
                    for word in words:
                        if len(current_chunk) + len(word) + 1 > max_size:
                            if current_chunk:
                                chunks.append(current_chunk)
                                current_chunk = word
                            else:
                                # Single word is too long, just truncate it
                                chunks.append(word[:max_size])
                        else:
                            current_chunk += " " + word if current_chunk else word
                else:
                    current_chunk = line
            else:
                current_chunk += "\n" + line if current_chunk else line

        if current_chunk:
            chunks.append(current_chunk)

        return chunks
