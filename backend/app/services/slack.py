from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.config import get_settings


def _client() -> WebClient:
    return WebClient(token=get_settings().slack_bot_token)


def post_digest(digest: dict, channel: str | None = None) -> str:
    """Post a digest summary to Slack. Returns the message timestamp."""
    settings = get_settings()
    target = channel or settings.slack_default_channel

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Team Pulse — {digest['date']}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{digest['actor']}*\n{digest['summary']}",
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"{digest['event_count']} GitHub event{'s' if digest['event_count'] != 1 else ''} · via Team Pulse",
                }
            ],
        },
    ]

    try:
        response = _client().chat_postMessage(channel=target, blocks=blocks, text=digest["summary"])
        return response["ts"]
    except SlackApiError as exc:
        raise RuntimeError(exc.response["error"]) from exc
