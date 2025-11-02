#!/usr/bin/env python3
"""
خدمة وسيطة بسيطة لتوجيه طلبات Sajalni IMEI
استضافها على Railway.app أو Render.com (مجاني)

التشغيل المحلي للاختبار:
    pip install flask requests
    python sajalni_proxy_service.py

النشر على Railway:
    1. إنشاء حساب على railway.app
    2. "New Project" → "Deploy from GitHub repo"
    3. رفع هذا الملف + requirements.txt
    4. سيعطيك رابط مثل: https://your-app.railway.app
    
استخدامه في تطبيقك:
    في ملف .env على السيرفر الرئيسي:
    SAJALNI_PROXY_URL=https://your-app.railway.app/proxy
"""

from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# إعدادات Sajalni الافتراضية
SAJALNI_BASE = os.getenv('SAJALNI_BASE', 'https://enregistrement.sajalni.tn')
SAJALNI_VERIFY_PATH = os.getenv('SAJALNI_VERIFY_PATH', '/api/devices/verify-device')
SAJALNI_REFERER = os.getenv('SAJALNI_REFERER', 'https://enregistrement.sajalni.tn/verify-device')

@app.route('/')
def home():
    return jsonify({
        'service': 'Sajalni IMEI Proxy',
        'status': 'running',
        'endpoints': {
            '/proxy': 'POST - وكيل للتحقق من IMEI',
            '/health': 'GET - فحص الصحة'
        }
    })

@app.route('/health')
def health():
    """فحص صحة الخدمة"""
    try:
        # اختبار الاتصال بـ Sajalni
        resp = requests.get(
            SAJALNI_BASE,
            timeout=5,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        return jsonify({
            'status': 'healthy',
            'sajalni_reachable': True,
            'sajalni_status_code': resp.status_code
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'sajalni_reachable': False,
            'error': str(e)
        }), 500

@app.route('/proxy', methods=['POST'])
def proxy_verify():
    """
    وكيل لطلبات التحقق من IMEI
    
    Body المتوقع:
    {
        "imei": "123456789012345"
    }
    """
    try:
        data = request.get_json()
        if not data or 'imei' not in data:
            return jsonify({'error': 'IMEI مطلوب'}), 400
        
        imei = data['imei']
        
        # إنشاء session جديدة
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
            'Content-Type': 'application/json',
            'Origin': SAJALNI_BASE,
            'Referer': SAJALNI_REFERER,
            'X-Requested-With': 'XMLHttpRequest'
        })
        
        # محاولة warm-up (اختياري)
        try:
            session.get(SAJALNI_REFERER, timeout=3)
        except:
            pass
        
        # الطلب الفعلي
        url = f"{SAJALNI_BASE}{SAJALNI_VERIFY_PATH}"
        response = session.post(
            url,
            json={'imei': imei},
            timeout=15
        )
        
        # إعادة النتيجة كما هي
        return jsonify({
            'success': True,
            'status_code': response.status_code,
            'data': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        })
        
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'Timeout - Sajalni لم يستجب في الوقت المحدد'
        }), 504
        
    except requests.exceptions.ConnectionError as e:
        return jsonify({
            'success': False,
            'error': f'Connection Error: {str(e)}'
        }), 503
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Internal Error: {str(e)}'
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
