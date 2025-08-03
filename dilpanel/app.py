from flask import Flask, render_template, request, jsonify, session
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = "gizli-bir-anahtar"

genai.configure(api_key="AIzaSyBqoB83GdGshbCkyUCNMW8geJS9iGNDyl4")  # 🔁 kendi API key'inle değiştir

model = genai.GenerativeModel("gemini-2.0-flash-exp")  # chat destekliyorsa kalır, desteklemiyorsa 1.5-pro önerilir
chat_sessions = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start-roleplay", methods=["POST"])
def start_roleplay():
    data = request.get_json()
    roleplay_prompt = data.get("prompt", "")
    seviye = data.get("seviye", "A1")

    user_id = session.get("user_id")
    if not user_id:
        import uuid
        user_id = str(uuid.uuid4())
        session["user_id"] = user_id

    roleplay_system_prompt = f"""
Sen şu anda bir {seviye} seviyesinde İngilizce bilen bir kişiyle roleplay yapıyorsun.
Kullanıcının isteği: {roleplay_prompt}
Bundan sonra sohbete bu roleplaye uygun şekilde devam etmelisin. Bu konudan şaşma.Yazacağın mesajlar okunacağı için emoji tırnak işaret gibi şeyler kullanma. Sadece harf kullan.
"""

    chat = model.start_chat(history=[
        {"role": "user", "parts": [roleplay_system_prompt.strip()]}
    ])

    chat_sessions[user_id] = chat
    session["roleplay_started"] = True

    response = chat.send_message("Ready?")
    return jsonify({"reply": response.text})

@app.route("/ask", methods=["POST"])
def ask():
    user_id = session.get("user_id")
    if not user_id or user_id not in chat_sessions:
        return jsonify({"reply": "Lütfen önce roleplay başlatın."})

    chat = chat_sessions[user_id]
    data = request.get_json()
    user_input = data.get("message", "")

    final_message = f"""
Şu anda roleplay içersindesin, kesinlikle Türkçe kullanmıyor ve önceki mesajlar ile sohbeti devam ettiriyorsun.
Türkçe mesaj kullanmak yok, roleplay hariç bir şeyde söyleme ve roleplayi devam ettir.
kullanıcının mesajı: "{user_input}"
""".strip()

    try:
        response = chat.send_message(final_message)
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"reply": f"Hata: {str(e)}"})

@app.route("/start-level-test", methods=["POST"])
def start_level_test():
    user_id = session.get("user_id")
    if not user_id:
        import uuid
        user_id = str(uuid.uuid4())
        session["user_id"] = user_id

    level_test_prompt = """
Sen şu anda benim İngilizce seviyemi ölçmek için bir test yapıyorsun. 
Bana 3 tane genel soru soracaksın ve verdiğim cevaplara göre seviyemi belirleyeceksin.

Kurallar:
1. Sadece İngilizce konuş
2. Emoji, tırnak işareti gibi şeyler kullanma, sadece harf kullan
3. İlk soruyu sor ve cevabımı bekle
4. Her soru için cevabımı analiz et
5. 3 soru bittikten sonra seviyemi belirle ve gelişim önerileri ver

İlk soruyu sor:
"""

    chat = model.start_chat(history=[
        {"role": "user", "parts": [level_test_prompt.strip()]}
    ])

    chat_sessions[user_id] = chat
    session["level_test_started"] = True
    session["question_count"] = 0
    session["answers"] = []

    response = chat.send_message("Ask the first question.")
    return jsonify({"reply": response.text})

@app.route("/level-test-answer", methods=["POST"])
def level_test_answer():
    user_id = session.get("user_id")
    if not user_id or user_id not in chat_sessions:
        return jsonify({"reply": "Lütfen önce seviye testi başlatın."})

    chat = chat_sessions[user_id]
    data = request.get_json()
    user_answer = data.get("answer", "")

    # Cevabı kaydet
    session["answers"] = session.get("answers", []) + [user_answer]
    session["question_count"] = session.get("question_count", 0) + 1

    if session["question_count"] < 3:
        # Sonraki soruyu sor
        next_question_prompt = f"""
Kullanıcının {session['question_count']}. cevabı: "{user_answer}"

Bu cevabı analiz et ve {session['question_count'] + 1}. soruyu sor. 
Sadece soruyu sor, başka bir şey söyleme.
"""
        response = chat.send_message(next_question_prompt)
        return jsonify({"reply": response.text, "question_number": session["question_count"] + 1})
    else:
        # Final değerlendirme
        final_evaluation_prompt = f"""
Kullanıcının 3 cevabı:
1. "{session['answers'][0]}"
2. "{session['answers'][1]}"
3. "{session['answers'][2]}"

Bu 3 cevaba göre kullanıcının İngilizce seviyesini belirle (A1, A2, B1, B2, C1, C2).

Değerlendirme kriterleri:
- Gramer doğruluğu
- Kelime bilgisi
- Cümle yapısı
- Akıcılık
- Karmaşıklık seviyesi

Sonuç formatı:
SEVİYE: [Seviye]
AÇIKLAMA: [Seviye açıklaması]
HATALAR: [Yapılan hatalar]
GELİŞİM: [Gelişim önerileri]

Sadece bu formatta cevap ver, başka bir şey ekleme.
"""
        response = chat.send_message(final_evaluation_prompt)
        return jsonify({"reply": response.text, "completed": True})



if __name__ == "__main__":
    app.run(debug=True) 