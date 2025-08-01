
import asyncio
import json
import os
import logging
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
from aiogram.types import FSInputFile
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart, Command

TOKEN = os.getenv("TELEGRAM_TOKEN", "8038418922:AAEtOuH1NJeIEeOGBWDCQkVf1Zqf77Nx63U")
CHANNEL = "@kamolidinov_channel"
ADMIN_USERNAME = "@kamolidinov_uz"
ADMIN_PASSWORD = "KAMOLIDINOVPRODUCT™"

# Fayllar
PROFILE_FILE = "profiles.json"
COINS_FILE = "coins.json"
TESTS_FILE = "tests.json"
RESULTS_FILE = "results.json"
REFERRALS_FILE = "referrals.json"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# === JSON yordamchi ===
def load_json(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# === Referal tizim ===
def add_coins(user_id, amount):
    """Foydalanuvchiga coin qo'shish"""
    coins = load_json(COINS_FILE)
    user_id_str = str(user_id)
    
    if user_id_str not in coins:
        coins[user_id_str] = 0
    
    coins[user_id_str] += amount
    save_json(COINS_FILE, coins)
    return coins[user_id_str]

def process_referral(referrer_id, new_user_id):
    """Referal sistemasini ishlash"""
    referrals = load_json(REFERRALS_FILE)
    referrer_str = str(referrer_id)
    new_user_str = str(new_user_id)
    
    # Yangi foydalanuvchi avval ro'yxatdan o'tmaganini tekshirish
    if new_user_str not in referrals:
        referrals[new_user_str] = {
            "referred_by": referrer_str,
            "date": datetime.now().strftime("%d.%m.%Y %H:%M")
        }
        
        # Referrer uchun coinlar
        if referrer_str not in referrals:
            referrals[referrer_str] = {
                "referred_by": None,
                "date": datetime.now().strftime("%d.%m.%Y %H:%M")
            }
        
        if "referrals_count" not in referrals[referrer_str]:
            referrals[referrer_str]["referrals_count"] = 0
        
        referrals[referrer_str]["referrals_count"] += 1
        save_json(REFERRALS_FILE, referrals)
        
        # Coinlar berish
        referrer_coins = add_coins(referrer_id, 10)  # Taklif qilgan uchun 10 coin
        new_user_coins = add_coins(new_user_id, 5)   # Yangi foydalanuvchi uchun 5 coin
        
        return True, referrer_coins, new_user_coins
    
    return False, 0, 0

# === State-lar ===
class TestStates(StatesGroup):
    waiting_for_password = State()
    waiting_for_image = State()
    waiting_for_test_code = State()
    waiting_for_answers = State()
    waiting_for_duration = State()

class CertificateStates(StatesGroup):
    selecting_test = State()

class ProfileEdit(StatesGroup):
    editing_name = State()
    editing_about = State()

# === Keyboard-lar ===
def main_menu():
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="👤 Admin"), KeyboardButton(text="🧪 Testlar")],
        [KeyboardButton(text="👤 Profil"), KeyboardButton(text="🪙 KPT Coin")],
        [KeyboardButton(text="🎓 Sertifikat")]
    ])

def test_menu():
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="✅ Testni tekshirish"), KeyboardButton(text="✏️ Test yaratish")],
        [KeyboardButton(text="🔙 Asosiy menyu")]
    ])

def profile_edit_menu():
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="✏️ Ismni o'zgartirish"), KeyboardButton(text="✏️ Ma'lumot o'zgartirish")],
        [KeyboardButton(text="🔙 Asosiy menyu")]
    ])

# === Certificate helper functions ===
def get_font(size=48):
    """Get font with fallbacks for different systems"""
    font_paths = [
        # Common system fonts
        "/System/Library/Fonts/Arial.ttf",  # macOS
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",  # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
        "/Windows/Fonts/arial.ttf",  # Windows
        "/Windows/Fonts/calibri.ttf",  # Windows
        "Roboto-Bold.ttf",  # Original font if exists
    ]
    
    for font_path in font_paths:
        try:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        except Exception:
            continue
    
    # Return default font if none found
    try:
        return ImageFont.load_default()
    except Exception:
        return None

