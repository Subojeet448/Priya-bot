"""
PRIYA AI BOT - ULTIMATE EDITION
Complete Production Bot with Social, Shop, Admin & Gaming Features
Version: 3.0.0
Author: Subojeet Mandal
"""

import os
import time
import asyncio
import httpx
import base64
import re
import zipfile
import threading
import json
import random
import string
import hashlib
import hmac
import pickle
import sqlite3
import shutil
import logging
import uuid
import csv
from datetime import datetime, timedelta
from io import BytesIO, StringIO
from functools import wraps
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict, deque

from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash, make_response
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, BotCommand
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

# ==================== CONFIGURATION & LOGGING ====================

load_dotenv()

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment
ENV = os.getenv("ENVIRONMENT", "production")
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Single bot token
CONFIG_VERSION = "3.0.0"

# 8 OpenRouter API Keys for rotation
OPENROUTER_KEYS = [
    os.getenv("OPENROUTER_KEY_1", "key1_here"),
    os.getenv("OPENROUTER_KEY_2", "key2_here"),
    os.getenv("OPENROUTER_KEY_3", "key3_here"),
    os.getenv("OPENROUTER_KEY_4", "key4_here"),
    os.getenv("OPENROUTER_KEY_5", "key5_here"),
    os.getenv("OPENROUTER_KEY_6", "key6_here"),
    os.getenv("OPENROUTER_KEY_7", "key7_here"),
    os.getenv("OPENROUTER_KEY_8", "key8_here")
]

# Remove empty keys
OPENROUTER_KEYS = [key for key in OPENROUTER_KEYS if key and key != "key1_here"]

# Conversation states
(
    SELECTING_ACTION,
    CONNECT_USERNAME,
    CHAT_MESSAGE,
    GROUP_NAME,
    SHOP_BUY,
    SHOP_QUANTITY,
    REPORT_REASON,
    BROADCAST_MESSAGE,
    FEATURE_TOGGLE,
    MENU_EDIT,
    GAME_DIFFICULTY,
    AWAITING_REPLY,
    AWAITING_FEEDBACK,
    ENTERING_PROMO,
    ENTERING_AMOUNT
) = range(15)

# ==================== DATABASE SETUP ====================

