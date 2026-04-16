import disnake
from disnake.ext import commands
from datetime import datetime, timedelta, timezone
import humanize


class InfoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_utc_now(self):
        """Получение текущего UTC времени (совместимо со всеми версиями Python)"""
        return datetime.now(timezone.utc)

    @commands.slash_command(name="info", description="Информация о сервере или пользователе")
    async def info(
            self,
            inter: disnake.ApplicationCommandInteraction,
            user: disnake.User = commands.Param(default=None, description="Пользователь (опционально)")
    ):
        # Если указан пользователь - показываем инфо о нём
        if user:
            await self.user_info(inter, user)
        else:
            await self.server_info(inter)

    async def server_info(self, inter: disnake.ApplicationCommandInteraction):
        """Информация о сервере"""
        guild = inter.guild

        # Основная информация
        created_at = guild.created_at
        now_utc = self.get_utc_now()
        server_age = humanize.precisedelta(now_utc - created_at, format="%d")

        # Статистика участников
        total_members = guild.member_count
        humans = sum(1 for m in guild.members if not m.bot)
        bots = total_members - humans
        online = sum(1 for m in guild.members if m.status != disnake.Status.offline)

        # Каналы
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)

        # Количество банов
        try:
            ban_count = len([entry async for entry in guild.bans()])
        except:
            ban_count = "Нет прав"

        # Роли
        roles_count = len(guild.roles) - 1  # минус @everyone

        # Эмодзи и стикеры
        emojis_count = len(guild.emojis)
        stickers_count = len(guild.stickers)

        # Бусты
        boost_level = guild.premium_tier
        boost_count = guild.premium_subscription_count or 0

        # Создатель сервера
        owner = guild.owner

        # Безопасность
        verification_level = str(guild.verification_level).title()

        embed = disnake.Embed(
            title=f"📊 Информация о сервере: {guild.name}",
            color=disnake.Color.blue(),
            timestamp=now_utc
        )

        # Аватар сервера (если есть)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # Основная информация
        embed.add_field(name="🆔 ID сервера", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="👑 Создатель", value=owner.mention if owner else "Неизвестно", inline=True)
        embed.add_field(name="📅 Серверу", value=f"{server_age}", inline=True)

        # Статистика участников
        embed.add_field(name="👥 Всего участников", value=f"**{total_members}**", inline=True)
        embed.add_field(name="👤 Людей", value=f"{humans}", inline=True)
        embed.add_field(name="🤖 Ботов", value=f"{bots}", inline=True)
        embed.add_field(name="🟢 Онлайн", value=f"{online}", inline=True)
        embed.add_field(name="🔨 В бане", value=f"{ban_count}", inline=True)
        embed.add_field(name="📊 Статус", value=f"{online}/{total_members}", inline=True)

        # Каналы и роли
        embed.add_field(name="💬 Текстовых каналов", value=f"{text_channels}", inline=True)
        embed.add_field(name="🔊 Голосовых каналов", value=f"{voice_channels}", inline=True)
        embed.add_field(name="🎭 Ролей", value=f"{roles_count}", inline=True)

        # Бусты и эмодзи
        embed.add_field(name="🚀 Уровень буста", value=f"{boost_level} (⭐ {boost_count})", inline=True)
        embed.add_field(name="😀 Эмодзи", value=f"{emojis_count}", inline=True)
        embed.add_field(name="📎 Стикеры", value=f"{stickers_count}", inline=True)

        # Безопасность
        embed.add_field(name="🔒 Уровень верификации", value=verification_level, inline=True)

        # Дата создания
        embed.set_footer(text=f"Сервер создан: {created_at.strftime('%d.%m.%Y %H:%M')}")

        await inter.response.send_message(embed=embed)

    async def user_info(self, inter: disnake.ApplicationCommandInteraction, user: disnake.User):
        """Информация о пользователе"""
        guild = inter.guild
        member = guild.get_member(user.id)

        now_utc = self.get_utc_now()

        # Если пользователь не на сервере
        if not member:
            created_at = user.created_at
            account_age = humanize.precisedelta(now_utc - created_at, format="%d")

            embed = disnake.Embed(
                title=f"👤 Информация о пользователе: {user.name}",
                description="❌ Пользователь не находится на этом сервере",
                color=disnake.Color.red(),
                timestamp=now_utc
            )
            embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
            embed.add_field(name="🆔 ID", value=f"`{user.id}`", inline=True)
            embed.add_field(name="📅 Аккаунт создан", value=f"{created_at.strftime('%d.%m.%Y %H:%M')}\n({account_age})",
                            inline=True)
            await inter.response.send_message(embed=embed)
            return

        # Основная информация
        created_at = member.created_at
        joined_at = member.joined_at
        account_age = humanize.precisedelta(now_utc - created_at, format="%d")
        join_age = humanize.precisedelta(now_utc - joined_at, format="%d")

        # Статус
        status_emoji = {
            disnake.Status.online: "🟢",
            disnake.Status.idle: "🟡",
            disnake.Status.dnd: "🔴",
            disnake.Status.offline: "⚫"
        }
        status_text = {
            disnake.Status.online: "В сети",
            disnake.Status.idle: "Не активен",
            disnake.Status.dnd: "Не беспокоить",
            disnake.Status.offline: "Не в сети"
        }
        status_icon = status_emoji.get(member.status, "⚫")
        status_name = status_text.get(member.status, "Неизвестно")

        # Активность
        activity = None
        if member.activity:
            if member.activity.type == disnake.ActivityType.playing:
                activity = f"🎮 Играет: {member.activity.name}"
            elif member.activity.type == disnake.ActivityType.streaming:
                activity = f"📺 Стримит: {member.activity.name}"
            elif member.activity.type == disnake.ActivityType.listening:
                activity = f"🎵 Слушает: {member.activity.name}"
            elif member.activity.type == disnake.ActivityType.watching:
                activity = f"📺 Смотрит: {member.activity.name}"
            else:
                activity = f"📌 {member.activity.name}"

        # Роли (топ 10)
        roles = [role.mention for role in member.roles if role.name != "@everyone"]
        roles_display = ", ".join(roles[:10]) if roles else "Нет ролей"
        if len(roles) > 10:
            roles_display += f" и ещё {len(roles) - 10}"

        # Права (для администраторов/модераторов)
        is_admin = member.guild_permissions.administrator
        is_mod = member.guild_permissions.manage_messages or member.guild_permissions.kick_members

        # Информация о таймауте
        timeout_until = member.current_timeout
        if timeout_until:
            timeout_remaining = humanize.precisedelta(timeout_until - now_utc, format="%d")
            timeout_text = f"⏰ До {timeout_until.strftime('%d.%m.%Y %H:%M')} (осталось {timeout_remaining})"
        else:
            timeout_text = "Нет"

        embed = disnake.Embed(
            title=f"👤 Информация о пользователе: {member.display_name}",
            color=disnake.Color.green() if is_admin else (disnake.Color.orange() if is_mod else disnake.Color.blue()),
            timestamp=now_utc
        )

        # Аватар
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)

        # Основная информация
        embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="🏷 Имя", value=member.name, inline=True)
        embed.add_field(name="📛 Ник на сервере", value=member.display_name, inline=True)

        # Статус и активность
        embed.add_field(name="📊 Статус", value=f"{status_icon} {status_name}", inline=True)
        embed.add_field(name="🎮 Активность", value=activity or "Не активен", inline=True)

        # Время
        embed.add_field(name="📅 Аккаунт создан", value=f"{created_at.strftime('%d.%m.%Y %H:%M')}\n({account_age})",
                        inline=True)
        embed.add_field(name="📥 Присоединился", value=f"{joined_at.strftime('%d.%m.%Y %H:%M')}\n({join_age})",
                        inline=True)

        # Роли и права
        embed.add_field(name="🎭 Роли", value=roles_display[:1024] if len(roles_display) > 1024 else roles_display,
                        inline=False)
        embed.add_field(name="🔒 Администратор", value="✅ Да" if is_admin else "❌ Нет", inline=True)
        embed.add_field(name="🛡 Модератор", value="✅ Да" if is_mod else "❌ Нет", inline=True)
        embed.add_field(name="⏰ Таймаут", value=timeout_text, inline=True)

        # Дополнительная информация
        embed.add_field(name="🤖 Бот", value="✅ Да" if member.bot else "❌ Нет", inline=True)

        # Голосовой канал
        voice_state = member.voice
        if voice_state and voice_state.channel:
            voice_text = f"{voice_state.channel.mention}"
            if voice_state.mute:
                voice_text += " (🔇 Заглушен)"
            if voice_state.deaf:
                voice_text += " (🔇 Глухой)"
            embed.add_field(name="🎤 В голосовом канале", value=voice_text, inline=True)
        else:
            embed.add_field(name="🎤 В голосовом канале", value="❌ Нет", inline=True)

        # Бан (если есть)
        try:
            ban_entry = await guild.fetch_ban(user)
            embed.add_field(name="🔨 Забанен", value=f"Причина: {ban_entry.reason or 'Не указана'}", inline=False)
            embed.color = disnake.Color.red()
        except:
            pass

        embed.set_footer(text=f"Запросил: {inter.author.display_name}",
                         icon_url=inter.author.avatar.url if inter.author.avatar else None)

        await inter.response.send_message(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(InfoCog(bot))