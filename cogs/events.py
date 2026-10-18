import discord
from discord.ext import commands
from database.db import (
    get_guild_settings, get_excluded_roles, get_user_roles,
    save_user_roles, log_action
)
from utils.embeds import send_log, LOTUS_COLOR, LOTUS_FOOTER


class EventsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        settings = await get_guild_settings(guild.id)

        # 1. Выдача роли входа
        if settings and settings["start_role_id"]:
            role = guild.get_role(int(settings["start_role_id"]))
            if role and role.is_assignable():
                try:
                    await member.add_roles(role, reason="LOTUS: Роль входа")
                    await log_action(guild.id, member.id, "START_ROLE_ADDED", role.id, "Auto-assigned on join")
                except discord.HTTPException:
                    pass

        # 2. Восстановление сохранённых ролей (кроме исключённых)
        saved_roles = await get_user_roles(guild.id, member.id)
        excluded_roles = await get_excluded_roles(guild.id)

        roles_to_restore = [rid for rid in saved_roles if rid not in excluded_roles]
        valid_roles = [
            guild.get_role(rid) for rid in roles_to_restore
            if guild.get_role(rid) and guild.get_role(rid).is_assignable()
            and guild.get_role(rid).position < guild.me.top_role.position
        ]

        if valid_roles:
            try:
                await member.add_roles(*valid_roles, reason="LOTUS: Восстановление ролей")
                for role in valid_roles:
                    await log_action(guild.id, member.id, "ROLE_RESTORED", role.id, "Restored on rejoin")
                await send_log(guild, discord.Embed(
                    color=LOTUS_COLOR,
                    title="🔄 Роли восстановлены",
                    description=f"**Участник:** {member.mention} (`{member.id}`)\n**Восстановлено ролей:** {len(valid_roles)}"
                ).add_field(name="Роли", value=", ".join(r.mention for r in valid_roles), inline=False)
                .set_footer(text=LOTUS_FOOTER).set_timestamp(discord.utils.utcnow()),
                    settings.get("log_channel_id") if settings else None
                )
            except discord.HTTPException:
                pass

        # 3. Лог входа
        await send_log(guild, discord.Embed(
            color=discord.Color.green(),
            title="➕ Участник присоединился",
            description=f"**Участник:** {member.mention} (`{member.id}`)\n**Аккаунт создан:** <t:{int(member.created_at.timestamp())}:R>"
        ).set_thumbnail(url=member.display_avatar.url)
        .set_footer(text=LOTUS_FOOTER).set_timestamp(discord.utils.utcnow()),
            settings.get("log_channel_id") if settings else None
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        settings = await get_guild_settings(guild.id)
        excluded_roles = await get_excluded_roles(guild.id)

        # Сохраняем роли (кроме @everyone и исключённых)
        roles_to_save = [
            r.id for r in member.roles
            if r.id != guild.id and r.id not in excluded_roles
        ]

        if roles_to_save:
            await save_user_roles(guild.id, member.id, roles_to_save)
            for role_id in roles_to_save:
                await log_action(guild.id, member.id, "ROLE_SAVED", role_id, "Saved on leave")

        # Лог выхода
        saved_names = [guild.get_role(rid).name for rid in roles_to_save if guild.get_role(rid)]
        excluded_names = [guild.get_role(rid).name for rid in excluded_roles if guild.get_role(rid)]

        await send_log(guild, discord.Embed(
            color=discord.Color.red(),
            title="➖ Участник покинул сервер",
            description=(
                f"**Участник:** {member} (`{member.id}`)\n"
                f"**Было ролей:** {len(member.roles) - 1}\n"
                f"**Сохранено ролей:** {len(roles_to_save)}"
            )
        ).add_field(
            name="Сохранённые роли",
            value=", ".join(f"`{n}`" for n in saved_names) if saved_names else "`Нет`",
            inline=False
        ).add_field(
            name="Исключённые роли (не сохранены)",
            value=", ".join(f"`{n}`" for n in excluded_names) if excluded_names else "`Нет`",
            inline=False
        ).set_thumbnail(url=member.display_avatar.url)
        .set_footer(text=LOTUS_FOOTER).set_timestamp(discord.utils.utcnow()),
            settings.get("log_channel_id") if settings else None
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(EventsCog(bot))