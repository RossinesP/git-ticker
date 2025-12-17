"""Service for orchestrating notification sending."""

from git_ticker.notifications.domain.value_objects import SlackChannel, SlackMessage
from git_ticker.notifications.repositories.implementations import (
    SlackNotificationRepositoryImpl,
)


class NotificationService:
    """Service for orchestrating notification operations."""

    def __init__(self, slack_repository: SlackNotificationRepositoryImpl) -> None:
        """Initialize the notification service.

        Args:
            slack_repository: Repository for sending Slack notifications
        """
        self._slack_repository = slack_repository

    def send_summary_to_slack(self, summary: str, channel_name: str) -> None:
        """Send a commit summary to a Slack channel.

        Args:
            summary: The markdown summary to send
            channel_name: The name of the Slack channel (without # prefix)

        Raises:
            ValueError: If the channel name or summary is invalid, or if Slack
                token is not configured
            RuntimeError: If there's an error sending the message to Slack
        """
        # Create value objects
        channel = SlackChannel(name=channel_name)
        message = SlackMessage(text=summary, title="📝 GitLab Ticker - Development Branch Summary")

        # Send the message
        success = self._slack_repository.send_message(channel, message)

        if not success:
            raise RuntimeError("Failed to send message to Slack (API returned failure)")
