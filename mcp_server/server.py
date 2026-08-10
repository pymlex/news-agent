"""MCP server exposing the trusted-media builder skill."""

from mcp.server import MCPServer


from agent.skills.trusted_media import build_trusted_media, trusted_media_markdown
from utils.db import db


mcp = MCPServer("news-agent-trusted-media")


@mcp.tool()
def create_trusted_media_list(
    preferences: str,
    profile_name: str = "default",
    region: str = "",
) -> str:
    """Create a weighted trusted media list from natural language preferences.

    Prefer qualified domain experts and established outlets over social media
    coaches. The list is stored under the given profile and later used to
    colour provenance graphs and rank sources.

    Args:
        preferences: Topics, regions and preferred experts in natural language.
        profile_name: Profile that owns the trusted list.
        region: Optional geographic focus.

    Returns:
        Markdown table of trusted outlets.
    """

    outlets = build_trusted_media(
        preferences=preferences,
        profile_name=profile_name,
        region=region,
    )
    return trusted_media_markdown(outlets, profile_name)


@mcp.tool()
def show_trusted_media(profile_name: str = "default") -> str:
    """Return the trusted media table saved for a profile."""

    outlets = db.list_trusted_media(profile_name)
    if not outlets:
        return "Trusted media list is empty for this profile."
    return trusted_media_markdown(outlets, profile_name)


def main() -> None:
    """Run the MCP server over stdio."""

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
