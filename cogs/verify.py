import discord
from discord.ext import commands
import random
import string
from pathlib import Path
from email_validator import validate_email, EmailNotValidError
from config import Config
from utils.emailer import send_email

class VerifyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.MSG_FILE = "verification_msg_id.txt"
        self.pending_verifications = {}
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Setup verification message on bot ready"""
        await self.setup_verification_message()
    
    async def setup_verification_message(self):
        """Create or verify the verification message exists"""
        guild = self.bot.get_guild(Config.GUILD_ID)
        if not guild:
            print("❌ Guild not found")
            return
        
        channel = discord.utils.get(guild.text_channels, name="lnmiit-verification")
        if not channel:
            print("❌ Channel 'lnmiit-verification' not found")
            return
        
        # Check if verification message already exists
        if Path(self.MSG_FILE).exists():
            try:
                with open(self.MSG_FILE, "r") as f:
                    msg_id = int(f.read().strip())
                await channel.fetch_message(msg_id)
                print("✅ Verification message already exists")
                return
            except (discord.NotFound, ValueError):
                print("⚠️ Previous verification message not found, creating new one")
        
        # Create new verification message
        embed = discord.Embed(
            title="🎓 LNMIIT Discord Verification",
            description="React with ✅ to begin email verification process",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📧 Email Requirements",
            value="• Must be a valid LNMIIT email (@lnmiit.ac.in)\n• You'll receive a DM with verification steps",
            inline=False
        )
        
        msg = await channel.send(embed=embed)
        await msg.add_reaction("✅")
        
        with open(self.MSG_FILE, "w") as f:
            f.write(str(msg.id))
        
        print("✅ Created new verification message")
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle reaction-based verification"""
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return
        
        # Check if it's the verification message
        if not Path(self.MSG_FILE).exists():
            return
        
        try:
            with open(self.MSG_FILE, "r") as f:
                verify_msg_id = int(f.read().strip())
        except (ValueError, FileNotFoundError):
            return
        
        if payload.message_id != verify_msg_id or str(payload.emoji) != "✅":
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        
        if not member:
            return
        
        # Check if user is already verified
        lnmiit_role = discord.utils.get(guild.roles, name="lnmiit")
        if lnmiit_role and lnmiit_role in member.roles:
            try:
                await member.send("✅ You are already verified!")
            except discord.Forbidden:
                pass
            return
        
        # Start verification process
        await self.start_verification(member, guild)
    
    async def start_verification(self, member, guild):
        """Start the verification process for a member"""
        try:
            # Send initial DM
            embed = discord.Embed(
                title="📧 Email Verification",
                description="Please enter your LNMIIT email address:",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Format",
                value="Example: 23ucc123@lnmiit.ac.in",
                inline=False
            )
            embed.set_footer(text="You have 2 minutes to respond")
            
            await member.send(embed=embed)
        except discord.Forbidden:
            print(f"❌ Cannot send DM to {member.display_name}")
            return
        
        def check(m):
            return m.author.id == member.id and isinstance(m.channel, discord.DMChannel)
        
        try:
            # Get email from user
            email_msg = await self.bot.wait_for('message', check=check, timeout=120)
            email = email_msg.content.strip().lower()
            
            # Validate email
            try:
                valid = validate_email(email)
                email = valid.email
            except EmailNotValidError:
                await member.send("❌ Invalid email format. Please try again.")
                return
            
            if not email.endswith("@lnmiit.ac.in"):
                await member.send("❌ Email must end with '@lnmiit.ac.in'. Please try again.")
                return
            
            # Generate and send OTP
            otp = ''.join(random.choices(string.digits, k=6))
            self.pending_verifications[member.id] = (email, otp)
            
            email_sent = await send_email(email, otp)
            if not email_sent:
                await member.send("❌ Failed to send OTP. Please contact an admin.")
                return
            
            embed = discord.Embed(
                title="📨 OTP Sent",
                description=f"Please check your email: {email}",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Next Step",
                value="Reply with the 6-digit code from your email",
                inline=False
            )
            embed.set_footer(text="You have 2 minutes to respond")
            
            await member.send(embed=embed)
            
            # Get OTP from user
            otp_msg = await self.bot.wait_for('message', check=check, timeout=120)
            
            if member.id not in self.pending_verifications:
                await member.send("❌ Verification session expired. Please try again.")
                return
            
            stored_email, stored_otp = self.pending_verifications[member.id]
            
            if otp_msg.content.strip() != stored_otp:
                await member.send("❌ Incorrect OTP. Please try again.")
                del self.pending_verifications[member.id]
                return
            
            # Assign roles
            await self.assign_roles(member, guild, email)
            
            # Clean up
            del self.pending_verifications[member.id]
            
        except Exception as e:
            await member.send("❌ Verification failed. Please try again.")
            if member.id in self.pending_verifications:
                del self.pending_verifications[member.id]
            print(f"Verification error for {member.display_name}: {e}")
    
    async def assign_roles(self, member, guild, email):
        """Assign appropriate roles to verified member"""
        roles_assigned = []
        
        # Assign LNMIIT role
        lnmiit_role = discord.utils.get(guild.roles, name="lnmiit")
        if not lnmiit_role:
            lnmiit_role = await guild.create_role(name="lnmiit", color=discord.Color.blue())
        
        if lnmiit_role not in member.roles:
            await member.add_roles(lnmiit_role)
            roles_assigned.append("lnmiit")
        
        # Assign batch role based on email
        batch_year = email[:2]
        batch_role_name = f"Y{batch_year}"
        batch_role = discord.utils.get(guild.roles, name=batch_role_name)
        
        if not batch_role:
            batch_role = await guild.create_role(name=batch_role_name, color=discord.Color.random())
        
        if batch_role not in member.roles:
            await member.add_roles(batch_role)
            roles_assigned.append(batch_role_name)
        
        # Send success message
        embed = discord.Embed(
            title="🎉 Verification Successful!",
            description=f"Welcome to the LNMIIT Discord server!",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Roles Assigned",
            value=", ".join(roles_assigned) if roles_assigned else "No new roles",
            inline=False
        )
        embed.add_field(
            name="Next Steps",
            value="You can now access all server channels and features!",
            inline=False
        )
        
        await member.send(embed=embed)
        print(f"✅ Successfully verified {member.display_name} with email {email}")

async def setup(bot):
    await bot.add_cog(VerifyCog(bot))
