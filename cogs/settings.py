import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, button
from database.db import get_guild_settings, set_log_channel, get_excluded_roles
from utils.embeds import (
    success, error, info, send_log, has_admin_permission,
    format_role_list, LOTUS_COLOR, LOTUS_FOOTER
)


class SettingsView(View):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(timeout=120)
        self.interaction = interaction
        self.guild = interaction.guild
        self.message = None

    async def refresh_embed(self) -> discord.Embed:
        settings = await get_guild_settings(self.guild.id)
        start_role = None
        log_channel = None
        if settings:
            start_role = self.guild.get_role(int(settings["start_role_id"])) if settings["start_role_id"] else None
            log_channel = self.guild.get_channel(int(settings["log_channel_id"])) if settings["log_channel_id"] else None
        excluded_count = len(await get_excluded_roles(self.guild.id))

        embed = info("⚙️ Панель настроек LOTUS", "Нажми кнопки ниже для изменения настроек")
        embed.add_field(name="🎭 Роль входа", value=start_role.mention if start_role else "`Не установлена`", inline=True)
        embed.add_field(name="📋 Канал логов", value=log_channel.mention if log_channel else "`Не установлен`", inline=True)
        embed.add_field(name="🛡️ Исключаемых ролей", value=f"`{excluded_count}`", inline=True)
        return embed

    def _update_buttons(self, start_role, log_channel):
        # Кнопка удаления роли входа
        self.clear_items()
        self.add_item(Button(
            label="🎭 Установить роль входа",
            style=discord.ButtonStyle.primary,
            custom_id="set_startrole"
        ))
        self.add_item(Button(
            label="🗑️ Убрать роль входа",
            style=discord.ButtonStyle.danger,
            custom_id="clear_startrole",
            disabled=not start_role
        ))
        self.add_item(Button(
            label="📋 Установить канал логов",
            style=discord.ButtonStyle.primary,
            custom_id="set_logchannel"
        ))
        self.add_item(Button(
            label="🗑️ Убрать канал логов",
            style=discord.ButtonStyle.danger,
            custom_id="clear_logchannel",
            disabled=not log_channel
        ))
        self.add_item(Button(
            label="🛡️ Исключаемые роли",
            style=discord.ButtonStyle.secondary,
            custom_id="open_excluderoles"
        ))
        self.add_item(Button(
            label="🔄 Обновить",
            style=discord.ButtonStyle.secondary,
            custom_id="refresh"
        ))

    @button(label="🎭 Установить роль входа", style=discord.ButtonStyle.primary, custom_id="set_startrole", row=0)
    async def btn_set_startrole(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("❌ Не твоя панель!", ephemeral=True)
            return
        await interaction.response.send_message(
            "🎭 Напиши название роли или упомяни её (например: `@Участник`):",
            ephemeral=True
        )
        # Ждём ответа
        def check(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel_id
        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30)
            # Парсим роль
            role = None
            if msg.role_mentions:
                role = msg.role_mentions[0]
            else:
                role = discord.utils.get(self.guild.roles, name=msg.content)
            if not role:
                await msg.reply("❌ Роль не найдена", delete_after=5)
                return
            if role.position >= self.guild.me.top_role.position:
                await msg.reply("❌ Моя роль должна быть выше!", delete_after=5)
                return
            from database.db import set_start_role
            await set_start_role(self.guild.id, role.id)
            await msg.reply(f"✅ Роль входа установлена: {role.mention}", delete_after=5)
            settings = await get_guild_settings(self.guild.id)
            await send_log(self.guild, discord.Embed(
                color=LOTUS_COLOR, title="🎭 Роль входа изменена",
                description=f"**Админ:** {interaction.user.mention}\n**Новая роль:** {role.mention}"
            ).set_footer(text=LOTUS_FOOTER).set_timestamp(discord.utils.utcnow()),
                settings.get("log_channel_id") if settings else None
            )
            await self.refresh_panel(interaction)
        except:
            pass

    @button(label="🗑️ Убрать роль входа", style=discord.ButtonStyle.danger, custom_id="clear_startrole", row=0)
    async def btn_clear_startrole(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("❌ Не твоя панель!", ephemeral=True)
            return
        from database.db import set_start_role
        await set_start_role(self.guild.id, None)
        settings = await get_guild_settings(self.guild.id)
        await send_log(self.guild, discord.Embed(
            color=LOTUS_COLOR, title="🎭 Роль входа убрана",
            description=f"**Админ:** {interaction.user.mention}"
        ).set_footer(text=LOTUS_FOOTER).set_timestamp(discord.utils.utcnow()),
            settings.get("log_channel_id") if settings else None
        )
        await self.refresh_panel(interaction)

    @button(label="📋 Установить канал логов", style=discord.ButtonStyle.primary, custom_id="set_logchannel", row=1)
    async def btn_set_logchannel(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("❌ Не твоя панель!", ephemeral=True)
            return
        await interaction.response.send_message(
            "📋 Упомяни канал для логов (например: `#logs`):",
            ephemeral=True
        )
        def check(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel_id
        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30)
            channel = None
            if msg.channel_mentions:
                channel = msg.channel_mentions[0]
            else:
                channel = discord.utils.get(self.guild.text_channels, name=msg.content.lstrip("#"))
            if not channel or not isinstance(channel, discord.TextChannel):
                await msg.reply("❌ Канал не найден", delete_after=5)
                return
            perms = channel.permissions_for(self.guild.me)
            if not (perms.view_channel and perms.send_messages and perms.embed_links):
                await msg.reply("❌ У бота нет прав в этом канале!", delete_after=5)
                return
            await set_log_channel(self.guild.id, channel.id)
            await msg.reply(f"✅ Канал логов установлен: {channel.mention}", delete_after=5)
            settings = await get_guild_settings(self.guild.id)
            await send_log(self.guild, discord.Embed(
                color=LOTUS_COLOR, title="📋 Канал логов изменён",
                description=f"**Админ:** {interaction.user.mention}\n**Канал:** {channel.mention}"
            ).set_footer(text=LOTUS_FOOTER).set_timestamp(discord.utils.utcnow()),
                channel.id
            )
            await self.refresh_panel(interaction)
        except:
            pass

    @button(label="🗑️ Убрать канал логов", style=discord.ButtonStyle.danger, custom_id="clear_logchannel", row=1)
    async def btn_clear_logchannel(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("❌ Не твоя панель!", ephemeral=True)
            return
        await set_log_channel(self.guild.id, None)
        settings = await get_guild_settings(self.guild.id)
        await send_log(self.guild, discord.Embed(
            color=LOTUS_COLOR, title="📋 Канал логов убран",
            description=f"**Админ:** {interaction.user.mention}"
        ).set_footer(text=LOTUS_FOOTER).set_timestamp(discord.utils.utcnow()),
            settings.get("log_channel_id") if settings else None
        )
        await self.refresh_panel(interaction)

    @button(label="🛡️ Исключаемые роли", style=discord.ButtonStyle.secondary, custom_id="open_excluderoles", row=2)
    async def btn_open_excluderoles(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("❌ Не твоя панель!", ephemeral=True)
            return
        # Открываем панель excluderoles
        from cogs.excluderoles import ExcludeRolesView
        excluded = await get_excluded_roles(self.guild.id)
        embed = info("🛡️ Панель исключаемых ролей", "Выбери роли для добавления/удаления из исключений:")
        embed.add_field(name="Текущие исключения", value=format_role_list(excluded, self.guild) or "`Нет`", inline=False)
        embed.add_field(name="ℹ️ Как работает", value="Роли в этом списке **не сохраняются** при выходе и **не восстанавливаются** при входе.", inline=False)
        view = ExcludeRolesView(interaction, self.guild, excluded)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

    @button(label="🔄 Обновить", style=discord.ButtonStyle.secondary, custom_id="refresh", row=2)
    async def btn_refresh(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("❌ Не твоя панель!", ephemeral=True)
            return
        await self.refresh_panel(interaction)

    async def refresh_panel(self, interaction: discord.Interaction):
        settings = await get_guild_settings(self.guild.id)
        start_role = self.guild.get_role(int(settings["start_role_id"])) if settings and settings["start_role_id"] else None
        log_channel = self.guild.get_channel(int(settings["log_channel_id"])) if settings and settings["log_channel_id"] else None

        self._update_buttons(start_role, log_channel)
        embed = await self.refresh_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass


class SettingsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="settings", description="⚙️ Настройки бота LOTUS")
    @app_commands.describe(action="Действие", channel="Канал для логов")
    @app_commands.choices(action=[
        app_commands.Choice(name="logchannel 📋 Канал логов", value="logchannel"),
        app_commands.Choice(name="view 👁️ Посмотреть настройки", value="view"),
        app_commands.Choice(name="panel 🎮 Интерактивная панель", value="panel"),
    ])
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def settings(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        channel: discord.TextChannel = None
    ):
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=error("Нет прав", "Требуются права **Администратора** или **Управление сервером**"),
                ephemeral=True
            )
            return

        guild = interaction.guild
        action_val = action.value

        if action_val == "logchannel":
            if channel:
                perms = channel.permissions_for(guild.me)
                if not (perms.view_channel and perms.send_messages and perms.embed_links):
                    await interaction.response.send_message(
                        embed=error("Нет прав", "У бота нет прав на отправку сообщений в этот канал!"),
                        ephemeral=True
                    )
                    return
                await set_log_channel(guild.id, channel.id)
                await interaction.response.send_message(
                    embed=success("Канал логов установлен", f"Логи будут отправляться в {channel.mention}")
                )
            else:
                await set_log_channel(guild.id, None)
                await interaction.response.send_message(
                    embed=success("Логи отключены", "Логи больше не будут отправляться")
                )

        elif action_val == "view":
            settings = await get_guild_settings(guild.id)
            start_role = guild.get_role(int(settings["start_role_id"])) if settings and settings["start_role_id"] else None
            log_channel = guild.get_channel(int(settings["log_channel_id"])) if settings and settings["log_channel_id"] else None
            excluded_count = len(await get_excluded_roles(guild.id))

            embed = info("⚙️ Настройки LOTUS", "Текущая конфигурация бота")
            embed.add_field(name="🎭 Роль входа", value=start_role.mention if start_role else "`Не установлена`", inline=True)
            embed.add_field(name="📋 Канал логов", value=log_channel.mention if log_channel else "`Не установлен`", inline=True)
            embed.add_field(name="🛡️ Исключаемых ролей", value=f"`{excluded_count}`", inline=True)
            embed.add_field(name="🤖 Бот", value=self.bot.user.mention, inline=True)
            if settings:
                embed.add_field(name="📅 Обновлено", value=f"<t:{settings['updated_at']}:R>", inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action_val == "panel":
            view = SettingsView(interaction)
            view.bot = self.bot
            embed = await view.refresh_embed()
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            view.message = await interaction.original_response()


async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))