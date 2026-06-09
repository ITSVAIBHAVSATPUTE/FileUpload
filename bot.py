import os
import zipfile
import tempfile
import shutil
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from github import Github

# Telegram bot token ( @BotFather se le )
BOT_TOKEN = "8208647691:AAESXj-hmmES2DYv7nhH2TYxZ4UvTmWceAI"

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {}
    await update.message.reply_text(
        "🤖 *GitHub Upload Bot*\n\n"
        "1. /token - GitHub token daalne ke liye\n"
        "2. /repo - Repo name daalne ke liye\n"
        "3. ZIP file bhejo - Upload ho jayega\n\n"
        "Pehle /token phir /repo phir ZIP bhejo",
        parse_mode="Markdown"
    )

async def set_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("Usage: /token github_pat_xxxxx")
        return
    
    token = context.args[0]
    user_data[user_id]['token'] = token
    
    try:
        g = Github(token)
        user = g.get_user()
        await update.message.reply_text(f"✅ Token valid!\n👤 GitHub: {user.login}\n\nAb /repo likho")
    except:
        await update.message.reply_text("❌ Token galat hai! Dobara daalo")

async def set_repo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("Usage: /repo repo_name\n\nExample: /repo my-backup")
        return
    
    repo_name = context.args[0]
    user_data[user_id]['repo'] = repo_name
    
    await update.message.reply_text(f"✅ Repo name: {repo_name}\n\nAb ZIP file bhejo, main upload kar dunga!")

async def handle_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if user has token and repo
    if 'token' not in user_data.get(user_id, {}):
        await update.message.reply_text("❌ Pehle /token daalo!")
        return
    
    if 'repo' not in user_data.get(user_id, {}):
        await update.message.reply_text("❌ Pehle /repo se repo name daalo!")
        return
    
    document = update.message.document
    if not document.file_name.endswith('.zip'):
        await update.message.reply_text("❌ Sirf ZIP file bhejo!")
        return
    
    await update.message.reply_text(f"📥 ZIP mil gaya: {document.file_name}\n\n⏳ Extract aur upload ho raha hai...")
    
    # Download ZIP
    file = await context.bot.get_file(document.file_id)
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, document.file_name)
    await file.download_to_drive(zip_path)
    
    # Extract
    extract_dir = os.path.join(temp_dir, "extracted")
    os.makedirs(extract_dir, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # Upload to GitHub
    try:
        token = user_data[user_id]['token']
        repo_name = user_data[user_id]['repo']
        
        g = Github(token)
        user = g.get_user()
        
        # Try to create repo if not exists
        try:
            repo = user.get_repo(repo_name)
            await update.message.reply_text(f"📁 Repo exist karta hai: {repo_name}")
        except:
            repo = user.create_repo(repo_name)
            await update.message.reply_text(f"✅ Naya repo bana diya: {repo_name}")
        
        # Upload all files
        uploaded = 0
        failed = 0
        
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                file_path = os.path.join(root, file)
                github_path = os.path.relpath(file_path, extract_dir)
                
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    
                    try:
                        existing = repo.get_contents(github_path)
                        repo.update_file(github_path, f"Update {github_path}", content, existing.sha)
                    except:
                        repo.create_file(github_path, f"Add {github_path}", content)
                    
                    uploaded += 1
                except Exception as e:
                    failed += 1
                    print(f"Failed: {github_path} - {e}")
        
        # Cleanup
        shutil.rmtree(temp_dir)
        
        repo_url = f"https://github.com/{user.login}/{repo_name}"
        await update.message.reply_text(
            f"✅ *Upload Complete!*\n\n"
            f"📁 Repo: [Click Here]({repo_url})\n"
            f"📄 Files uploaded: {uploaded}\n"
            f"❌ Failed: {failed}\n\n"
            f"Direct link: {repo_url}",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        shutil.rmtree(temp_dir)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("token", set_token))
    app.add_handler(CommandHandler("repo", set_repo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_zip))
    
    print("🤖 Bot chal raha hai...")
    app.run_polling()

if __name__ == "__main__":
    main()
