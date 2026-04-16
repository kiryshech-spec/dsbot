import disnake
from disnake.ext import commands
from datetime import datetime, timedelta

# ID канала для логов
LOG_CHANNEL_ID = 1492883517573566624

# ID роли, которая может использовать модерационные команды
MODERATOR_ROLE_ID = 1413460782179553280


def has_mod_perms(inter: disnake.ApplicationCommandInteraction) -> bool:
    """Проверка прав модератора"""
    if inter.author.guild_permissions.administrator:
        return True
    if MODERATOR_ROLE_ID:
        role = inter.guild.get_role(MODERATOR_ROLE_ID)
        if role and role in inter.author.roles:
            return True
    return False


class ModerationCog(commands.Cog):
    """Ког для модерационных команд"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def check_permissions(self, inter: disnake.ApplicationCommandInteraction) -> bool:
        """Проверка прав перед выполнением команды"""
        if not has_mod_perms(inter):
            return False
        return True

    async def send_log(self, guild: disnake.Guild, embed: disnake.Embed):
        """Отправляет лог в указанный канал"""
        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(embed=embed)

    # ========== KICK ==========
    @commands.slash_command(name="kick", description="Кикнуть пользователя с сервера")
    async def kick(
        self,
        inter: disnake.ApplicationCommandInteraction,
        user: disnake.Member,
        reason: str = "Причина не указана"
    ):
        if not self.check_permissions(inter):
            await inter.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)
            return

        if user == inter.author:
            await inter.response.send_message("❌ Вы не можете кикнуть самого себя!", ephemeral=True)
            return

        if user.guild_permissions.administrator:
            await inter.response.send_message("❌ Нельзя кикнуть администратора!", ephemeral=True)
            return

        try:
            embed = disnake.Embed(
                title="👢 Кик пользователя",
                description=f"**{user.mention}** был кикнут",
                color=disnake.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="👮 Модератор", value=inter.author.mention, inline=True)
            embed.add_field(name="📝 Причина", value=reason, inline=True)

            await user.kick(reason=reason)
            await inter.response.send_message(embed=embed)

            # Отправляем лог
            await self.send_log(inter.guild, embed)

            # Отправляем уведомление в ЛС
            try:
                dm_embed = disnake.Embed(
                    title="Вы были кикнуты",
                    description=f"Сервер: **{inter.guild.name}**\nПричина: {reason}",
                    color=disnake.Color.red()
                )
                await user.send(embed=dm_embed)
            except:
                pass

        except Exception as e:
            await inter.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

    # ========== BAN ==========
    @commands.slash_command(name="ban", description="Забанить пользователя")
    async def ban(
        self,
        inter: disnake.ApplicationCommandInteraction,
        user: disnake.User,
        reason: str = "Причина не указана",
        delete_days: int = commands.Param(default=1, ge=0, le=7, description="Дней истории сообщений для удаления (0-7)")
    ):
        if not self.check_permissions(inter):
            await inter.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)
            return

        if user == inter.author:
            await inter.response.send_message("❌ Вы не можете забанить самого себя!", ephemeral=True)
            return

        member = inter.guild.get_member(user.id)
        if member and member.guild_permissions.administrator:
            await inter.response.send_message("❌ Нельзя забанить администратора!", ephemeral=True)
            return

        try:
            embed = disnake.Embed(
                title="🔨 Бан пользователя",
                description=f"**{user.mention}** был забанен",
                color=disnake.Color.dark_red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="👮 Модератор", value=inter.author.mention, inline=True)
            embed.add_field(name="📝 Причина", value=reason, inline=True)
            embed.add_field(name="🗑 Удалено сообщений за", value=f"{delete_days} дней", inline=True)

            await inter.guild.ban(user, reason=reason, delete_message_days=delete_days)
            await inter.response.send_message(embed=embed)

            # Отправляем лог
            await self.send_log(inter.guild, embed)

            # Отправляем уведомление в ЛС
            try:
                dm_embed = disnake.Embed(
                    title="Вы были забанены",
                    description=f"Сервер: **{inter.guild.name}**\nПричина: {reason}",
                    color=disnake.Color.dark_red()
                )
                await user.send(embed=dm_embed)
            except:
                pass

        except Exception as e:
            await inter.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

    # ========== UNBAN ==========
    @commands.slash_command(name="unban", description="Разбанить пользователя")
    async def unban(
        self,
        inter: disnake.ApplicationCommandInteraction,
        user_id: str = commands.Param(description="ID пользователя или User#Tag"),
        reason: str = "Причина не указана"
    ):
        if not self.check_permissions(inter):
            await inter.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)
            return

        try:
            if user_id.isdigit():
                user = await self.bot.fetch_user(int(user_id))
            else:
                ban_list = [entry async for entry in inter.guild.bans()]
                for ban_entry in ban_list:
                    if str(ban_entry.user) == user_id:
                        user = ban_entry.user
                        break
                else:
                    await inter.response.send_message(f"❌ Пользователь {user_id} не найден в банах!", ephemeral=True)
                    return

            embed = disnake.Embed(
                title="🔓 Разбан пользователя",
                description=f"**{user.mention}** был разбанен",
                color=disnake.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="👮 Модератор", value=inter.author.mention, inline=True)
            embed.add_field(name="📝 Причина", value=reason, inline=True)

            await inter.guild.unban(user, reason=reason)
            await inter.response.send_message(embed=embed)

            # Отправляем лог
            await self.send_log(inter.guild, embed)

        except disnake.NotFound:
            await inter.response.send_message("❌ Пользователь не найден в списке банов!", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

    # ========== MUTE (ИСПРАВЛЕНО) ==========
    @commands.slash_command(name="mute", description="Выдать мьют пользователю (таймаут)")
    async def mute(
        self,
        inter: disnake.ApplicationCommandInteraction,
        user: disnake.Member,
        minutes: int = commands.Param(description="Количество минут (от 1 до 40320)", ge=1, le=40320),
        reason: str = "Причина не указана"
    ):
        if not self.check_permissions(inter):
            await inter.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)
            return

        if user == inter.author:
            await inter.response.send_message("❌ Вы не можете замутить самого себя!", ephemeral=True)
            return

        if user.guild_permissions.administrator:
            await inter.response.send_message("❌ Нельзя замутить администратора!", ephemeral=True)
            return

        try:
            duration = timedelta(minutes=minutes)
            until = disnake.utils.utcnow() + duration

            # ИСПРАВЛЕНО: используем timeout до даты
            await user.edit(timeout=until, reason=reason)

            embed = disnake.Embed(
                title="🔇 Мьют пользователя",
                description=f"**{user.mention}** получил мьют",
                color=disnake.Color.orange(),
                timestamp=datetime.now()
            )
            embed.add_field(name="👮 Модератор", value=inter.author.mention, inline=True)
            embed.add_field(name="⏰ Длительность", value=f"{minutes} минут", inline=True)
            embed.add_field(name="📝 Причина", value=reason, inline=True)

            await inter.response.send_message(embed=embed)

            # Отправляем лог
            await self.send_log(inter.guild, embed)

            # Отправляем уведомление в ЛС
            try:
                dm_embed = disnake.Embed(
                    title="Вы получили мьют",
                    description=f"Сервер: **{inter.guild.name}**\nДлительность: {minutes} минут\nПричина: {reason}",
                    color=disnake.Color.orange()
                )
                await user.send(embed=dm_embed)
            except:
                pass

        except Exception as e:
            await inter.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

    # ========== UNMUTE (ИСПРАВЛЕНО) ==========
    @commands.slash_command(name="unmute", description="Снять мьют с пользователя")
    async def unmute(
        self,
        inter: disnake.ApplicationCommandInteraction,
        user: disnake.Member,
        reason: str = "Причина не указана"
    ):
        if not self.check_permissions(inter):
            await inter.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)
            return

        if not user.current_timeout:
            await inter.response.send_message(f"❌ У пользователя {user.mention} нет активного мьюта!", ephemeral=True)
            return

        try:
            # ИСПРАВЛЕНО: снимаем таймаут через None
            await user.edit(timeout=None, reason=reason)

            embed = disnake.Embed(
                title="🔊 Снятие мьюта",
                description=f"**{user.mention}** был размьючен",
                color=disnake.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="👮 Модератор", value=inter.author.mention, inline=True)
            embed.add_field(name="📝 Причина", value=reason, inline=True)

            await inter.response.send_message(embed=embed)

            # Отправляем лог
            await self.send_log(inter.guild, embed)

            # Отправляем уведомление в ЛС
            try:
                dm_embed = disnake.Embed(
                    title="С вас сняли мьют",
                    description=f"Сервер: **{inter.guild.name}**\nПричина снятия: {reason}",
                    color=disnake.Color.green()
                )
                await user.send(embed=dm_embed)
            except:
                pass

        except Exception as e:
            await inter.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

    # ========== TIME-OUT (ИСПРАВЛЕНО) ==========
    @commands.slash_command(name="time-out", description="Выдать временный таймаут пользователю")
    async def timeout(
        self,
        inter: disnake.ApplicationCommandInteraction,
        user: disnake.Member,
        duration: str = commands.Param(description="Длительность (например: 5m, 1h, 2d, 1w)"),
        reason: str = "Причина не указана"
    ):
        if not self.check_permissions(inter):
            await inter.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)
            return

        if user == inter.author:
            await inter.response.send_message("❌ Вы не можете выдать таймаут самому себе!", ephemeral=True)
            return

        if user.guild_permissions.administrator:
            await inter.response.send_message("❌ Нельзя выдать таймаут администратору!", ephemeral=True)
            return

        try:
            value = int(duration[:-1])
            unit = duration[-1].lower()

            if unit == 'm':
                delta = timedelta(minutes=value)
            elif unit == 'h':
                delta = timedelta(hours=value)
            elif unit == 'd':
                delta = timedelta(days=value)
            elif unit == 'w':
                delta = timedelta(weeks=value)
            else:
                await inter.response.send_message("❌ Неверный формат! Используйте: 5m, 1h, 2d, 1w", ephemeral=True)
                return

            if delta.total_seconds() > 28 * 24 * 3600:
                await inter.response.send_message("❌ Таймаут не может быть больше 28 дней!", ephemeral=True)
                return

            until = disnake.utils.utcnow() + delta

            # ИСПРАВЛЕНО: используем edit с параметром timeout
            await user.edit(timeout=until, reason=reason)

            if unit == 'm':
                duration_str = f"{value} минут"
            elif unit == 'h':
                duration_str = f"{value} часов"
            elif unit == 'd':
                duration_str = f"{value} дней"
            else:
                duration_str = f"{value} недель"

            embed = disnake.Embed(
                title="⏰ Таймаут пользователя",
                description=f"**{user.mention}** получил таймаут",
                color=disnake.Color.dark_orange(),
                timestamp=datetime.now()
            )
            embed.add_field(name="👮 Модератор", value=inter.author.mention, inline=True)
            embed.add_field(name="⏰ Длительность", value=duration_str, inline=True)
            embed.add_field(name="📝 Причина", value=reason, inline=True)

            await inter.response.send_message(embed=embed)

            # Отправляем лог
            await self.send_log(inter.guild, embed)

        except ValueError:
            await inter.response.send_message("❌ Неверный формат! Используйте: 5m, 1h, 2d, 1w", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

    # ========== GARBAGE ==========
    @commands.slash_command(name="garbage", description="Очистить сообщения в канале")
    async def garbage(
        self,
        inter: disnake.ApplicationCommandInteraction,
        amount: int = commands.Param(description="Количество сообщений для удаления (1-100)", ge=1, le=100)
    ):
        if not self.check_permissions(inter):
            await inter.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)
            return

        try:
            deleted = await inter.channel.purge(limit=amount)

            embed = disnake.Embed(
                title="🗑 Очистка чата",
                description=f"Удалено **{len(deleted)}** сообщений",
                color=disnake.Color.blurple(),
                timestamp=datetime.now()
            )
            embed.add_field(name="👮 Модератор", value=inter.author.mention, inline=True)
            embed.add_field(name="📊 Канал", value=inter.channel.mention, inline=True)
            embed.add_field(name="📊 Всего удалено", value=f"{len(deleted)}/{amount}", inline=True)

            await inter.response.send_message(embed=embed, ephemeral=True)

            # Отправляем лог
            log_embed = disnake.Embed(
                title="🧹 Очистка сообщений",
                description=f"**Канал:** {inter.channel.mention}\n**Удалено:** {len(deleted)} сообщений\n**Модератор:** {inter.author.mention}",
                color=disnake.Color.blurple(),
                timestamp=datetime.now()
            )
            await self.send_log(inter.guild, log_embed)

        except Exception as e:
            await inter.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(ModerationCog(bot))