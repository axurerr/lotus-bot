import discord
from discord import app_commands
from discord.ext import commands
from database.db import get_guild_settings, set_start_role, log_action
from utils.embeds import success, error, send_log, has_admin_permission, LOTUS_COLOR, LOTUS_FOOTER


class SetStartRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setstartrole", description="🎭 Установить роль, которую получает каждый новый участник")
    @app_commands.describe(role="Роль для выдачи при входе (оставь пустым для отключения)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setstartrole(self, interaction: discord.Interaction, role: discord.Role = None):
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=error("Нет прав", "Требуются права **Администратора** или **Управление сервером**"),
                ephemeral=True
            )
            return

        guild = interaction.guild
        bot_member = guild.me

        if role:
            if role.position >= bot_member.top_role.position:
                await interaction.response.send_message(
                    embed=error("Ошибка иерархии", "Моя роль должна быть выше указанной роли!"),
                    ephemeral=True
                )
                return

            set_start_role(guild.id, role.id)

            embed = success(
                "Роль входа установлена",
                f"Теперь каждый новый участник будет получать роль {role.mention} при заходе на сервер."
            )
            embed.add_field(name="Роль", value=f"{role.mention} (`{role.id}`)", inline=True)

            await interaction.response.send_message(embed=embed)

            await send_log(guild, discord.Embed(
                color=LOTUS_COLOR,
                title="🎭 Роль входа изменена",
                description=f"**Администратор:** {interaction.user.mention}\n**Новая роль:** {role.mention}"
            ).set_footer(text=LOTUS_FOOTER).set_timestamp(discord.utils.utcnow()), 
                (await get_guild_settings(guild.id)).get("log_channel_id") if await get_guild_settings(guild.id) else None
            )
        else:
            set_start_role(guild.id, None)

            embed = success(
                "Роль входа отключена",
                "Новые участники больше не будут автоматически получать роль при входе."
            )
            await interaction.response.send_message(embed=embed)

            await send_log(guild, discord.Embed(
                color=LOTUS_COLOR,
                title="🎭 Роль входа отключена",
                description=f"**Администратор:** {interaction.user.mention}"
            ).set_footer(text=LOTUS_FOOTER).set_timestamp(discord.utils.utcnow()),
                (await get_guild_settings(guild.id)).get("log_channel_id") if await get_guild_settings(guild.id) else None
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(SetStartRole(bot))