conn = sqlite3.connect("superbase.db", check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Enable foreign keys
cur.execute("PRAGMA foreign_keys = ON")

# ==================== ENUMS ====================

class UserRole(Enum):
    USER = "user"
    PREMIUM = "premium"
    VIP = "vip"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class Permission(Enum):
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_USERS = "manage_users"
    MANAGE_PLANS = "manage_plans"
    MANAGE_BANS = "manage_bans"
    MANAGE_BROADCAST = "manage_broadcast"
    VIEW_LOGS = "view_logs"
    MANAGE_ADMINS = "manage_admins"
    MANAGE_FEATURES = "manage_features"
    MANAGE_SHOP = "manage_shop"
    MANAGE_GAMES = "manage_games"
    MANAGE_SOCIAL = "manage_social"

# ==================== COMPLETE DATABASE SCHEMA ====================

def init_database():
    """Initialize complete database schema"""
    
    # Schema version tracking
    cur.execute("""
    CREATE TABLE IF NOT EXISTS schema_versions (
        version TEXT PRIMARY KEY,
        applied_at INTEGER,
        description TEXT
    )
    """)
    
    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        language TEXT DEFAULT 'en',
        role TEXT DEFAULT 'user',
        plan_id TEXT DEFAULT 'free',
        plan_expiry INTEGER,
        voice_mode INTEGER DEFAULT 0,
        voice_engine TEXT DEFAULT 'gtts',
        voice_name TEXT DEFAULT '',
        daily_requests INTEGER DEFAULT 0,
        total_requests INTEGER DEFAULT 0,
        last_request_date TEXT,
        created_at INTEGER,
        updated_at INTEGER,
        is_verified INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        telegram_id TEXT UNIQUE,
        email TEXT,
        phone TEXT,
        notes TEXT,
        metadata TEXT,
        preferences TEXT,
        coin_balance INTEGER DEFAULT 1000,
        total_coins_earned INTEGER DEFAULT 1000,
        total_coins_spent INTEGER DEFAULT 0,
        referral_code TEXT UNIQUE,
        referred_by TEXT,
        last_login INTEGER,
        login_count INTEGER DEFAULT 0,
        theme_preference TEXT DEFAULT 'default',
        chat_bubble_style TEXT DEFAULT 'default',
        emoji_pack TEXT DEFAULT 'default',
        voice_style TEXT DEFAULT 'default'
    )
    """)
    
    # User Levels & XP
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_levels (
        user_id TEXT PRIMARY KEY,
        level INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,
        total_xp INTEGER DEFAULT 0,
        activity_score INTEGER DEFAULT 0,
        next_level_xp INTEGER DEFAULT 100,
        created_at INTEGER,
        updated_at INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    """)
    
    # Friend System
    cur.execute("""
    CREATE TABLE IF NOT EXISTS friend_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user TEXT NOT NULL,
        to_user TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at INTEGER,
        updated_at INTEGER,
        FOREIGN KEY(from_user) REFERENCES users(user_id),
        FOREIGN KEY(to_user) REFERENCES users(user_id),
        UNIQUE(from_user, to_user)
    )
    """)
    
    # Friends list
    cur.execute("""
    CREATE TABLE IF NOT EXISTS friends (
        user_id TEXT,
        friend_id TEXT,
        created_at INTEGER,
        PRIMARY KEY(user_id, friend_id),
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        FOREIGN KEY(friend_id) REFERENCES users(user_id)
    )
    """)
    
    # Direct Chat Sessions
    cur.execute("""
    CREATE TABLE IF NOT EXISTS direct_chat_sessions (
        id TEXT PRIMARY KEY,
        user_a TEXT NOT NULL,
        user_b TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        smart_mode INTEGER DEFAULT 0,
        auto_translate INTEGER DEFAULT 0,
        spam_filter INTEGER DEFAULT 1,
        created_at INTEGER,
        last_message_at INTEGER,
        FOREIGN KEY(user_a) REFERENCES users(user_id),
        FOREIGN KEY(user_b) REFERENCES users(user_id),
        UNIQUE(user_a, user_b)
    )
    """)
    
    # Chat Messages
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        from_user TEXT NOT NULL,
        message TEXT,
        is_forwarded INTEGER DEFAULT 0,
        translated_message TEXT,
        created_at INTEGER,
        FOREIGN KEY(session_id) REFERENCES direct_chat_sessions(id),
        FOREIGN KEY(from_user) REFERENCES users(user_id)
    )
    """)
    
    # Block System
    cur.execute("""
    CREATE TABLE IF NOT EXISTS blocks (
        user_id TEXT NOT NULL,
        blocked_user_id TEXT NOT NULL,
        created_at INTEGER,
        PRIMARY KEY(user_id, blocked_user_id),
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        FOREIGN KEY(blocked_user_id) REFERENCES users(user_id)
    )
    """)
    
    # Group Rooms
    cur.execute("""
    CREATE TABLE IF NOT EXISTS group_rooms (
        id TEXT PRIMARY KEY,
        name TEXT,
        description TEXT,
        created_by TEXT,
        is_private INTEGER DEFAULT 0,
        max_members INTEGER DEFAULT 50,
        created_at INTEGER,
        updated_at INTEGER,
        FOREIGN KEY(created_by) REFERENCES users(user_id)
    )
    """)
    
    # Group Members
    cur.execute("""
    CREATE TABLE IF NOT EXISTS group_members (
        room_id TEXT,
        user_id TEXT,
        role TEXT DEFAULT 'member',
        joined_at INTEGER,
        last_read INTEGER,
        PRIMARY KEY(room_id, user_id),
        FOREIGN KEY(room_id) REFERENCES group_rooms(id),
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    """)
    
    # Group Messages
    cur.execute("""
    CREATE TABLE IF NOT EXISTS group_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id TEXT,
        user_id TEXT,
        message TEXT,
        created_at INTEGER,
        FOREIGN KEY(room_id) REFERENCES group_rooms(id),
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    """)
    
    # SHOP SYSTEM TABLES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS shop_categories (
        id TEXT PRIMARY KEY,
        name TEXT,
        description TEXT,
        icon TEXT,
        display_order INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at INTEGER
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS shop_items (
        id TEXT PRIMARY KEY,
        category_id TEXT,
        name TEXT,
        description TEXT,
        price INTEGER,
        item_type TEXT,
        item_value TEXT,
        stock INTEGER DEFAULT -1,
        is_active INTEGER DEFAULT 1,
        is_limited INTEGER DEFAULT 0,
        purchase_limit INTEGER DEFAULT 0,
        icon TEXT,
        created_at INTEGER,
        updated_at INTEGER,
        FOREIGN KEY(category_id) REFERENCES shop_categories(id)
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        item_id TEXT,
        quantity INTEGER,
        price_paid INTEGER,
        purchased_at INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        FOREIGN KEY(item_id) REFERENCES shop_items(id)
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_inventory (
        user_id TEXT,
        item_id TEXT,
        quantity INTEGER DEFAULT 1,
        acquired_at INTEGER,
        is_equipped INTEGER DEFAULT 0,
        PRIMARY KEY(user_id, item_id),
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        FOREIGN KEY(item_id) REFERENCES shop_items(id)
    )
    """)
    
    # GAMES TABLES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS games (
        id TEXT PRIMARY KEY,
        name TEXT,
        description TEXT,
        game_type TEXT,
        min_players INTEGER DEFAULT 1,
        max_players INTEGER DEFAULT 2,
        is_active INTEGER DEFAULT 1,
        coin_reward INTEGER DEFAULT 10,
        xp_reward INTEGER DEFAULT 5,
        created_at INTEGER
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS game_sessions (
        id TEXT PRIMARY KEY,
        game_id TEXT,
        status TEXT DEFAULT 'waiting',
        created_by TEXT,
        created_at INTEGER,
        started_at INTEGER,
        ended_at INTEGER,
        winner TEXT,
        FOREIGN KEY(game_id) REFERENCES games(id),
        FOREIGN KEY(created_by) REFERENCES users(user_id)
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS game_players (
        session_id TEXT,
        user_id TEXT,
        score INTEGER DEFAULT 0,
        joined_at INTEGER,
        PRIMARY KEY(session_id, user_id),
        FOREIGN KEY(session_id) REFERENCES game_sessions(id),
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS game_moves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        user_id TEXT,
        move_data TEXT,
        created_at INTEGER,
        FOREIGN KEY(session_id) REFERENCES game_sessions(id),
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS quiz_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT,
        options TEXT,
        correct_answer INTEGER,
        difficulty TEXT DEFAULT 'medium',
        category TEXT,
        points INTEGER DEFAULT 10,
        created_at INTEGER
    )
    """)
    
    # BADGES & ACHIEVEMENTS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS badges (
        id TEXT PRIMARY KEY,
        name TEXT,
        description TEXT,
        icon TEXT,
        requirement_type TEXT,
        requirement_value INTEGER,
        coin_reward INTEGER DEFAULT 0,
        xp_reward INTEGER DEFAULT 0,
        created_at INTEGER
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_badges (
        user_id TEXT,
        badge_id TEXT,
        earned_at INTEGER,
        PRIMARY KEY(user_id, badge_id),
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        FOREIGN KEY(badge_id) REFERENCES badges(id)
    )
    """)
    
    # REPORTS & MODERATION
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reporter_id TEXT,
        reported_user_id TEXT,
        reason TEXT,
        details TEXT,
        status TEXT DEFAULT 'pending',
        created_at INTEGER,
        resolved_at INTEGER,
        resolved_by TEXT,
        FOREIGN KEY(reporter_id) REFERENCES users(user_id),
        FOREIGN KEY(reported_user_id) REFERENCES users(user_id)
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS moderation_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        moderator_id TEXT,
        action TEXT,
        target_user TEXT,
        reason TEXT,
        created_at INTEGER,
        FOREIGN KEY(moderator_id) REFERENCES users(user_id),
        FOREIGN KEY(target_user) REFERENCES users(user_id)
    )
    """)
    
    # DYNAMIC MENU SYSTEM
    cur.execute("""
    CREATE TABLE IF NOT EXISTS menus (
        id TEXT PRIMARY KEY,
        name TEXT,
        parent_id TEXT,
        menu_type TEXT DEFAULT 'user',  -- user, admin, both
        command TEXT,
        data TEXT,
        icon TEXT,
        display_order INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        required_permission TEXT,
        created_at INTEGER,
        updated_at INTEGER
    )
    """)
    
    # USER SESSIONS FOR CHAT
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        session_type TEXT,
        session_data TEXT,
        created_at INTEGER,
        expires_at INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    """)
    
    # DAILY COINS CLAIM
    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_claims (
        user_id TEXT PRIMARY KEY,
        last_claim INTEGER,
        streak INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    """)
    
    # SYSTEM CONFIG
    cur.execute("""
    CREATE TABLE IF NOT EXISTS system_config (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER,
        updated_by TEXT
    )
    """)
    
    # Insert default categories if not exists
    cur.execute("SELECT COUNT(*) FROM shop_categories")
    if cur.fetchone()[0] == 0:
        categories = [
            ("cosmetics", "🎨 Cosmetics", "Profile themes, chat bubbles & more", "🎨", 1),
            ("features", "⚡ Features", "Unlock premium features", "⚡", 2),
            ("powerups", "🤖 Power-ups", "AI enhancement items", "🤖", 3),
            ("utility", "🛠️ Utility", "Useful items & tools", "🛠️", 4)
        ]
        for cat_id, name, desc, icon, order in categories:
            cur.execute("""
                INSERT INTO shop_categories (id, name, description, icon, display_order, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (cat_id, name, desc, icon, order, int(time.time())))
    
    # Insert default shop items
    cur.execute("SELECT COUNT(*) FROM shop_items")
    if cur.fetchone()[0] == 0:
        items = [
            # Cosmetics
            ("theme_dark", "cosmetics", "🌙 Dark Theme", "Dark mode for your profile", 500, "theme", "dark", -1),
            ("theme_neon", "cosmetics", "✨ Neon Theme", "Bright neon profile theme", 800, "theme", "neon", -1),
            ("bubble_rounded", "cosmetics", "💬 Rounded Bubbles", "Rounded chat bubbles", 300, "bubble", "rounded", -1),
            ("bubble_modern", "cosmetics", "🌟 Modern Bubbles", "Modern chat bubble style", 400, "bubble", "modern", -1),
            ("emoji_premium", "cosmetics", "😎 Premium Emojis", "Exclusive emoji pack", 600, "emoji", "premium", -1),
            ("voice_robot", "cosmetics", "🤖 Robot Voice", "Robot style voice", 700, "voice", "robot", -1),
            
            # Features
            ("fast_ai", "features", "⚡ Fast AI", "Priority AI responses", 1000, "feature", "fast_ai", -1),
            ("long_memory", "features", "🧠 Long Memory", "Extended conversation memory", 1500, "feature", "long_memory", -1),
            ("creative_mode", "features", "🎨 Creative Mode", "More creative responses", 1200, "feature", "creative_mode", -1),
            
            # Power-ups
            ("xp_boost", "powerups", "📈 XP Boost", "2x XP for 24 hours", 800, "powerup", "xp_boost", 10),
            ("coin_boost", "powerups", "💰 Coin Boost", "2x coins for 24 hours", 1000, "powerup", "coin_boost", 10),
            
            # Utility
            ("name_change", "utility", "📝 Name Change", "Change your username", 2000, "utility", "name_change", 1),
            ("profile_badge", "utility", "🏅 Special Badge", "Get a unique profile badge", 3000, "utility", "profile_badge", 1)
        ]
        for item_id, cat_id, name, desc, price, item_type, item_value, stock in items:
            cur.execute("""
                INSERT INTO shop_items (id, category_id, name, description, price, item_type, item_value, stock, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (item_id, cat_id, name, desc, price, item_type, item_value, stock, int(time.time())))
    
    # Insert default games
    cur.execute("SELECT COUNT(*) FROM games")
    if cur.fetchone()[0] == 0:
        games = [
            ("quiz", "📝 Quiz Battle", "Test your knowledge", "quiz", 1, 2, 20, 15),
            ("memory", "🧠 Memory Game", "Test your memory", "memory", 1, 1, 15, 10),
            ("reaction", "⚡ Reaction Test", "How fast are you?", "reaction", 1, 2, 10, 5),
            ("puzzle", "🧩 Puzzle Challenge", "Solve the puzzle", "puzzle", 1, 1, 25, 20)
        ]
        for game_id, name, desc, g_type, min_p, max_p, coin_reward, xp_reward in games:
            cur.execute("""
                INSERT INTO games (id, name, description, game_type, min_players, max_players, coin_reward, xp_reward, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (game_id, name, desc, g_type, min_p, max_p, coin_reward, xp_reward, int(time.time())))
    
    # Insert default badges
    cur.execute("SELECT COUNT(*) FROM badges")
    if cur.fetchone()[0] == 0:
        badges = [
            ("beginner", "🌟 Beginner", "Complete 10 chats", "messages", 10, 100, 50),
            ("social", "🤝 Socialite", "Make 5 friends", "friends", 5, 200, 100),
            ("gamer", "🎮 Gamer", "Play 10 games", "games", 10, 300, 150),
            ("streak_7", "🔥 7 Day Streak", "7 day login streak", "streak", 7, 500, 200),
            ("streak_30", "⚡ 30 Day Streak", "30 day login streak", "streak", 30, 2000, 1000),
            ("shopper", "🛍️ Shopper", "Buy 5 shop items", "purchases", 5, 400, 150)
        ]
        for badge_id, name, desc, req_type, req_value, coin, xp in badges:
            cur.execute("""
                INSERT INTO badges (id, name, description, icon, requirement_type, requirement_value, coin_reward, xp_reward, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (badge_id, name, desc, "🏆", req_type, req_value, coin, xp, int(time.time())))
    
    # Insert default menus
    cur.execute("SELECT COUNT(*) FROM menus")
    if cur.fetchone()[0] == 0:
        menus = [
            # User menus
            ("user_main", "📱 Main Menu", None, "user", "main", None, "🏠", 1),
            ("user_profile", "👤 My Profile", "user_main", "user", "profile", None, "👤", 1),
            ("user_friends", "🤝 Friends", "user_main", "user", "friends", None, "🤝", 2),
            ("user_shop", "🛒 Shop", "user_main", "user", "shop", None, "🛒", 3),
            ("user_games", "🎮 Games", "user_main", "user", "games", None, "🎮", 4),
            ("user_chat", "💬 Direct Chat", "user_main", "user", "connect", None, "💬", 5),
            
            # Admin menus
            ("admin_main", "⚙️ Admin Panel", None, "admin", "admin", None, "⚙️", 1),
            ("admin_users", "👥 Manage Users", "admin_main", "admin", "admin_users", None, "👥", 1, "manage_users"),
            ("admin_features", "⚡ Features", "admin_main", "admin", "admin_features", None, "⚡", 2, "manage_features"),
            ("admin_shop", "🛍️ Manage Shop", "admin_main", "admin", "admin_shop", None, "🛍️", 3, "manage_shop"),
            ("admin_games", "🎲 Manage Games", "admin_main", "admin", "admin_games", None, "🎲", 4, "manage_games"),
            ("admin_broadcast", "📢 Broadcast", "admin_main", "admin", "broadcast", None, "📢", 5, "manage_broadcast"),
            ("admin_stats", "📊 Statistics", "admin_main", "admin", "stats", None, "📊", 6, "view_analytics"),
            ("admin_clear", "🗑️ Clear Database", "admin_main", "admin", "clearall", None, "🗑️", 7, "manage_users")
        ]
        for menu_id, name, parent, menu_type, cmd, data, icon, order, *perms in menus:
            perm = perms[0] if perms else None
            cur.execute("""
                INSERT INTO menus (id, name, parent_id, menu_type, command, data, icon, display_order, required_permission, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (menu_id, name, parent, menu_type, cmd, data, icon, order, perm, int(time.time())))
    
    # Insert default config
    cur.execute("SELECT COUNT(*) FROM system_config")
    if cur.fetchone()[0] == 0:
        configs = [
            ("daily_coins", "1000"),
            ("max_friends", "100"),
            ("max_group_members", "50"),
            ("maintenance_mode", "false"),
            ("welcome_message", "Welcome to Priya AI Bot! 🎉"),
            ("default_language", "en"),
            ("xp_per_message", "10"),
            ("coins_per_message", "5")
        ]
        for key, value in configs:
            cur.execute("""
                INSERT INTO system_config (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, int(time.time())))
    
    conn.commit()
    logger.info("✅ Database schema initialized successfully")

# Initialize database
init_database()

# ==================== CACHE MANAGER ====================

class CacheManager:
    """Simple cache manager with SQLite backend"""
    
    def __init__(self, default_ttl=300):
        self.default_ttl = default_ttl
        self.memory_cache = {}
        self.cache_timestamps = {}
    
    def get(self, key):
        """Get value from cache"""
        # Check memory cache first
        if key in self.memory_cache:
            if key in self.cache_timestamps and self.cache_timestamps[key] > time.time():
                return self.memory_cache[key]
        
        # Check database cache
        cur.execute(
            "SELECT value FROM cache WHERE key=? AND (expires_at IS NULL OR expires_at > ?)",
            (key, int(time.time()))
        )
        row = cur.fetchone()
        if row:
            value = json.loads(row[0])
            # Store in memory
            self.memory_cache[key] = value
            self.cache_timestamps[key] = time.time() + 60
            return value
        return None
    
    def set(self, key, value, ttl=None):
        """Set value in cache"""
        expires = int(time.time()) + (ttl or self.default_ttl) if ttl != -1 else None
        
        # Store in memory
        self.memory_cache[key] = value
        self.cache_timestamps[key] = time.time() + (ttl or self.default_ttl)
        
        # Store in database
        cur.execute("""
            REPLACE INTO cache (key, value, expires_at, created_at)
            VALUES (?, ?, ?, ?)
        """, (key, json.dumps(value), expires, int(time.time())))
        conn.commit()
    
    def delete(self, key):
        """Delete from cache"""
        if key in self.memory_cache:
            del self.memory_cache[key]
        if key in self.cache_timestamps:
            del self.cache_timestamps[key]
        
        cur.execute("DELETE FROM cache WHERE key=?", (key,))
        conn.commit()
    
    def clear(self):
        """Clear expired cache"""
        cur.execute("DELETE FROM cache WHERE expires_at < ?", (int(time.time()),))
        conn.commit()
        
        # Clear expired memory cache
        now = time.time()
        self.memory_cache = {k: v for k, v in self.memory_cache.items() 
                           if k in self.cache_timestamps and self.cache_timestamps[k] > now}

cache = CacheManager()

# ==================== USER MANAGER ====================

def get_user(user_id):
    """Get user by ID"""
    # Try cache first
    cache_key = f"user:{user_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    cur.execute("SELECT * FROM users WHERE user_id=? OR telegram_id=?", (str(user_id), str(user_id)))
    row = cur.fetchone()
    if row:
        user = dict(row)
        cache.set(cache_key, user, 300)  # Cache for 5 minutes
        return user
    return None

def create_user(telegram_id, username="", first_name="", last_name=""):
    """Create new user"""
    user_id = str(uuid.uuid4())
    now = int(time.time())
    
    # Generate referral code
    referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    try:
        cur.execute("""
            INSERT INTO users (
                user_id, username, first_name, last_name, role, plan_id,
                created_at, updated_at, telegram_id, referral_code, coin_balance
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, username, first_name, last_name, "user", "free",
            now, now, str(telegram_id), referral_code, 1000
        ))
        
        # Create level entry
        cur.execute("""
            INSERT INTO user_levels (user_id, created_at, updated_at)
            VALUES (?, ?, ?)
        """, (user_id, now, now))
        
        conn.commit()
        
        # Clear cache
        cache.delete(f"user:{telegram_id}")
        cache.delete(f"user:{user_id}")
        
        logger.info(f"✅ New user created: {telegram_id}")
        return user_id
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        conn.rollback()
        return None

def update_user(user_id, **kwargs):
    """Update user fields"""
    if not kwargs:
        return
    
    fields = []
    values = []
    for key, value in kwargs.items():
        fields.append(f"{key}=?")
        values.append(value)
    
    values.append(int(time.time()))
    values.append(str(user_id))
    
    query = f"UPDATE users SET {', '.join(fields)}, updated_at=? WHERE user_id=?"
    
    try:
        cur.execute(query, values)
        conn.commit()
        
        # Clear cache
        cache.delete(f"user:{user_id}")
        user = get_user(user_id)
        if user and user.get('telegram_id'):
            cache.delete(f"user:{user['telegram_id']}")
    except Exception as e:
        logger.error(f"Error updating user: {e}")

# ==================== LEVEL & XP MANAGER ====================

class LevelManager:
    """Manage user levels and XP"""
    
    def add_xp(self, user_id, xp_amount):
        """Add XP to user"""
        cur.execute("SELECT * FROM user_levels WHERE user_id=?", (str(user_id),))
        level_data = cur.fetchone()
        
        if not level_data:
            # Create level data
            cur.execute("""
                INSERT INTO user_levels (user_id, xp, total_xp, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (str(user_id), xp_amount, xp_amount, int(time.time()), int(time.time())))
            conn.commit()
            return self.check_level_up(user_id)
        
        current_xp = level_data['xp'] + xp_amount
        total_xp = level_data['total_xp'] + xp_amount
        
        cur.execute("""
            UPDATE user_levels 
            SET xp=?, total_xp=?, updated_at=?
            WHERE user_id=?
        """, (current_xp, total_xp, int(time.time()), str(user_id)))
        conn.commit()
        
        return self.check_level_up(user_id)
    
    def check_level_up(self, user_id):
        """Check if user leveled up"""
        cur.execute("SELECT * FROM user_levels WHERE user_id=?", (str(user_id),))
        level_data = cur.fetchone()
        
        if not level_data:
            return False
        
        level = level_data['level']
        xp = level_data['xp']
        next_xp = level_data['next_level_xp']
        
        leveled_up = False
        while xp >= next_xp:
            level += 1
            xp -= next_xp
            next_xp = int(next_xp * 1.5)  # Increase requirement
            leveled_up = True
        
        if leveled_up:
            cur.execute("""
                UPDATE user_levels 
                SET level=?, xp=?, next_level_xp=?, updated_at=?
                WHERE user_id=?
            """, (level, xp, next_xp, int(time.time()), str(user_id)))
            conn.commit()
            
            # Award coins for level up
            coin_reward = level * 100
            cur.execute("""
                UPDATE users SET coin_balance = coin_balance + ? 
                WHERE user_id=?
            """, (coin_reward, str(user_id)))
            conn.commit()
        
        return leveled_up
    
    def get_level_info(self, user_id):
        """Get user level info"""
        cur.execute("SELECT * FROM user_levels WHERE user_id=?", (str(user_id),))
        return cur.fetchone()

level_manager = LevelManager()

# ==================== COIN MANAGER ====================

class CoinManager:
    """Manage user coins"""
    
    def add_coins(self, user_id, amount, reason=""):
        """Add coins to user"""
        cur.execute("""
            UPDATE users 
            SET coin_balance = coin_balance + ?, 
                total_coins_earned = total_coins_earned + ?
            WHERE user_id=?
        """, (amount, amount, str(user_id)))
        conn.commit()
        
        # Clear cache
        cache.delete(f"user:{user_id}")
        
        logger.info(f"Added {amount} coins to {user_id} for {reason}")
        return True
    
    def spend_coins(self, user_id, amount, reason=""):
        """Spend coins"""
        user = get_user(user_id)
        if not user or user['coin_balance'] < amount:
            return False
        
        cur.execute("""
            UPDATE users 
            SET coin_balance = coin_balance - ?,
                total_coins_spent = total_coins_spent + ?
            WHERE user_id=?
        """, (amount, amount, str(user_id)))
        conn.commit()
        
        # Clear cache
        cache.delete(f"user:{user_id}")
        
        logger.info(f"{user_id} spent {amount} coins on {reason}")
        return True
    
    def get_balance(self, user_id):
        """Get user coin balance"""
        user = get_user(user_id)
        return user['coin_balance'] if user else 0
    
    def daily_claim(self, user_id):
        """Claim daily coins"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        cur.execute("SELECT * FROM daily_claims WHERE user_id=?", (str(user_id),))
        claim = cur.fetchone()
        
        now = int(time.time())
        today_start = int(datetime.now().replace(hour=0, minute=0, second=0).timestamp())
        
        if claim and claim['last_claim'] >= today_start:
            return False, "Already claimed today"
        
        # Calculate streak
        streak = 1
        if claim:
            yesterday_start = today_start - 86400
            if claim['last_claim'] >= yesterday_start:
                streak = claim['streak'] + 1
            else:
                streak = 1
        
        # Base coins + streak bonus
        base_coins = 1000
        bonus = min(streak * 100, 1000)  # Max 1000 bonus
        total_coins = base_coins + bonus
        
        self.add_coins(user_id, total_coins, f"daily_claim_streak_{streak}")
        
        # Update claim record
        cur.execute("""
            INSERT OR REPLACE INTO daily_claims (user_id, last_claim, streak)
            VALUES (?, ?, ?)
        """, (str(user_id), now, streak))
        conn.commit()
        
        return True, {"coins": total_coins, "streak": streak, "bonus": bonus}

coin_manager = CoinManager()

# ==================== FRIEND MANAGER ====================

class FriendManager:
    """Manage friend system"""
    
    def send_request(self, from_user, to_user):
        """Send friend request"""
        # Check if already friends
        if self.are_friends(from_user, to_user):
            return False, "Already friends"
        
        # Check if blocked
        if self.is_blocked(to_user, from_user) or self.is_blocked(from_user, to_user):
            return False, "User blocked"
        
        # Check existing request
        cur.execute("""
            SELECT status FROM friend_requests 
            WHERE (from_user=? AND to_user=?) OR (from_user=? AND to_user=?)
        """, (str(from_user), str(to_user), str(to_user), str(from_user)))
        
        existing = cur.fetchone()
        if existing:
            if existing['status'] == 'pending':
                return False, "Request already pending"
            elif existing['status'] == 'accepted':
                return False, "Already friends"
        
        now = int(time.time())
        cur.execute("""
            INSERT INTO friend_requests (from_user, to_user, status, created_at, updated_at)
            VALUES (?, ?, 'pending', ?, ?)
        """, (str(from_user), str(to_user), now, now))
        conn.commit()
        
        return True, "Request sent"
    
    def accept_request(self, user_id, from_user):
        """Accept friend request"""
        cur.execute("""
            UPDATE friend_requests 
            SET status='accepted', updated_at=?
            WHERE from_user=? AND to_user=? AND status='pending'
        """, (int(time.time()), str(from_user), str(user_id)))
        
        if cur.rowcount > 0:
            # Add to friends table
            now = int(time.time())
            cur.execute("""
                INSERT INTO friends (user_id, friend_id, created_at)
                VALUES (?, ?, ?), (?, ?, ?)
            """, (str(user_id), str(from_user), now, str(from_user), str(user_id), now))
            conn.commit()
            return True, "Friend request accepted"
        
        return False, "No pending request"
    
    def reject_request(self, user_id, from_user):
        """Reject friend request"""
        cur.execute("""
            UPDATE friend_requests 
            SET status='rejected', updated_at=?
            WHERE from_user=? AND to_user=? AND status='pending'
        """, (int(time.time()), str(from_user), str(user_id)))
        conn.commit()
        return True, "Request rejected"
    
    def remove_friend(self, user_id, friend_id):
        """Remove friend"""
        cur.execute("""
            DELETE FROM friends 
            WHERE (user_id=? AND friend_id=?) OR (user_id=? AND friend_id=?)
        """, (str(user_id), str(friend_id), str(friend_id), str(user_id)))
        conn.commit()
        return True
    
    def get_friends(self, user_id):
        """Get user's friends"""
        cur.execute("""
            SELECT u.user_id, u.username, u.first_name, u.last_name, f.created_at
            FROM friends f
            JOIN users u ON f.friend_id = u.user_id
            WHERE f.user_id=?
            ORDER BY f.created_at DESC
        """, (str(user_id),))
        return cur.fetchall()
    
    def get_pending_requests(self, user_id):
        """Get pending friend requests"""
        cur.execute("""
            SELECT fr.*, u.username, u.first_name
            FROM friend_requests fr
            JOIN users u ON fr.from_user = u.user_id
            WHERE fr.to_user=? AND fr.status='pending'
            ORDER BY fr.created_at DESC
        """, (str(user_id),))
        return cur.fetchall()
    
    def are_friends(self, user1, user2):
        """Check if users are friends"""
        cur.execute("""
            SELECT * FROM friends 
            WHERE user_id=? AND friend_id=?
        """, (str(user1), str(user2)))
        return cur.fetchone() is not None
    
    def block_user(self, user_id, block_user_id):
        """Block a user"""
        # Remove from friends if exists
        self.remove_friend(user_id, block_user_id)
        self.remove_friend(block_user_id, user_id)
        
        # Add to blocks
        now = int(time.time())
        cur.execute("""
            INSERT OR REPLACE INTO blocks (user_id, blocked_user_id, created_at)
            VALUES (?, ?, ?)
        """, (str(user_id), str(block_user_id), now))
        conn.commit()
        return True
    
    def unblock_user(self, user_id, block_user_id):
        """Unblock a user"""
        cur.execute("""
            DELETE FROM blocks 
            WHERE user_id=? AND blocked_user_id=?
        """, (str(user_id), str(block_user_id)))
        conn.commit()
        return True
    
    def is_blocked(self, user_id, target_user_id):
        """Check if user is blocked"""
        cur.execute("""
            SELECT * FROM blocks 
            WHERE user_id=? AND blocked_user_id=?
        """, (str(user_id), str(target_user_id)))
        return cur.fetchone() is not None
    
    def get_blocked_users(self, user_id):
        """Get blocked users"""
        cur.execute("""
            SELECT u.user_id, u.username, u.first_name, b.created_at
            FROM blocks b
            JOIN users u ON b.blocked_user_id = u.user_id
            WHERE b.user_id=?
            ORDER BY b.created_at DESC
        """, (str(user_id),))
        return cur.fetchall()

friend_manager = FriendManager()

# ==================== DIRECT CHAT MANAGER ====================

class DirectChatManager:
    """Manage direct chat between users"""
    
    def create_session(self, user_a, user_b):
        """Create direct chat session"""
        # Check if session exists
        cur.execute("""
            SELECT * FROM direct_chat_sessions 
            WHERE (user_a=? AND user_b=?) OR (user_a=? AND user_b=?)
        """, (str(user_a), str(user_b), str(user_b), str(user_a)))
        
        existing = cur.fetchone()
        if existing:
            return existing['id']
        
        session_id = str(uuid.uuid4())
        now = int(time.time())
        
        cur.execute("""
            INSERT INTO direct_chat_sessions (id, user_a, user_b, created_at, last_message_at)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, str(user_a), str(user_b), now, now))
        conn.commit()
        
        return session_id
    
    def send_message(self, session_id, from_user, message):
        """Send message in chat"""
        now = int(time.time())
        
        cur.execute("""
            INSERT INTO chat_messages (session_id, from_user, message, created_at)
            VALUES (?, ?, ?, ?)
        """, (session_id, str(from_user), message, now))
        
        cur.execute("""
            UPDATE direct_chat_sessions SET last_message_at=? WHERE id=?
        """, (now, session_id))
        
        conn.commit()
        return cur.lastrowid
    
    def get_session(self, user_a, user_b):
        """Get chat session between users"""
        cur.execute("""
            SELECT * FROM direct_chat_sessions 
            WHERE (user_a=? AND user_b=?) OR (user_a=? AND user_b=?)
        """, (str(user_a), str(user_b), str(user_b), str(user_a)))
        return cur.fetchone()
    
    def get_messages(self, session_id, limit=50):
        """Get recent messages"""
        cur.execute("""
            SELECT cm.*, u.username, u.first_name
            FROM chat_messages cm
            JOIN users u ON cm.from_user = u.user_id
            WHERE cm.session_id=?
            ORDER BY cm.created_at DESC
            LIMIT ?
        """, (session_id, limit))
        
        messages = cur.fetchall()
        return list(reversed(messages))  # Return in chronological order
    
    def toggle_smart_mode(self, session_id, enabled):
        """Toggle smart mode (AI assisted)"""
        cur.execute("""
            UPDATE direct_chat_sessions SET smart_mode=? WHERE id=?
        """, (1 if enabled else 0, session_id))
        conn.commit()
        return True
    
    def toggle_translate(self, session_id, enabled):
        """Toggle auto-translate"""
        cur.execute("""
            UPDATE direct_chat_sessions SET auto_translate=? WHERE id=?
        """, (1 if enabled else 0, session_id))
        conn.commit()
        return True

direct_chat = DirectChatManager()

# ==================== GROUP MANAGER ====================

class GroupManager:
    """Manage group rooms"""
    
    def create_room(self, name, created_by, description="", is_private=False):
        """Create group room"""
        room_id = str(uuid.uuid4())
        now = int(time.time())
        
        cur.execute("""
            INSERT INTO group_rooms (id, name, description, created_by, is_private, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (room_id, name, description, str(created_by), 1 if is_private else 0, now, now))
        
        # Add creator as admin
        cur.execute("""
            INSERT INTO group_members (room_id, user_id, role, joined_at)
            VALUES (?, ?, 'owner', ?)
        """, (room_id, str(created_by), now))
        
        conn.commit()
        return room_id
    
    def add_member(self, room_id, user_id):
        """Add member to room"""
        # Check if already member
        cur.execute("""
            SELECT * FROM group_members WHERE room_id=? AND user_id=?
        """, (room_id, str(user_id)))
        
        if cur.fetchone():
            return False, "Already a member"
        
        # Check room capacity
        cur.execute("""
            SELECT COUNT(*) as count, max_members FROM group_members gm
            JOIN group_rooms gr ON gm.room_id = gr.id
            WHERE gm.room_id=?
        """, (room_id,))
        
        room_info = cur.fetchone()
        if room_info and room_info['count'] >= room_info['max_members']:
            return False, "Room is full"
        
        now = int(time.time())
        cur.execute("""
            INSERT INTO group_members (room_id, user_id, role, joined_at, last_read)
            VALUES (?, ?, 'member', ?, ?)
        """, (room_id, str(user_id), now, now))
        conn.commit()
        
        return True, "Joined room"
    
    def remove_member(self, room_id, user_id):
        """Remove member from room"""
        cur.execute("""
            DELETE FROM group_members WHERE room_id=? AND user_id=?
        """, (room_id, str(user_id)))
        conn.commit()
        return True
    
    def send_message(self, room_id, user_id, message):
        """Send message to group"""
        now = int(time.time())
        
        cur.execute("""
            INSERT INTO group_messages (room_id, user_id, message, created_at)
            VALUES (?, ?, ?, ?)
        """, (room_id, str(user_id), message, now))
        
        cur.execute("""
            UPDATE group_rooms SET updated_at=? WHERE id=?
        """, (now, room_id))
        
        conn.commit()
        return cur.lastrowid
    
    def get_messages(self, room_id, limit=50):
        """Get recent messages"""
        cur.execute("""
            SELECT gm.*, u.username, u.first_name
            FROM group_messages gm
            JOIN users u ON gm.user_id = u.user_id
            WHERE gm.room_id=?
            ORDER BY gm.created_at DESC
            LIMIT ?
        """, (room_id, limit))
        
        messages = cur.fetchall()
        return list(reversed(messages))
    
    def get_members(self, room_id):
        """Get room members"""
        cur.execute("""
            SELECT u.user_id, u.username, u.first_name, gm.role, gm.joined_at
            FROM group_members gm
            JOIN users u ON gm.user_id = u.user_id
            WHERE gm.room_id=?
            ORDER BY 
                CASE gm.role
                    WHEN 'owner' THEN 1
                    WHEN 'admin' THEN 2
                    ELSE 3
                END, gm.joined_at
        """, (room_id,))
        return cur.fetchall()
    
    def get_user_rooms(self, user_id):
        """Get rooms user is in"""
        cur.execute("""
            SELECT gr.*, gm.role
            FROM group_members gm
            JOIN group_rooms gr ON gm.room_id = gr.id
            WHERE gm.user_id=?
            ORDER BY gr.updated_at DESC
        """, (str(user_id),))
        return cur.fetchall()

group_manager = GroupManager()

# ==================== SHOP MANAGER ====================

class ShopManager:
    """Manage shop and purchases"""
    
    def get_categories(self):
        """Get all shop categories"""
        cur.execute("""
            SELECT * FROM shop_categories 
            WHERE is_active=1 
            ORDER BY display_order
        """)
        return cur.fetchall()
    
    def get_items(self, category_id=None):
        """Get shop items"""
        if category_id:
            cur.execute("""
                SELECT * FROM shop_items 
                WHERE category_id=? AND is_active=1
                ORDER BY price
            """, (category_id,))
        else:
            cur.execute("""
                SELECT * FROM shop_items 
                WHERE is_active=1
                ORDER BY category_id, price
            """)
        return cur.fetchall()
    
    def get_item(self, item_id):
        """Get item details"""
        cur.execute("SELECT * FROM shop_items WHERE id=?", (item_id,))
        return cur.fetchone()
    
    def buy_item(self, user_id, item_id, quantity=1):
        """Buy item from shop"""
        item = self.get_item(item_id)
        if not item or not item['is_active']:
            return False, "Item not available"
        
        # Check stock
        if item['stock'] != -1 and item['stock'] < quantity:
            return False, "Out of stock"
        
        # Check purchase limit
        if item['purchase_limit'] > 0:
            cur.execute("""
                SELECT SUM(quantity) as total FROM user_purchases 
                WHERE user_id=? AND item_id=?
            """, (str(user_id), item_id))
            purchased = cur.fetchone()
            if purchased and purchased['total'] >= item['purchase_limit']:
                return False, "Purchase limit reached"
        
        # Calculate total price
        total_price = item['price'] * quantity
        
        # Check coins
        if not coin_manager.spend_coins(user_id, total_price, f"bought {item['name']}"):
            return False, "Insufficient coins"
        
        # Record purchase
        now = int(time.time())
        cur.execute("""
            INSERT INTO user_purchases (user_id, item_id, quantity, price_paid, purchased_at)
            VALUES (?, ?, ?, ?, ?)
        """, (str(user_id), item_id, quantity, total_price, now))
        
        # Update inventory
        cur.execute("""
            INSERT INTO user_inventory (user_id, item_id, quantity, acquired_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, item_id) DO UPDATE SET
                quantity = quantity + ?
        """, (str(user_id), item_id, quantity, now, quantity))
        
        # Update stock if limited
        if item['stock'] != -1:
            cur.execute("""
                UPDATE shop_items SET stock = stock - ? WHERE id=?
            """, (quantity, item_id))
        
        conn.commit()
        
        # Apply item effects
        self.apply_item_effect(user_id, item)
        
        return True, "Purchase successful"
    
    def apply_item_effect(self, user_id, item):
        """Apply item effect after purchase"""
        item_type = item['item_type']
        item_value = item['item_value']
        
        if item_type == "theme":
            update_user(user_id, theme_preference=item_value)
        
        elif item_type == "bubble":
            update_user(user_id, chat_bubble_style=item_value)
        
        elif item_type == "emoji":
            update_user(user_id, emoji_pack=item_value)
        
        elif item_type == "voice":
            update_user(user_id, voice_style=item_value)
        
        elif item_type == "feature":
            # Unlock feature in user metadata
            user = get_user(user_id)
            metadata = json.loads(user.get('metadata', '{}'))
            if 'unlocked_features' not in metadata:
                metadata['unlocked_features'] = []
            if item_value not in metadata['unlocked_features']:
                metadata['unlocked_features'].append(item_value)
            update_user(user_id, metadata=json.dumps(metadata))
        
        elif item_type == "powerup":
            # Store in active powerups
            user = get_user(user_id)
            metadata = json.loads(user.get('metadata', '{}'))
            if 'active_powerups' not in metadata:
                metadata['active_powerups'] = {}
            metadata['active_powerups'][item_value] = int(time.time()) + 86400  # 24 hours
            update_user(user_id, metadata=json.dumps(metadata))
    
    def get_inventory(self, user_id):
        """Get user inventory"""
        cur.execute("""
            SELECT ui.*, si.name, si.description, si.icon, si.item_type
            FROM user_inventory ui
            JOIN shop_items si ON ui.item_id = si.id
            WHERE ui.user_id=?
            ORDER BY ui.acquired_at DESC
        """, (str(user_id),))
        return cur.fetchall()
    
    def equip_item(self, user_id, item_id):
        """Equip cosmetic item"""
        # Check if user owns item
        cur.execute("""
            SELECT * FROM user_inventory WHERE user_id=? AND item_id=?
        """, (str(user_id), item_id))
        
        if not cur.fetchone():
            return False, "You don't own this item"
        
        # Get item details
        item = self.get_item(item_id)
        if item['item_type'] not in ['theme', 'bubble', 'emoji', 'voice']:
            return False, "This item cannot be equipped"
        
        # Unequip previous items of same type
        if item['item_type'] == 'theme':
            update_user(user_id, theme_preference=item['item_value'])
        elif item['item_type'] == 'bubble':
            update_user(user_id, chat_bubble_style=item['item_value'])
        elif item['item_type'] == 'emoji':
            update_user(user_id, emoji_pack=item['item_value'])
        elif item['item_type'] == 'voice':
            update_user(user_id, voice_style=item['item_value'])
        
        return True, "Item equipped"

shop_manager = ShopManager()

# ==================== GAME MANAGER ====================

class GameManager:
    """Manage games and game sessions"""
    
    def get_games(self):
        """Get available games"""
        cur.execute("SELECT * FROM games WHERE is_active=1")
        return cur.fetchall()
    
    def create_session(self, game_id, created_by):
        """Create game session"""
        session_id = str(uuid.uuid4())
        now = int(time.time())
        
        cur.execute("""
            INSERT INTO game_sessions (id, game_id, status, created_by, created_at)
            VALUES (?, ?, 'waiting', ?, ?)
        """, (session_id, game_id, str(created_by), now))
        
        # Add creator as player
        cur.execute("""
            INSERT INTO game_players (session_id, user_id, joined_at)
            VALUES (?, ?, ?)
        """, (session_id, str(created_by), now))
        
        conn.commit()
        return session_id
    
    def join_session(self, session_id, user_id):
        """Join game session"""
        # Check if session exists and is waiting
        cur.execute("SELECT * FROM game_sessions WHERE id=?", (session_id,))
        session = cur.fetchone()
        
        if not session:
            return False, "Session not found"
        
        if session['status'] != 'waiting':
            return False, "Game already started"
        
        # Check if already in session
        cur.execute("""
            SELECT * FROM game_players WHERE session_id=? AND user_id=?
        """, (session_id, str(user_id)))
        
        if cur.fetchone():
            return False, "Already in game"
        
        # Check max players
        game = self.get_game(session['game_id'])
        cur.execute("SELECT COUNT(*) as count FROM game_players WHERE session_id=?", (session_id,))
        player_count = cur.fetchone()['count']
        
        if player_count >= game['max_players']:
            return False, "Game is full"
        
        # Add player
        now = int(time.time())
        cur.execute("""
            INSERT INTO game_players (session_id, user_id, joined_at)
            VALUES (?, ?, ?)
        """, (session_id, str(user_id), now))
        conn.commit()
        
        # Start game if enough players
        player_count += 1
        if player_count >= game['min_players']:
            self.start_game(session_id)
        
        return True, "Joined game"
    
    def start_game(self, session_id):
        """Start game session"""
        cur.execute("""
            UPDATE game_sessions 
            SET status='active', started_at=?
            WHERE id=?
        """, (int(time.time()), session_id))
        conn.commit()
        return True
    
    def end_game(self, session_id, winner_id=None):
        """End game and distribute rewards"""
        cur.execute("SELECT * FROM game_sessions WHERE id=?", (session_id,))
        session = cur.fetchone()
        
        if not session:
            return False
        
        game = self.get_game(session['game_id'])
        now = int(time.time())
        
        # Update session
        cur.execute("""
            UPDATE game_sessions 
            SET status='ended', ended_at=?, winner=?
            WHERE id=?
        """, (now, str(winner_id) if winner_id else None, session_id))
        
        # Get all players
        cur.execute("SELECT user_id FROM game_players WHERE session_id=?", (session_id,))
        players = cur.fetchall()
        
        # Distribute rewards
        for player in players:
            if winner_id and player['user_id'] == winner_id:
                # Winner gets full rewards
                coin_manager.add_coins(player['user_id'], game['coin_reward'], f"won_game_{game['id']}")
                level_manager.add_xp(player['user_id'], game['xp_reward'])
            else:
                # Losers get half
                coin_manager.add_coins(player['user_id'], game['coin_reward'] // 2, f"played_game_{game['id']}")
                level_manager.add_xp(player['user_id'], game['xp_reward'] // 2)
        
        conn.commit()
        return True
    
    def get_game(self, game_id):
        """Get game details"""
        cur.execute("SELECT * FROM games WHERE id=?", (game_id,))
        return cur.fetchone()
    
    def get_active_sessions(self, game_id=None):
        """Get active game sessions"""
        if game_id:
            cur.execute("""
                SELECT * FROM game_sessions 
                WHERE game_id=? AND status='waiting'
                ORDER BY created_at DESC
            """, (game_id,))
        else:
            cur.execute("""
                SELECT * FROM game_sessions 
                WHERE status='waiting'
                ORDER BY created_at DESC
            """)
        return cur.fetchall()
    
    def get_quiz_question(self, difficulty='medium'):
        """Get random quiz question"""
        cur.execute("""
            SELECT * FROM quiz_questions 
            WHERE difficulty=?
            ORDER BY RANDOM() LIMIT 1
        """, (difficulty,))
        return cur.fetchone()

game_manager = GameManager()

# ==================== BADGE MANAGER ====================

class BadgeManager:
    """Manage badges and achievements"""
    
    def check_and_award(self, user_id):
        """Check and award badges"""
        user = get_user(user_id)
        if not user:
            return []
        
        awarded = []
        
        # Get all badges
        cur.execute("SELECT * FROM badges")
        badges = cur.fetchall()
        
        for badge in badges:
            # Check if already has
            cur.execute("""
                SELECT * FROM user_badges WHERE user_id=? AND badge_id=?
            """, (str(user_id), badge['id']))
            
            if cur.fetchone():
                continue
            
            # Check requirement
            has_badge = False
            
            if badge['requirement_type'] == 'messages':
                # Count total messages
                cur.execute("""
                    SELECT COUNT(*) as count FROM chat_messages WHERE from_user=?
                """, (str(user_id),))
                count = cur.fetchone()['count']
                if count >= badge['requirement_value']:
                    has_badge = True
            
            elif badge['requirement_type'] == 'friends':
                # Count friends
                cur.execute("""
                    SELECT COUNT(*) as count FROM friends WHERE user_id=?
                """, (str(user_id),))
                count = cur.fetchone()['count']
                if count >= badge['requirement_value']:
                    has_badge = True
            
            elif badge['requirement_type'] == 'games':
                # Count games played
                cur.execute("""
                    SELECT COUNT(*) as count FROM game_players WHERE user_id=?
                """, (str(user_id),))
                count = cur.fetchone()['count']
                if count >= badge['requirement_value']:
                    has_badge = True
            
            elif badge['requirement_type'] == 'streak':
                # Get streak
                cur.execute("SELECT streak FROM daily_claims WHERE user_id=?", (str(user_id),))
                claim = cur.fetchone()
                if claim and claim['streak'] >= badge['requirement_value']:
                    has_badge = True
            
            elif badge['requirement_type'] == 'purchases':
                # Count purchases
                cur.execute("""
                    SELECT COUNT(*) as count FROM user_purchases WHERE user_id=?
                """, (str(user_id),))
                count = cur.fetchone()['count']
                if count >= badge['requirement_value']:
                    has_badge = True
            
            if has_badge:
                # Award badge
                now = int(time.time())
                cur.execute("""
                    INSERT INTO user_badges (user_id, badge_id, earned_at)
                    VALUES (?, ?, ?)
                """, (str(user_id), badge['id'], now))
                
                # Give rewards
                if badge['coin_reward'] > 0:
                    coin_manager.add_coins(user_id, badge['coin_reward'], f"badge_{badge['id']}")
                
                if badge['xp_reward'] > 0:
                    level_manager.add_xp(user_id, badge['xp_reward'])
                
                awarded.append(badge)
        
        conn.commit()
        return awarded
    
    def get_user_badges(self, user_id):
        """Get user's badges"""
        cur.execute("""
            SELECT b.*, ub.earned_at
            FROM user_badges ub
            JOIN badges b ON ub.badge_id = b.id
            WHERE ub.user_id=?
            ORDER BY ub.earned_at DESC
        """, (str(user_id),))
        return cur.fetchall()

badge_manager = BadgeManager()

# ==================== REPORT MANAGER ====================

class ReportManager:
    """Manage user reports"""
    
    def create_report(self, reporter_id, reported_user_id, reason, details=""):
        """Create new report"""
        now = int(time.time())
        
        cur.execute("""
            INSERT INTO reports (reporter_id, reported_user_id, reason, details, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (str(reporter_id), str(reported_user_id), reason, details, now))
        conn.commit()
        
        return cur.lastrowid
    
    def get_pending_reports(self):
        """Get pending reports"""
        cur.execute("""
            SELECT r.*, u1.username as reporter_name, u2.username as reported_name
            FROM reports r
            JOIN users u1 ON r.reporter_id = u1.user_id
            JOIN users u2 ON r.reported_user_id = u2.user_id
            WHERE r.status='pending'
            ORDER BY r.created_at DESC
        """)
        return cur.fetchall()
    
    def resolve_report(self, report_id, resolved_by, action_taken=""):
        """Resolve report"""
        cur.execute("""
            UPDATE reports 
            SET status='resolved', resolved_at=?, resolved_by=?
            WHERE id=?
        """, (int(time.time()), str(resolved_by), report_id))
        conn.commit()
        
        # Log moderation action
        cur.execute("""
            INSERT INTO moderation_logs (moderator_id, action, target_user, reason, created_at)
            SELECT ?, 'report_resolved', reported_user_id, ?, ?
            FROM reports WHERE id=?
        """, (str(resolved_by), action_taken, int(time.time()), report_id))
        conn.commit()
        
        return True

report_manager = ReportManager()

# ==================== MENU MANAGER ====================

class MenuManager:
    """Manage dynamic menus"""
    
    def get_user_menu(self, user_id=None):
        """Get user menu based on role"""
        user = get_user(user_id) if user_id else None
        
        if user and user['role'] in ['admin', 'super_admin']:
            # Admin gets admin menus
            cur.execute("""
                SELECT * FROM menus 
                WHERE menu_type IN ('both', 'admin') AND is_active=1
                ORDER BY display_order
            """)
        else:
            # Regular user gets user menus
            cur.execute("""
                SELECT * FROM menus 
                WHERE menu_type IN ('both', 'user') AND is_active=1
                ORDER BY display_order
            """)
        
        menus = cur.fetchall()
        return self.build_menu_tree(menus)
    
    def get_admin_menu(self):
        """Get admin menu"""
        cur.execute("""
            SELECT * FROM menus 
            WHERE menu_type IN ('both', 'admin') AND is_active=1
            ORDER BY display_order
        """)
        menus = cur.fetchall()
        return self.build_menu_tree(menus)
    
    def build_menu_tree(self, menus, parent_id=None):
        """Build menu tree"""
        tree = []
        for menu in menus:
            if menu['parent_id'] == parent_id:
                menu_dict = dict(menu)
                children = self.build_menu_tree(menus, menu['id'])
                if children:
                    menu_dict['children'] = children
                tree.append(menu_dict)
        return tree
    
    def get_menu_buttons(self, menu_items, user_id=None, user_role='user'):
        """Create inline keyboard from menu items"""
        keyboard = []
        
        for item in menu_items:
            # Check permission
            if item.get('required_permission'):
                if user_role != 'admin' and user_role != 'super_admin':
                    continue
            
            # Create button
            if item.get('command'):
                callback_data = f"menu:{item['command']}"
            else:
                callback_data = f"menu:{item['id']}"
            
            button = InlineKeyboardButton(
                f"{item.get('icon', '•')} {item['name']}",
                callback_data=callback_data
            )
            
            keyboard.append([button])
        
        # Add back button if not root
        if menu_items and menu_items[0].get('parent_id'):
            keyboard.append([
                InlineKeyboardButton("🔙 Back", callback_data="menu:back")
            ])
        
        return InlineKeyboardMarkup(keyboard)

menu_manager = MenuManager()

# ==================== ADMIN MANAGER ====================

class AdminManager:
    """Manage admin users and permissions"""
    
    def __init__(self):
        self.admins = set()
        self.load_admins()
    
    def load_admins(self):
        """Load admin users"""
        cur.execute("SELECT user_id FROM users WHERE role IN ('admin', 'super_admin')")
        for row in cur.fetchall():
            self.admins.add(row['user_id'])
    
    def is_admin(self, user_id):
        """Check if user is admin"""
        return str(user_id) in self.admins
    
    def add_admin(self, user_id, added_by):
        """Add admin user"""
        cur.execute("""
            UPDATE users SET role='admin' WHERE user_id=?
        """, (str(user_id),))
        conn.commit()
        self.admins.add(str(user_id))
        
        # Log action
        cur.execute("""
            INSERT INTO moderation_logs (moderator_id, action, target_user, created_at)
            VALUES (?, 'add_admin', ?, ?)
        """, (str(added_by), str(user_id), int(time.time())))
        conn.commit()
        
        return True
    
    def remove_admin(self, user_id, removed_by):
        """Remove admin user"""
        cur.execute("""
            UPDATE users SET role='user' WHERE user_id=?
        """, (str(user_id),))
        conn.commit()
        self.admins.discard(str(user_id))
        
        # Log action
        cur.execute("""
            INSERT INTO moderation_logs (moderator_id, action, target_user, created_at)
            VALUES (?, 'remove_admin', ?, ?)
        """, (str(removed_by), str(user_id), int(time.time())))
        conn.commit()
        
        return True
    
    def clear_database(self, admin_id):
        """Clear database (admin only)"""
        if not self.is_admin(admin_id):
            return False, "Permission denied"
        
        try:
            # Backup first
            backup_file = f"backup_before_clear_{int(time.time())}.db"
            shutil.copy2("superbase.db", backup_file)
            
            # Clear tables but keep structure
            tables = [
                "chat_messages", "group_messages", "user_purchases", 
                "user_inventory", "game_sessions", "game_players",
                "game_moves", "reports", "moderation_logs",
                "friend_requests", "friends", "blocks", "daily_claims"
            ]
            
            for table in tables:
                cur.execute(f"DELETE FROM {table}")
            
            # Reset user coins to 1000
            cur.execute("UPDATE users SET coin_balance=1000, total_coins_earned=1000, total_coins_spent=0")
            
            # Reset levels
            cur.execute("UPDATE user_levels SET level=1, xp=0, total_xp=0, activity_score=0, next_level_xp=100")
            
            conn.commit()
            
            # Log action
            cur.execute("""
                INSERT INTO moderation_logs (moderator_id, action, reason, created_at)
                VALUES (?, 'clear_database', 'Database cleared by admin', ?)
            """, (str(admin_id), int(time.time())))
            conn.commit()
            
            logger.warning(f"Database cleared by admin {admin_id}, backup saved as {backup_file}")
            return True, f"Database cleared. Backup saved as {backup_file}"
            
        except Exception as e:
            logger.error(f"Error clearing database: {e}")
            return False, f"Error: {e}"

admin_manager = AdminManager()

# ==================== BOT STATUS ====================

BOT_UPDATING = False
bot_instance = None

def set_bot(bot):
    global bot_instance
    bot_instance = bot

def get_bot():
    return bot_instance

# ==================== HELPER FUNCTIONS ====================

def is_banned(user_id):
    """Check if user is banned"""
    cur.execute("SELECT * FROM bans WHERE user_id=?", (str(user_id),))
    return cur.fetchone() is not None

def check_daily_limit(user_id):
    """Check daily message limit"""
    user = get_user(user_id)
    if not user:
        return True
    
    # Admin has no limit
    if user['role'] in ['admin', 'super_admin']:
        return False
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    if user['last_request_date'] != today:
        # Reset daily count
        cur.execute("""
            UPDATE users SET daily_requests=0, last_request_date=? WHERE user_id=?
        """, (today, str(user_id)))
        conn.commit()
        return False
    
    # Check limit (100 for free, 500 for premium, unlimited for admin)
    limit = 500 if user['plan_id'] != 'free' else 100
    return user['daily_requests'] >= limit

def increment_daily_count(user_id):
    """Increment daily request count"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    cur.execute("""
        UPDATE users 
        SET daily_requests = daily_requests + 1,
            total_requests = total_requests + 1,
            last_request_date=?
        WHERE user_id=?
    """, (today, str(user_id)))
    conn.commit()
    
    # Add XP for message
    level_manager.add_xp(user_id, 10)
    coin_manager.add_coins(user_id, 5, "daily_message")

def save_msg(user_id, role, text):
    """Save message to memory (for AI context)"""
    memory_key = f"memory:{user_id}"
    memory = cache.get(memory_key) or []
    
    memory.append({"role": role, "content": text, "timestamp": time.time()})
    
    # Keep last 20 messages
    if len(memory) > 20:
        memory = memory[-20:]
    
    cache.set(memory_key, memory, 86400)  # 24 hours

def load_memory(user_id):
    """Load user's conversation memory"""
    memory_key = f"memory:{user_id}"
    memory = cache.get(memory_key) or []
    
    # Filter out old messages (older than 24 hours)
    cutoff = time.time() - 86400
    memory = [m for m in memory if m.get('timestamp', 0) > cutoff]
    
    # Return messages without timestamps
    return [{"role": m["role"], "content": m["content"]} for m in memory]

def set_voice_mode(user_id, mode):
    """Set voice mode for user"""
    update_user(user_id, voice_mode=mode)

def set_voice(user_id, engine, name):
    """Set voice engine and name"""
    update_user(user_id, voice_engine=engine, voice_name=name)

async def safe_action(bot, chat_id, action=None):
    """Safe bot action with error handling"""
    try:
        if action:
            await bot.send_chat_action(chat_id=chat_id, action=action)
    except Exception as e:
        logger.error(f"Error sending chat action: {e}")

# ==================== AI FUNCTIONS ====================

async def ask_openrouter(messages, model="openai/gpt-4o-mini"):
    """Ask OpenRouter AI with multiple key rotation"""
    
    # Try each key in random order
    keys = OPENROUTER_KEYS.copy()
    random.shuffle(keys)
    
    for api_key in keys:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://t.me/priya_ai_bot",
            "X-Title": "Priya AI Bot"
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload
                )

            if r.status_code == 200:
                data = r.json()
                if data.get("choices"):
                    return data["choices"][0]["message"]["content"]
            elif r.status_code == 429:  # Rate limit
                await asyncio.sleep(1)
                continue
            else:
                logger.warning(f"API failed ({r.status_code}) → switching key")

        except Exception as e:
            logger.error(f"API crash: {e}")
            continue

    return "🥺 Bestie AI ka token khatam ho gaya… thoda baad mein try karo 💔"

async def generate_image_pollinations(prompt):
    """Generate image using Pollinations API"""
    try:
        url = f"https://image.pollinations.ai/prompt/{prompt}?nologo=true"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url)
            if r.status_code == 200:
                return BytesIO(r.content)
    except Exception as e:
        logger.error(f"Image generation error: {e}")
    return None

async def search_web_serp(query):
    """Search web using SerpAPI"""
    try:
        api_key = os.getenv("SERPAPI_KEY")
        if not api_key:
            return ""
        
        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": api_key,
            "num": 3
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            if r.status_code == 200:
                data = r.json()
                results = []
                for result in data.get("organic_results", [])[:3]:
                    title = result.get("title", "")
                    snippet = result.get("snippet", "")
                    results.append(f"• {title}\n  {snippet}")
                
                if results:
                    return "🌐 Web Search Results:\n" + "\n\n".join(results)
    except Exception as e:
        logger.error(f"Web search error: {e}")
    return ""

def search_youtube(query):
    """Search YouTube"""
    try:
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            return ""
        
        youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
        
        request = youtube.search().list(
            q=query,
            part="snippet",
            maxResults=3,
            type="video"
        )
        response = request.execute()
        
        results = []
        for item in response.get("items", []):
            title = item["snippet"]["title"]
            video_id = item["id"]["videoId"]
            url = f"https://youtu.be/{video_id}"
            results.append(f"🎥 {title}\n{url}")
        
        if results:
            return "📺 YouTube Results:\n" + "\n\n".join(results)
    except Exception as e:
        logger.error(f"YouTube search error: {e}")
    return ""

# ==================== TELEGRAM BOT HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    uid = update.effective_user.id
    username = update.effective_user.username or ""
    first_name = update.effective_user.first_name or ""
    last_name = update.effective_user.last_name or ""
    
    # Check if user exists
    user = get_user(uid)
    if not user:
        user_id = create_user(uid, username, first_name, last_name)
        if not user_id:
            await update.message.reply_text("❌ Error creating user. Please try again later.")
            return
    
    # Get welcome message
    welcome = """🌟 Welcome to Priya AI Bot! 🌟

Namaste! 🙏 Main Priya hoon, aapki personal AI assistant. 

✨ *What I can do:*
• Chat with AI in Hinglish
• Web Search / YouTube Search
• Image Generation
• Voice Messages
• Games & Fun
• Social Features
• Daily Rewards

📌 *Commands:*
/umenu - Open User Menu
/profile - Your Profile
/daily - Claim Daily Coins
/shop - Open Shop
/games - Play Games
/connect @user - Chat with Friends
/help - All Commands

💫 *Daily Rewards:* Get 1000 coins daily!

Kya help chahiye aapko? 😊"""
    
    await update.message.reply_text(welcome, parse_mode="Markdown")

async def umenu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User menu command"""
    uid = update.effective_user.id
    
    # Get user
    user = get_user(uid)
    if not user:
        user_id = create_user(uid, update.effective_user.username, update.effective_user.first_name)
        user = get_user(user_id)
    
    # Get menu
    menu_items = menu_manager.get_user_menu(uid)
    
    # Create message
    message = "📱 *Priya Bot Menu*\n\nChoose an option:"
    
    # Create keyboard
    keyboard = []
    for item in menu_items:
        if item.get('command'):
            callback = f"menu:{item['command']}"
        else:
            callback = f"menu:{item['id']}"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{item.get('icon', '•')} {item['name']}",
                callback_data=callback
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin menu command"""
    uid = update.effective_user.id
    
    # Check if admin
    if not admin_manager.is_admin(uid):
        await update.message.reply_text("❌ This command is for admins only.")
        return
    
    # Get admin menu
    menu_items = menu_manager.get_admin_menu()
    
    # Create message
    message = "⚙️ *Admin Control Panel*\n\nSelect an option:"
    
    # Create keyboard
    keyboard = []
    for item in menu_items:
        keyboard.append([
            InlineKeyboardButton(
                f"{item.get('icon', '•')} {item['name']}",
                callback_data=f"admin:{item['command']}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)

async def clearall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear database command (admin only)"""
    uid = update.effective_user.id
    
    # Check if admin
    if not admin_manager.is_admin(uid):
        await update.message.reply_text("❌ This command is for admins only.")
        return
    
    # Ask for confirmation
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, Clear Everything", callback_data="admin:clear_confirm"),
            InlineKeyboardButton("❌ No, Cancel", callback_data="admin:cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ *WARNING!*\n\n"
        "This will clear ALL user data including:\n"
        "• Chat messages\n"
        "• Friend lists\n"
        "• Game sessions\n"
        "• Purchases\n"
        "• Reports\n\n"
        "A backup will be created automatically.\n\n"
        "Are you absolutely sure?",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user profile"""
    uid = update.effective_user.id
    
    user = get_user(uid)
    if not user:
        user_id = create_user(uid, update.effective_user.username, update.effective_user.first_name)
        user = get_user(user_id)
    
    # Get level info
    level_info = level_manager.get_level_info(user['user_id'])
    
    # Get badges
    badges = badge_manager.get_user_badges(user['user_id'])
    
    # Get streak
    cur.execute("SELECT streak FROM daily_claims WHERE user_id=?", (user['user_id'],))
    claim = cur.fetchone()
    streak = claim['streak'] if claim else 0
    
    # Format badges
    badge_text = ""
    if badges:
        badge_list = [f"{b['icon']} {b['name']}" for b in badges[:5]]
        badge_text = "\n".join(badge_list)
        if len(badges) > 5:
            badge_text += f"\n+{len(badges)-5} more"
    else:
        badge_text = "No badges yet"
    
    message = f"""👤 *Your Profile*

📊 *Stats:*
• Level: {level_info['level'] if level_info else 1}
• XP: {level_info['xp'] if level_info else 0}/{level_info['next_level_xp'] if level_info else 100}
• Total XP: {level_info['total_xp'] if level_info else 0}
• Messages: {user['total_requests']}

💰 *Coins:*
• Balance: {user['coin_balance']}
• Total Earned: {user['total_coins_earned']}
• Total Spent: {user['total_coins_spent']}

🔥 *Streak:* {streak} days

🎖️ *Badges:* 
{badge_text}

💎 *Plan:* {user['plan_id']}

/preferences - Customize your profile
/shop - Visit shop
/daily - Claim daily coins"""
    
    # Create keyboard
    keyboard = [
        [
            InlineKeyboardButton("🎨 Change Theme", callback_data="profile:theme"),
            InlineKeyboardButton("💬 Bubble Style", callback_data="profile:bubble")
        ],
        [
            InlineKeyboardButton("😎 Emoji Pack", callback_data="profile:emoji"),
            InlineKeyboardButton("🎤 Voice Style", callback_data="profile:voice")
        ],
        [InlineKeyboardButton("📊 Full Stats", callback_data="profile:stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)

async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Claim daily coins"""
    uid = update.effective_user.id
    
    user = get_user(uid)
    if not user:
        user_id = create_user(uid, update.effective_user.username, update.effective_user.first_name)
        user = get_user(user_id)
    
    success, data = coin_manager.daily_claim(user['user_id'])
    
    if success:
        message = f"""✅ *Daily Rewards Claimed!*

💰 Coins Received: {data['coins']}
🔥 Current Streak: {data['streak']} days
✨ Bonus: +{data['bonus']} streak bonus

Come back tomorrow for more! 🎉"""
    else:
        # Calculate time remaining
        cur.execute("SELECT last_claim FROM daily_claims WHERE user_id=?", (user['user_id'],))
        claim = cur.fetchone()
        if claim:
            next_claim = claim['last_claim'] + 86400
            time_left = next_claim - int(time.time())
            hours = time_left // 3600
            minutes = (time_left % 3600) // 60
            message = f"❌ Already claimed today!\n\nNext claim in: {hours}h {minutes}m"
        else:
            message = "❌ Error claiming rewards"
    
    await update.message.reply_text(message, parse_mode="Markdown")

async def connect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Connect with another user"""
    uid = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "Usage: /connect @username\n"
            "Example: /connect @john_doe"
        )
        return
    
    username = context.args[0].lstrip('@')
    
    # Find user by username
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    target_user = cur.fetchone()
    
    if not target_user:
        await update.message.reply_text("❌ User not found!")
        return
    
    if target_user['user_id'] == str(uid):
        await update.message.reply_text("❌ You cannot connect with yourself!")
        return
    
    # Get current user
    user = get_user(uid)
    
    # Send friend request
    success, message = friend_manager.send_request(user['user_id'], target_user['user_id'])
    
    if success:
        # Notify target user
        try:
            bot = get_bot()
            if bot:
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Accept", callback_data=f"friend:accept:{user['user_id']}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"friend:reject:{user['user_id']}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await bot.send_message(
                    chat_id=int(target_user['telegram_id']),
                    text=f"📨 Friend request from {user['first_name'] or user['username']}!",
                    reply_markup=reply_markup
                )
        except Exception as e:
            logger.error(f"Error notifying user: {e}")
    
    await update.message.reply_text(message)

async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open shop"""
    uid = update.effective_user.id
    
    # Get categories
    categories = shop_manager.get_categories()
    
    message = "🛒 *Priya Shop*\n\n"
    message += f"💰 Your Balance: {get_user(uid)['coin_balance']} coins\n\n"
    message += "Choose a category:\n"
    
    keyboard = []
    for cat in categories:
        keyboard.append([
            InlineKeyboardButton(
                f"{cat['icon']} {cat['name']}",
                callback_data=f"shop:category:{cat['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("📦 My Inventory", callback_data="shop:inventory")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)

async def games_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open games menu"""
    games = game_manager.get_games()
    
    message = "🎮 *Games & Fun*\n\nChoose a game:\n"
    
    keyboard = []
    for game in games:
        keyboard.append([
            InlineKeyboardButton(
                f"{game['name']} - {game['description']}",
                callback_data=f"game:play:{game['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🏆 Leaderboard", callback_data="game:leaderboard")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)

async def friends_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show friends menu"""
    uid = update.effective_user.id
    user = get_user(uid)
    
    friends = friend_manager.get_friends(user['user_id'])
    requests = friend_manager.get_pending_requests(user['user_id'])
    
    message = "🤝 *Friends*\n\n"
    
    if friends:
        message += "👥 Your Friends:\n"
        for f in friends[:10]:
            name = f['first_name'] or f['username'] or f['user_id'][:8]
            message += f"• {name}\n"
        if len(friends) > 10:
            message += f"+{len(friends)-10} more\n"
    else:
        message += "No friends yet. Use /connect to add friends!\n"
    
    if requests:
        message += f"\n📨 Pending Requests: {len(requests)}"
    
    keyboard = [
        [InlineKeyboardButton("📨 Friend Requests", callback_data="friends:requests")],
        [InlineKeyboardButton("🚫 Blocked Users", callback_data="friends:blocked")],
        [InlineKeyboardButton("🔍 Find Users", callback_data="friends:find")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help"""
    help_text = """📚 *Priya Bot Commands*

👤 *User Commands:*
/umenu - Open main menu
/profile - Your profile
/daily - Claim daily coins
/shop - Open shop
/games - Play games
/friends - Friend list
/connect @user - Connect with user
/preferences - Customize profile

🤖 *AI Features:*
• Chat with me normally
• "web search [query]" - Search internet
• "youtube [query]" - Search YouTube
• "draw [prompt]" - Generate image
• "voice on/off" - Toggle voice

🎮 *Games:*
• Quiz Battle
• Memory Game
• Reaction Test
• Puzzle Challenge

🛒 *Shop Items:*
• Themes & Bubbles
• Emoji Packs
• Voice Styles
• Power-ups
• Features

👑 *Admin Commands:*
/admin - Admin panel
/clearall - Clear database (with backup)
/broadcast - Send message to all users
/stats - View bot statistics

Need more help? Just ask me! 😊"""
    
    await update.message.reply_text(help_text, parse_mode="Markdown")

# ==================== CALLBACK HANDLERS ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    uid = query.from_user.id
    
    # Get user
    user = get_user(uid)
    if not user:
        user_id = create_user(uid, query.from_user.username, query.from_user.first_name)
        user = get_user(user_id)
    
    # Handle menu callbacks
    if data.startswith("menu:"):
        await handle_menu_callback(query, context, user)
    
    # Handle admin callbacks
    elif data.startswith("admin:"):
        await handle_admin_callback(query, context, user)
    
    # Handle friend callbacks
    elif data.startswith("friend:"):
        await handle_friend_callback(query, context, user)
    
    # Handle shop callbacks
    elif data.startswith("shop:"):
        await handle_shop_callback(query, context, user)
    
    # Handle game callbacks
    elif data.startswith("game:"):
        await handle_game_callback(query, context, user)
    
    # Handle profile callbacks
    elif data.startswith("profile:"):
        await handle_profile_callback(query, context, user)

async def handle_menu_callback(query, context, user):
    """Handle menu callbacks"""
    command = query.data.split(":", 1)[1]
    
    if command == "back":
        # Go back to main menu
        await umenu_command(query, context)
    
    elif command == "profile":
        # Show profile
        await profile_command(query, context)
    
    elif command == "friends":
        # Show friends
        await friends_command(query, context)
    
    elif command == "shop":
        # Show shop
        await shop_command(query, context)
    
    elif command == "games":
        # Show games
        await games_command(query, context)
    
    elif command == "connect":
        # Ask for username
        await query.edit_message_text(
            "🔗 *Direct Chat*\n\n"
            "To connect with someone, use:\n"
            "/connect @username\n\n"
            "Example: /connect @john_doe",
            parse_mode="Markdown"
        )
    
    elif command == "daily":
        # Claim daily
        await daily_command(query, context)

async def handle_admin_callback(query, context, user):
    """Handle admin callbacks"""
    if not admin_manager.is_admin(user['user_id']):
        await query.edit_message_text("❌ Access denied!")
        return
    
    command = query.data.split(":", 1)[1]
    
    if command == "users":
        # Show users
        cur.execute("SELECT user_id, username, first_name, role, coin_balance FROM users ORDER BY created_at DESC LIMIT 20")
        users = cur.fetchall()
        
        message = "👥 *Recent Users:*\n\n"
        for u in users:
            name = u['first_name'] or u['username'] or u['user_id'][:8]
            message += f"• {name} | Role: {u['role']} | Coins: {u['coin_balance']}\n"
        
        await query.edit_message_text(message, parse_mode="Markdown")
    
    elif command == "stats":
        # Show stats
        cur.execute("SELECT COUNT(*) as total FROM users")
        total_users = cur.fetchone()['total']
        
        cur.execute("SELECT COUNT(*) as total FROM users WHERE last_request_date=date('now')")
        active_today = cur.fetchone()['total']
        
        cur.execute("SELECT SUM(total_requests) as total FROM users")
        total_messages = cur.fetchone()['total'] or 0
        
        cur.execute("SELECT SUM(coin_balance) as total FROM users")
        total_coins = cur.fetchone()['total'] or 0
        
        message = f"""📊 *Bot Statistics*

👥 Total Users: {total_users}
📱 Active Today: {active_today}
💬 Total Messages: {total_messages}
💰 Total Coins: {total_coins}

🔄 System Status: Online
📦 Version: {CONFIG_VERSION}"""
        
        await query.edit_message_text(message, parse_mode="Markdown")
    
    elif command == "broadcast":
        # Broadcast message
        context.user_data['broadcast_mode'] = True
        await query.edit_message_text(
            "📢 *Broadcast Mode*\n\n"
            "Send the message you want to broadcast to all users:",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    elif command == "clear_confirm":
        # Confirm clear database
        success, msg = admin_manager.clear_database(user['user_id'])
        
        if success:
            await query.edit_message_text(f"✅ {msg}")
        else:
            await query.edit_message_text(f"❌ {msg}")
    
    elif command == "cancel":
        await query.edit_message_text("❌ Operation cancelled.")

async def handle_friend_callback(query, context, user):
    """Handle friend callbacks"""
    parts = query.data.split(":")
    action = parts[1]
    
    if action == "accept" and len(parts) > 2:
        from_user = parts[2]
        success, msg = friend_manager.accept_request(user['user_id'], from_user)
        await query.edit_message_text(msg)
    
    elif action == "reject" and len(parts) > 2:
        from_user = parts[2]
        success, msg = friend_manager.reject_request(user['user_id'], from_user)
        await query.edit_message_text(msg)
    
    elif action == "requests":
        requests = friend_manager.get_pending_requests(user['user_id'])
        
        if not requests:
            await query.edit_message_text("No pending friend requests.")
            return
        
        message = "📨 *Friend Requests*\n\n"
        keyboard = []
        
        for req in requests:
            name = req['first_name'] or req['username'] or req['from_user'][:8]
            message += f"From: {name}\n"
            keyboard.append([
                InlineKeyboardButton(f"✅ Accept {name}", callback_data=f"friend:accept:{req['from_user']}"),
                InlineKeyboardButton(f"❌ Reject", callback_data=f"friend:reject:{req['from_user']}")
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu:friends")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode="Markdown", reply_markup=reply_markup)
    
    elif action == "blocked":
        blocked = friend_manager.get_blocked_users(user['user_id'])
        
        if not blocked:
            await query.edit_message_text("No blocked users.")
            return
        
        message = "🚫 *Blocked Users*\n\n"
        for b in blocked:
            name = b['first_name'] or b['username'] or b['user_id'][:8]
            message += f"• {name}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu:friends")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode="Markdown", reply_markup=reply_markup)

async def handle_shop_callback(query, context, user):
    """Handle shop callbacks"""
    parts = query.data.split(":")
    
    if parts[1] == "category" and len(parts) > 2:
        category_id = parts[2]
        
        # Get category
        cur.execute("SELECT * FROM shop_categories WHERE id=?", (category_id,))
        category = cur.fetchone()
        
        # Get items
        items = shop_manager.get_items(category_id)
        
        message = f"{category['icon']} *{category['name']}*\n\n"
        message += f"💰 Your Balance: {user['coin_balance']} coins\n\n"
        
        keyboard = []
        for item in items:
            stock_text = f" (Stock: {item['stock']})" if item['stock'] != -1 else ""
            button_text = f"{item['name']} - {item['price']} coins{stock_text}"
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=f"shop:buy:{item['id']}")
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Shop", callback_data="menu:shop")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode="Markdown", reply_markup=reply_markup)
    
    elif parts[1] == "buy" and len(parts) > 2:
        item_id = parts[2]
        item = shop_manager.get_item(item_id)
        
        if not item:
            await query.edit_message_text("❌ Item not found!")
            return
        
        message = f"🛒 *Buy {item['name']}*\n\n"
        message += f"📝 {item['description']}\n"
        message += f"💰 Price: {item['price']} coins\n"
        message += f"📦 Stock: {'Unlimited' if item['stock'] == -1 else item['stock']}\n\n"
        message += f"Your balance: {user['coin_balance']} coins"
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Buy Now", callback_data=f"shop:confirm:{item_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"shop:category:{item['category_id']}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode="Markdown", reply_markup=reply_markup)
    
    elif parts[1] == "confirm" and len(parts) > 2:
        item_id = parts[2]
        success, msg = shop_manager.buy_item(user['user_id'], item_id)
        
        if success:
            # Check for badges
            awarded = badge_manager.check_and_award(user['user_id'])
            
            message = f"✅ {msg}\n\n"
            if awarded:
                badge_names = [b['name'] for b in awarded]
                message += f"🎉 New badges earned: {', '.join(badge_names)}"
            
            await query.edit_message_text(message)
        else:
            await query.edit_message_text(f"❌ {msg}")
    
    elif parts[1] == "inventory":
        inventory = shop_manager.get_inventory(user['user_id'])
        
        if not inventory:
            await query.edit_message_text("📦 Your inventory is empty. Visit the shop to buy items!")
            return
        
        message = "📦 *Your Inventory*\n\n"
        
        for item in inventory[:10]:
            equip_text = " (Equipped)" if item['is_equipped'] else ""
            message += f"• {item['icon']} {item['name']} x{item['quantity']}{equip_text}\n"
        
        if len(inventory) > 10:
            message += f"\n+{len(inventory)-10} more items"
        
        keyboard = [
            [InlineKeyboardButton("🎨 Equip Items", callback_data="shop:equip")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu:shop")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode="Markdown", reply_markup=reply_markup)

async def handle_game_callback(query, context, user):
    """Handle game callbacks"""
    parts = query.data.split(":")
    
    if parts[1] == "play" and len(parts) > 2:
        game_id = parts[2]
        
        # Create game session
        session_id = game_manager.create_session(game_id, user['user_id'])
        
        game = game_manager.get_game(game_id)
        
        if game['game_type'] == 'quiz':
            # Get quiz question
            question = game_manager.get_quiz_question()
            
            if question:
                options = json.loads(question['options'])
                
                message = f"📝 *Quiz Time!*\n\n{question['question']}\n\n"
                
                keyboard = []
                for i, option in enumerate(options):
                    keyboard.append([
                        InlineKeyboardButton(
                            option,
                            callback_data=f"game:answer:{session_id}:{i}:{question['id']}"
                        )
                    ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(message, parse_mode="Markdown", reply_markup=reply_markup)
        
        elif game['game_type'] == 'memory':
            # Memory game
            await query.edit_message_text(
                "🧠 *Memory Game*\n\n"
                "Coming soon! Stay tuned...",
                parse_mode="Markdown"
            )
    
    elif parts[1] == "leaderboard":
        # Show leaderboard
        cur.execute("""
            SELECT u.username, u.first_name, ul.level, ul.total_xp
            FROM user_levels ul
            JOIN users u ON ul.user_id = u.user_id
            ORDER BY ul.total_xp DESC
            LIMIT 10
        """)
        
        top_players = cur.fetchall()
        
        message = "🏆 *Leaderboard*\n\n"
        
        for i, player in enumerate(top_players, 1):
            name = player['first_name'] or player['username'] or f"Player{i}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "👤"
            message += f"{medal} {i}. {name} - Level {player['level']} (XP: {player['total_xp']})\n"
        
        # Get user rank
        cur.execute("""
            SELECT COUNT(*) + 1 as rank
            FROM user_levels
            WHERE total_xp > (SELECT total_xp FROM user_levels WHERE user_id=?)
        """, (user['user_id'],))
        
        rank = cur.fetchone()
        if rank:
            message += f"\nYour Rank: #{rank['rank']}"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu:games")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode="Markdown", reply_markup=reply_markup)
    
    elif parts[1] == "answer" and len(parts) > 4:
        session_id = parts[2]
        answer_idx = int(parts[3])
        question_id = parts[4]
        
        # Check answer
        cur.execute("SELECT * FROM quiz_questions WHERE id=?", (question_id,))
        question = cur.fetchone()
        
        if question and answer_idx == question['correct_answer']:
            # Correct answer
            game_manager.end_game(session_id, user['user_id'])
            await query.edit_message_text("✅ Correct! You win! 🎉")
        else:
            # Wrong answer
            correct_option = json.loads(question['options'])[question['correct_answer']]
            await query.edit_message_text(f"❌ Wrong answer!\nCorrect answer: {correct_option}")

async def handle_profile_callback(query, context, user):
    """Handle profile callbacks"""
    action = query.data.split(":")[1]
    
    if action == "theme":
        # Get available themes from inventory
        cur.execute("""
            SELECT si.* FROM user_inventory ui
            JOIN shop_items si ON ui.item_id = si.id
            WHERE ui.user_id=? AND si.item_type='theme'
        """, (user['user_id'],))
        
        themes = cur.fetchall()
        
        if not themes:
            await query.edit_message_text(
                "You don't have any themes yet!\nBuy them from the shop: /shop",
                parse_mode="Markdown"
            )
            return
        
        message = "🎨 *Choose Theme*\n\nCurrent: " + user['theme_preference']
        
        keyboard = []
        for theme in themes:
            check = "✓" if theme['item_value'] == user['theme_preference'] else ""
            keyboard.append([
                InlineKeyboardButton(
                    f"{theme['name']} {check}",
                    callback_data=f"profile:set_theme:{theme['item_value']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu:profile")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode="Markdown", reply_markup=reply_markup)
    
    elif action.startswith("set_theme"):
        theme = action.split(":")[2]
        update_user(user['user_id'], theme_preference=theme)
        await query.edit_message_text(f"✅ Theme changed to {theme}!")
    
    elif action == "stats":
        # Show detailed stats
        # Get game stats
        cur.execute("SELECT COUNT(*) as games FROM game_players WHERE user_id=?", (user['user_id'],))
        games_played = cur.fetchone()['games']
        
        cur.execute("SELECT COUNT(*) as wins FROM game_sessions WHERE winner=?", (user['user_id'],))
        games_won = cur.fetchone()['wins']
        
        cur.execute("SELECT COUNT(*) as friends FROM friends WHERE user_id=?", (user['user_id'],))
        friend_count = cur.fetchone()['friends']
        
        cur.execute("SELECT COUNT(*) as purchases FROM user_purchases WHERE user_id=?", (user['user_id'],))
        purchases = cur.fetchone()['purchases']
        
        message = f"""📊 *Detailed Statistics*

🎮 Games Played: {games_played}
🏆 Games Won: {games_won}
🤝 Friends: {friend_count}
🛍️ Purchases: {purchases}
💬 Total Messages: {user['total_requests']}

⚡ XP per message: 10
💰 Coins per message: 5"""
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu:profile")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode="Markdown", reply_markup=reply_markup)

# ==================== MESSAGE HANDLERS ====================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    uid = update.effective_user.id
    
    # Check maintenance mode
    if BOT_UPDATING:
        await update.message.reply_text(
            "⚙️ Bot abhi update ho raha hai...\nThodi der baad aana bestie 💖"
        )
        return

    # Ban check
    if is_banned(uid):
        await update.message.reply_text(
            "🚫 Aap ban ho chuke ho.\nAdmin se contact karein 🙏"
        )
        return

    # Daily limit check
    if check_daily_limit(uid):
        await update.message.reply_text(
            "📊 Daily limit reached (100 msgs). Kal aana bestie! 💖"
        )
        return

    # Check if user exists
    user = get_user(uid)
    if not user:
        user_id = create_user(uid, update.effective_user.username, update.effective_user.first_name)
        user = get_user(user_id)

    text = update.message.text
    save_msg(uid, "user", text)
    
    # Increment daily count
    increment_daily_count(uid)

    smart = text.lower()
    
    # Check if in broadcast mode
    if context.user_data.get('broadcast_mode'):
        if admin_manager.is_admin(uid):
            # Send broadcast to all users
            cur.execute("SELECT telegram_id FROM users WHERE telegram_id IS NOT NULL")
            users = cur.fetchall()
            
            success_count = 0
            fail_count = 0
            
            for u in users:
                try:
                    await context.bot.send_message(
                        chat_id=int(u['telegram_id']),
                        text=f"📢 *Broadcast Message*\n\n{text}",
                        parse_mode="Markdown"
                    )
                    success_count += 1
                    await asyncio.sleep(0.05)  # Rate limit
                except:
                    fail_count += 1
            
            await update.message.reply_text(
                f"✅ Broadcast sent!\n\n"
                f"✓ Success: {success_count}\n"
                f"✗ Failed: {fail_count}"
            )
            
            context.user_data['broadcast_mode'] = False
            return
        else:
            context.user_data['broadcast_mode'] = False
    
    # Voice commands
    if "voice on" in smart:
        set_voice_mode(uid, 1)
        await update.message.reply_text("🔊 Voice ON - ab main bolungi 🎤")
        return
    
    if "voice off" in smart:
        set_voice_mode(uid, 0)
        await update.message.reply_text("🔇 Voice OFF - ab sirf text mode")
        return
    
    # Check for game challenges
    if "challenge" in smart and "@" in smart:
        # Extract username
        mention = re.search(r'@(\w+)', smart)
        if mention:
            username = mention.group(1)
            
            # Find user
            cur.execute("SELECT * FROM users WHERE username=?", (username,))
            target = cur.fetchone()
            
            if target and friend_manager.are_friends(user['user_id'], target['user_id']):
                # Create game session
                session_id = game_manager.create_session("quiz", user['user_id'])
                
                # Notify target
                try:
                    keyboard = [
                        [InlineKeyboardButton("🎮 Accept Challenge", callback_data=f"game:join:{session_id}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await context.bot.send_message(
                        chat_id=int(target['telegram_id']),
                        text=f"🎮 {user['first_name'] or user['username']} has challenged you to a game!",
                        reply_markup=reply_markup
                    )
                    
                    await update.message.reply_text("✅ Challenge sent!")
                except:
                    await update.message.reply_text("❌ Could not send challenge")
                return

    # Web search
    web_ctx = ""
    if "web search " in smart:
        query = smart.replace("web search ", "").strip()
        await safe_action(context.bot, update.effective_chat.id)
        web_ctx = await search_web_serp(query)

    # YouTube search
    yt_ctx = ""
    if "youtube " in smart:
        query = smart.replace("youtube ", "").strip()
        await safe_action(context.bot, update.effective_chat.id)
        yt_ctx = search_youtube(query)

    # Image generation
    if any(x in smart for x in ["draw ", "generate ", "create image "]):
        prompt = re.sub(r"(draw|generate|create image)", "", smart).strip()
        if prompt:
            await safe_action(context.bot, update.effective_chat.id, ChatAction.UPLOAD_PHOTO)
            
            img = await generate_image_pollinations(prompt)
            if img:
                await update.message.reply_photo(
                    photo=InputFile(img, "image.jpg"),
                    caption=f"🎨 Generated: {prompt}"
                )
                
                # Add XP
                level_manager.add_xp(user['user_id'], 15)
                coin_manager.add_coins(user['user_id'], 10, "image_generation")
                return

    # Time/Date
    if "time" in smart or "date" in smart:
        now = datetime.now()
        msg = f"🕒 Time: {now.strftime('%H:%M:%S')}\n📅 Date: {now.strftime('%d %B %Y')}"
        await update.message.reply_text(msg)
        return

    # AI Chat
    messages = [{"role": "system", "content": """You are Priya — a friendly Indian AI created by Subojeet Mandal.
Speak natural Hinglish, warm and supportive.
Help with coding, studies, and daily questions clearly.
Be simple, positive, and respectful.
You can chat, play games, help with shopping, and connect with friends.
Always encourage users to have fun and learn."""}]
    
    # Add memory
    messages += load_memory(uid)[-12:]

    if web_ctx:
        messages.append({"role": "system", "content": web_ctx})
    if yt_ctx:
        messages.append({"role": "system", "content": yt_ctx})

    await safe_action(context.bot, update.effective_chat.id)
    
    # Get reply from AI
    reply = await ask_openrouter(messages)

    save_msg(uid, "assistant", reply)
    await update.message.reply_text(reply)
    
    # Check for badges
    awarded = badge_manager.check_and_award(user['user_id'])
    if awarded:
        badge_names = [b["name"] for b in awarded]
        await update.message.reply_text(f"🎉 Congratulations! You earned new badges: {', '.join(badge_names)}")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages"""
    uid = update.effective_user.id
    
    user = get_user(uid)
    if not user or not user['voice_mode']:
        await update.message.reply_text("Voice mode is off. Use 'voice on' to enable.")
        return
    
    await update.message.reply_text("🎤 Voice message received! Processing...")
    # Voice processing would go here

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages"""
    await update.message.reply_text("📸 Nice photo! But I can't see it yet. Working on it!")

# ==================== ERROR HANDLER ====================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again later."
            )
    except:
        pass

# ==================== FLASK WEB APP ====================

app_web = Flask(__name__)
app_web.secret_key = os.getenv("FLASK_SECRET_KEY", "priya_secret_key_2024")
CORS(app_web)
socketio = SocketIO(app_web, cors_allowed_origins="*")

# Flask Login
login_manager = LoginManager()
login_manager.init_app(app_web)
login_manager.login_view = 'login'

class WebUser(UserMixin):
    def __init__(self, user_id, username, role):
        self.id = user_id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    user = get_user(user_id)
    if user:
        return WebUser(user['user_id'], user['username'], user['role'])
    return None

@app_web.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app_web.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple admin login (in production, use proper auth)
        if username == os.getenv("ADMIN_USERNAME") and password == os.getenv("ADMIN_PASSWORD"):
            # Find or create admin user
            cur.execute("SELECT * FROM users WHERE username=?", (username,))
            user = cur.fetchone()
            
            if not user:
                # Create admin user
                user_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO users (user_id, username, role, created_at)
                    VALUES (?, ?, 'admin', ?)
                """, (user_id, username, int(time.time())))
                conn.commit()
            else:
                user_id = user['user_id']
            
            web_user = WebUser(user_id, username, 'admin')
            login_user(web_user)
            return redirect(url_for('admin_dashboard'))
        
        flash("Invalid credentials", "danger")
    
    return render_template('login.html')

@app_web.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app_web.route('/admin')
@login_required
def admin_dashboard():
    """Admin dashboard"""
    if current_user.role not in ['admin', 'super_admin']:
        flash("Access denied", "danger")
        return redirect(url_for('index'))
    
    # Get stats
    cur.execute("SELECT COUNT(*) as total FROM users")
    total_users = cur.fetchone()['total']
    
    cur.execute("SELECT COUNT(*) as total FROM users WHERE last_request_date=date('now')")
    active_today = cur.fetchone()['total']
    
    cur.execute("SELECT SUM(total_requests) as total FROM users")
    total_messages = cur.fetchone()['total'] or 0
    
    cur.execute("SELECT SUM(coin_balance) as total FROM users")
    total_coins = cur.fetchone()['total'] or 0
    
    # Recent users
    cur.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT 10")
    recent_users = cur.fetchall()
    
    return render_template('admin_dashboard.html',
                         total_users=total_users,
                         active_today=active_today,
                         total_messages=total_messages,
                         total_coins=total_coins,
                         recent_users=recent_users)

@app_web.route('/admin/users')
@login_required
def admin_users():
    """User management"""
    if current_user.role not in ['admin', 'super_admin']:
        flash("Access denied", "danger")
        return redirect(url_for('index'))
    
    cur.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = cur.fetchall()
    
    return render_template('admin_users.html', users=users)

@app_web.route('/admin/shop')
@login_required
def admin_shop():
    """Shop management"""
    if current_user.role not in ['admin', 'super_admin']:
        flash("Access denied", "danger")
        return redirect(url_for('index'))
    
    items = shop_manager.get_items()
    categories = shop_manager.get_categories()
    
    return render_template('admin_shop.html', items=items, categories=categories)

@app_web.route('/admin/stats')
@login_required
def admin_stats():
    """Statistics"""
    if current_user.role not in ['admin', 'super_admin']:
        flash("Access denied", "danger")
        return redirect(url_for('index'))
    
    # Daily stats for last 7 days
    dates = []
    user_counts = []
    msg_counts = []
    
    for i in range(6, -1, -1):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        dates.append(date)
        
        cur.execute("SELECT COUNT(*) as count FROM users WHERE date(last_request_date, 'unixepoch')=?", (date,))
        user_counts.append(cur.fetchone()['count'])
        
        # This is simplified - in production you'd have daily message logs
        msg_counts.append(random.randint(100, 1000))
    
    return render_template('admin_stats.html',
                         dates=dates,
                         user_counts=user_counts,
                         msg_counts=msg_counts)

# ==================== MAIN FUNCTION ====================

def run_web():
    """Run Flask web server"""
    app_web.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)

def main():
    """Main function"""
    # Start web server in thread
    threading.Thread(target=run_web, daemon=True).start()
    
    # Create bot application
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Set bot instance for web
    set_bot(app.bot)
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("umenu", umenu_command))
    app.add_handler(CommandHandler("admin", admin_menu))
    app.add_handler(CommandHandler("clearall", clearall_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("daily", daily_command))
    app.add_handler(CommandHandler("shop", shop_command))
    app.add_handler(CommandHandler("games", games_command))
    app.add_handler(CommandHandler("friends", friends_command))
    app.add_handler(CommandHandler("connect", connect_command))
    app.add_handler(CommandHandler("help", help_command))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Callback handler
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    logger.info("🚀 PRIYA AI BOT STARTED with all features!")
    logger.info(f"🌐 Web interface: http://localhost:10000")
    logger.info(f"📱 Bot is running...")
    logger.info(f"⚙️ Environment: {ENV}")
    logger.info(f"📦 Version: {CONFIG_VERSION}")
    logger.info(f"🔑 OpenRouter keys loaded: {len(OPENROUTER_KEYS)}")
    
    # Start polling
    app.run_polling()

if __name__ == "__main__":
    main()
