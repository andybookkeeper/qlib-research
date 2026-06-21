# Authentication & Permissions Specification
# User auth, role-based access, session management (Future-Ready)

## Overview

**MVP Status**: Single-user, no auth. This spec is **future-ready** for when multi-user support is added.

Current (MVP):
- No login
- No session management
- App assumes single local user
- All features accessible

Future (Phase 2):
- Local user accounts
- JWT-based authentication
- Role-based permissions (admin, trader, analyst)
- Audit logging of user actions

## Authentication Architecture (Phase 2)

```
┌─────────────────────┐
│  React SPA          │
│  localStorage:      │
│  - access_token     │
│  - refresh_token    │
└─────────────────────┘
          ↓ POST /auth/login
┌─────────────────────────────────────┐
│  FastAPI Auth Service               │
│  - Verify credentials               │
│  - Issue JWT tokens                 │
│  - Manage sessions                  │
└─────────────────────────────────────┘
          ↓ JWT verification
┌─────────────────────────────────────┐
│  Protected Endpoints                │
│  - Check token validity             │
│  - Verify permissions               │
│  - Allow/deny access                │
└─────────────────────────────────────┘
```

## JWT Token Structure

### Access Token (Short-lived)

```json
{
  "sub": "user_id_123",
  "username": "alice",
  "email": "alice@example.com",
  "roles": ["trader"],
  "permissions": ["trade_execute", "portfolio_read", "analysis_read"],
  "exp": 1705700400,
  "iat": 1705696800,
  "iss": "qlib-trading-api"
}
```

### Refresh Token (Long-lived)

```json
{
  "sub": "user_id_123",
  "type": "refresh",
  "exp": 1706301600,
  "iat": 1705696800,
  "iss": "qlib-trading-api"
}
```

## User Model

```python
# src/qlib_research/app/models/user.py

from sqlalchemy import Column, String, DateTime, Boolean, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from enum import Enum as PyEnum

Base = declarative_base()

class UserRole(str, PyEnum):
    ADMIN = "admin"          # Full access, user management
    TRADER = "trader"        # Can trade, view portfolio
    ANALYST = "analyst"      # Read-only analysis, no trading
    VIEWER = "viewer"        # Dashboard view only

class User(Base):
    """User account"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True)  # UUID
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  # bcrypt
    
    role = Column(Enum(UserRole), default=UserRole.TRADER)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Preferences
    daily_loss_limit_usd = Column(Float, default=2500)
    max_position_size_pct = Column(Float, default=0.10)
    
    @property
    def permissions(self) -> list[str]:
        """Get permissions based on role"""
        if self.role == UserRole.ADMIN:
            return [
                "trade_execute", "trade_cancel", "trade_modify",
                "portfolio_read", "portfolio_edit",
                "analysis_read", "analysis_create",
                "research_read", "research_execute",
                "settings_read", "settings_edit",
                "user_manage", "audit_read"
            ]
        elif self.role == UserRole.TRADER:
            return [
                "trade_execute", "trade_cancel",
                "portfolio_read",
                "analysis_read",
                "research_read",
                "settings_read", "settings_edit_own"
            ]
        elif self.role == UserRole.ANALYST:
            return [
                "portfolio_read",
                "analysis_read",
                "research_read",
                "settings_read"
            ]
        else:  # VIEWER
            return ["portfolio_read", "analysis_read"]
```

## Authentication Flow

### Login Endpoint

```python
# src/qlib_research/app/api/routes/auth.py

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import jwt
import bcrypt

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds

class TokenPayload(BaseModel):
    sub: str
    username: str
    email: str
    roles: list[str]
    permissions: list[str]

@router.post("/login")
async def login(request: LoginRequest, db=Depends(get_db)):
    """
    Authenticate user and return JWT tokens.
    
    Request:
    {
      "username": "alice",
      "password": "secure_password"
    }
    
    Response:
    {
      "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "token_type": "bearer",
      "expires_in": 3600
    }
    """
    
    # Find user by username
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Verify password
    if not bcrypt.checkpw(
        request.password.encode(),
        user.password_hash.encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Generate JWT tokens
    access_token_payload = {
        "sub": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "permissions": user.permissions,
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow()
    }
    
    refresh_token_payload = {
        "sub": user.id,
        "type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=7),
        "iat": datetime.utcnow()
    }
    
    access_token = jwt.encode(
        access_token_payload,
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    
    refresh_token = jwt.encode(
        refresh_token_payload,
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600
    )

@router.post("/refresh")
async def refresh_token(refresh_token: str, db=Depends(get_db)):
    """
    Refresh access token using refresh token.
    """
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload["sub"]
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Generate new access token
        new_access_token = jwt.encode(
            {
                "sub": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "permissions": user.permissions,
                "exp": datetime.utcnow() + timedelta(hours=1),
                "iat": datetime.utcnow()
            },
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": 3600
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout user (token is invalidated by removing from client).
    Future: Can add token blacklist if needed.
    """
    return {"message": "Successfully logged out"}
```

## Token Verification

