"""Value objects for the notifications domain."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SlackChannel:
    """Value object representing a Slack channel.

    Attributes:
        name: The channel name without the # prefix
    """

    name: str

    def __post_init__(self) -> None:
        """Validate the channel name."""
        if not self.name:
            raise ValueError("Channel name cannot be empty")

        if self.name.startswith("#"):
            raise ValueError(
                "Channel name should not include the # prefix. "
                f"Use '{self.name[1:]}' instead of '{self.name}'"
            )

        # Slack channel names can only contain lowercase letters, numbers, hyphens, and underscores
        if not all(c.islower() or c.isdigit() or c in "-_" for c in self.name):
            raise ValueError(
                f"Invalid channel name '{self.name}'. "
                "Channel names can only contain lowercase letters, numbers, "
                "hyphens, and underscores"
            )


@dataclass(frozen=True)
class SlackMessage:
    """Value object representing a message to send to Slack.

    Attributes:
        text: The message text in markdown format
        title: Optional title for the message
    """

    text: str
    title: str | None = None

    def __post_init__(self) -> None:
        """Validate the message."""
        if not self.text:
            raise ValueError("Message text cannot be empty")
