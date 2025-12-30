#!/usr/bin/env python3
"""
Jarvis Telegram Bot - Mobile Interface
Natural language interface to all Jarvis capabilities via Telegram
"""

import os
import sys
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import asyncio
from typing import Dict, Any

# Add paths
sys.path.append('/Volumes/AI_WORKSPACE/CORE/jarvis/modules')
sys.path.append('/Volumes/AI_WORKSPACE/video_analyzer')

# Import modules
from video_analyzer import VideoAnalyzer
from video_knowledge_loader import search_video_knowledge

# Configuration
TELEGRAM_BOT_TOKEN = "8004546042:AAF9_VBt6G-uh2XGHCNhpP47C3egcjI9mtI"
API_BASE = "http://localhost:8000"

class JarvisTelegramBot:
    """Enhanced Telegram bot with full Jarvis integration"""

    def __init__(self):
        self.api_base = API_BASE
        self.analyzer = VideoAnalyzer()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        keyboard = [
            [InlineKeyboardButton("🎬 Analyze Video", callback_data="analyze")],
            [InlineKeyboardButton("⚡ Workflows", callback_data="workflows")],
            [InlineKeyboardButton("🤖 Agents", callback_data="agents")],
            [InlineKeyboardButton("🔍 Search Knowledge", callback_data="search")],
            [InlineKeyboardButton("📊 System Status", callback_data="status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        welcome_message = """
🚀 *Jarvis Command Center*

I'm your AI assistant with access to:
• Video analysis & knowledge extraction
• Automation workflows
• Specialist AI agents
• Knowledge search
• System monitoring

Send me a video URL to analyze, or use the buttons below:
        """

        await update.message.reply_text(
            welcome_message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command handler"""
        help_text = """
📚 *Available Commands*

*Natural Language:*
Just type what you want! Examples:
• "Analyze this video: [URL]"
• "Search for n8n tutorials"
• "Run performance analysis"
• "Show system status"

*Quick Commands:*
/start - Main menu
/analyze [URL] - Analyze video
/search [query] - Search knowledge
/agent [name] [task] - Run agent
/workflow [id] - Trigger workflow
/status - System status
/help - This message

*Tips:*
• Send any video URL directly to analyze it
• Use natural language for complex requests
• All features from web interface work here!
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Analyze video command"""
        if not context.args:
            await update.message.reply_text("Please provide a URL: /analyze [URL]")
            return

        url = context.args[0]
        await update.message.reply_text("🔄 Analyzing video...")

        try:
            # Call API to analyze
            response = requests.post(
                f"{self.api_base}/analyze",
                json={"url": url, "analysis_type": "video"}
            )
            result = response.json()

            if result.get("status") == "completed":
                analysis = result.get("analysis", {})
                message = self._format_analysis_result(analysis)
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Analysis failed. Please try again.")

        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Search knowledge command"""
        if not context.args:
            await update.message.reply_text("Please provide a search query: /search [query]")
            return

        query = ' '.join(context.args)
        await update.message.reply_text(f"🔍 Searching for: {query}")

        try:
            response = requests.get(
                f"{self.api_base}/knowledge/search",
                params={"query": query}
            )
            result = response.json()

            if result.get("results"):
                message = f"*Found {result['count']} results:*\n\n"
                for item in result["results"][:3]:
                    message += f"📄 *{item['skill']}*\n{item['snippet']}\n\n"
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text("No results found.")

        except Exception as e:
            await update.message.reply_text(f"Search error: {str(e)}")

    async def agent_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Execute agent command"""
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /agent [agent_name] [task description]")
            return

        agent = context.args[0]
        task = ' '.join(context.args[1:])

        await update.message.reply_text(f"🤖 Executing {agent} agent...")

        try:
            response = requests.post(
                f"{self.api_base}/agent/execute",
                json={"agent": agent, "task": task}
            )
            result = response.json()

            if result.get("status") == "executing":
                await update.message.reply_text(
                    f"✅ Agent started!\nTask ID: `{result['task_id']}`",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(f"Failed: {result}")

        except Exception as e:
            await update.message.reply_text(f"Agent error: {str(e)}")

    async def workflow_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Trigger workflow command"""
        if not context.args:
            await update.message.reply_text("Please provide workflow ID: /workflow [id]")
            return

        workflow_id = context.args[0]
        params = {}
        if len(context.args) > 1:
            # Try to parse additional params as JSON
            try:
                params = json.loads(' '.join(context.args[1:]))
            except:
                pass

        await update.message.reply_text(f"⚡ Triggering workflow: {workflow_id}")

        try:
            response = requests.post(
                f"{self.api_base}/workflow/trigger",
                json={"workflow_id": workflow_id, "parameters": params}
            )
            result = response.json()

            if result.get("status") == "triggered":
                await update.message.reply_text("✅ Workflow triggered successfully!")
            else:
                await update.message.reply_text(f"Failed: {result}")

        except Exception as e:
            await update.message.reply_text(f"Workflow error: {str(e)}")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """System status command"""
        try:
            # Get system status
            response = requests.get(f"{self.api_base}/processes")
            result = response.json()

            # Get recent tasks
            tasks_response = requests.get(f"{self.api_base}/tasks/recent")
            tasks = tasks_response.json()

            message = "*📊 System Status*\n\n"
            message += f"*Active Processes:* {result.get('count', 0)}\n"

            if result.get("processes"):
                message += "\n*Top Processes:*\n"
                for proc in result["processes"][:3]:
                    message += f"• {proc['name']} - CPU: {proc['cpu']:.1f}%, MEM: {proc['memory']:.1f}%\n"

            if tasks.get("tasks"):
                message += f"\n*Recent Tasks:* {len(tasks['tasks'])}\n"
                for task in tasks["tasks"][:3]:
                    message += f"• {task['type']} - {task['status']}\n"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            await update.message.reply_text(f"Status error: {str(e)}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages with NLP"""
        text = update.message.text.lower()

        # Check if it's a video URL
        if 'http' in text and any(domain in text for domain in ['youtube.com', 'youtu.be', 'tiktok.com']):
            # Extract URL and analyze
            import re
            urls = re.findall(r'(https?://[^\s]+)', update.message.text)
            if urls:
                await update.message.reply_text("🎬 Detected video URL, analyzing...")
                await self.analyze_video_direct(update, urls[0])
                return

        # Natural language processing
        try:
            response = requests.post(
                f"{self.api_base}/command",
                json={"command": text}
            )
            result = response.json()

            # Route based on detected action
            if result.get("action") == "video_analysis":
                await update.message.reply_text("Please provide a video URL to analyze.")
            elif result.get("action") == "workflow_automation":
                await update.message.reply_text("Which workflow would you like to trigger?")
            elif result.get("action") == "system_monitoring":
                await self.status_command(update, context)
            else:
                # Show suggested agents
                if result.get("suggested_agents"):
                    keyboard = []
                    for agent in result["suggested_agents"]:
                        keyboard.append([InlineKeyboardButton(
                            f"🤖 {agent}",
                            callback_data=f"agent:{agent}"
                        )])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await update.message.reply_text(
                        "I can help with that! Choose an agent:",
                        reply_markup=reply_markup
                    )
                else:
                    await update.message.reply_text(
                        f"Processing: {result.get('message', 'Understanding your request...')}"
                    )

        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")

    async def analyze_video_direct(self, update: Update, url: str):
        """Direct video analysis"""
        try:
            analysis = self.analyzer.analyze_video_url(url)
            if analysis:
                message = self._format_analysis_result(analysis)
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Could not analyze video")
        except Exception as e:
            await update.message.reply_text(f"Analysis error: {str(e)}")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()

        data = query.data

        if data == "analyze":
            await query.edit_message_text("Send me a video URL to analyze!")
        elif data == "workflows":
            await query.edit_message_text("Available workflows:\n• master-pipeline\n• video-processor\n• knowledge-extractor")
        elif data == "agents":
            # List agents
            response = requests.get(f"{self.api_base}/agents")
            agents = response.json().get("agents", {})
            message = "*Available Agents:*\n\n"
            for agent, desc in agents.items():
                message += f"• *{agent}*: {desc}\n"
            await query.edit_message_text(message, parse_mode='Markdown')
        elif data == "search":
            await query.edit_message_text("What would you like to search for?")
        elif data == "status":
            # Create a fake update object for status command
            await self.status_command(query, context)
        elif data.startswith("agent:"):
            agent = data.split(":")[1]
            await query.edit_message_text(f"What task should {agent} perform?")

    def _format_analysis_result(self, analysis: Dict) -> str:
        """Format analysis result for Telegram"""
        message = "📊 *Video Analysis Complete!*\n\n"

        if "metadata" in analysis:
            meta = analysis["metadata"]
            if meta.get("title"):
                message += f"*Title:* {meta['title'][:100]}\n"
            if meta.get("duration"):
                message += f"*Duration:* {meta['duration']} seconds\n"
            if meta.get("uploader"):
                message += f"*Uploader:* {meta['uploader']}\n"
            if meta.get("view_count"):
                message += f"*Views:* {meta['view_count']:,}\n"

        if analysis.get("transcript"):
            transcript = analysis["transcript"][:300] + "..." if len(analysis["transcript"]) > 300 else analysis["transcript"]
            message += f"\n*Transcript:*\n_{transcript}_\n"

        if analysis.get("extracted_features"):
            message += "\n*Key Features:*\n"
            for i, feature in enumerate(analysis["extracted_features"][:3], 1):
                message += f"{i}. {feature}\n"

        if analysis.get("frames"):
            message += f"\n*Frames Extracted:* {len(analysis['frames'])}"

        return message

def main():
    """Run the bot"""
    bot = JarvisTelegramBot()

    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CommandHandler("analyze", bot.analyze_command))
    application.add_handler(CommandHandler("search", bot.search_command))
    application.add_handler(CommandHandler("agent", bot.agent_command))
    application.add_handler(CommandHandler("workflow", bot.workflow_command))
    application.add_handler(CommandHandler("status", bot.status_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    application.add_handler(CallbackQueryHandler(bot.button_callback))

    # Run bot
    print("🤖 Jarvis Telegram Bot started!")
    application.run_polling()

if __name__ == "__main__":
    main()