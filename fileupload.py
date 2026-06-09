import os
import zipfile
import shutil
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from github import Github

# Bot Token - Telegram se @BotFather se lena
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

# Temporary storage
user_data = {}

class GitHubUploader:
    def __init__(self, token):
        self.g = Github(token)
        self.user = self.g.get_user()
    
    def create_repo(self, repo_name):
        try:
            repo = self.user.create_repo(repo_name)
            return repo, None
        except:
            repo = self.user.get_repo(repo_name)
            return repo, "exists"
    
    def upload_folder(self, repo, folder_path, branch="main"):
        uploaded = []
        failed = []
        
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                github_path = os.path.relpath(file_path, folder_path)
                
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    
                    # Check if file exists
                    try:
                        existing = repo.get_contents(github_path, ref=branch)
                        repo.update_file(github_path, f"Update {github_path}", content, existing.sha, branch=branch)
                    except:
                        repo.create_file(github_path, f"Add {github_path}", content, branch=branch)
                    
                    uploaded.append(github_path)
                except Exception as e:
                    failed.append(f"{github_path}: {str(e)}")
        
        return uploaded, failed

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {}
    
    await update.message.reply_text(
        "🤖 *GitHub Uploader Bot*\n\n"
        "1️⃣ Pehle GitHub Token daalo\n"
        "2️⃣ Phir ZIP file bhejo\n"
        "3️⃣ Bot extract karke GitHub pe upload karega\n\n"
        "Token daalne ke liye: /settoken",
        parse_mode="Markdown"
    )

async def set_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "Usage: `/settoken YOUR_GITHUB_TOKEN`\n\n"
            "Token kaise banaye:\n"
            "1. GitHub → Settings → Developer settings\n"
            "2. Personal access tokens → Tokens (classic)\n"
            "3. Generate new token → 'repo' tick karo\n"
            "4. Generate → Token copy karo",
            parse_mode="Markdown"
        )
        return
    
    token = context.args[0]
    user_data[user_id]['token'] = token
    
    # Test token
    try:
        g = Github(token)
        user = g.get_user()
        await update.message.reply_text(f"✅ Token valid!\n👤 Logged in as: {user.login}")
    except:
        await update.message.reply_text("❌ Invalid token! Check and try again.")
        return
    
    await update.message.reply_text(
        "✅ Token saved!\n\n"
        "Ab ZIP file bhejo:\n"
        "1. Folder ko ZIP karo\n"
        "2. Yahan bhejo\n"
        "3. Bot extract karega aur upload karega"
    )

async def handle_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if 'token' not in user_data.get(user_id, {}):
        await update.message.reply_text("❌ Pehle /settoken se GitHub token daalo!")
        return
    
    document = update.message.document
    if not document.file_name.endswith('.zip'):
        await update.message.reply_text("❌ Sirf ZIP file bhejo!")
        return
    
    await update.message.reply_text("📥 ZIP file mil gaya! Processing...")
    
    # Download ZIP
    file = await context.bot.get_file(document.file_id)
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, document.file_name)
    await file.download_to_drive(zip_path)
    
    # Extract ZIP
    extract_dir = os.path.join(temp_dir, "extracted")
    os.makedirs(extract_dir, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    await update.message.reply_text("📂 ZIP extract ho gaya! Uploading to GitHub...")
    
    # Upload to GitHub
    try:
        uploader = GitHubUploader(user_data[user_id]['token'])
        repo_name = os.path.splitext(document.file_name)[0]
        
        await update.message.reply_text(f"📁 Creating repo: {repo_name}")
        repo, status = uploader.create_repo(repo_name)
        
        if status == "exists":
            await update.message.reply_text(f"⚠️ Repo {repo_name} already exists! Uploading...")
        
        # Upload files
        uploaded, failed = uploader.upload_folder(repo, extract_dir)
        
        # Cleanup
        shutil.rmtree(temp_dir)
        
        # Result
        result_msg = f"✅ *Upload Complete!*\n\n"
        result_msg += f"📦 Repo: [{repo_name}](https://github.com/{uploader.user.login}/{repo_name})\n"
        result_msg += f"📄 Uploaded: {len(uploaded)} files\n"
        
        if failed:
            result_msg += f"❌ Failed: {len(failed)} files\n\n"
            result_msg += "Check repo directly."
        
        await update.message.reply_text(result_msg, parse_mode="Markdown", disable_web_page_preview=True)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "upload_another":
        await query.message.reply_text("Send another ZIP file!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("settoken", set_token))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_zip))
    
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()