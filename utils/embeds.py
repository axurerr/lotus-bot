import discord
from discord import Embed, Color
from typing import Optional

LOTUS_COLOR = 0x9b59b6
LOTUS_FOOTER = "LOTUS • Role Management System"


def create_embed(
    title: str = None,
    description: str = None,
    color: int = LOTUS_COLOR,
    fields: list[dict] = None,
    footer: str = LOTUS_FOOTER,
    thumbnail: str = None,
    image: str = None
) -> Embed:
    embed = Embed(color=color)
    if title:
        embed.title = title
    if description:
        embed.description = description
    if fields:
        for f in fields:
            embed.add_field(name=f["name"], value=f["value"], inline=f.get("inline", False))
    if footer:
        embed.set_footer(text=footer)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if image:
        embed.set_image(url=image)
    return embed


def success(title: str, description: str) -> Embed:
    return create_embed(title=f"✅ {title}", description=description, color=Color.green())


def error(title: str, description: str) -> Embed:
    return create_embed(title=f"❌ {title}", description=description, color=Color.red())


def warning(title: str, description: str) -> Embed:
    return create_embed(title=f"⚠️ {title}", description=description, color=Color.yellow())


def info(title: str, description: str) -> Embed:
    return create_embed(title=f"ℹ️ {title}", description=description, color=Color.blue())


async def send_log(guild: discord.Guild, embed: Embed, log_channel_id: int | None):
    if not log_channel_id:
        return
    channel = guild.get_channel(log_channel_id)
    if isinstance(channel, discord.TextChannel):
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass


def has_admin_permission(member: discord.Member) -> bool:
    return member.guild_permissions.administrator or member.guild_permissions.manage_guild


def format_role_list(role_ids: list[int], guild: discord.Guild) -> str:
    if not role_ids:
        return "`Нет ролей`"
    lines = []
    for rid in role_ids:
        role = guild.get_role(rid)
        if role:
            lines.append(f"`{role.name}` ({role.mention})")
        else:
            lines.append(f"`{rid}` (не найдена)")
    return "\n".join(lines)


def chunk_list(lst: list, size: int) -> list[list]:
    return [lst[i:i + size] for i in range(0, len(lst), size)]