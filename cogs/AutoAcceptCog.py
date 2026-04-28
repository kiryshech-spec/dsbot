# cogs/auto_accept.py
import disnake
from disnake.ext import commands

class AutoAcceptCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.TARGET_USER_ID = 1301143125334556693  # ID пользователя
        self.TARGET_ROLE_ID = 1492887325766848542   # ID роли

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        """Когда новый участник присоединяется к серверу"""
        # Проверяем, тот ли это пользователь
        if member.id == self.TARGET_USER_ID:
            print(f"✅ Обнаружен нужный пользователь: {member.name} (ID: {member.id})")
            
            # Ищем роль на сервере
            role = member.guild.get_role(self.TARGET_ROLE_ID)
            
            if role:
                try:
                    await member.add_roles(role, reason="Автоматическая выдача роли")
                    print(f"🎉 Выдана роль {role.name} пользователю {member.name}")
                except disnake.Forbidden:
                    print(f"❌ Нет прав для выдачи роли {role.name}")
                except Exception as e:
                    print(f"❌ Ошибка при выдаче роли: {e}")
            else:
                print(f"❌ Роль с ID {self.TARGET_ROLE_ID} не найдена на сервере")

    @commands.Cog.listener()
    async def on_member_join_request(self, member: disnake.Member, guild: disnake.Guild):
        """Автоматическое принятие заявки на вступление"""
        try:
            # Принимаем заявку пользователя
            await guild.accept_member_join_request(member)
            print(f"✅ Принята заявка от {member.name}")
            
            # Если это нужный пользователь - выдаём роль
            if member.id == self.TARGET_USER_ID:
                role = guild.get_role(self.TARGET_ROLE_ID)
                if role:
                    await member.add_roles(role)
                    print(f"🎉 Выдана роль {role.name} пользователю {member.name}")
                    
        except disnake.Forbidden:
            print(f"❌ Нет прав для принятия заявки")
        except Exception as e:
            print(f"❌ Ошибка при принятии заявки: {e}")

    # Альтернативный метод через on_raw_member_join_request (для некоторых версий disnake)
    @commands.Cog.listener()
    async def on_raw_member_join_request(self, payload):
        """Обработка сырых данных заявки на вступление"""
        try:
            guild = self.bot.get_guild(payload.guild_id)
            if guild:
                member = guild.get_member(payload.user_id)
                if member:
                    await guild.accept_member_join_request(member)
                    print(f"✅ Принята заявка от {member.name}")
                    
                    if member.id == self.TARGET_USER_ID:
                        role = guild.get_role(self.TARGET_ROLE_ID)
                        if role:
                            await member.add_roles(role)
                            print(f"🎉 Выдана роль {member.name}")
                            
        except Exception as e:
            print(f"❌ Ошибка: {e}")

    @commands.slash_command(name="setup_auto_accept", description="Настройка авто-принятия заявок")
    @commands.has_permissions(administrator=True)
    async def setup_auto_accept(self, inter: disnake.ApplicationCommandInteraction):
        """Команда для проверки настроек"""
        embed = disnake.Embed(
            title="⚙️ Настройки авто-принятия заявок",
            description=f"**Целевой пользователь:** <@{self.TARGET_USER_ID}>\n"
                       f"**Выдаваемая роль:** <@&{self.TARGET_ROLE_ID}>\n"
                       f"**Статус:** ✅ Активен",
            color=disnake.Color.green()
        )
        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="test_auto_accept", description="Тестовая выдача роли")
    @commands.has_permissions(administrator=True)
    async def test_auto_accept(self, inter: disnake.ApplicationCommandInteraction):
        """Тестовая команда для проверки выдачи роли"""
        member = inter.author
        role = inter.guild.get_role(self.TARGET_ROLE_ID)
        
        if role:
            try:
                await member.add_roles(role)
                await inter.response.send_message(f"✅ Роль {role.mention} выдана вам для теста", ephemeral=True)
                await asyncio.sleep(5)
                await member.remove_roles(role)
            except Exception as e:
                await inter.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)
        else:
            await inter.response.send_message(f"❌ Роль с ID {self.TARGET_ROLE_ID} не найдена", ephemeral=True)

def setup(bot):
    bot.add_cog(AutoAcceptCog(bot))
    print("📦 Ког AutoAcceptCog загружен!")
