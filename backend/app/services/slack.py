import logging

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.config import get_settings

logger = logging.getLogger(__name__)

# slack_sdk's WebClient re-raises raw connection/timeout failures (DNS,
# refused connection, TLS, socket timeout) as-is rather than wrapping them
# in a SlackApiError — all of urllib.error.URLError, socket.timeout /
# TimeoutError, and ConnectionError subclass OSError, so catching that
# alongside SlackApiError covers "Slack said no" and "couldn't reach Slack
# at all" without also swallowing unrelated bugs (bare Exception would).
_CONNECTION_ERRORS = OSError


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
        logger.error("Slack API error posting digest for %s: %s", digest.get("actor"), exc.response["error"])
        raise RuntimeError(exc.response["error"]) from exc
    except _CONNECTION_ERRORS as exc:
        logger.error("Slack connection error posting digest for %s: %s", digest.get("actor"), exc)
        raise RuntimeError(f"could not reach Slack: {exc}") from exc


def post_team_digest(team_digest: dict, channel: str | None = None) -> str:
    """Post a team-level digest to Slack. Returns the message timestamp."""
    settings = get_settings()
    target = channel or settings.slack_default_channel

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Team Pulse — {team_digest['date']} — Team Standup",
            },
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": team_digest["team_summary"]},
        },
        {"type": "divider"},
    ]

    for actor in team_digest["actors"]:
        count = actor["event_count"]
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{actor['actor']}* · {count} event{'s' if count != 1 else ''}\n"
                    f"{actor['summary']}"
                ),
            },
        })

    attention = team_digest.get("attention") or []
    if attention:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*⚠ Attention*"},
        })
        for item in attention:
            label = "Thrashing" if item["state"] == "THRASHING" else "Silent & stuck"
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{item['actor']}* — {label}\n{item['evidence']}",
                },
            })

    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": (
                    f"{team_digest['actor_count']} contributor{'s' if team_digest['actor_count'] != 1 else ''} · "
                    f"{team_digest['event_count']} events · via Team Pulse"
                ),
            }
        ],
    })

    try:
        response = _client().chat_postMessage(
            channel=target, blocks=blocks, text=team_digest["team_summary"]
        )
        return response["ts"]
    except SlackApiError as exc:
        logger.error("Slack API error posting team digest: %s", exc.response["error"])
        raise RuntimeError(exc.response["error"]) from exc
    except _CONNECTION_ERRORS as exc:
        logger.error("Slack connection error posting team digest: %s", exc)
        raise RuntimeError(f"could not reach Slack: {exc}") from exc
