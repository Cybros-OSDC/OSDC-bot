import discord
from discord.ext import commands
from datetime import datetime
import difflib
import asyncio

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Remove default help command to replace with custom one
        self.bot.remove_command('help')
    
    @commands.command(name='help')
    async def custom_help(self, ctx, *, command_name: str = None):
        """🎯 Show beautiful help information for commands"""
        
        if command_name:
            # Show help for specific command
            command = self.bot.get_command(command_name.lower())
            if command:
                embed = await self.create_command_help_embed(command)
                view = CommandHelpView(command.name, ctx.author.id)
            else:
                embed = await self.create_command_not_found_embed(command_name)
                view = BackToMainView(ctx.author.id)
        else:
            # Show main help menu
            embed = await self.create_main_help_embed(ctx)
            view = MainHelpView(ctx.author.id)
        
        message = await ctx.send(embed=embed, view=view)
        view.message = message  # Store message reference for editing
    
    async def create_main_help_embed(self, ctx_or_interaction):
        """Create the main help embed with categories - handles both Context and Interaction"""
        embed = discord.Embed(
            title="🤖 CyBot Help",
            description="*All your needs in one place*\n\n"
                       "**Choose a category below to explore commands, or use `!help <command>` for specific help**",
            color=discord.Color.from_rgb(88, 101, 242),
            timestamp=datetime.now()
        )
        
        # Handle both Context and Interaction objects
        if hasattr(ctx_or_interaction, 'author'):
            # This is a Context object (from command)
            user = ctx_or_interaction.author
        else:
            # This is an Interaction object (from button/dropdown)
            user = ctx_or_interaction.user
        
        # Add bot info
        embed.set_author(
            name=f"Help requested by {user.display_name}",
            icon_url=user.avatar.url if user.avatar else user.default_avatar.url
        )
        
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        # Count commands by category
        command_counts = self.get_command_counts()
        total_commands = sum(command_counts.values())
        
        embed.add_field(
            name="📊 Bot Statistics",
            value=f"📈 **{total_commands}** total commands\n"
                  f"⚡ **{len(self.bot.guilds)}** servers\n"
                  f"👥 **{len(set(self.bot.get_all_members()))}** users\n\n",
            inline=True
        )
        
        # embed.add_field(
        #     name="🎯 Quick Start Guide",
        #     value="• Click buttons below to explore\n"
        #           "• Use dropdown menus to navigate\n"
        #           "• Try `!help <command>` for details",
        #     inline=True
        # )
        
        embed.add_field(
            name="\u200b",  # Empty field for spacing
            value="\u200b",
            inline=True
        )
        
        # Command categories overview
        categories_text = ""
        category_emojis = {
            "Help": "❓",
            "GitHub": "🐙",
            "Verification": "✅", 
            "Info": "ℹ️",
            "Roles": "🎭",
            "GitHubFeed": "📡",
            "GitHubLeaderboard": "🏆",
            "General": "⚙️"
        }
        
        for category, count in command_counts.items():
            emoji = category_emojis.get(category, "📝")
            categories_text += f"{emoji} **{category}**: {count} command{'s' if count != 1 else ''}\n"
        
        embed.add_field(
            name="\n\n📚 Available Categories",
            value=categories_text or "No categories found",
            inline=False
        )
        
        # embed.add_field(
        #     name="💡 Pro Tips",
        #     value="• Commands are **case-insensitive**\n"
        #           "• Use `!help` anytime to return here\n" 
        #           "• Buttons timeout after 5 minutes\n"
        #           "• Some commands need special permissions",
        #     inline=True
        # )
        
        # embed.add_field(
        #     name="🔗 Useful Links",
        #     value="[📖 Bot Guide](https://example.com) • "
        #           "[🐛 Report Issues](https://github.com/example) • "
        #           "[💬 Support](https://discord.gg/example)",
        #     inline=True
        # )
        
        embed.set_footer(
            text="CyBot • Made with ❤ for CyBros OSDC",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        
        return embed
    
    async def create_command_help_embed(self, command):
        """Create detailed help embed for a specific command"""
        embed = discord.Embed(
            title=f"📖 Command: {command.name}",
            description=command.help or "No description available",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        # Command signature
        signature = f"!{command.name}"
        if command.signature:
            signature += f" {command.signature}"
        
        embed.add_field(
            name="💻 Usage",
            value=f"``````",
            inline=False
        )
        
        # Aliases
        if command.aliases:
            aliases_text = ", ".join([f"`!{alias}`" for alias in command.aliases])
            embed.add_field(
                name="🔄 Alternative Commands",
                value=aliases_text,
                inline=True
            )
        
        # Category
        if command.cog:
            category_name = command.cog.qualified_name.replace("Cog", "")
            embed.add_field(
                name="📂 Category",
                value=f"**{category_name}**",
                inline=True
            )
        
        # Permissions
        if hasattr(command.callback, '__commands_checks__'):
            embed.add_field(
                name="🔑 Permissions",
                value="Special permissions required",
                inline=True
            )
        
        # Examples
        examples = self.get_command_examples(command.name)
        if examples:
            embed.add_field(
                name="💡 Examples",
                value=examples,
                inline=False
            )
        
        # Additional info for specific commands
        additional_info = self.get_additional_command_info(command.name)
        if additional_info:
            embed.add_field(
                name="ℹ️ Additional Information",
                value=additional_info,
                inline=False
            )
        
        embed.set_footer(
            text=f"Command help • Use !help to go back",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        
        return embed
    
    async def create_command_not_found_embed(self, command_name):
        """Create embed for when command is not found"""
        embed = discord.Embed(
            title="❌ Command Not Found",
            description=f"Sorry, I couldn't find a command called `{command_name}`",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        # Suggest similar commands
        similar_commands = self.find_similar_commands(command_name)
        if similar_commands:
            suggestions = "\n".join([f"• `!{cmd}`" for cmd in similar_commands[:3]])
            embed.add_field(
                name="💡 Did you mean one of these?",
                value=suggestions,
                inline=False
            )
        
        embed.add_field(
            name="🔍 What you can do",
            value="• Check your spelling and try again\n"
                  "• Use `!help` to see all available commands\n"
                  "• Browse commands by category using the menu below",
            inline=False
        )
        
        embed.set_footer(
            text="Tip: Commands are case-insensitive",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        
        return embed
    
    async def create_category_embed(self, category, bot):
        """Create embed for specific category"""
        category_info = {
            "github": {
                "title": "🐙 GitHub Commands",
                "description": "Manage your GitHub profile, track contributions, and view repository information",
                "color": discord.Color.from_rgb(36, 41, 47),
                "icon": "🐙"
            },
            "verification": {
                "title": "✅ Verification Commands", 
                "description": "Get verified with your LNMIIT email and access the full server",
                "color": discord.Color.green(),
                "icon": "✅"
            },
            "info": {
                "title": "ℹ️ Information Commands",
                "description": "Get detailed information about users, server, and bot statistics",
                "color": discord.Color.blue(),
                "icon": "ℹ️"
            },
            "roles": {
                "title": "🎭 Roles & Management",
                "description": "Role management, leaderboards, and community features",
                "color": discord.Color.purple(),
                "icon": "🎭"
            },
            "feed": {
                "title": "📡 GitHub Feed",
                "description": "Subscribe to repository updates and track open source activity",
                "color": discord.Color.orange(),
                "icon": "📡"
            },
            "leaderboard": {
                "title": "🏆 Leaderboards",
                "description": "View contribution rankings and community statistics",
                "color": discord.Color.gold(),
                "icon": "🏆"
            }
        }
        
        info = category_info.get(category, {
            "title": f"📝 {category.title()} Commands",
            "description": f"Commands in the {category} category",
            "color": discord.Color.blue(),
            "icon": "📝"
        })
        
        embed = discord.Embed(
            title=info["title"],
            description=info["description"],
            color=info["color"],
            timestamp=datetime.now()
        )
        
        # Get commands for this category
        category_commands = []
        for command in bot.commands:
            if command.cog:
                cmd_category = command.cog.qualified_name.replace("Cog", "").lower()
                if cmd_category == category.lower() or (category == "github" and cmd_category in ["github", "githubfeed", "githubleaderboard"]):
                    category_commands.append(command)
        
        # Add commands in this category
        if category_commands:
            commands_text = ""
            for i, command in enumerate(category_commands[:8], 1):  # Limit to 8 commands
                commands_text += f"**{i}. !{command.name}**\n"
                description = command.help or "No description available"
                if len(description) > 60:
                    description = description[:60] + "..."
                commands_text += f"   {description}\n\n"
            
            embed.add_field(
                name=f"📝 Commands ({len(category_commands)})",
                value=commands_text,
                inline=False
            )
        else:
            embed.add_field(
                name="📝 Commands",
                value="No commands found in this category",
                inline=False
            )
        
        embed.add_field(
            name="💡 Usage Tips",
            value=f"• Use `!help <command>` for detailed help\n"
                  f"• All commands start with `!`\n"
                  f"• Commands are case-insensitive",
            inline=True
        )
        
        embed.add_field(
            name="🔄 Navigation", 
            value=f"• Use buttons to go back\n"
                  f"• Select other categories from dropdown\n"
                  f"• Commands timeout after 5 minutes",
            inline=True
        )
        
        embed.set_footer(
            text=f"{info['icon']} {category.title()} Category • CyBot Help System",
            icon_url=bot.user.avatar.url if bot.user.avatar else None
        )
        
        return embed
    
    def get_command_counts(self):
        """Get command count by category"""
        counts = {}
        for command in self.bot.commands:
            if command.cog:
                category = command.cog.qualified_name.replace("Cog", "")
            else:
                category = "General"
            counts[category] = counts.get(category, 0) + 1
        return counts
    
    def get_command_examples(self, command_name):
        """Get examples for specific commands"""
        examples_dict = {
            "link_github": "`!link_github octocat`\n`!link_github your-username`",
            "github_profile": "`!github_profile`\n`!github_profile octocat`",
            "info": "`!info`\n`!info @username`",
            "leaderboard": "`!leaderboard`\n`!leaderboard stars`",
            "github": "`!github subscribe microsoft/vscode`\n`!github list`",
            "help": "`!help`\n`!help link_github`"
        }
        return examples_dict.get(command_name)
    
    def get_additional_command_info(self, command_name):
        """Get additional information for specific commands"""
        info_dict = {
            "link_github": "**Note**: Your GitHub profile must be public for stats to work properly.",
            "github_profile": "**Tip**: Link your GitHub account first using `!link_github`",
            "verify": "**Important**: You need a valid @lnmiit.ac.in email address",
            "github": "**Info**: Repository updates are checked every 5 minutes"
        }
        return info_dict.get(command_name)
    
    def find_similar_commands(self, command_name):
        """Find similar command names using fuzzy matching"""
        command_names = [cmd.name for cmd in self.bot.commands]
        # Add common aliases and variations
        command_names.extend(["github", "verify", "help", "info", "stats", "profile"])
        similar = difflib.get_close_matches(command_name.lower(), command_names, n=3, cutoff=0.5)
        return similar

class MainHelpView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.message = None
    
    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You can't use this menu! Use `!help` to get your own.", ephemeral=True)
            return False
        return True
    
    async def on_timeout(self):
        try:
            # Disable all items when view times out
            for item in self.children:
                item.disabled = True
            
            if self.message:
                await self.message.edit(view=self)
        except discord.NotFound:
            pass  # Message was deleted
        except Exception as e:
            print(f"Error in timeout handler: {e}")
    
    @discord.ui.select(
        placeholder="🔍 Choose a category to explore...",
        options=[
            discord.SelectOption(
                label="GitHub Integration",
                emoji="🐙",
                description="Link profiles, track contributions",
                value="github"
            ),
            discord.SelectOption(
                label="Verification System",
                emoji="✅", 
                description="Email verification and setup",
                value="verification"
            ),
            discord.SelectOption(
                label="User Information",
                emoji="ℹ️",
                description="User profiles and statistics", 
                value="info"
            ),
            discord.SelectOption(
                label="Roles & Management",
                emoji="🎭",
                description="Role assignment and management",
                value="roles"
            ),
            discord.SelectOption(
                label="GitHub Feed",
                emoji="📡",
                description="Repository updates and activity tracking",
                value="feed"
            ),
            discord.SelectOption(
                label="Leaderboards",
                emoji="🏆",
                description="Contribution rankings and achievements",
                value="leaderboard"
            )
        ]
    )
    async def category_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        try:
            category = select.values[0]
            help_cog = interaction.client.get_cog('HelpCog')
            embed = await help_cog.create_category_embed(category, interaction.client)
            view = CategoryView(self.user_id, category)
            view.message = self.message
            
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            print(f"Error in category_select: {e}")
            try:
                await interaction.followup.send("❌ An error occurred while loading the category.", ephemeral=True)
            except:
                pass
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            help_cog = interaction.client.get_cog('HelpCog')
            embed = await help_cog.create_main_help_embed(interaction)  # Fixed: passes interaction
            view = MainHelpView(self.user_id)
            view.message = self.message
            
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            print(f"Error in refresh_help: {e}")
            try:
                await interaction.followup.send("❌ An error occurred while refreshing.", ephemeral=True)
            except:
                pass
    
    @discord.ui.button(label="📊 Bot Info", style=discord.ButtonStyle.primary, emoji="📊")
    async def show_bot_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            bot = interaction.client
            embed = discord.Embed(
                title="🤖 CyBot Information",
                description="Your friendly LNMIIT Discord assistant",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
            
            embed.add_field(
                name="📈 Statistics",
                value=f"**Servers**: {len(bot.guilds)}\n"
                      f"**Users**: {len(set(bot.get_all_members()))}\n"
                      f"**Commands**: {len(bot.commands)}\n"
                      f"**Uptime**: Since bot restart",
                inline=True
            )
            
            embed.add_field(
                name="🛠️ Technical Info",
                value=f"**Python**: 3.8+\n"
                      f"**Discord.py**: 2.0+\n"
                      f"**Prefix**: !\n"
                      f"**Latency**: {round(bot.latency * 1000)}ms",
                inline=True
            )
            
            embed.add_field(
                name="✨ Features",
                value="• Email Verification\n"
                      "• GitHub Integration\n"
                      "• Role Management\n"
                      "• Activity Tracking\n"
                      "• Interactive Help",
                inline=True
            )
            
            embed.set_footer(text="CyBot • Made with ❤️ for LNMIIT")
            
            view = BackToMainView(self.user_id)
            view.message = self.message
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            print(f"Error in show_bot_info: {e}")
            try:
                await interaction.followup.send("❌ An error occurred while showing bot info.", ephemeral=True)
            except:
                pass

class CategoryView(discord.ui.View):
    def __init__(self, user_id, category):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.category = category
        self.message = None
    
    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You can't use this menu! Use `!help` to get your own.", ephemeral=True)
            return False
        return True
    
    async def on_timeout(self):
        try:
            for item in self.children:
                item.disabled = True
            
            if self.message:
                await self.message.edit(view=self)
        except discord.NotFound:
            pass
        except Exception as e:
            print(f"Error in CategoryView timeout: {e}")
    
    @discord.ui.button(label="🏠 Main Menu", style=discord.ButtonStyle.secondary, emoji="🏠")
    async def back_to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            help_cog = interaction.client.get_cog('HelpCog')
            embed = await help_cog.create_main_help_embed(interaction)  # Fixed: passes interaction
            view = MainHelpView(self.user_id)
            view.message = self.message
            
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            print(f"Error in back_to_main: {e}")
            try:
                await interaction.followup.send("❌ An error occurred while going back to main menu.", ephemeral=True)
            except:
                pass
    
    @discord.ui.button(label="📂 Categories", style=discord.ButtonStyle.primary, emoji="📂")
    async def show_categories(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            help_cog = interaction.client.get_cog('HelpCog')
            embed = await help_cog.create_main_help_embed(interaction)  # Fixed: passes interaction
            view = MainHelpView(self.user_id)
            view.message = self.message
            
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            print(f"Error in show_categories: {e}")
            try:
                await interaction.followup.send("❌ An error occurred while showing categories.", ephemeral=True)
            except:
                pass

class CommandHelpView(discord.ui.View):
    def __init__(self, command_name, user_id):
        super().__init__(timeout=300)
        self.command_name = command_name
        self.user_id = user_id
        self.message = None
    
    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You can't use this menu! Use `!help` to get your own.", ephemeral=True)
            return False
        return True
    
    async def on_timeout(self):
        try:
            for item in self.children:
                item.disabled = True
            
            if self.message:
                await self.message.edit(view=self)
        except discord.NotFound:
            pass
        except Exception as e:
            print(f"Error in CommandHelpView timeout: {e}")
    
    @discord.ui.button(label="🏠 Main Menu", style=discord.ButtonStyle.secondary, emoji="🏠")
    async def back_to_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            help_cog = interaction.client.get_cog('HelpCog')
            embed = await help_cog.create_main_help_embed(interaction)  # Fixed: passes interaction
            view = MainHelpView(self.user_id)
            view.message = self.message
            
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            print(f"Error in back_to_help: {e}")
            try:
                await interaction.followup.send("❌ An error occurred while going back to help.", ephemeral=True)
            except:
                pass
    
    @discord.ui.button(label="💻 Try It", style=discord.ButtonStyle.primary, emoji="💻")
    async def try_command(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            embed = discord.Embed(
                title="💡 Ready to try the command?",
                description=f"Type `!{self.command_name}` in the chat to use it!\n\n"
                           f"**Quick Copy**: `!{self.command_name}`",
                color=discord.Color.green()
            )
            embed.set_footer(text="This message is only visible to you")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"Error in try_command: {e}")
            try:
                await interaction.followup.send("❌ An error occurred.", ephemeral=True)
            except:
                pass

class BackToMainView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.message = None
    
    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You can't use this menu! Use `!help` to get your own.", ephemeral=True)
            return False
        return True
    
    async def on_timeout(self):
        try:
            for item in self.children:
                item.disabled = True
            
            if self.message:
                await self.message.edit(view=self)
        except discord.NotFound:
            pass
        except Exception as e:
            print(f"Error in BackToMainView timeout: {e}")
    
    @discord.ui.button(label="🏠 Back to Help Menu", style=discord.ButtonStyle.primary, emoji="🏠")
    async def back_to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            help_cog = interaction.client.get_cog('HelpCog')
            embed = await help_cog.create_main_help_embed(interaction)  # Fixed: passes interaction
            view = MainHelpView(self.user_id)
            view.message = self.message
            
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            print(f"Error in back_to_main: {e}")
            try:
                await interaction.followup.send("❌ An error occurred while going back to main menu.", ephemeral=True)
            except:
                pass

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