def create_certificate_background():
    """Create a cybersecurity-themed certificate background"""
    width, height = 800, 600
    
    # Create image with dark background (black/dark blue)
    img = Image.new('RGB', (width, height), color='#0a0a0a')
    draw = ImageDraw.Draw(img)
    
    # Draw gradient-like effect with rectangles
    for i in range(0, height//4, 2):
        alpha = int(255 * (1 - i/(height//4)))
        color = f"#{hex(min(20+i//2, 40))[2:].zfill(2)}{hex(min(20+i//3, 60))[2:].zfill(2)}{hex(min(30+i//2, 80))[2:].zfill(2)}"
        try:
            draw.rectangle([0, i*4, width, (i+1)*4], fill=color)
        except:
            pass
    
    # Draw cyber-style borders
    border_color = '#00ff41'  # Matrix green
    border_width = 3
    
    # Main border
    draw.rectangle([border_width, border_width, width-border_width, height-border_width], 
                  outline=border_color, width=border_width)
    
    # Inner border with glow effect
    draw.rectangle([border_width*3, border_width*3, width-border_width*3, height-border_width*3], 
                  outline='#33ff66', width=1)
    
    # Corner decorations (cyber style)
    corner_size = 30
    corner_color = '#ff6b35'
    
    # Top corners
    for x, y in [(20, 20), (width-50, 20), (20, height-50), (width-50, height-50)]:
        draw.rectangle([x, y, x+corner_size, y+corner_size], outline=corner_color, width=2)
        draw.rectangle([x+5, y+5, x+corner_size-5, y+corner_size-5], outline=border_color, width=1)
    
    # Title
    title_font = get_font(42)
    if title_font:
        title_text = "SERTIFIKAT"
        bbox = draw.textbbox((0, 0), title_text, font=title_font)
        title_width = bbox[2] - bbox[0]
        title_x = (width - title_width) // 2
        
        # Glow effect for title
        for offset in [(2,2), (1,1), (0,0)]:
            color = '#00ff41' if offset == (0,0) else '#003311'
            draw.text((title_x + offset[0], 60 + offset[1]), title_text, font=title_font, fill=color)
    
    # Subtitle
    subtitle_font = get_font(18)
    if subtitle_font:
        subtitle_text = "Juda katta natija!"
        bbox = draw.textbbox((0, 0), subtitle_text, font=subtitle_font)
        subtitle_width = bbox[2] - bbox[0]
        subtitle_x = (width - subtitle_width) // 2
        draw.text((subtitle_x, 120), subtitle_text, font=subtitle_font, fill='#cccccc')
        
        # Organization info
        org_text = "Kamolidinov's Bot va @test_world_01 tomonidan taqdim etildi"
        bbox = draw.textbbox((0, 0), org_text, font=subtitle_font)
        org_width = bbox[2] - bbox[0]
        org_x = (width - org_width) // 2
        draw.text((org_x, 150), org_text, font=subtitle_font, fill='#999999')
    
    # Add some cyber elements
    # Draw circuit-like lines
    circuit_color = '#004422'
    for i in range(5):
        y = 200 + i * 40
        draw.line([(50, y), (width-50, y)], fill=circuit_color, width=1)
        draw.line([(50, y), (70, y-10), (90, y+10), (110, y-5)], fill=circuit_color, width=1)
    
    return img

def get_text_dimensions(draw, text, font):
    """Get text dimensions using the new textbbox method"""
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        return width, height
    except AttributeError:
        # Fallback for older PIL versions
        try:
            return draw.textsize(text, font=font)
        except AttributeError:
            # If both methods fail, estimate
            return len(text) * 12, 20

# === Test helper functions ===
def is_test_active(test_data):
    """Check if test is still active based on duration"""
    if 'created_time' not in test_data or 'duration_hours' not in test_data:
        return True  # Old tests without duration are considered active
    
    created_time = datetime.fromisoformat(test_data['created_time'])
    duration_hours = test_data['duration_hours']
    
    expiry_time = created_time + timedelta(hours=duration_hours)
    return datetime.now() < expiry_time

def get_user_tests(user_id):
    """Get list of tests user has participated in"""
    results = load_json(RESULTS_FILE)
    user_id_str = str(user_id)
    user_tests = []
    
    if user_id_str in results:
        for test_code, result in results[user_id_str].items():
            tests = load_json(TESTS_FILE)
            if test_code in tests:
                user_tests.append({
                    'code': test_code,
                    'score': result['score'],
                    'total': result['total'],
                    'date': result.get('date', 'Noma\'lum')
                })
    
    return user_tests

def create_results_pdf(test_code):
    """Create PDF with all test results"""
    results = load_json(RESULTS_FILE)
    tests = load_json(TESTS_FILE)
    profiles = load_json(PROFILE_FILE)
    
    if test_code not in tests:
        return None
    
    # Create PDF
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Background color
    p.setFillColorRGB(0.95, 0.95, 1.0)  # Light blue background
    p.rect(0, 0, width, height, fill=1)
    
    # Header background
    p.setFillColorRGB(0.2, 0.3, 0.8)  # Dark blue
    p.rect(0, height - 80, width, 80, fill=1)
    
    # Title
    p.setFillColorRGB(1, 1, 1)  # White text
    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, height - 50, f"📊 Test Natijalari - Kod: {test_code}")
    
    # Test info
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 70, f"Kamolidinov's Bot va @test_world_01 tomonidan taqdim etildi")
    
    # Headers
    y_position = height - 120
    p.setFillColorRGB(0, 0, 0)  # Black text
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y_position, "№")
    p.drawString(100, y_position, "Foydalanuvchi Ismi")
    p.drawString(320, y_position, "Natija")
    p.drawString(420, y_position, "Sana")
    
    # Draw header line
    p.setStrokeColorRGB(0.2, 0.3, 0.8)
    p.setLineWidth(2)
    p.line(50, y_position - 5, 520, y_position - 5)
    
    # Results
    y_position -= 30
    p.setFont("Helvetica", 11)
    
    count = 1
    for user_id, user_results in results.items():
        if test_code in user_results:
            result = user_results[test_code]
            
            # Get user name from profile
            user_name = profiles.get(user_id, {}).get('name', 'Noma\'lum foydalanuvchi')
            
            # Alternate row colors
            if count % 2 == 0:
                p.setFillColorRGB(0.9, 0.9, 0.95)
                p.rect(40, y_position - 5, 480, 18, fill=1)
            
            p.setFillColorRGB(0, 0, 0)
            p.drawString(50, y_position, str(count))
            p.drawString(100, y_position, user_name[:35])  # Show full name with limit
            
            # Score with color coding
            percentage = (result['score'] / result['total']) * 100
            if percentage >= 80:
                p.setFillColorRGB(0, 0.7, 0)  # Green for excellent
            elif percentage >= 60:
                p.setFillColorRGB(0.8, 0.6, 0)  # Orange for good
            else:
                p.setFillColorRGB(0.8, 0, 0)  # Red for needs improvement
            
            p.drawString(320, y_position, f"{result['score']}/{result['total']} ({percentage:.1f}%)")
            
            p.setFillColorRGB(0, 0, 0)
            date_value = result.get('date', 'Noma\'lum')
            p.drawString(420, y_position, date_value)
            
            y_position -= 25
            count += 1
            
            # New page if needed
            if y_position < 100:
                p.showPage()
                # Reset background for new page
                p.setFillColorRGB(0.95, 0.95, 1.0)
                p.rect(0, 0, width, height, fill=1)
                y_position = height - 50
    
    # Footer
    p.setFillColorRGB(0.5, 0.5, 0.5)
    p.setFont("Helvetica", 10)
    p.drawString(50, 30, f"Jami qatnashchilar: {count - 1} kishi")
    p.drawString(400, 30, f"Yaratildi: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    
    p.save()
    buffer.seek(0)
    return buffer

def create_certificates_pdf(test_code):
    """Create PDF with all certificates for a test"""
    results = load_json(RESULTS_FILE)
    tests = load_json(TESTS_FILE)
    profiles = load_json(PROFILE_FILE)
    
    if test_code not in tests:
        return None
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    def draw_certificate_background(p):
        """Draw certificate background design"""
        # Gradient background effect
        for i in range(0, int(height), 10):
            gray_level = 0.95 - (i / height) * 0.1
            p.setFillColorRGB(gray_level, gray_level, 1.0)
            p.rect(0, i, width, 10, fill=1)
        
        # Main border
        p.setStrokeColorRGB(0.2, 0.3, 0.8)  # Dark blue
        p.setLineWidth(5)
        p.rect(30, 30, width - 60, height - 60, fill=0)
        
        # Inner decorative border
        p.setStrokeColorRGB(0.8, 0.6, 0.2)  # Gold
        p.setLineWidth(2)
        p.rect(50, 50, width - 100, height - 100, fill=0)
        
        # Corner decorations
        corner_size = 40
        corners = [(50, 50), (width - 90, 50), (50, height - 90), (width - 90, height - 90)]
        
        p.setFillColorRGB(0.8, 0.6, 0.2)  # Gold fill
        for x, y in corners:
            # Draw decorative corners
            p.rect(x, y, corner_size, corner_size, fill=1)
            p.setFillColorRGB(0.2, 0.3, 0.8)  # Blue center
            p.rect(x + 10, y + 10, corner_size - 20, corner_size - 20, fill=1)
        
        # Top decorative line
        p.setStrokeColorRGB(0.8, 0.6, 0.2)
        p.setLineWidth(3)
        p.line(100, height - 120, width - 100, height - 120)
        
        # Bottom decorative line
        p.line(100, 120, width - 100, 120)
    
    # Title page with design
    draw_certificate_background(p)
    
    # Title
    p.setFillColorRGB(0.2, 0.3, 0.8)  # Dark blue
    p.setFont("Helvetica-Bold", 28)
    title_text = "🎓 SERTIFIKATLAR"
    text_width = p.stringWidth(title_text, "Helvetica-Bold", 28)
    p.drawString((width - text_width) / 2, height - 150, title_text)
    
    # Subtitle
    p.setFont("Helvetica", 16)
    subtitle = f"Test kodi: {test_code}"
    text_width = p.stringWidth(subtitle, "Helvetica", 16)
    p.drawString((width - text_width) / 2, height - 180, subtitle)
    
    # Organization info
    p.setFillColorRGB(0.4, 0.4, 0.4)
    p.setFont("Helvetica", 14)
    org_text = "Kamolidinov's Bot va @test_world_01 tomonidan taqdim etildi"
    text_width = p.stringWidth(org_text, "Helvetica", 14)
    p.drawString((width - text_width) / 2, height - 210, org_text)
    
    certificate_count = 0
    
    for user_id, user_results in results.items():
        if test_code in user_results:
            result = user_results[test_code]
            
            # Only create certificate if score is good (>= 60%)
            if result['score'] / result['total'] >= 0.6:
                p.showPage()  # New page for each certificate
                
                # Draw background for each certificate
                draw_certificate_background(p)
                
                # Certificate title
                p.setFillColorRGB(0.2, 0.3, 0.8)  # Dark blue
                p.setFont("Helvetica-Bold", 32)
                title_text = "SERTIFIKAT"
                text_width = p.stringWidth(title_text, "Helvetica-Bold", 32)
                p.drawString((width - text_width) / 2, height - 180, title_text)
                
                # Achievement subtitle
                p.setFillColorRGB(0.8, 0.6, 0.2)  # Gold
                p.setFont("Helvetica-Bold", 18)
                subtitle = "Bilimlaringiz bo'yicha ajoyib natija!"
                text_width = p.stringWidth(subtitle, "Helvetica-Bold", 18)
                p.drawString((width - text_width) / 2, height - 220, subtitle)
                
                # User name in box
                user_name = profiles.get(user_id, {}).get('name', 'Noma\'lum foydalanuvchi')
                p.setFillColorRGB(0.9, 0.9, 1.0)  # Light blue background
                p.rect(100, height - 300, width - 200, 40, fill=1)
                p.setStrokeColorRGB(0.2, 0.3, 0.8)
                p.setLineWidth(2)
                p.rect(100, height - 300, width - 200, 40, fill=0)
                
                p.setFillColorRGB(0.2, 0.3, 0.8)
                p.setFont("Helvetica-Bold", 20)
                name_text = f"{user_name}"
                text_width = p.stringWidth(name_text, "Helvetica-Bold", 20)
                p.drawString((width - text_width) / 2, height - 290, name_text)
                
                # Score with styling
                percentage = (result['score'] / result['total']) * 100
                p.setFillColorRGB(0, 0, 0)
                p.setFont("Helvetica", 16)
                
                score_text = f"Natija: {result['score']}/{result['total']} ({percentage:.1f}%)"
                text_width = p.stringWidth(score_text, "Helvetica", 16)
                p.drawString((width - text_width) / 2, height - 350, score_text)
                
                date_text = result.get('date', 'Noma\'lum')
                date_display = f"Sana: {date_text}"
                text_width = p.stringWidth(date_display, "Helvetica", 16)
                p.drawString((width - text_width) / 2, height - 380, date_display)
                
                # Congratulations message
                p.setFillColorRGB(0.6, 0.6, 0.6)
                p.setFont("Helvetica", 14)
                
                congrats_lines = [
                    "Tabriklaymiz! Siz muvaffaqiyatli",
                    "bilimlaringizni namoyish etdingiz.",
                    "",
                    "Rahmat! Testimizda qatnashganligingiz uchun"
                ]
                
                y_pos = height - 450
                for line in congrats_lines:
                    if line:
                        text_width = p.stringWidth(line, "Helvetica", 14)
                        p.drawString((width - text_width) / 2, y_pos, line)
                    y_pos -= 20
                
                # Signature area
                p.setStrokeColorRGB(0.5, 0.5, 0.5)
                p.setLineWidth(1)
                p.line(width - 200, 100, width - 50, 100)
                p.setFont("Helvetica", 10)
                p.drawString(width - 190, 85, "Kamolidinov's Bot")
                
                certificate_count += 1
    
    if certificate_count == 0:
        p.showPage()
        draw_certificate_background(p)
        p.setFillColorRGB(0.8, 0, 0)
        p.setFont("Helvetica-Bold", 16)
        no_cert_text = "Hech kim sertifikat olish uchun yetarli ball to'play olmadi."
        text_width = p.stringWidth(no_cert_text, "Helvetica-Bold", 16)
        p.drawString((width - text_width) / 2, height / 2, no_cert_text)
        
        p.setFillColorRGB(0.4, 0.4, 0.4)
        p.setFont("Helvetica", 14)
        min_text = "Sertifikat olish uchun kamida 60% ball kerak."
        text_width = p.stringWidth(min_text, "Helvetica", 14)
        p.drawString((width - text_width) / 2, height / 2 - 30, min_text)
    
    p.save()
    buffer.seek(0)
    return buffer

# === Kanalga obuna ===
async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["creator", "administrator", "member"]
    except:
        return False

# === /start (Referal tizim bilan) ===
@dp.message(CommandStart())
async def start(message: Message):
    if not await is_subscribed(message.from_user.id):
        btn = InlineKeyboardButton("🔔 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL[1:]}")
        await message.answer("Iltimos kanalga obuna bo'ling:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn]]))
        return
    
    # Referal tizimini tekshirish
    args = message.text.split()
    referrer_id = None
    
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
        except ValueError:
            pass
    
    # Yangi foydalanuvchi va referal tizim
    if referrer_id and referrer_id != message.from_user.id:
        success, referrer_coins, new_user_coins = process_referral(referrer_id, message.from_user.id)
        
        if success:
            # Yangi foydalanuvchiga xabar
            await message.answer(
                f"🎉 Botga xush kelibsiz!\n\n"
                f"🪙 Siz referal link orqali kelganingiz uchun {new_user_coins} KPT coin oldingiz!\n"
                f"💡 Siz ham boshqalarni taklif qilib coin olishingiz mumkin!",
                reply_markup=main_menu()
            )
            
            # Referer ga xabar
            try:
                referrals = load_json(REFERRALS_FILE)
                referrer_str = str(referrer_id)
                total_referrals = referrals.get(referrer_str, {}).get("referrals_count", 0)
                
                await bot.send_message(
                    referrer_id,
                    f"🎉 Yangi foydalanuvchi sizning linkingiz orqali keldi!\n\n"
                    f"🪙 Sizga 10 KPT coin qo'shildi! (Jami: {referrer_coins})\n"
                    f"👥 Jami taklif qilganlaringiz: {total_referrals} kishi\n"
                    f"💰 Davom eting va ko'proq coin to'plang!"
                )
            except Exception as e:
                logging.error(f"Could not notify referrer: {e}")
        else:
            await message.answer("Botga xush kelibsiz!", reply_markup=main_menu())
    else:
        # Oddiy start
        await message.answer("Botga xush kelibsiz!", reply_markup=main_menu())

# === Admin bo'limi ===
@dp.message(F.text == "👤 Admin")
async def admin(message: Message):
    await message.answer(f"admin  (yaratuvchi) haqida ma'lumot; bu botni middle dasturchi Kamolidinov Ulug'bek yaratdi.Admin: {ADMIN_USERNAME} agarda taklif yoki reklamalar kerak bo'lsa adminga murojaat qiling")

# === Profil bo'limi ===
@dp.message(F.text == "👤 Profil")
async def profile(message: Message):
    profiles = load_json(PROFILE_FILE)
    uid = str(message.from_user.id)
    if uid not in profiles:
        profiles[uid] = {
            "name": message.from_user.first_name,
            "about": "---"
        }
        save_json(PROFILE_FILE, profiles)
    p = profiles[uid]
    await message.answer(f"👤 Profil:\nIsm: {p['name']}\nQo'shimcha: {p['about']}", reply_markup=profile_edit_menu())

@dp.message(F.text == "✏️ Ismni o'zgartirish")
async def edit_name(message: Message, state: FSMContext):
    await message.answer("Yangi ismingizni yuboring:")
    await state.set_state(ProfileEdit.editing_name)

@dp.message(ProfileEdit.editing_name)
async def save_name(message: Message, state: FSMContext):
    profiles = load_json(PROFILE_FILE)
    uid = str(message.from_user.id)
    profiles[uid]["name"] = message.text
    save_json(PROFILE_FILE, profiles)
    await message.answer("✅ Ismingiz yangilandi.")
    await state.clear()

@dp.message(F.text == "✏️ Ma'lumot o'zgartirish")
async def edit_about(message: Message, state: FSMContext):
    await message.answer("Yangi ma'lumotni yuboring:")
    await state.set_state(ProfileEdit.editing_about)

@dp.message(ProfileEdit.editing_about)
async def save_about(message: Message, state: FSMContext):
    profiles = load_json(PROFILE_FILE)
    uid = str(message.from_user.id)
    profiles[uid]["about"] = message.text
    save_json(PROFILE_FILE, profiles)
    await message.answer("✅ Ma'lumot yangilandi.")
    await state.clear()

# === KPT Coin (Yangilangan referal tizim bilan) ===
@dp.message(F.text == "🪙 KPT Coin")
async def kpt(message: Message):
    coins = load_json(COINS_FILE)
    referrals = load_json(REFERRALS_FILE)
    uid = str(message.from_user.id)
    
    # Coin balansini tekshirish/yaratish
    if uid not in coins:
        coins[uid] = 0
        save_json(COINS_FILE, coins)
    
    # Referal ma'lumotlarini olish
    total_referrals = referrals.get(uid, {}).get("referrals_count", 0)
    
    # Bot username olish
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start={uid}"
    
    message_text = (
        f"🪙 **KPT Coin Hisobingiz**\n\n"
        f"💰 Joriy balansingiz: **{coins[uid]} KPT**\n"
        f"👥 Taklif qilganlaringiz: **{total_referrals} kishi**\n\n"
        f"📢 **Coin olish yo'llari:**\n"
        f"• Do'stlarni taklif qiling: +10 coin\n"
        f"• Yangi foydalanuvchi: +5 coin\n"
        f"• Test topshiring: +3 coin\n\n"
        f"🔗 **Sizning referal havolangiz:**\n"
        f"`{ref_link}`\n\n"
        f"💡 Bu linkni do'stlaringizga yuboring va coin to'plang!"
    )
    
    await message.answer(message_text, parse_mode="Markdown")

# === Test menyu ===
@dp.message(F.text == "🧪 Testlar")
async def test_menu_handler(message: Message):
    await message.answer("Test menyusi:", reply_markup=test_menu())

# === Test yaratish ===
@dp.message(F.text == "✏️ Test yaratish")
async def test_create(message: Message, state: FSMContext):
    await message.answer("Parolni kiriting:")
    await state.set_state(TestStates.waiting_for_password)

@dp.message(TestStates.waiting_for_password)
async def check_pass(message: Message, state: FSMContext):
    if message.text == ADMIN_PASSWORD:
        await message.answer("✅ Rasm yuboring:")
        await state.set_state(TestStates.waiting_for_image)
    else:
        await message.answer("❌ Noto'g'ri parol.")
        await state.clear()

@dp.message(TestStates.waiting_for_image, F.photo)
async def get_image(message: Message, state: FSMContext):
    await state.update_data(image=message.photo[-1].file_id)
    await message.answer("Test kodi?")
    await state.set_state(TestStates.waiting_for_test_code)

@dp.message(TestStates.waiting_for_test_code)
async def get_code(message: Message, state: FSMContext):
    await state.update_data(code=message.text)
    await message.answer("Javoblarni kiriting (masalan: abcd):")
    await state.set_state(TestStates.waiting_for_answers)

@dp.message(TestStates.waiting_for_answers)
async def get_answers(message: Message, state: FSMContext):
    await state.update_data(answers=message.text)
    await message.answer("Test necha soat faol bo'lishi kerak? (masalan: 24)")
    await state.set_state(TestStates.waiting_for_duration)

@dp.message(TestStates.waiting_for_duration)
async def save_test(message: Message, state: FSMContext):
    try:
        duration_hours = int(message.text)
        if duration_hours <= 0:
            await message.answer("❌ Soat soni musbat bo'lishi kerak. Qaytadan kiriting:")
            return
    except ValueError:
        await message.answer("❌ Iltimos, faqat raqam kiriting. Qaytadan kiriting:")
        return
    
    data = await state.get_data()
    tests = load_json(TESTS_FILE)
    
    # Save test with duration and creation time
    tests[data["code"]] = {
        "answers": data["answers"],
        "image_id": data["image"],
        "duration_hours": duration_hours,
        "created_time": datetime.now().isoformat()
    }
    save_json(TESTS_FILE, tests)

    # Improved announcement caption
    caption = (
        f"🎯 **YANGI TESTGA MARHAMAT QILING!**\n\n"
        f"🔐 O'zingizni egallagan bilimlaringizni sinab ko'ring!\n"
        f"🏆 Eng yaxshi natija ko'rsatganlarga **MAXSUS SERTIFIKATLAR** taqdim etiladi!\n\n"
        f"🆔 **Test kodi:** `{data['code']}`\n"
        f"⏰ **Faol muddati:** {duration_hours} soat\n"
        f"📊 **Minimal ball:** 60% (sertifikat olish uchun)\n\n"
        f"📝 **Qanday qatnashish:**\n"
        f"Savollarni diqqat bilan o'rganib, quyidagi formatda javob yuboring:\n"
        f"`{data['code']}*abcd`\n\n"
        f"💡 **Maslahat:** Har bir savolni ehtiyotkorlik bilan o'qing!\n"
        f"🚀 **Omad tilaymiz!** O'z bilimlaringizni namoyish eting!\n\n"
        f"🏅 Yuqori ball to'plaganlar alohida e'tirof etiladi!"
    )

    await message.answer_photo(photo=data["image"], caption=caption, parse_mode="Markdown")
    await state.clear()

# === Test tekshirish ===
@dp.message(F.text == "✅ Testni tekshirish")
async def test_check_help(message: Message):
    await message.answer("Shunday yuboring: 123*abcd")

@dp.message(F.text.regexp(r"^\d+\*[a-z]+$"))
async def test_check(message: Message):
    try:
        code, answers = message.text.split("*")
        tests = load_json(TESTS_FILE)
        
        if code not in tests:
            await message.answer("❌ Test topilmadi.")
            return
        
        test_data = tests[code]
        
        # Check if test is still active
        if not is_test_active(test_data):
            await message.answer("❌ Bu testning muddati tugagan. Test endi faol emas.")
            return
        
        correct = test_data["answers"]
        score = sum(1 for a, c in zip(answers, correct) if a == c)
        total = len(correct)
        percentage = (score / total) * 100
        
        # Check if user already took this test
        results = load_json(RESULTS_FILE)
        user_id = str(message.from_user.id)
        
        if user_id in results and code in results[user_id]:
            await message.answer(
                f"❌ Siz bu testda allaqachon qatnashgansiz!\n\n"
                f"📊 Oldingi natijangiz: {results[user_id][code]['score']}/{results[user_id][code]['total']} "
                f"({results[user_id][code]['percentage']:.1f}%)\n"
                f"📅 Sana: {results[user_id][code]['date']}\n\n"
                f"💡 Har bir testda faqat bir marta qatnashish mumkin."
            )
            return
        
        # Save result
        if user_id not in results:
            results[user_id] = {}
        
        results[user_id][code] = {
            'score': score,
            'total': total,
            'percentage': percentage,
            'date': datetime.now().strftime("%d.%m.%Y %H:%M")
        }
        save_json(RESULTS_FILE, results)
        
        # Test topshirgani uchun coin berish
        coins_earned = add_coins(message.from_user.id, 3)
        
        # Response message
        if percentage >= 60:
            await message.answer(
                f"🎉 Ajoyib natija!\n"
                f"✅ {score}/{total} ta to'g'ri ({percentage:.1f}%)\n\n"
                f"🏆 Siz sertifikat olish uchun yetarli ball to'pladingiz!\n"
                f"🎓 Sertifikat olish uchun 'Sertifikat' tugmasini bosing.\n\n"
                f"🪙 Test topshirganingiz uchun 3 KPT coin oldingiz! (Jami: {coins_earned})"
            )
        else:
            await message.answer(
                f"📊 Test yakunlandi!\n"
                f"✅ {score}/{total} ta to'g'ri ({percentage:.1f}%)\n\n"
                f"😔 Sertifikat olish uchun kamida 60% ball kerak.\n"
                f"💪 Keyingi marta ko'proq tayyorgarlik ko'ring!\n"
                f"Testimizda qatnashganligingiz uchun tashakkur!\n\n"
                f"🪙 Test topshirganingiz uchun 3 KPT coin oldingiz! (Jami: {coins_earned})"
            )
            
    except Exception as e:
        await message.answer("❌ Xatolik yuz berdi!")
        logging.error(f"Test check error: {e}")

# === Sertifikat yaratish (Yangilangan) ===
@dp.message(F.text == "🎓 Sertifikat")
async def certificate_menu(message: Message, state: FSMContext):
    user_tests = get_user_tests(message.from_user.id)
    
    if not user_tests:
        await message.answer("❌ Siz hali birorta testda qatnashmadingiz. Avval test topshiring!")
        return
    
    # Filter tests where user got >= 60%
    eligible_tests = [test for test in user_tests if (test['score'] / test['total']) >= 0.6]
    
    if not eligible_tests:
        await message.answer("❌ Sertifikat olish uchun yetarli ball to'plagan testlaringiz yo'q. Kamida 60% ball kerak.")
        return
    
    # Create inline keyboard with test options
    keyboard = []
    for test in eligible_tests:
        percentage = (test['score'] / test['total']) * 100
        button_text = f"Test {test['code']} ({test['score']}/{test['total']} - {percentage:.1f}%)"
        keyboard.append([InlineKeyboardButton(text=button_text, callback_data=f"cert_{test['code']}")])
    
    await message.answer(
        "🎓 Qaysi test uchun sertifikat olmoqchisiz?\n\n"
        "Faqat 60% va undan yuqori ball to'plagan testlar ko'rsatilgan:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query(F.data.startswith("cert_"))
async def create_certificate(callback: types.CallbackQuery):
    test_code = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    # Verify user has the test result
    results = load_json(RESULTS_FILE)
    user_id_str = str(user_id)
    
    if user_id_str not in results or test_code not in results[user_id_str]:
        await callback.answer("❌ Test natijangiz topilmadi!")
        return
    
    result = results[user_id_str][test_code]
    
    if result['percentage'] < 60:
        await callback.answer("❌ Bu test uchun yetarli ball yo'q!")
        return
    
    user_name = callback.from_user.full_name or callback.from_user.first_name or "Foydalanuvchi"
    today = datetime.today().strftime("%d.%m.%Y")
    file_name = f"certificate_{user_id}_{test_code}.png"

    try:
        # Create certificate background
        cert = create_certificate_background()
        logging.info("Created certificate background programmatically")
        
        draw = ImageDraw.Draw(cert)

        # Get fonts with fallbacks
        name_font = get_font(32)
        info_font = get_font(16)
        
        if not name_font:
            name_font = ImageFont.load_default()
            info_font = ImageFont.load_default()

        # Draw user name (main subject)
        if name_font:
            text_width, text_height = get_text_dimensions(draw, user_name, name_font)
            x = (cert.width - text_width) // 2
            y = cert.height // 2 - 30
            
            # Glow effect for name
            for offset in [(2,2), (1,1), (0,0)]:
                color = '#00ff41' if offset == (0,0) else '#003311'
                draw.text((x + offset[0], y + offset[1]), user_name, font=name_font, fill=color)

        # Draw test info and score
        if info_font:
            test_info = f"Test kodi: {test_code}"
            score_info = f"Natija: {result['score']}/{result['total']} ({result['percentage']:.1f}%)"
            date_info = f"Sana: {today}"
            
            # Test code
            text_width, _ = get_text_dimensions(draw, test_info, info_font)
            x = (cert.width - text_width) // 2
            draw.text((x, cert.height // 2 + 30), test_info, font=info_font, fill='#cccccc')
            
            # Score
            text_width, _ = get_text_dimensions(draw, score_info, info_font)
            x = (cert.width - text_width) // 2
            draw.text((x, cert.height // 2 + 55), score_info, font=info_font, fill='#ffffff')
            
            # Date (bottom right)
            text_width, _ = get_text_dimensions(draw, date_info, info_font)
            draw.text((cert.width - text_width - 30, cert.height - 40), date_info, font=info_font, fill='#999999')
            
            # Thank you message
            thanks_text = "Testimizda Qatnashganligingiz uchun Rahmat!"
            text_width, _ = get_text_dimensions(draw, thanks_text, info_font)
            x = (cert.width - text_width) // 2
            draw.text((x, cert.height - 80), thanks_text, font=info_font, fill='#ffaa00')

        # Save certificate
        cert.save(file_name, 'PNG', quality=95)
        logging.info(f"Certificate saved: {file_name}")

        # Send certificate
        photo_file = FSInputFile(file_name)
        caption = (
            f"🎓 **SERTIFIKAT TAYYOR!**\n\n"
            f"✅ Test: {test_code}\n"
            f"📊 Natija: {result['score']}/{result['total']} ({result['percentage']:.1f}%)\n"
            f"🗓 Sana: {today}\n\n"
            f"🏆 **Tabriklaymiz!** Bilimlaringizni \n "
            f"muvaffaqiyatli namoyish etdingiz.\n\n"
            f"🤝 **Kamolidinov's Bot** va **@test_world_01** tomonidan taqdim etildi.\n"
            f"💙 Sizning bilimlaringiz uchun rahmat!"
        )
        
        await callback.message.answer_photo(photo=photo_file, caption=caption, parse_mode="Markdown")
        await callback.answer("✅ Sertifikat yuborildi!")

        # Clean up
        if os.path.exists(file_name):
            os.remove(file_name)
            logging.info(f"Certificate file cleaned up: {file_name}")

    except Exception as e:
        logging.error(f"Certificate generation error: {e}")
        await callback.answer(f"❌ Xatolik: {str(e)}", show_alert=True)

# === /natija command for admin results ===
@dp.message(F.text.regexp(r"^/natija\*\w+$"))
async def get_test_results(message: Message):
    # Extract test code
    test_code = message.text.split("*")[1]
    
    try:
        # Create results PDF
        results_pdf_buffer = create_results_pdf(test_code)
        if not results_pdf_buffer:
            await message.answer("❌ Bu test kodi uchun ma'lumot topilmadi.")
            return
        
        # Create certificates PDF
        certificates_pdf_buffer = create_certificates_pdf(test_code)
        
        # Save results PDF to file temporarily
        results_filename = f"test_results_{test_code}.pdf"
        with open(results_filename, "wb") as f:
            f.write(results_pdf_buffer.getvalue())
        
        # Send results PDF
        results_file = FSInputFile(results_filename)
        await message.answer_document(
            document=results_file,
            caption=f"📊 Test {test_code} natijalari\n\nBu faylda testda qatnashgan barcha foydalanuvchilarning ismlari va ballari ko'rsatilgan."
        )
        
        # Clean up results file
        if os.path.exists(results_filename):
            os.remove(results_filename)
        
        # Send certificates PDF if available
        if certificates_pdf_buffer:
            certificates_filename = f"certificates_{test_code}.pdf"
            with open(certificates_filename, "wb") as f:
                f.write(certificates_pdf_buffer.getvalue())
            
            certificates_file = FSInputFile(certificates_filename)
            await message.answer_document(
                document=certificates_file,
                caption=f"🎓 Test {test_code} sertifikatlari\n\n60% va undan yuqori ball to'plagan foydalanuvchilar uchun sertifikatlar."
            )
            
            # Clean up certificates file
            if os.path.exists(certificates_filename):
                os.remove(certificates_filename)
        
    except Exception as e:
        logging.error(f"Results generation error: {e}")
        await message.answer(f"❌ Natijalarni yaratishda xatolik: {str(e)}")

# === Coin berish funksiyasi (Admin) ===
@dp.message(F.text.regexp(r"^/coinberdi\*(.+)$"))
async def give_coins_command(message: Message, state: FSMContext):
    # Extract parameters from command
    params = message.text.split("*")[1]
    
    # Check if it's the password prompt or actual coin giving
    if params == "KPT":
        await message.answer("🔐 Admin parolini kiriting:")
        await state.set_state(CoinGivingStates.waiting_for_password)
    else:
        await message.answer("❌ Noto'g'ri format. To'g'ri format: /coinberdi*KPT")

# === Coin berish state-lari ===
class CoinGivingStates(StatesGroup):
    waiting_for_password = State()
    waiting_for_user_id = State()
    waiting_for_amount = State()

@dp.message(CoinGivingStates.waiting_for_password)
async def check_coin_password(message: Message, state: FSMContext):
    if message.text == ADMIN_PASSWORD:
        await message.answer("✅ Parol to'g'ri!\nFoydalanuvchi ID sini kiriting:")
        await state.set_state(CoinGivingStates.waiting_for_user_id)
    else:
        await message.answer("❌ Noto'g'ri parol.")
        await state.clear()

@dp.message(CoinGivingStates.waiting_for_user_id)
async def get_user_id_for_coins(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        await state.update_data(target_user_id=user_id)
        await message.answer("💰 Necha KPT coin bermoqchisiz?")
        await state.set_state(CoinGivingStates.waiting_for_amount)
    except ValueError:
        await message.answer("❌ Iltimos, to'g'ri foydalanuvchi ID raqamini kiriting:")

@dp.message(CoinGivingStates.waiting_for_amount)
async def give_coins_to_user(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            await message.answer("❌ Coin miqdori musbat bo'lishi kerak. Qaytadan kiriting:")
            return
        
        data = await state.get_data()
        target_user_id = data['target_user_id']
        
        # Add coins to user
        new_balance = add_coins(target_user_id, amount)
        
        # Get user info if available
        profiles = load_json(PROFILE_FILE)
        user_name = profiles.get(str(target_user_id), {}).get('name', 'Noma\'lum foydalanuvchi')
        
        await message.answer(
            f"✅ Coin muvaffaqiyatli berildi!\n\n"
            f"👤 Foydalanuvchi: {user_name} (ID: {target_user_id})\n"
            f"💰 Berilgan coin: {amount} KPT\n"
            f"🪙 Yangi balans: {new_balance} KPT"
        )
        
        # Notify the user who received coins
        try:
            await bot.send_message(
                target_user_id,
                f"🎉 Sizga admin tomonidan coin berildi!\n\n"
                f"💰 Olgan coiningiz: {amount} KPT\n"
                f"🪙 Yangi balansingiz: {new_balance} KPT\n\n"
                f"🙏 Rahmat!"
            )
        except Exception as e:
            await message.answer(f"⚠️ Coin berildi, lekin foydalanuvchiga xabar yuborib bo'lmadi: {str(e)}")
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Iltimos, to'g'ri raqam kiriting:")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
        await state.clear()

# === Coin olish funksiyasi (Admin) ===
@dp.message(F.text.regexp(r"^/coinoldi\*(.+)$"))
async def take_coins_command(message: Message, state: FSMContext):
    # Extract parameters from command
    params = message.text.split("*")[1]
    
    # Check if it's the password prompt or actual coin taking
    if params == "KPT":
        await message.answer("🔐 Admin parolini kiriting:")
        await state.set_state(CoinTakingStates.waiting_for_password)
    else:
        await message.answer("❌ Noto'g'ri format. To'g'ri format: /coinoldi*KPT")

# === Coin olish state-lari ===
class CoinTakingStates(StatesGroup):
    waiting_for_password = State()
    waiting_for_user_id = State()
    waiting_for_amount = State()

@dp.message(CoinTakingStates.waiting_for_password)
async def check_take_password(message: Message, state: FSMContext):
    if message.text == ADMIN_PASSWORD:
        await message.answer("✅ Parol to'g'ri!\nFoydalanuvchi ID sini kiriting:")
        await state.set_state(CoinTakingStates.waiting_for_user_id)
    else:
        await message.answer("❌ Noto'g'ri parol.")
        await state.clear()

@dp.message(CoinTakingStates.waiting_for_user_id)
async def get_user_id_for_taking_coins(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        
        # Check if user exists and has coins
        coins = load_json(COINS_FILE)
        user_id_str = str(user_id)
        
        if user_id_str not in coins:
            await message.answer("❌ Bu foydalanuvchi hali coin olmagan. Qaytadan ID kiriting:")
            return
        
        current_balance = coins[user_id_str]
        await state.update_data(target_user_id=user_id, current_balance=current_balance)
        await message.answer(f"💰 Foydalanuvchining joriy balansi: {current_balance} KPT\nNecha KPT coin olmoqchisiz?")
        await state.set_state(CoinTakingStates.waiting_for_amount)
    except ValueError:
        await message.answer("❌ Iltimos, to'g'ri foydalanuvchi ID raqamini kiriting:")

@dp.message(CoinTakingStates.waiting_for_amount)
async def take_coins_from_user(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            await message.answer("❌ Coin miqdori musbat bo'lishi kerak. Qaytadan kiriting:")
            return
        
        data = await state.get_data()
        target_user_id = data['target_user_id']
        current_balance = data['current_balance']
        
        if amount > current_balance:
            await message.answer(f"❌ Foydalanuvchida yetarli coin yo'q! Joriy balans: {current_balance} KPT\nBoshqa miqdor kiriting:")
            return
        
        # Remove coins from user
        coins = load_json(COINS_FILE)
        user_id_str = str(target_user_id)
        coins[user_id_str] -= amount
        save_json(COINS_FILE, coins)
        
        new_balance = coins[user_id_str]
        
        # Get user info if available
        profiles = load_json(PROFILE_FILE)
        user_name = profiles.get(user_id_str, {}).get('name', 'Noma\'lum foydalanuvchi')
        
        await message.answer(
            f"✅ Coin muvaffaqiyatli olindi!\n\n"
            f"👤 Foydalanuvchi: {user_name} (ID: {target_user_id})\n"
            f"💸 Olingan coin: {amount} KPT\n"
            f"🪙 Yangi balans: {new_balance} KPT\n"
            f"📉 Eski balans: {current_balance} KPT"
        )
        
        # Notify the user whose coins were taken
        try:
            await bot.send_message(
                target_user_id,
                f"⚠️ Admin tomonidan coiningiz kamaytirildi!\n\n"
                f"💸 Olingan coin: {amount} KPT\n"
                f"🪙 Yangi balansingiz: {new_balance} KPT\n\n"
                f"ℹ️ Admin bilan bog'lanish: {ADMIN_USERNAME}"
            )
        except Exception as e:
            await message.answer(f"⚠️ Coin olindi, lekin foydalanuvchiga xabar yuborib bo'lmadi: {str(e)}")
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Iltimos, to'g'ri raqam kiriting:")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
        await state.clear()

# === Asosiy menyuga qaytish ===
@dp.message(F.text == "🔙 Asosiy menyu")
async def back(message: Message):
    await message.answer("Asosiy menyuga qaytdingiz", reply_markup=main_menu())

# === Run ===
async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.info("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
