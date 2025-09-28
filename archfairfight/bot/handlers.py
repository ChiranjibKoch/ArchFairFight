"""
Bot command handlers for ArchFairFight.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from pyrogram import Client, filters
from pyrogram.types import Message, User, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import structlog

from ..database import UserOps, ChallengeOps, FightOps
from ..database.models import User as UserModel, Challenge, ChallengeStatus, FightType
from ..challenge import ChallengeManager
from .utils import get_user_mention, parse_user_identifier, format_user_stats, format_leaderboard

logger = structlog.get_logger(__name__)


def setup_handlers(client: Client):
    """Setup all bot handlers."""
    
    @client.on_message(filters.command("start"))
    async def start_handler(client: Client, message: Message):
        """Handle /start command."""
        user_ops = UserOps()
        
        # Create or get user
        user_data = UserModel(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        
        existing_user = await user_ops.get_user_by_telegram_id(message.from_user.id)
        if not existing_user:
            await user_ops.create_user(user_data)
            welcome_msg = (
                f"🎉 **Welcome to ArchFairFight!** {get_user_mention(message.from_user)}\n\n"
                f"🥊 Ready to challenge your friends to epic voice chat battles?\n\n"
                f"📋 **Available Commands:**\n"
                f"• `/challenge @username` - Challenge someone to a fight\n"
                f"• `/stats` - View your fight statistics\n"
                f"• `/leaderboard` - See top fighters\n"
                f"• `/help` - Get help and instructions\n\n"
                f"Let the battles begin! ⚔️"
            )
        else:
            welcome_msg = (
                f"👋 **Welcome back, fighter!** {get_user_mention(message.from_user)}\n\n"
                f"Ready for another round? Use `/challenge @username` to start a fight!"
            )
        
        await message.reply_text(welcome_msg)
    
    @client.on_message(filters.command("help"))
    async def help_handler(client: Client, message: Message):
        """Handle /help command."""
        help_text = (
            f"🔥 **ArchFairFight Help** 🔥\n\n"
            f"**How to Fight:**\n"
            f"1️⃣ Use `/challenge @opponent` to challenge someone\n"
            f"2️⃣ They get Accept/Deny buttons to respond\n"
            f"3️⃣ If accepted, choose fight type (Timing/Volume)\n"
            f"4️⃣ Both participants join the voice chat\n"
            f"5️⃣ Fight automatically recorded and judged!\n\n"
            f"**Fight Types:**\n"
            f"⏱ **Timing Fight:** Stay in VC as long as possible\n"
            f"🔊 **Volume Fight:** Most active speaker wins\n\n"
            f"**Commands:**\n"
            f"• `/challenge @user` - Start a challenge\n"
            f"• `/stats` - Your fight statistics\n"
            f"• `/leaderboard` - Top 10 fighters\n"
            f"• `/cancel` - Cancel pending challenges\n\n"
            f"**Tips:**\n"
            f"• You have 30 seconds to join after accepting\n"
            f"• Fights are automatically recorded\n"
            f"• AI judges the winner based on activity\n\n"
            f"Ready to become a legend? ⚔️"
        )
        await message.reply_text(help_text)
    
    @client.on_message(filters.command("challenge"))
    async def challenge_handler(client: Client, message: Message):
        """Handle /challenge command."""
        if len(message.command) < 2:
            await message.reply_text(
                "❌ **Invalid usage!**\n\n"
                "Use: `/challenge @username` or `/challenge user_id`\n\n"
                "Example: `/challenge @john_doe`"
            )
            return
        
        challenger = message.from_user
        opponent_identifier = message.command[1]
        
        # Parse opponent identifier
        username, user_id = parse_user_identifier(opponent_identifier)
        
        try:
            # Get opponent user object
            if username:
                try:
                    opponent = await client.get_users(username)
                except Exception:
                    await message.reply_text(f"❌ User @{username} not found!")
                    return
            elif user_id:
                try:
                    opponent = await client.get_users(user_id)
                except Exception:
                    await message.reply_text(f"❌ User with ID {user_id} not found!")
                    return
            else:
                await message.reply_text("❌ Invalid user identifier!")
                return
            
            # Check if trying to challenge self
            if opponent.id == challenger.id:
                await message.reply_text("❌ You can't challenge yourself!")
                return
            
            # Check if opponent is a bot
            if opponent.is_bot:
                await message.reply_text("❌ You can't challenge bots!")
                return
            
            # Create challenge
            challenge_manager = ChallengeManager()
            challenge_id = await challenge_manager.create_challenge(
                challenger_id=challenger.id,
                opponent_id=opponent.id,
                chat_id=message.chat.id
            )
            
            if not challenge_id:
                await message.reply_text("❌ Failed to create challenge. Please try again!")
                return
            
            # Send challenge message to opponent
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Accept", callback_data=f"accept_{challenge_id}"),
                    InlineKeyboardButton("❌ Decline", callback_data=f"decline_{challenge_id}")
                ]
            ])
            
            challenge_text = (
                f"⚔️ **Challenge Received!**\n\n"
                f"🥊 {get_user_mention(challenger)} has challenged you to a voice chat fight!\n\n"
                f"Will you accept the challenge?"
            )
            
            try:
                sent_message = await client.send_message(
                    opponent.id,
                    challenge_text,
                    reply_markup=keyboard
                )
                
                # Update challenge with message info
                challenge_ops = ChallengeOps()
                await challenge_ops.update_challenge_status(
                    challenge_id,
                    ChallengeStatus.PENDING,
                    challenge_message_id=sent_message.id
                )
                
                await message.reply_text(
                    f"✅ Challenge sent to {get_user_mention(opponent)}!\n"
                    f"Waiting for their response..."
                )
                
            except Exception as e:
                logger.error("Failed to send challenge message", error=str(e))
                await message.reply_text(
                    "❌ Couldn't send challenge to the user. They might have blocked the bot or disabled private messages."
                )
                
        except Exception as e:
            logger.error("Error in challenge handler", error=str(e))
            await message.reply_text("❌ An error occurred while creating the challenge.")
    
    @client.on_message(filters.command("stats"))
    async def stats_handler(client: Client, message: Message):
        """Handle /stats command."""
        user_ops = UserOps()
        user = await user_ops.get_user_by_telegram_id(message.from_user.id)
        
        if not user:
            await message.reply_text("❌ User not found. Use /start to register!")
            return
        
        stats_text = format_user_stats(user.dict())
        await message.reply_text(stats_text)
    
    @client.on_message(filters.command("leaderboard"))
    async def leaderboard_handler(client: Client, message: Message):
        """Handle /leaderboard command."""
        user_ops = UserOps()
        top_users = await user_ops.get_leaderboard(limit=10)
        
        leaderboard_text = format_leaderboard([user.dict() for user in top_users])
        await message.reply_text(leaderboard_text)
    
    @client.on_callback_query()
    async def callback_handler(client: Client, callback_query: CallbackQuery):
        """Handle callback queries from inline keyboards."""
        data = callback_query.data
        user = callback_query.from_user
        
        if data.startswith("accept_"):
            challenge_id = data.split("_", 1)[1]
            await handle_challenge_response(client, callback_query, challenge_id, True)
            
        elif data.startswith("decline_"):
            challenge_id = data.split("_", 1)[1]
            await handle_challenge_response(client, callback_query, challenge_id, False)
            
        elif data.startswith("fight_type_"):
            parts = data.split("_", 2)
            fight_type = parts[2]
            challenge_id = parts[1] if len(parts) > 2 else parts[1]
            await handle_fight_type_selection(client, callback_query, challenge_id, fight_type)


async def handle_challenge_response(client: Client, callback_query: CallbackQuery, 
                                  challenge_id: str, accepted: bool):
    """Handle challenge accept/decline response."""
    challenge_ops = ChallengeOps()
    challenge_manager = ChallengeManager()
    
    challenge = await challenge_ops.get_challenge(challenge_id)
    if not challenge:
        await callback_query.answer("❌ Challenge not found!")
        return
    
    if challenge.opponent_id != callback_query.from_user.id:
        await callback_query.answer("❌ This challenge is not for you!")
        return
    
    if challenge.status != ChallengeStatus.PENDING:
        await callback_query.answer("❌ This challenge has already been responded to!")
        return
    
    if accepted:
        # Update challenge status
        await challenge_ops.update_challenge_status(challenge_id, ChallengeStatus.ACCEPTED)
        
        # Show fight type selection
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⏱ Timing Fight", callback_data=f"fight_type_{challenge_id}_timing"),
                InlineKeyboardButton("🔊 Volume Fight", callback_data=f"fight_type_{challenge_id}_volume")
            ]
        ])
        
        await callback_query.edit_message_text(
            "✅ **Challenge Accepted!**\n\n"
            "Choose your fight type:",
            reply_markup=keyboard
        )
        
        # Notify challenger
        try:
            challenger = await client.get_users(challenge.challenger_id)
            await client.send_message(
                challenge.challenger_id,
                f"🎉 {get_user_mention(callback_query.from_user)} accepted your challenge!\n"
                f"They're now selecting the fight type..."
            )
        except Exception as e:
            logger.error("Failed to notify challenger", error=str(e))
            
    else:
        # Update challenge status
        await challenge_ops.update_challenge_status(challenge_id, ChallengeStatus.DECLINED)
        
        await callback_query.edit_message_text(
            "❌ **Challenge Declined**\n\n"
            "Maybe next time! 🤝"
        )
        
        # Notify challenger
        try:
            await client.send_message(
                challenge.challenger_id,
                f"💔 {get_user_mention(callback_query.from_user)} declined your challenge.\n"
                f"Better luck next time!"
            )
        except Exception as e:
            logger.error("Failed to notify challenger", error=str(e))


async def handle_fight_type_selection(client: Client, callback_query: CallbackQuery, 
                                    challenge_id: str, fight_type: str):
    """Handle fight type selection."""
    challenge_ops = ChallengeOps()
    challenge_manager = ChallengeManager()
    
    challenge = await challenge_ops.get_challenge(challenge_id)
    if not challenge:
        await callback_query.answer("❌ Challenge not found!")
        return
    
    # Update challenge with fight type
    fight_type_enum = FightType.TIMING if fight_type == "timing" else FightType.VOLUME
    await challenge_ops.update_challenge_status(
        challenge_id, 
        ChallengeStatus.IN_PROGRESS,
        fight_type=fight_type_enum,
        fight_starts_at=datetime.utcnow()
    )
    
    await callback_query.edit_message_text(
        f"⚔️ **Fight Starting!**\n\n"
        f"🎯 **Type:** {fight_type.title()}\n"
        f"⏰ **Join Time:** 30 seconds\n\n"
        f"Get ready to join the voice chat!"
    )
    
    # Start the fight
    try:
        success = await challenge_manager.start_fight(challenge_id)
        if success:
            # Notify both participants
            challenger = await client.get_users(challenge.challenger_id)
            opponent = await client.get_users(challenge.opponent_id)
            
            fight_message = (
                f"🔥 **FIGHT STARTED!** 🔥\n\n"
                f"👥 {get_user_mention(challenger)} vs {get_user_mention(opponent)}\n"
                f"🎯 **Type:** {fight_type.title()}\n\n"
                f"⚠️ You have 30 seconds to join the voice chat!\n"
                f"🤖 Userbots are joining to monitor the fight..."
            )
            
            await client.send_message(challenge.challenger_id, fight_message)
            await client.send_message(challenge.opponent_id, fight_message)
            
        else:
            await callback_query.answer("❌ Failed to start fight!")
            
    except Exception as e:
        logger.error("Failed to start fight", error=str(e))
        await callback_query.answer("❌ Error starting fight!")