```python
# src/qlib_research/app/api/security.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
import jwt

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security)
) -> User:
    """
    Verify JWT token and return current user.
    
    Used as dependency: @router.get("/protected")
                        async def protected(user=Depends(get_current_user)):
    """
    
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    # Get user from DB
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user

async def require_permission(permission: str):
    """
    Create dependency that checks for specific permission.
    
    Usage: @router.get("/trade")
           async def trade(user=Depends(require_permission("trade_execute"))):
    """
    
    async def check_permission(current_user: User = Depends(get_current_user)):
        if permission not in current_user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission} required"
            )
        return current_user
    
    return check_permission

async def require_role(role: UserRole):
    """Check user has minimum role level"""
    
    async def check_role(current_user: User = Depends(get_current_user)):
        if current_user.role != role and (
            # Admin can access everything
            current_user.role != UserRole.ADMIN
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {role} required"
            )
        return current_user
    
    return check_role
```

## Protected Endpoints

```python
# Example: Trade execution requires permission

@router.post("/orders")
async def create_order(
    order_req: OrderRequest,
    current_user: User = Depends(require_permission("trade_execute"))
):
    """Create order (requires trader role)"""
    # ... implementation
    return order

# Example: Admin-only endpoint

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Delete user (admin only)"""
    # ... implementation
    return {"deleted": user_id}

# Example: Analyst can view but not trade

@router.get("/portfolio/positions")
async def get_positions(
    current_user: User = Depends(require_permission("portfolio_read"))
):
    """Get portfolio positions"""
    # ... implementation
    return positions
```

## MVP Implementation (No Auth)

For MVP, all endpoints are **accessible without auth**. To enable, uncomment the `Depends(get_current_user)`:

```python
# MVP: No auth
@router.post("/orders")
async def create_order(order_req: OrderRequest):
    """Create order (MVP: no auth)"""
    return order

# Phase 2: With auth
@router.post("/orders")
async def create_order(
    order_req: OrderRequest,
    current_user: User = Depends(require_permission("trade_execute"))
):
    """Create order (requires trader role)"""
    return order
```

## Session Management

```python
# src/qlib_research/app/services/session_manager.py

from datetime import datetime, timedelta

class SessionManager:
    """Manage active user sessions"""
    
    def __init__(self):
        self.active_sessions = {}  # user_id -> [sessions]
    
    def create_session(self, user_id: str, token: str) -> dict:
        """Create new session"""
        session = {
            "token": token,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "ip_address": None,  # Would capture from request
            "user_agent": None
        }
        
        if user_id not in self.active_sessions:
            self.active_sessions[user_id] = []
        
        self.active_sessions[user_id].append(session)
        return session
    
    def invalidate_session(self, user_id: str, token: str):
        """Logout specific session"""
        if user_id in self.active_sessions:
            self.active_sessions[user_id] = [
                s for s in self.active_sessions[user_id]
                if s["token"] != token
            ]
    
    def logout_all(self, user_id: str):
        """Logout all sessions for user"""
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]
```

## Frontend Implementation

### Login Component

```javascript
// src/components/Auth/LoginForm.vue

<template>
  <div class="login-form">
    <h2>Login</h2>
    
    <form @submit.prevent="login">
      <div class="form-group">
        <label>Username</label>
        <input v-model="username" type="text" required />
      </div>
      
      <div class="form-group">
        <label>Password</label>
        <input v-model="password" type="password" required />
      </div>
      
      <button type="submit" :disabled="loading">
        {{ loading ? 'Logging in...' : 'Login' }}
      </button>
      
      <p v-if="error" class="error">{{ error }}</p>
    </form>
  </div>
</template>

<script>
export default {
  data() {
    return {
      username: '',
      password: '',
      loading: false,
      error: null
    }
  },
  methods: {
    async login() {
      this.loading = true
      this.error = null
      
      try {
        const response = await fetch('/api/v1/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: this.username,
            password: this.password
          })
        })
        
        if (!response.ok) {
          throw new Error('Invalid credentials')
        }
        
        const data = await response.json()
        
        // Store tokens
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)
        
        // Redirect to dashboard
        this.$router.push('/portfolio')
        
      } catch (err) {
        this.error = err.message
      } finally {
        this.loading = false
      }
    }
  }
}
</script>
```

### HTTP Interceptor

```javascript
// src/api/http-client.js

import axios from 'axios'

const client = axios.create({
  baseURL: 'http://localhost:8000'
})

// Add token to all requests
client.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle token refresh on 401
client.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('refresh_token')
      
      try {
        const response = await axios.post('/api/v1/auth/refresh', {
          refresh_token: refreshToken
        })
        
        localStorage.setItem('access_token', response.data.access_token)
        
        // Retry original request
        return client(error.config)
        
      } catch {
        // Refresh failed, redirect to login
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
      }
    }
    
    return Promise.reject(error)
  }
)

export default client
```

## Acceptance Criteria

- [ ] JWT token generation works
- [ ] Token refresh endpoint functional
- [ ] Permission checks on protected endpoints
- [ ] Role-based access control working
- [ ] Login/logout flow functional (Phase 2)
- [ ] Token stored securely in localStorage
- [ ] Expired tokens trigger refresh
- [ ] Invalid tokens return 401
- [ ] Audit logging of auth events
- [ ] Unit tests for auth helpers

## Known Limitations (MVP)

- No authentication (single user)
- No session management
- No role-based access control
- Tokens not used (code ready for Phase 2)
- No rate limiting on auth endpoints
- No account lockout on failed login
