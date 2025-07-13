import discord
from discord.ext import commands
import json
from pathlib import Path
from utils.github_api import load_links, get_github_stars, get_github_repos
from config import Config

class InfoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.github_links_file = "github_links.json"
    
    @commands.command()
    async def info(self, ctx, member: discord.Member = None):
        """Show user information"""
        if member is None:
            member = ctx.author
        
        embed = discord.Embed(
            title=f"ℹ️ User Information",
            color=discord.Color.blue()
        )
        
        # Basic Discord info
        embed.add_field(
            name="👤 Discord Info",
            value=f"**Name:** {member.display_name}\n"
                  f"**ID:** {member.id}\n"
                  f"**Joined:** {member.joined_at.strftime('%Y-%m-%d') if member.joined_at else 'Unknown'}\n"
                  f"**Created:** {member.created_at.strftime('%Y-%m-%d')}",
            inline=False
        )
        
        # Roles
        roles = [role.name for role in member.roles if role.name != "@everyone"]
        if roles:
            embed.add_field(
                name="🏷️ Roles",
                value=", ".join(roles),
                inline=False
            )
        
        # GitHub info if linked
        try:
            links = load_links(self.github_links_file)
            if member.id in links:
                github_username = links[member.id]
                embed.add_field(
                    name="🐙 GitHub",
                    value=f"**Username:** [{github_username}](https://github.com/{github_username})",
                    inline=False
                )
        except Exception as e:
            print(f"Error loading GitHub info: {e}")
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def server_info(self, ctx):
        """Show server information"""
        guild = ctx.guild
        
        embed = discord.Embed(
            title=f"📊 Server Information",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="🏠 Server Details",
            value=f"**Name:** {guild.name}\n"
                  f"**ID:** {guild.id}\n"
                  f"**Owner:** {guild.owner.mention if guild.owner else 'Unknown'}\n"
                  f"**Created:** {guild.created_at.strftime('%Y-%m-%d')}\n"
                  f"**Members:** {guild.member_count}",
            inline=False
        )
        
        embed.add_field(
            name="📈 Channels",
            value=f"**Text:** {len(guild.text_channels)}\n"
                  f"**Voice:** {len(guild.voice_channels)}\n"
                  f"**Categories:** {len(guild.categories)}",
            inline=True
        )
        
        embed.add_field(
            name="🎭 Roles",
            value=f"**Total:** {len(guild.roles)}",
            inline=True
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(InfoCog(bot))
