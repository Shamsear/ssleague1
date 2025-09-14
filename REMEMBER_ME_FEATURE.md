# Remember Me Feature - Documentation

## How It Works

When users check "Remember me" during login, they stay logged in for 30 days even after closing their browser.

## Implementation

### 1. Database Fields (models.py)
- `remember_token`: Stores unique token for each user
- `token_expires_at`: Token expiration timestamp (30 days from creation)

### 2. Token Generation (models.py ~line 76)
When user logs in with "Remember me" checked:
- Generates secure random token
- Stores in database with 30-day expiration
- Returns token for cookie

### 3. Cookie Setting (app.py ~line 327)
- Sets `remember_token` cookie with 30-day expiration
- Uses `httpOnly` for security (no JavaScript access)
- `secure=False` for HTTP/HTTPS compatibility (change to `True` for HTTPS-only)

### 4. Auto-Login Middleware (app.py ~line 231)
```python
@app.before_request
def check_remember_token():
    # Runs before every request
    # If user not logged in but has valid token, logs them in automatically
```

### 5. Logout Cleanup (app.py ~line 1301)
- Clears remember token from database
- Deletes remember_token cookie

## Security Notes

1. **Token Security**: Uses `secrets.token_urlsafe(32)` for cryptographically secure tokens
2. **HttpOnly Cookie**: Prevents XSS attacks (JavaScript can't access)
3. **Token Expiration**: Automatic 30-day expiration
4. **Logout Clears Token**: Token invalidated on explicit logout

## Configuration

To enable HTTPS-only cookies (production):
```python
# app.py line ~334
secure=True  # Change from False to True
```

## User Experience

✅ User logs in with "Remember me" → Stays logged in for 30 days
✅ User closes browser → Still logged in when returning
✅ User clicks logout → Token cleared, must login again
✅ After 30 days → Token expires, must login again