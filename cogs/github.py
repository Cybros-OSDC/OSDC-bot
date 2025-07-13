import discord
from discord.ext import commands
import json
import asyncio
from pathlib import Path
from utils.github_api import GitHubAPI, load_links, save_links, get_github_stars, get_github_repos
from config import Config

class GitHubCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.github_links_file = "github_links.json"
        self.github_api = None
        
    async def cog_load(self):
        """Initialize GitHub API when cog loads"""
        self.github_api = GitHubAPI(token=getattr(Config, 'GITHUB_TOKEN', None))
    
    async def cog_unload(self):
        """Clean up when cog unloads"""
        if self.github_api and hasattr(self.github_api, 'session'):
            if self.github_api.session and not self.github_api.session.closed:
                await self.github_api.session.close()
    
    @commands.command()
    async def link_github(self, ctx, github_username: str):
        """Link Discord account to GitHub username"""
        try:
            # Verify GitHub username exists
            async with GitHubAPI(getattr(Config, 'GITHUB_TOKEN', None)) as api:
                user_info = await api.fetch_user_info(github_username)
                if not user_info:
                    await ctx.send(f"❌ GitHub user '{github_username}' not found!")
                    return
            
            # Load existing links
            links = load_links(self.github_links_file)
            
            # Add new link
            links[ctx.author.id] = github_username
            
            # Save links
            save_links(links, self.github_links_file)
            
            embed = discord.Embed(
                title="✅ GitHub Account Linked",
                description=f"Successfully linked {ctx.author.mention} to GitHub user **{github_username}**",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Profile",
                value=f"[{github_username}](https://github.com/{github_username})",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error linking GitHub account: {e}")
    
    @commands.command()
    async def github_profile(self, ctx, github_username: str = None):
        """Show GitHub profile information"""
        if not github_username:
            # Check if user has linked account
            links = load_links(self.github_links_file)
            if ctx.author.id not in links:
                await ctx.send("❌ Please provide a GitHub username or link your account first!")
                return
            github_username = links[ctx.author.id]
        
        try:
            await ctx.send(f"🔍 Fetching GitHub profile for **{github_username}**...")
            
            async with GitHubAPI(getattr(Config, 'GITHUB_TOKEN', None)) as api:
                stats = await api.fetch_user_stats(github_username)
                
                if not stats.get("user_info"):
                    await ctx.send(f"❌ Could not fetch profile for **{github_username}**")
                    return
                
                user_info = stats["user_info"]
                
                embed = discord.Embed(
                    title=f"🐙 {github_username}'s GitHub Profile",
                    url=f"https://github.com/{github_username}",
                    color=discord.Color.blue()
                )
                
                # Basic info
                if user_info.get("name"):
                    embed.add_field(name="Name", value=user_info["name"], inline=True)
                if user_info.get("company"):
                    embed.add_field(name="Company", value=user_info["company"], inline=True)
                if user_info.get("location"):
                    embed.add_field(name="Location", value=user_info["location"], inline=True)
                
                # Stats
                embed.add_field(
                    name="📊 Statistics",
                    value=f"**Followers:** {user_info.get('followers', 0)}\n"
                          f"**Following:** {user_info.get('following', 0)}\n"
                          f"**Public Repos:** {user_info.get('public_repos', 0)}\n"
                          f"**Total Stars:** {stats.get('total_stars', 0)}\n"
                          f"**Merged PRs:** {stats.get('merged_prs', 0)}\n"
                          f"**Issues Opened:** {stats.get('issues_opened', 0)}",
                    inline=False
                )
                
                # Bio
                if user_info.get("bio"):
                    embed.add_field(name="Bio", value=user_info["bio"], inline=False)
                
                # Avatar
                if user_info.get("avatar_url"):
                    embed.set_thumbnail(url=user_info["avatar_url"])
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            await ctx.send(f"❌ Error fetching GitHub profile: {e}")
    
    @commands.command()
    async def top_repos(self, ctx, github_username: str = None):
        """Show top repositories for a GitHub user"""
        if not github_username:
            links = load_links(self.github_links_file)
            if ctx.author.id not in links:
                await ctx.send("❌ Please provide a GitHub username or link your account first!")
                return
            github_username = links[ctx.author.id]
        
        try:
            await ctx.send(f"🔍 Fetching top repositories for **{github_username}**...")
            
            async with GitHubAPI(getattr(Config, 'GITHUB_TOKEN', None)) as api:
                repos = await api.fetch_user_repos(github_username)
                
                if not repos:
                    await ctx.send(f"❌ No repositories found for **{github_username}**")
                    return
                
                # Sort by stars
                sorted_repos = sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)
                top_repos = sorted_repos[:10]
                
                embed = discord.Embed(
                    title=f"🌟 Top Repositories for {github_username}",
                    color=discord.Color.gold()
                )
                
                for i, repo in enumerate(top_repos, 1):
                    stars = repo.get("stargazers_count", 0)
                    language = repo.get("language", "Unknown")
                    description = repo.get("description", "No description")
                    
                    embed.add_field(
                        name=f"{i}. {repo['name']}",
                        value=f"⭐ {stars} | 📝 {language}\n{description[:100]}{'...' if len(description) > 100 else ''}\n[View Repo]({repo['html_url']})",
                        inline=False
                    )
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            await ctx.send(f"❌ Error fetching repositories: {e}")

async def setup(bot):
    await bot.add_cog(GitHubCog(bot))
