import discord
from discord.ext import commands, tasks
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from utils.github_api import GitHubAPI, load_links, save_links
from config import Config

class RolesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.github_links_file = "github_links.json"
        self.github_api = GitHubAPI(token=getattr(Config, 'GITHUB_TOKEN', None))
        
        # Start the daily role update task
        self.daily_leaderboard_update.start()
    
    def cog_unload(self):
        self.daily_leaderboard_update.cancel()
    
    @tasks.loop(hours=24)
    async def daily_leaderboard_update(self):
        """Update GitHub roles daily"""
        await self.update_github_roles()
    
    @daily_leaderboard_update.before_loop
    async def before_daily_update(self):
        await self.bot.wait_until_ready()
    
    async def update_github_roles(self):
        """Update GitHub-based roles for all linked users"""
        guild = self.bot.get_guild(Config.GUILD_ID)
        if not guild:
            return
        
        links = load_links(self.github_links_file)
        user_stats = []
        
        async with self.github_api as api:
            for discord_id, github_username in links.items():
                try:
                    stats = await api.fetch_user_stats(github_username)
                    user_stats.append((discord_id, github_username, stats))
                except Exception as e:
                    print(f"Error fetching stats for {github_username}: {e}")
        
        # Sort by total stars
        user_stats.sort(key=lambda x: x[2].get("total_stars", 0), reverse=True)
        
        # Update roles
        await self.assign_top_contributor_roles(guild, user_stats)
        await self.assign_open_source_roles(guild, user_stats)
        
        # Post daily leaderboard
        await self.post_daily_leaderboard(guild, user_stats)
    
    async def assign_top_contributor_roles(self, guild, user_stats):
        """Assign GitHub Top 3 roles"""
        # Get or create GitHub Top 3 role
        top_role = discord.utils.get(guild.roles, name="GitHub Top 3")
        if not top_role:
            top_role = await guild.create_role(
                name="GitHub Top 3",
                color=discord.Color.gold(),
                mentionable=True
            )
        
        # Remove role from all members
        for member in guild.members:
            if top_role in member.roles:
                await member.remove_roles(top_role, reason="Daily leaderboard update")
        
        # Assign to top 3
        for i, (discord_id, github_username, stats) in enumerate(user_stats[:3]):
            member = guild.get_member(discord_id)
            if member:
                await member.add_roles(top_role, reason="Top 3 GitHub contributor")
    
    async def assign_open_source_roles(self, guild, user_stats):
        """Assign Open Source Contributor roles"""
        # Get or create Open Source Contributor role
        os_role = discord.utils.get(guild.roles, name="Open Source Contributor")
        if not os_role:
            os_role = await guild.create_role(
                name="Open Source Contributor",
                color=discord.Color.green(),
                mentionable=True
            )
        
        # Assign to users with 50+ stars or 5+ repos
        for discord_id, github_username, stats in user_stats:
            member = guild.get_member(discord_id)
            if member:
                stars = stats.get("total_stars", 0)
                repos = stats.get("total_repos", 0)
                
                if stars >= 50 or repos >= 5:
                    if os_role not in member.roles:
                        await member.add_roles(os_role, reason="Open source contributor")
                else:
                    if os_role in member.roles:
                        await member.remove_roles(os_role, reason="No longer meets criteria")
    
    async def post_daily_leaderboard(self, guild, user_stats):
        """Post daily leaderboard to the channel"""
        # Find general channel or create one
        channel = discord.utils.get(guild.text_channels, name="general")
        if not channel:
            channel = discord.utils.get(guild.text_channels, name="github-updates")
        
        if not channel:
            return
        
        embed = discord.Embed(
            title="🏆 Daily GitHub Leaderboard",
            description="Top contributors based on GitHub stars",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        leaderboard_text = ""
        for i, (discord_id, github_username, stats) in enumerate(user_stats[:10], 1):
            member = guild.get_member(discord_id)
            display_name = member.display_name if member else github_username
            stars = stats.get("total_stars", 0)
            repos = stats.get("total_repos", 0)
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            leaderboard_text += f"{medal} **{display_name}** - ⭐{stars} stars, 📚{repos} repos\n"
        
        if leaderboard_text:
            embed.add_field(name="Top Contributors", value=leaderboard_text, inline=False)
        
        await channel.send(embed=embed)
    
    @commands.command()
    async def update_roles(self, ctx):
        """Manually update GitHub roles (admin only)"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ You need administrator permissions to use this command!")
            return
        
        await ctx.send("🔄 Updating GitHub roles...")
        await self.update_github_roles()
        await ctx.send("✅ GitHub roles updated successfully!")
    
    @commands.command()
    async def github_leaderboard(self, ctx):
        """Show current GitHub leaderboard"""
        links = load_links(self.github_links_file)
        user_stats = []
        
        await ctx.send("📊 Fetching GitHub leaderboard...")
        
        async with self.github_api as api:
            for discord_id, github_username in links.items():
                try:
                    stats = await api.fetch_user_stats(github_username)
                    user_stats.append((discord_id, github_username, stats))
                except Exception as e:
                    print(f"Error fetching stats for {github_username}: {e}")
        
        if not user_stats:
            await ctx.send("❌ No GitHub data available!")
            return
        
        user_stats.sort(key=lambda x: x[2].get("total_stars", 0), reverse=True)
        
        embed = discord.Embed(
            title="🏆 GitHub Leaderboard",
            description="Top contributors based on GitHub stars",
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
        
        embed.add_field(name="Top Contributors", value=leaderboard_text, inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(RolesCog(bot))
