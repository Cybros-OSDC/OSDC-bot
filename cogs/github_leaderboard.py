import discord
from discord.ext import commands, tasks
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from utils.github_api import GitHubAPI, load_links
from config import Config

class GitHubLeaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.github_api = GitHubAPI(token=getattr(Config, 'GITHUB_TOKEN', None))
        self.github_links_file = Path("github_links.json")
        
        # Configuration
        self.leaderboard_channel_id = getattr(Config, 'LEADERBOARD_CHANNEL_ID', None)
        
        # Start background tasks
        if self.leaderboard_channel_id:
            self.weekly_leaderboard.start()
            self.monthly_leaderboard.start()
    
    def cog_unload(self):
        self.weekly_leaderboard.cancel()
        self.monthly_leaderboard.cancel()
    
    async def fetch_all_user_stats(self) -> List[Tuple[int, str, Dict]]:
        """Fetch stats for all linked users"""
        links = load_links(self.github_links_file)
        user_stats = []
        
        async with self.github_api as api:
            for discord_id, github_username in links.items():
                try:
                    stats = await api.fetch_user_stats(github_username)
                    user_stats.append((discord_id, github_username, stats))
                except Exception as e:
                    print(f"Error fetching stats for {github_username}: {e}")
        
        return user_stats
    
    @tasks.loop(hours=168)  # Every week
    async def weekly_leaderboard(self):
        """Post weekly leaderboard"""
        if not self.leaderboard_channel_id:
            return
        
        channel = self.bot.get_channel(self.leaderboard_channel_id)
        if not channel:
            return
        
        user_stats = await self.fetch_all_user_stats()
        if not user_stats:
            return
        
        # Sort by total stars
        user_stats.sort(key=lambda x: x[2].get("total_stars", 0), reverse=True)
        
        embed = discord.Embed(
            title="🏆 Weekly GitHub Leaderboard",
            description="Top contributors this week",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        leaderboard_text = ""
        for i, (discord_id, github_username, stats) in enumerate(user_stats[:10], 1):
            guild = self.bot.get_guild(Config.GUILD_ID)
            member = guild.get_member(discord_id) if guild else None
            display_name = member.display_name if member else github_username
            
            stars = stats.get("total_stars", 0)
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            leaderboard_text += f"{medal} **{display_name}** - ⭐{stars}\n"
        
        embed.add_field(name="🏆 Rankings", value=leaderboard_text, inline=False)
        await channel.send(embed=embed)
    
    @tasks.loop(hours=720)  # Every month
    async def monthly_leaderboard(self):
        """Post monthly leaderboard with special recognition"""
        if not self.leaderboard_channel_id:
            return
        
        channel = self.bot.get_channel(self.leaderboard_channel_id)
        if not channel:
            return
        
        user_stats = await self.fetch_all_user_stats()
        if not user_stats:
            return
        
        # Sort by total stars
        user_stats.sort(key=lambda x: x[2].get("total_stars", 0), reverse=True)
        
        # Update GitHub Top 3 role
        guild = self.bot.get_guild(Config.GUILD_ID)
        if guild:
            top_3_role = discord.utils.get(guild.roles, name="GitHub Top 3")
            if not top_3_role:
                top_3_role = await guild.create_role(
                    name="GitHub Top 3",
                    color=discord.Color.gold(),
                    mentionable=True
                )
            
            # Remove role from all members
            for member in guild.members:
                if top_3_role in member.roles:
                    await member.remove_roles(top_3_role)
            
            # Add role to top 3
            for i, (discord_id, github_username, stats) in enumerate(user_stats[:3]):
                member = guild.get_member(discord_id)
                if member:
                    await member.add_roles(top_3_role)
        
        embed = discord.Embed(
            title="🎉 Monthly GitHub Champions",
            description="Congratulations to this month's top contributors!",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        leaderboard_text = ""
        for i, (discord_id, github_username, stats) in enumerate(user_stats[:15], 1):
            guild = self.bot.get_guild(Config.GUILD_ID)
            member = guild.get_member(discord_id) if guild else None
            display_name = member.display_name if member else github_username
            
            stars = stats.get("total_stars", 0)
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            leaderboard_text += f"{medal} **{display_name}** - ⭐{stars}\n"
        
        embed.add_field(name="🏆 Rankings", value=leaderboard_text, inline=False)
        await channel.send(embed=embed)
    
    @weekly_leaderboard.before_loop
    async def before_weekly_leaderboard(self):
        await self.bot.wait_until_ready()
    
    @monthly_leaderboard.before_loop
    async def before_monthly_leaderboard(self):
        await self.bot.wait_until_ready()
    
    @commands.command(name="leaderboard")
    async def show_leaderboard(self, ctx):
        """Show current GitHub leaderboard"""
        await ctx.send("📊 Fetching leaderboard data...")
        user_stats = await self.fetch_all_user_stats()
        
        if not user_stats:
            await ctx.send("❌ No GitHub data available!")
            return
        
        user_stats.sort(key=lambda x: x[2].get("total_stars", 0), reverse=True)
        
        embed = discord.Embed(
            title="🏆 GitHub Leaderboard",
            description="Current top contributors",
            color=discord.Color.blue()
        )
        
        leaderboard_text = ""
        for i, (discord_id, github_username, stats) in enumerate(user_stats[:10], 1):
            member = ctx.guild.get_member(discord_id)
            display_name = member.display_name if member else github_username
            
            stars = stats.get("total_stars", 0)
            repos = stats.get("total_repos", 0)
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            leaderboard_text += f"{medal} **{display_name}** - ⭐{stars} stars, 📚{repos} repos\n"
        
        embed.add_field(name="🏆 Rankings", value=leaderboard_text, inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(GitHubLeaderboard(bot))
