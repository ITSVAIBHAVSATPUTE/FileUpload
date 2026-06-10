import os
import zipfile
import tempfile
import shutil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from github import Github

BOT_TOKEN = "8208647691:AAESXj-hmmES2DYv7nhH2TYxZ4UvTmWceAI"  # @BotFather se lo

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {}
    await update.message.reply_text(
        "🤖 *GitHub ZIP Uploader*\n\n"
        "1️⃣ /token - GitHub token daalo\n"
        "2️⃣ /connect - Connect karo aur repos dekho\n"
        "3️⃣ ZIP file bhejo - Upload ho jayega\n\n"
        "Pehle /token phir /connect",
        parse_mode="Markdown"
    )

async def set_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /token github_pat_xxxxx\n\nToken kaise banaye:\nGitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate → repo tick karo")
        return
    
    token = context.args[0]
    user_data[user_id]['token'] = token
    
    try:
        g = Github(token)
        user = g.get_user()
        user_data[user_id]['github'] = g
        user_data[user_id]['username'] = user.login
        await update.message.reply_text(f"✅ Connected as: *{user.login}*\n\nAb /connect karo repo select karne ke liye", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Invalid token! Error: {str(e)}")

async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if 'github' not in user_data.get(user_id, {}):
        await update.message.reply_text("❌ Pehle /token daalo!")
        return
    
    g = user_data[user_id]['github']
    user = g.get_user()
    
    await update.message.reply_text("📡 Fetching your repositories...")
    
    # Get all repos
    repos = []
    for repo in user.get_repos():
        repos.append(repo.name)
    
    # Limit to 20 repos
    repos = repos[:20]
    
    # Create buttons
    keyboard = []
    for repo in repos:
        keyboard.append([InlineKeyboardButton(f"📁 {repo}", callback_data=f"select_{repo}")])
    keyboard.append([InlineKeyboardButton("➕ Create New Repo", callback_data="create_new")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"📂 *Select repository:*\n\nTotal: {len(repos)} repos\n\n👇 Click on any repo to upload there,\nor click 'Create New Repo'",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith("select_"):
        repo_name = data.replace("select_", "")
        user_data[user_id]['target_repo'] = repo_name
        await query.edit_message_text(f"✅ Selected repo: *{repo_name}*\n\nAb ZIP file bhejo, main extract aur upload kar dunga!", parse_mode="Markdown")
    
    elif data == "create_new":
        await query.edit_message_text("📝 *New Repo*\n\nRepo name bhejo (jaise: my-backup-2026)\n\nSirf name likho, link nahi.", parse_mode="Markdown")
        user_data[user_id]['awaiting_repo_name'] = True

async def handle_repo_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_data.get(user_id, {}).get('awaiting_repo_name'):
        repo_name = update.message.text.strip()
        
        # Remove any spaces or special chars
        repo_name = repo_name.replace(" ", "-").lower()
        
        try:
            g = user_data[user_id]['github']
            user = g.get_user()
            repo = user.create_repo(repo_name)
            user_data[user_id]['target_repo'] = repo_name
            user_data[user_id]['awaiting_repo_name'] = False
            
            await update.message.reply_text(f"✅ *New repo created:* {repo_name}\n\nAb ZIP file bhejo!", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Repo create nahi ho paaya! Error: {str(e)}\n\nDoosra naam try karo.")

async def handle_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if 'github' not in user_data.get(user_id, {}):
        await update.message.reply_text("❌ Pehle /token aur /connect karo!")
        return
    
    if 'target_repo' not in user_data.get(user_id, {}):
        await update.message.reply_text("❌ Pehle /connect se repo select karo!")
        return
    
    document = update.message.document
    if not document.file_name.endswith('.zip'):
        await update.message.reply_text("❌ Sirf ZIP file bhejo!")
        return
    
    await update.message.reply_text(f"📥 *ZIP mil gaya:* {document.file_name}\n\n⏳ Processing...", parse_mode="Markdown")
    
    # Download ZIP
    file = await context.bot.get_file(document.file_id)
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, document.file_name)
    await file.download_to_drive(zip_path)
    
    # Extract with progress
    extract_dir = os.path.join(temp_dir, "extracted")
    os.makedirs(extract_dir, exist_ok=True)
    
    progress_msg = await update.message.reply_text("📂 *Extracting ZIP...*\n\n", parse_mode="Markdown")
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        file_list = zip_ref.namelist()
        total_files = len(file_list)
        
        for i, file_name in enumerate(file_list):
            zip_ref.extract(file_name, extract_dir)
            if i % 10 == 0 or i == total_files - 1:
                await progress_msg.edit_text(
                    f"📂 *Extracting ZIP...*\n\n"
                    f"📄 `{file_name}`\n"
                    f"Progress: {i+1}/{total_files} files\n"
                    f"{(i+1)*100//total_files}% complete",
                    parse_mode="Markdown"
                )
    
    await progress_msg.edit_text(f"✅ *Extraction complete!* {total_files} files extracted.\n\n⏳ Uploading to GitHub...", parse_mode="Markdown")
    
    # Upload to GitHub
    try:
        g = user_data[user_id]['github']
        user = g.get_user()
        repo_name = user_data[user_id]['target_repo']
        repo = user.get_repo(repo_name)
        
        uploaded = 0
        failed = 0
        
        # Get all files to upload
        all_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                all_files.append(os.path.join(root, file))
        
        upload_msg = await update.message.reply_text(f"📤 *Uploading to GitHub...*\n\n0/{len(all_files)} files", parse_mode="Markdown")
        
        for i, file_path in enumerate(all_files):
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
                
                # Update progress every file
                if i % 5 == 0 or i == len(all_files) - 1:
                    await upload_msg.edit_text(
                        f"📤 *Uploading to GitHub...*\n\n"
                        f"📄 `{github_path}`\n"
                        f"Progress: {i+1}/{len(all_files)} files\n"
                        f"✅ Uploaded: {uploaded} | ❌ Failed: {failed}",
                        parse_mode="Markdown"
                    )
                    
            except Exception as e:
                failed += 1
                print(f"Failed: {github_path} - {e}")
        
        # Cleanup
        shutil.rmtree(temp_dir)
        
        repo_url = f"https://github.com/{user.login}/{repo_name}"
        await upload_msg.edit_text(
            f"✅ *Upload Complete!*\n\n"
            f"📁 Repo: [{repo_name}]({repo_url})\n"
            f"📄 Files extracted: {total_files}\n"
            f"✅ Uploaded: {uploaded}\n"
            f"❌ Failed: {failed}\n\n"
            f"[🔗 Open Repository]({repo_url})",
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
    app.add_handler(CommandHandler("connect", connect))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_repo_name))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_zip))
    
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()