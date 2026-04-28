# cogs/server_links.py
import disnake
from disnake.ext import commands

class ServerLinksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """Выводит ссылки на сервера при запуске"""
        print(f"\n{'='*50}")
        print(f"✅ Бот {self.bot.user} запущен!")
        print(f"📊 Всего серверов: {len(self.bot.guilds)}\n")
        
        for guild in self.bot.guilds:
            invite_link = await self.get_invite_link(guild)
            print(f"🔹 {guild.name} (ID: {guild.id})")
            print(f"   📎 {invite_link}\n")
        
        print(f"{'='*50}")

    async def get_invite_link(self, guild: disnake.Guild) -> str:
        """Создаёт ссылку-приглашение на сервер"""
        try:
            # Ищем канал где бот может создать приглашение
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).create_instant_invite:
                    invite = await channel.create_invite(
                        max_age=0,
                        max_uses=0,
                        reason="Ссылка для логов бота"
                    )
                    return invite.url
            
            return "❌ Нет прав для создания приглашения"
            
        except disnake.Forbidden:
            return "❌ Нет прав (Forbidden)"
        except Exception as e:
            return f"❌ Ошибка: {type(e).__name__}"

# Функция setup для загрузки кога
def setup(bot):
    bot.add_cog(ServerLinksCog(bot))
