"""DiscordClient — sends messages and images to Discord channels or DMs."""
from __future__ import annotations

import textwrap

import discord


class DiscordClient(discord.Client):
    """
    Async Discord client built on ``discord.py``.

    Supports:
      - Sending text messages to a named channel (auto-chunked to 2 000 chars).
      - Sending image attachments to a channel.
      - Sending private DMs (text + optional image) by Discord user ID.

    Usage::

        DiscordClient(
            token="BOT_TOKEN",
            channel_name="echoes-weekly",
            message="Hello team!",
        )

    The constructor is **blocking** — it starts the event loop, runs
    ``on_ready``, and exits cleanly.
    """

    def __init__(
        self,
        token: str,
        channel_name: str = "",
        message: str = "",
        image_path: str = "",
        user_id: int = 0,
    ):
        """
        Args:
            token: Discord bot token.
            channel_name: Text channel name to send the message/image to.
            message: Text message to send.
            image_path: Local file path of the image to attach (optional).
            user_id: Discord user ID for private DMs (optional).
        """
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        super().__init__(intents=intents)

        self._token = token
        self.channel_name = channel_name
        self.message = message
        self.image_path = image_path
        self.user_id = user_id

        self.run(self._token)

    # ------------------------------------------------------------------
    # Event handler
    # ------------------------------------------------------------------

    async def on_ready(self) -> None:
        """Dispatch all queued actions once the bot is connected."""
        print(f"Discord bot connected as {self.user}")

        if self.channel_name and self.message:
            await self._send_text(self.channel_name, self.message)

        if self.channel_name and self.image_path:
            await self._send_image(self.channel_name, self.image_path)

        if self.user_id and not self.image_path and self.message:
            await self._dm_text(self.user_id, self.message)

        if self.user_id and self.image_path and self.message:
            await self._dm_text_and_image(self.user_id, self.message, self.image_path)

        await self.close()

    # ------------------------------------------------------------------
    # Channel helpers
    # ------------------------------------------------------------------

    async def _get_channel(self, name: str) -> discord.TextChannel | None:
        """Find a text channel by name across all guilds."""
        for guild in self.guilds:
            channel = discord.utils.get(guild.text_channels, name=name)
            if channel:
                return channel
        print(f"Channel '{name}' not found.")
        return None

    async def _send_text(self, channel_name: str, message: str) -> None:
        """Send a text message, chunked to Discord's 2 000-character limit."""
        channel = await self._get_channel(channel_name)
        if not channel:
            return
        chunks = textwrap.wrap(message, width=2000, break_long_words=False, replace_whitespace=False)
        for i, chunk in enumerate(chunks, 1):
            await channel.send(chunk)
            print(f"Sent chunk {i}/{len(chunks)} → #{channel.name}")

    async def _send_image(self, channel_name: str, image_path: str) -> None:
        """Send an image file to a channel."""
        channel = await self._get_channel(channel_name)
        if not channel:
            return
        try:
            with open(image_path, "rb") as f:
                await channel.send(file=discord.File(f))
                print(f"Image sent → #{channel.name}")
        except OSError as exc:
            print(f"Failed to send image: {exc}")

    # ------------------------------------------------------------------
    # DM helpers
    # ------------------------------------------------------------------

    async def _dm_text(self, user_id: int, message: str) -> None:
        """Send a private text DM to *user_id*, chunked if necessary."""
        try:
            user = await self.fetch_user(user_id)
            chunks = textwrap.wrap(message, width=2000, break_long_words=False, replace_whitespace=False)
            for chunk in chunks:
                await user.send(chunk)
            print(f"DM sent → user {user_id}")
        except Exception as exc:
            print(f"DM failed for user {user_id}: {exc}")

    async def _dm_text_and_image(self, user_id: int, message: str, image_path: str) -> None:
        """Send a text message with an image attachment to a user via DM."""
        try:
            user = await self.fetch_user(user_id)
            with open(image_path, "rb") as f:
                await user.send(message, file=discord.File(f))
            print(f"DM with image sent → user {user_id}")
        except Exception as exc:
            print(f"DM with image failed for user {user_id}: {exc}")
