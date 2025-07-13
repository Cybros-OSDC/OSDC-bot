import discord
from discord.ext import commands, tasks
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set
from utils.github_api import GitHubAPI
from config import Config

class GitHubFeed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.github_api = GitHubAPI(token=getattr(Config, 'GITHUB_TOKEN', None))
        self.feed_file = Path("github_feed_data.json")
        self.subscribers_file = Path("github_subscribers.json")
        
        # Load data
        self.repo_subscribers = self.load_subscribers()
        self.last_event_ids = self.load_last_events()
        
        # Configuration
        self.feed_channel_id = getattr(Config, 'GITHUB_FEED_CHANNEL_ID', None)
        
        # Start background task
        if self.feed_channel_id:
            self.feed_loop.start()
    
    def cog_unload(self):
        self.feed_loop.cancel()
    
    def load_subscribers(self) -> Dict[str, Set[int]]:
        """Load repository subscribers from file"""
        if self.subscribers_file.exists():
            try:
                with open(self.subscribers_file, 'r') as f:
                    data = json.load(f)
                    return {repo: set(users) for repo, users in data.items()}
            except Exception as e:
                print(f"Error loading subscribers: {e}")
        return {}
    
    def save_subscribers(self):
        """Save repository subscribers to file"""
        try:
            data = {repo: list(users) for repo, users in self.repo_subscribers.items()}
            with open(self.subscribers_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving subscribers: {e}")
    
    def load_last_events(self) -> Dict[str, str]:
        """Load last event IDs from file"""
        if self.feed_file.exists():
            try:
                with open(self.feed_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading last events: {e}")
        return {}
    
    def save_last_events(self):
        """Save last event IDs to file"""
        try:
            with open(self.feed_file, 'w') as f:
                json.dump(self.last_event_ids, f, indent=2)
        except Exception as e:
            print(f"Error saving last events: {e}")
    
    @tasks.loop(seconds=300)  # 5 minutes
    async def feed_loop(self):
        """Background task to fetch and post repository updates"""
        if not self.feed_channel_id:
            return
        
        channel = self.bot.get_channel(self.feed_channel_id)
        if not channel:
            return
        
        async with self.github_api as api:
            for repo in list(self.repo_subscribers.keys()):
                if not self.repo_subscribers[repo]:  # No subscribers
                    continue
                
                try:
                    events = await api.fetch_repo_events(repo, per_page=5)
                    if not events:
                        continue
                    
                    # Process new events
                    new_events = []
                    last_event_id = self.last_event_ids.get(repo)
                    
                    for event in events:
                        if last_event_id and event["id"] == last_event_id:
                            break
                        new_events.append(event)
                    
                    # Post new events
                    for event in reversed(new_events):
                        embed = self.create_event_embed(repo, event)
                        if embed:
                            await channel.send(embed=embed)
                            await asyncio.sleep(1)  # Rate limiting
                    
                    # Update last event ID
                    if events:
                        self.last_event_ids[repo] = events[0]["id"]
                
                except Exception as e:
                    print(f"Error processing events for {repo}: {e}")
        
        # Save updated data
        self.save_last_events()
    
    @feed_loop.before_loop
    async def before_feed_loop(self):
        await self.bot.wait_until_ready()
    
    def create_event_embed(self, repo: str, event: Dict) -> discord.Embed:
        """Create Discord embed for GitHub event"""
        event_type = event.get("type", "")
        actor = event.get("actor", {}).get("login", "Unknown")
        created_at = event.get("created_at", "")
        
        # Parse timestamp
        try:
            timestamp = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except:
            timestamp = datetime.now()
        
        # Different embed colors for different event types
        color_map = {
            "PushEvent": discord.Color.green(),
            "IssuesEvent": discord.Color.yellow(),
            "PullRequestEvent": discord.Color.blue(),
            "CreateEvent": discord.Color.purple(),
            "ReleaseEvent": discord.Color.gold(),
            "ForkEvent": discord.Color.orange(),
            "WatchEvent": discord.Color.red()
        }
        
        embed = discord.Embed(
            title=f"📂 {repo}",
            color=color_map.get(event_type, discord.Color.default()),
            timestamp=timestamp
        )
        
        # Event-specific formatting
        if event_type == "PushEvent":
            payload = event.get("payload", {})
            commits = payload.get("commits", [])
            commit_count = len(commits)
            
            embed.add_field(
                name="🔨 Push Event",
                value=f"**{actor}** pushed {commit_count} commit(s)",
                inline=False
            )
        elif event_type == "IssuesEvent":
            payload = event.get("payload", {})
            action = payload.get("action", "")
            issue = payload.get("issue", {})
            
            embed.add_field(
                name="🐛 Issue Event",
                value=f"**{actor}** {action} issue #{issue.get('number', '?')}",
                inline=False
            )
        elif event_type == "PullRequestEvent":
            payload = event.get("payload", {})
            action = payload.get("action", "")
            pr = payload.get("pull_request", {})
            
            embed.add_field(
                name="🔄 Pull Request Event",
                value=f"**{actor}** {action} PR #{pr.get('number', '?')}",
                inline=False
            )
        else:
            embed.add_field(
                name=f"📋 {event_type}",
                value=f"**{actor}** performed {event_type.lower()}",
                inline=False
            )
        
        embed.add_field(
            name="🔗 Repository",
            value=f"[{repo}](https://github.com/{repo})",
            inline=True
        )
        
        embed.set_footer(text=f"GitHub • {event_type}")
        return embed
    
    @commands.group(name="github", invoke_without_command=True)
    async def github_group(self, ctx):
        """GitHub integration commands"""
        embed = discord.Embed(
            title="🐙 GitHub Integration",
            description="Available commands for GitHub integration",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Repository Feed",
            value="`!github subscribe <repo>` - Subscribe to repository updates\n"
                  "`!github unsubscribe <repo>` - Unsubscribe from repository\n"
                  "`!github list` - List subscribed repositories",
            inline=False
        )
        await ctx.send(embed=embed)
    
    @github_group.command(name="subscribe")
    async def subscribe_repo(self, ctx, repo: str):
        """Subscribe to GitHub repository updates"""
        if "/" not in repo or len(repo.split("/")) != 2:
            await ctx.send("❌ Invalid repository format. Use `owner/repo`")
            return
        
        if repo not in self.repo_subscribers:
            self.repo_subscribers[repo] = set()
        
        if ctx.author.id in self.repo_subscribers[repo]:
            await ctx.send(f"✅ You are already subscribed to **{repo}**")
            return
        
        self.repo_subscribers[repo].add(ctx.author.id)
        self.save_subscribers()
        
        await ctx.send(f"✅ Subscribed to **{repo}** updates!")
    
    @github_group.command(name="unsubscribe")
    async def unsubscribe_repo(self, ctx, repo: str):
        """Unsubscribe from GitHub repository updates"""
        if repo not in self.repo_subscribers or ctx.author.id not in self.repo_subscribers[repo]:
            await ctx.send(f"❌ You are not subscribed to **{repo}**")
            return
        
        self.repo_subscribers[repo].discard(ctx.author.id)
        if not self.repo_subscribers[repo]:
            del self.repo_subscribers[repo]
        
        self.save_subscribers()
        await ctx.send(f"✅ Unsubscribed from **{repo}**")
    
    @github_group.command(name="list")
    async def list_subscriptions(self, ctx):
        """List your subscribed repositories"""
        user_repos = []
        for repo, subscribers in self.repo_subscribers.items():
            if ctx.author.id in subscribers:
                user_repos.append(repo)
        
        if not user_repos:
            await ctx.send("📭 You are not subscribed to any repositories")
            return
        
        embed = discord.Embed(
            title="📚 Your GitHub Subscriptions",
            description=f"You are subscribed to {len(user_repos)} repositories",
            color=discord.Color.blue()
        )
        
        for repo in user_repos:
            embed.add_field(
                name=repo,
                value=f"[View Repository](https://github.com/{repo})",
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(GitHubFeed(bot))
