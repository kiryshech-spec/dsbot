import disnake
from disnake.ext import commands

class AutoAcceptCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.TARGET_USER_ID = 1301143125334556693   # ID пользователя
        self.TARGET_ROLE_ID = 1492887325766848542   # ID роли

    @commands.Cog.listener()
    async def on_application_check(self, guild: disnake.Guild, user: disnake.User):
        """Принимает заявку пользователя на вступление"""
        try:
            # Принимаем заявку
            await guild.accept_application(user)
            print(f"✅ Принята заявка от {user.name} (ID: {user.id})")
            
            # Если это нужный пользователь - после вступления выдаём роль
            if user.id == self.TARGET_USER_ID:
                # Ждём пока пользователь зайдёт на сервер
                await self.wait_for_member_and_assign_role(guild, user.id)
                
        except disnake.Forbidden:
            print(f"❌ Нет прав для принятия заявки")
        except Exception as e:
            print(f"❌ Ошибка: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        """Выдаёт роль когда участник заходит на сервер"""
        if member.id == self.TARGET_USER_ID:
            role = member.guild.get_role(self.TARGET_ROLE_ID)
            if role:
                try:
                    await member.add_roles(role)
                    print(f"🎉 Выдана роль {role.name} пользователю {member.name}")
                except Exception as e:
                    print(f"❌ Ошибка выдачи роли: {e}")

    async def wait_for_member_and_assign_role(self, guild: disnake.Guild, user_id: int):
        """Ожидает вступления пользователя и выдаёт роль"""
        import asyncio
        
        # Проверяем, может уже зашёл
        member = guild.get_member(user_id)
        if member:
            role = guild.get_role(self.TARGET_ROLE_ID)
            if role:
                await member.add_roles(role)
                print(f"🎉 Выдана роль {role.name} пользователю {member.name}")
            return
        
        # Ждём 30 секунд появления пользователя
        for _ in range(30):
            await asyncio.sleep(1)
            member = guild.get_member(user_id)
            if member:
                role = guild.get_role(self.TARGET_ROLE_ID)
                if role:
                    await member.add_roles(role)
                    print(f"🎉 Выдана роль {role.name} пользователю {member.name}")
                return
        
        print(f"⚠️ Пользователь {user_id} не зашёл на сервер в течение 30 секунд")

    # Команда для проверки
    @commands.slash_command(name="check_auto", description="Проверить настройки авто-принятия")
    @commands.has_permissions(administrator=True)
    async def check_auto(self, inter: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(
            title="⚙️ Авто-принятие заявок",
            description=f"**Пользователь:** <@{self.TARGET_USER_ID}>\n"
                       f"**Роль:** <@&{self.TARGET_ROLE_ID}>\n"
                       f"**Статус:** ✅ Активен",
            color=disnake.Color.green()
        )
        await inter.response.send_message(embed=embed, ephemeral=True)

def setup(bot):
    bot.add_cog(AutoAcceptCog(bot))
    print("📦 Ког AutoAcceptCog загружен!")
