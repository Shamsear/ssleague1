# 🔧 Render Environment Variables Setup Instructions

## IMPORTANT: Only Add These 3 Variables Manually

Most environment variables are already configured in your `render.yaml` file. You only need to add **3 VAPID variables** manually in the Render dashboard.

## 📋 Step-by-Step Instructions

### 1. Access Environment Variables in Render
1. Go to your Render dashboard
2. Select your web service (ssleague)
3. Click on the **"Environment"** tab
4. Click **"Add Environment Variable"**

### 2. Add VAPID Variables (Required for Push Notifications)

Add these **3 variables** one by one:

#### Variable 1: VAPID_PRIVATE_KEY
- **Key:** `VAPID_PRIVATE_KEY`
- **Value:** 
```
LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1JR0hBZ0VBTUJNR0J5cUdTTTQ5QWdFR0NDcUdTTTQ5QXdFSEJHMHdhd0lCQVFRZ3p5ZDRIOCt6eDZFRUQ5TDMKUkRTZ3E0S1p2NEFQWTJ3SmE5QUhPK3Jmd2wyaFJBTkNBQVQzdmdHWXpDcUQ4VnovRkh4V3BRQ1NYZUhPNnVqSQp3VXB2aTk2L3d6OXJQRkJZSzhDWGd4YzZKZ0ZXdlFaQ2JPb2gvNHhROGR0WTNIN1o4cjU0dlJvWQotLS0tLUVORCBQUklWQVRFIEtFWS0tLS0tCg==
```

#### Variable 2: VAPID_PUBLIC_KEY
- **Key:** `VAPID_PUBLIC_KEY`
- **Value:**
```
LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUZrd0V3WUhLb1pJemowQ0FRWUlLb1pJemowREFRY0RRZ0FFOTc0Qm1Nd3FnL0ZjL3hSOFZxVUFrbDNoenVybwp5TUZLYjR2ZXY4TS9henhRV0N2QWw0TVhPaVlCVnIwR1FtenFJZitNVVBIYldOeCsyZksrZUwwYUdBPT0KLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tCg==
```

#### Variable 3: VAPID_CLAIMS_SUB
- **Key:** `VAPID_CLAIMS_SUB`
- **Value:** `mailto:admin@yourdomain.com`
  
  **⚠️ IMPORTANT:** Replace `yourdomain.com` with your actual domain name. If you don't have a domain, you can use `mailto:admin@example.com` for now.

### 3. Save Each Variable
- Click **"Add"** after entering each variable
- Make sure all 3 variables are successfully added

## ✅ Variables Already Configured (DO NOT ADD THESE)

These are already set up in your `render.yaml` file - **DO NOT add them manually**:

- ✅ `SECRET_KEY` (auto-generated)
- ✅ `DATABASE_URL` (auto-linked from PostgreSQL)
- ✅ `PYTHON_VERSION`
- ✅ `FLASK_APP`
- ✅ `FLASK_ENV`
- ✅ `FLASK_DEBUG`
- ✅ `WEB_CONCURRENCY`

## 🚫 Common Mistakes to Avoid

1. **Don't add SECRET_KEY manually** - it's auto-generated
2. **Don't add DATABASE_URL manually** - it's auto-linked from your PostgreSQL service
3. **Don't copy-paste with extra spaces** - make sure there are no leading/trailing spaces in the values
4. **Don't forget to update VAPID_CLAIMS_SUB** - replace the domain with your actual domain

## 📱 Testing VAPID Keys

After adding the variables and deploying:

1. Visit your deployed app
2. Try to subscribe to push notifications
3. Send a test notification from admin panel
4. Check browser console for any VAPID-related errors

## 🔄 If You Need to Regenerate VAPID Keys

If you need new VAPID keys for any reason:

```bash
python generate_vapid_keys.py
```

Then update the 3 environment variables in Render with the new values.

## 🎯 Final Checklist

- [ ] Added `VAPID_PRIVATE_KEY`
- [ ] Added `VAPID_PUBLIC_KEY` 
- [ ] Added `VAPID_CLAIMS_SUB` (with your domain)
- [ ] No extra spaces in values
- [ ] Did NOT add SECRET_KEY or DATABASE_URL manually
- [ ] Ready to deploy!

---

**That's it!** These 3 environment variables are all you need to add manually. Everything else is handled automatically by your render.yaml configuration.
