"""
Secure QR Code utilities with HMAC signatures and ephemeral token support
"""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


class SecureQRToken:
    """Handle secure QR token generation and validation"""
    
    # Get secret key from settings or use a default (should be in settings.py)
    SECRET_KEY = getattr(settings, 'QR_SECRET_KEY', settings.SECRET_KEY)
    
    # Token validity durations
    EPHEMERAL_DURATION = 60  # seconds
    STATIC_DURATION = None  # permanent
    
    @classmethod
    def generate_signature(cls, data: str) -> str:
        """Generate HMAC-SHA256 signature for data"""
        signature = hmac.new(
            cls.SECRET_KEY.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature[:16]  # Use first 16 chars for brevity
    
    @classmethod
    def verify_signature(cls, data: str, signature: str) -> bool:
        """Verify HMAC signature"""
        expected_signature = cls.generate_signature(data)
        return hmac.compare_digest(expected_signature, signature)
    
    @classmethod
    def generate_token(cls, entity_type: str, entity_id: Any, 
                      ephemeral: bool = False, metadata: Optional[Dict] = None) -> str:
        """
        Generate a secure QR token
        Format: <type>:<uuid>|sig=<signature>
        For ephemeral: <type>:<uuid>|eph=1|sig=<signature>
        """
        # Generate UUID for this token (maps to entity_id in cache/db)
        token_uuid = str(uuid.uuid4())
        
        # Build token data
        token_data = f"{entity_type}:{token_uuid}"
        
        if ephemeral:
            token_data += "|eph=1"
            
        # Generate signature
        signature = cls.generate_signature(token_data)
        
        # Build final token
        token = f"{token_data}|sig={signature}"
        
        # Store mapping in cache
        cache_key = f"qr_token:{token_uuid}"
        cache_data = {
            'entity_type': entity_type,
            'entity_id': entity_id,
            'ephemeral': ephemeral,
            'created_at': timezone.now().isoformat(),
            'metadata': metadata or {}
        }
        
        if ephemeral:
            cache.set(cache_key, cache_data, timeout=cls.EPHEMERAL_DURATION)
        else:
            # For static tokens, store indefinitely (or use a very long timeout)
            cache.set(cache_key, cache_data, timeout=86400 * 365)  # 1 year
            
        return token
    
    @classmethod
    def parse_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        Parse and validate a QR token
        Returns: {'valid': bool, 'entity_type': str, 'entity_id': Any, 
                  'ephemeral': bool, 'metadata': dict, 'error': str}
        """
        try:
            # Extract signature
            if '|sig=' not in token:
                return {'valid': False, 'error': 'Missing signature'}
            
            token_parts, signature = token.rsplit('|sig=', 1)
            
            # Verify signature
            if not cls.verify_signature(token_parts, signature):
                return {'valid': False, 'error': 'Invalid signature'}
            
            # Parse token parts
            parts = token_parts.split('|')
            type_uuid = parts[0]
            
            if ':' not in type_uuid:
                return {'valid': False, 'error': 'Invalid token format'}
            
            entity_type, token_uuid = type_uuid.split(':', 1)
            
            # Check if ephemeral
            ephemeral = 'eph=1' in parts
            
            # Retrieve entity data from cache
            cache_key = f"qr_token:{token_uuid}"
            cache_data = cache.get(cache_key)
            
            if not cache_data:
                return {'valid': False, 'error': 'Token expired or not found'}
            
            # For ephemeral tokens, check expiry
            if ephemeral:
                created_at = datetime.fromisoformat(cache_data['created_at'])
                if timezone.now() > created_at + timedelta(seconds=cls.EPHEMERAL_DURATION):
                    cache.delete(cache_key)  # Clean up expired token
                    return {'valid': False, 'error': 'Ephemeral token expired'}
            
            return {
                'valid': True,
                'entity_type': cache_data['entity_type'],
                'entity_id': cache_data['entity_id'],
                'ephemeral': cache_data.get('ephemeral', False),
                'metadata': cache_data.get('metadata', {}),
                'token_uuid': token_uuid
            }
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}


class QRContextFlow:
    """Manage context-based QR scanning flows"""
    
    # Flow definitions - can be extended or loaded from database
    FLOWS = {
        'device_transfer': {
            'sequence': ['user', 'device'],
            'action': 'transfer_device',
            'auto_execute': False,
            'description': 'Transfer device ownership'
        },
        'patient_admission': {
            'sequence': ['user', 'patient', 'bed'],
            'action': 'admit_patient',
            'auto_execute': True,
            'description': 'Admit patient to bed'
        },
        'device_usage': {
            'sequence': ['device', 'patient'],
            'action': 'log_device_usage',
            'auto_execute': True,
            'description': 'Log device usage on patient'
        },
        'device_maintenance': {
            'sequence': ['user', 'device'],
            'action': 'start_maintenance',
            'auto_execute': False,
            'description': 'Start device maintenance'
        },
        'bed_assignment': {
            'sequence': ['patient', 'bed'],
            'action': 'assign_bed',
            'auto_execute': True,
            'description': 'Assign patient to bed'
        }
    }
    
    @classmethod
    def get_session_key(cls, session_id: str) -> str:
        """Get cache key for a scan session"""
        return f"qr_session:{session_id}"
    
    @classmethod
    def start_session(cls, user_id: int, device_type: str = 'mobile') -> str:
        """Start a new scanning session"""
        session_id = str(uuid.uuid4())
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'device_type': device_type,
            'scans': [],
            'started_at': timezone.now().isoformat(),
            'matched_flow': None,
            'status': 'active'
        }
        
        cache.set(cls.get_session_key(session_id), session_data, timeout=300)  # 5 min timeout
        return session_id
    
    @classmethod
    def add_scan(cls, session_id: str, entity_type: str, entity_id: Any) -> Dict[str, Any]:
        """
        Add a scan to session and check for flow matches
        Returns: {'matched': bool, 'flow': dict, 'action_required': bool}
        """
        session_key = cls.get_session_key(session_id)
        session_data = cache.get(session_key)
        
        if not session_data:
            return {'error': 'Session expired or not found'}
        
        # Add scan to session
        scan_data = {
            'entity_type': entity_type,
            'entity_id': entity_id,
            'timestamp': timezone.now().isoformat()
        }
        session_data['scans'].append(scan_data)
        
        # Get current scan sequence
        scan_sequence = [scan['entity_type'] for scan in session_data['scans']]
        
        # Check for flow matches
        matched_flow = None
        for flow_name, flow_config in cls.FLOWS.items():
            if cls._matches_flow(scan_sequence, flow_config['sequence']):
                matched_flow = {
                    'name': flow_name,
                    'config': flow_config,
                    'entities': session_data['scans']
                }
                session_data['matched_flow'] = matched_flow
                break
        
        # Update session
        cache.set(session_key, session_data, timeout=300)
        
        if matched_flow:
            return {
                'matched': True,
                'flow': matched_flow,
                'action_required': not flow_config['auto_execute'],
                'auto_execute': flow_config['auto_execute']
            }
        
        return {
            'matched': False,
            'scan_count': len(session_data['scans']),
            'current_sequence': scan_sequence
        }
    
    @classmethod
    def _matches_flow(cls, scan_sequence: list, flow_sequence: list) -> bool:
        """Check if scan sequence matches a flow sequence"""
        if len(scan_sequence) != len(flow_sequence):
            return False
        
        for scan_type, flow_type in zip(scan_sequence, flow_sequence):
            # Handle different type names (e.g., 'customuser' vs 'user')
            scan_normalized = scan_type.lower().replace('customuser', 'user')
            flow_normalized = flow_type.lower()
            
            if scan_normalized != flow_normalized:
                return False
        
        return True
    
    @classmethod
    def execute_flow(cls, session_id: str) -> Dict[str, Any]:
        """Execute the matched flow action"""
        session_key = cls.get_session_key(session_id)
        session_data = cache.get(session_key)
        
        if not session_data or not session_data.get('matched_flow'):
            return {'error': 'No matched flow to execute'}
        
        flow = session_data['matched_flow']
        
        # Mark session as completed
        session_data['status'] = 'completed'
        session_data['completed_at'] = timezone.now().isoformat()
        cache.set(session_key, session_data, timeout=300)
        
        # Return flow execution details (actual execution logic would be in views)
        return {
            'success': True,
            'flow_name': flow['name'],
            'action': flow['config']['action'],
            'entities': flow['entities']
        }
    
    @classmethod
    def get_session(cls, session_id: str) -> Optional[Dict]:
        """Get session data"""
        return cache.get(cls.get_session_key(session_id))
    
    @classmethod
    def end_session(cls, session_id: str) -> bool:
        """End a scanning session"""
        session_key = cls.get_session_key(session_id)
        session_data = cache.get(session_key)
        
        if session_data:
            session_data['status'] = 'ended'
            session_data['ended_at'] = timezone.now().isoformat()
            cache.set(session_key, session_data, timeout=60)  # Keep for 1 minute for cleanup
            return True
        
        return False
