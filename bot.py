import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

class CyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.reactions = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            case_insensitive=True
            # Don't remove help command here - let the help cog handle it
        )
    
    async def setup_hook(self):
        """Load all cogs when bot starts"""
        initial_extensions = [
            "cogs.help",           # Load help cog FIRST
            "cogs.verify",
            "cogs.github", 
            "cogs.roles",
            "cogs.info",
            "cogs.github_feed",
            "cogs.github_leaderboard"
        ]
        
        for ext in initial_extensions:
            try:
                await self.load_extension(ext)
                print(f"✅ Loaded {ext}")
            except Exception as e:
                print(f"❌ Failed to load {ext}: {e}")
    
    async def on_ready(self):
        print(f"✅ {self.user} is online and ready!")
        print(f"📊 Connected to {len(self.guilds)} guilds")
        print(f"👥 Serving {len(set(self.get_all_members()))} users")
        print(f"📝 Loaded {len(self.commands)} commands")
    
    async def on_command_error(self, ctx, error):
        """Handle command errors with appealing messages"""
        if isinstance(error, commands.CommandNotFound):
            embed = discord.Embed(
                title="🤔 Command Not Found",
                description="That command doesn't exist! But don't worry, I can help you find what you're looking for.",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="💡 Quick Help",
                value="• Use `!help` to see all commands\n• Use `!help <command>` for specific help\n• Check for typos in your command",
                inline=False
            )
            embed.set_footer(text="This message will auto-delete in 15 seconds")
            await ctx.send(embed=embed, delete_after=15)
            
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="📝 Missing Information",
                description=f"The `!{ctx.command.name}` command needs more information to work.",
                color=discord.Color.yellow()
            )
            embed.add_field(
                name="🔧 How to fix this",
                value=f"Use `!help {ctx.command.name}` to see the correct usage",
                inline=False
            )
            await ctx.send(embed=embed, delete_after=20)
            
        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="❌ Invalid Input",
                description="The information you provided isn't in the right format.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="🛠️ Need help?",
                value=f"Use `!help {ctx.command.name}` for examples and correct usage",
                inline=False
            )
            await ctx.send(embed=embed, delete_after=20)
            
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="🚫 Permission Denied",
                description="You don't have permission to use this command.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="🔑 Required Permissions",
                value=", ".join(error.missing_permissions),
                inline=False
            )
            await ctx.send(embed=embed, delete_after=15)
            
        else:
            print(f"Unhandled command error: {error}")
            embed = discord.Embed(
                title="⚠️ Something Went Wrong",
                description="An unexpected error occurred. The developers have been notified.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="🆘 Need immediate help?",
                value="Contact a server administrator or try the command again",
                inline=False
            )
            await ctx.send(embed=embed, delete_after=30)

async def main():
    bot = CyBot()
    async with bot:
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
