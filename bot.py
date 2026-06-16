import subprocess
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Your Telegram Bot Token (get from @BotFather)
BOT_TOKEN = "8208647691:AAEeDi_3YWGUHYk5NVSMFrxcTHrYbnGW-EQ"

# Path to your .exe file (you'll upload this to Render)
EXE_PATH = "checker.exe"

async def start(update: Update, context):
    await update.message.reply_text("✅ Bot is ready! Send me a command or file.")

async def run_exe(update: Update, context):
    if not os.path.exists(EXE_PATH):
        await update.message.reply_text("❌ .exe file not found on server!")
        return
    
    await update.message.reply_text("⏳ Running your .exe file...")
    
    try:
        # Run .exe using WINE
        result = subprocess.run(
            ["wine", EXE_PATH],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout if result.stdout else result.stderr
        
        if output:
            # Send output (max 4000 characters for Telegram)
            if len(output) > 4000:
                output = output[:4000] + "\n\n... (truncated)"
            await update.message.reply_text(f"📤 Output:\n```\n{output}\n```", parse_mode="Markdown")
        else:
            await update.message.reply_text("✅ Program ran but produced no output.")
            
    except subprocess.TimeoutExpired:
        await update.message.reply_text("⏰ Program took too long (30s timeout).")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def handle_file(update: Update, context):
    file = await update.message.document.get_file()
    file_path = f"/app/{update.message.document.file_name}"
    await file.download_to_drive(file_path)
    await update.message.reply_text(f"✅ File saved as {file_path}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("run", run_exe))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()