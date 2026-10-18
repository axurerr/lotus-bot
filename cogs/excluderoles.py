import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Button
from database.db import (
    get_excluded_roles, add_excluded_role, remove_excluded_role,
    clear_excluded_roles, get_guild_settings
)
from utils.embeds import (
    success, error, info, send_log, has_admin_permission,
    format_role_list, LOTUS_COLOR, LOTUS_FOOTER
)


class ExcludeRolesView(View):
    def __init__(self, interaction: discord.Interaction, guild: discord.Guild, excluded: list[int]):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.guild = guild
        self.excluded = excluded.copy()
        self.message = None
        self._build_select()

    def _build_select(self):
        # Очищаем старые элементы
        self.clear_items()

        # Получаем доступные роли (бот выше, не managed, не @everyone)
        bot_top = self.guild.me.top_role.position
        available = [
            r for r in self.guild.roles.values()
            if r.id != self.guild.id and not r.managed and r.position < bot_top
        ]
        available.sort(key=lambda r: r.position, reverse=True)
        available = available[:25]  # Discord limit

        options = []
        for role in available:
            is_excluded = role.id in self.excluded
            options.append(discord.SelectOption(
                label=role.name[:100],
                value=str(role.id),
                description=("✅ В исключениях" if is_excluded else "➕ Добавить в исключения")[:100],
                default=is_excluded
            ))

        if not options:
            # Добавляем пустой placeholder если нет ролей
            self.add_item(Select(
                placeholder="Нет доступных ролей для управления",
                options=[discord.SelectOption(label="...", value="none")],
                disabled=True
            ))
            return

        select = Select(
            placeholder="Выбери роли для переключения исключения...",
            min_values=1,
            max_values=min(len(options), 25),
            options=options,
            custom_id="excluderoles_select"
        )
        select.callback = self.on_select
        self.add_item(select)

    async def on_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("❌ Это не твоя панель!", ephemeral=True)
            return

        selected_ids = [int(v) for v in interaction.data["values"]]
        added = 0
        removed = 0

        for role_id in selected_ids:
            if role_id in self.excluded:
                if await remove_excluded_role(self.guild.id, role_id):
                    self.excluded.remove(role_id)
                    removed += 1
            else:
                if await add_excluded_role(self.guild.id, role_id):
                    self.excluded.append(role_id)
                    added += 1

        # Перестраиваем селект
        self._build_select()

        embed = info("🛡️ Панель исключаемых ролей", "Выбери роли для добавления/удаления из исключений:")
        embed.add_field(name="Текущие исключения", value=format_role_list(self.excluded, self.guild) or "`Нет`", inline=False)
        result_text = ""
        if added:
            result_text += f"✅ Добавлено: {added}\n"
        if removed:
            result_text += f"❌ Удалено: {removed}"
        if result_text:
            embed.add_field(name="Результат", value=result_text, inline=False)
        embed.add_field(name="ℹ️ Как работает", value="Роли в этом списке **не сохраняются** при выходе и **не восстанавливаются** при входе.", inline=False)

        await interaction.response.edit_message(embed=embed, view=self)

        if added > 0 or removed > 0:
            settings = await get_guild_settings(self.guild.id)
            await send_log(self.guild, discord.Embed(
                color=LOTUS_COLOR,
                title="🛡️ Исключения изменены через панель",
                description=f"**Админ:** {interaction.user.mention}\n✅ Добавлено: {added}\n❌ Удалено: {removed}"
            ).set_footer(text=LOTUS_FOOTER).set_timestamp(discord.utils.utcnow()),
                settings.get("log_channel_id") if settings else None
            )

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass


class ExcludeRolesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="excluderoles", description="🛡️ Управление исключаемыми ролями (не сохраняются при выходе)")
    @app_commands.describe(action="Действие", role="Роль")
    @app_commands.choices(action=[
        app_commands.Choice(name="add ➕ Добавить", value="add"),
        app_commands.Choice(name="remove ➖ Удалить", value="remove"),
        app_commands.Choice(name="list 📋 Список", value="list"),
        app_commands.Choice(name="clear 🗑️ Очистить всё", value="clear"),
        app_commands.Choice(name="panel 🎮 Интерактивная панель", value="panel"),
    ])
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def excluderoles(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        role: discord.Role = None
    ):
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=error("Нет прав", "Требуются права **Администратора** или **Управление сервером**"),
                ephemeral=True
            )
            return

        guild = interaction.guild
        action_val = action.value

        if action_val == "add":
            if not role:
                await interaction.response.send_message(embed=error("Ошибка", "Укажи роль!"), ephemeral=True)
                return
            excluded = await get_excluded_roles(guild.id)
            if role.id in excluded:
                await interaction.response.send_message(
                    embed=error("Уже существует", f"Роль {role.mention} уже в исключениях"),
                    ephemeral=True
                )
                return
            await add_excluded_role(guild.id, role.id)
            await interaction.response.send_message(
                embed=success("Роль добавлена", f"Роль {role.mention} теперь не будет сохраняться при выходе")
            )
            settings = await get_guild_settings(guild.id)
            await send_log(guild, discord.Embed(
                color=LOTUS_COLOR,
                title="🛡️ Исключение добавлено",
                description=f"**Админ:** {interaction.user.mention}\n**Роль:** {role.mention}"
            ).set_footer(text=LOTUS_FOOTER).set_timestamp(discord.utils.utcnow()),
                settings.get("log_channel_id") if settings else None
            )

        elif action_val == "remove":
            if not role:
                await interaction.response.send_message(embed=error("Ошибка", "Укажи роль!"), ephemeral=True)
                return
            removed = await remove_excluded_role(guild.id, role.id)
            if not removed:
                await interaction.response.send_message(
                    embed=error("Не найдено", f"Роль {role.mention} не была в исключениях"),
                    ephemeral=True
                )
                return
            await interaction.response.send_message(
                embed=success("Роль удалена", f"Роль {role.mention} больше не в исключениях")
            )
            settings = await get_guild_settings(guild.id)
            await send_log(guild, discord.Embed(
                color=LOTUS_COLOR,
                title="🛡️ Исключение удалено",
                description=f"**Админ:** {interaction.user.mention}\n**Роль:** {role.mention}"
            ).set_footer(text=LOTUS_FOOTER).set_timestamp(discord.utils.utcnow()),
                settings.get("log_channel_id") if settings else None
            )

        elif action_val == "list":
            excluded = await get_excluded_roles(guild.id)
            embed = info("🛡️ Исключаемые роли", format_role_list(excluded, guild) or "Список пуст.")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action_val == "clear":
            count = await clear_excluded_roles(guild.id)
            await interaction.response.send_message(
                embed=success("Очищено", f"Удалено {count} исключаемых ролей")
            )
            settings = await get_guild_settings(guild.id)
            await send_log(guild, discord.Embed(
                color=LOTUS_COLOR,
                title="🛡️ Исключения очищены",
                description=f"**Админ:** {interaction.user.mention}\n**Удалено:** {count} ролей"
            ).set_footer(text=LOTUS_FOOTER).set_timestamp(discord.utils.utcnow()),
                settings.get("log_channel_id") if settings else None
            )

        elif action_val == "panel":
            excluded = await get_excluded_roles(guild.id)
            embed = info("🛡️ Панель исключаемых ролей", "Выбери роли для добавления/удаления из исключений:")
            embed.add_field(name="Текущие исключения", value=format_role_list(excluded, guild) or "`Нет`", inline=False)
            embed.add_field(name="ℹ️ Как работает", value="Роли в этом списке **не сохраняются** при выходе и **не восстанавливаются** при входе.", inline=False)

            view = ExcludeRolesView(interaction, guild, excluded)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            view.message = await interaction.original_response()


async def setup(bot: commands.Bot):
    await bot.add_cog(ExcludeRolesCog(bot))