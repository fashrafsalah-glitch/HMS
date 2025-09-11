"""
Dynamic QR Operations Manager
Handles dynamic operation detection, execution, and logging based on scanned QR sequences
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class QROperationsManager:
    """Manages dynamic QR code operations based on configured definitions"""
    
    def __init__(self):
        from .models import (
            OperationDefinition, OperationStep, OperationExecution,
            ScanSession, ScanHistory, Device, DeviceAccessory,
            DeviceUsageLog, DeviceTransferLog, PatientTransferLog,
            DeviceHandoverLog, AccessoryTransaction
        )
        from manager.models import Room
        self.OperationDefinition = OperationDefinition
        self.OperationStep = OperationStep
        self.OperationExecution = OperationExecution
        self.ScanSession = ScanSession
        self.ScanHistory = ScanHistory
        self.Device = Device
        self.DeviceAccessory = DeviceAccessory
        self.DeviceUsageLog = DeviceUsageLog
        self.DeviceTransferLog = DeviceTransferLog
        self.PatientTransferLog = PatientTransferLog
        self.DeviceHandoverLog = DeviceHandoverLog
        self.AccessoryTransaction = AccessoryTransaction
        self.Room = Room
    
    def check_session_timeout(self, session: 'ScanSession') -> bool:
        """Check if session has timed out based on operation settings"""
        if not session.current_operation:
            # Default 30 minute timeout if no operation
            timeout_minutes = 30
        else:
            timeout_minutes = session.current_operation.session_timeout_minutes
        
        if hasattr(session, 'last_activity'):
            last_activity = session.last_activity
        else:
            last_activity = session.updated_at
            
        timeout_delta = timedelta(minutes=timeout_minutes)
        return timezone.now() > last_activity + timeout_delta
    
    def get_scanned_entities(self, session: 'ScanSession') -> List[Dict]:
        """Get all scanned entities in current session"""
        scans = self.ScanHistory.objects.filter(
            session=session,
            is_valid=True
        ).order_by('scanned_at')
        
        entities = []
        for scan in scans:
            # entity_data might already be a dict or a string
            if scan.entity_data:
                if isinstance(scan.entity_data, dict):
                    data = scan.entity_data
                else:
                    data = json.loads(scan.entity_data)
            else:
                data = {}
                
            entities.append({
                'type': scan.entity_type,
                'id': scan.entity_id,
                'data': data,
                'scanned_at': scan.scanned_at
            })
        return entities
    
    def match_operation(self, scanned_entities: List[Dict]) -> Optional['OperationDefinition']:
        """Match scanned sequence to an operation definition"""
        print(f"[DEBUG match_operation] Checking {len(scanned_entities)} entities")
        print(f"[DEBUG match_operation] Entity types: {[e['type'] for e in scanned_entities]}")
        
        if not scanned_entities:
            return None
        
        # Get active operations
        active_operations = self.OperationDefinition.objects.filter(is_active=True)
        print(f"[DEBUG match_operation] Found {active_operations.count()} active operations")
        
        for operation in active_operations:
            steps = operation.steps.order_by('order')
            print(f"[DEBUG match_operation] Checking {operation.code} with {steps.count()} steps")
            if self._sequence_matches_steps(scanned_entities, steps):
                print(f"[DEBUG match_operation] MATCHED: {operation.code}")
                return operation
        
        print("[DEBUG match_operation] No operation matched")
        return None
    
    def _sequence_matches_steps(self, entities: List[Dict], steps) -> bool:
        """Check if scanned entities match operation steps"""
        required_steps = [s for s in steps if s.is_required]
        print(f"[DEBUG _sequence_matches_steps] Required steps: {len(required_steps)}")
        print(f"[DEBUG _sequence_matches_steps] Step types: {[s.entity_type for s in required_steps]}")
        print(f"[DEBUG _sequence_matches_steps] Entity types: {[e['type'] for e in entities]}")
        
        # Must have at least the required steps
        if len(entities) < len(required_steps):
            print(f"[DEBUG] Not enough entities: {len(entities)} < {len(required_steps)}")
            return False
        
        # Check each required step
        for i, step in enumerate(required_steps):
            if i >= len(entities):
                print(f"[DEBUG] Step {i} - no entity at this position")
                return False
                
            entity = entities[i]
            
            # Check entity type
            if entity['type'] != step.entity_type:
                print(f"[DEBUG] Step {i} - type mismatch: {entity['type']} != {step.entity_type}")
                return False
            
            # Check validation rule if exists
            if step.validation_rule:
                if not self._validate_entity(entity, step.validation_rule):
                    print(f"[DEBUG] Step {i} - validation rule failed")
                    return False
            
            # Check allowed entity IDs if specified
            if step.allowed_entity_ids:
                allowed_ids = json.loads(step.allowed_entity_ids)
                if str(entity['id']) not in allowed_ids:
                    print(f"[DEBUG] Step {i} - entity ID not in allowed list")
                    return False
        
        print(f"[DEBUG] All steps matched!")
        return True
    
    def _validate_entity(self, entity: Dict, rule: str) -> bool:
        """Validate entity against custom rule"""
        try:
            # Parse rule as JSON for complex validations
            rule_dict = json.loads(rule)
            
            # Example: {"status": "available", "department": "ICU"}
            for key, expected_value in rule_dict.items():
                if key not in entity.get('data', {}):
                    return False
                if entity['data'][key] != expected_value:
                    return False
            return True
        except:
            # If not JSON, treat as simple field check
            return rule in str(entity.get('data', {}))
    
    def execute_operation(
        self,
        operation: 'OperationDefinition',
        session: 'ScanSession',
        user: User,
        scanned_entities: List[Dict]
    ) -> Tuple[bool, Optional['OperationExecution'], str]:
        """Execute an operation and create appropriate logs"""
        print(f"[DEBUG execute_operation] Operation: {operation.code}, Auto: {operation.auto_execute}, Confirm: {operation.requires_confirmation}")
        print(f"[DEBUG execute_operation] Entities: {[e['type'] for e in scanned_entities]}")
        
        # Check if operation requires confirmation
        if operation.requires_confirmation:
            print("[DEBUG] Operation requires confirmation - creating pending execution")
            # Return pending execution for frontend confirmation
            execution = self.OperationExecution.objects.create(
                operation=operation,
                session=session,
                executed_by=user,
                status='pending',
                scanned_entities=json.dumps(scanned_entities),
                started_at=timezone.now()
            )
            return True, execution, "Operation requires confirmation"
        
        # Auto-execute if configured
        if operation.auto_execute:
            print("[DEBUG] Auto-executing operation")
            return self._perform_execution(operation, session, user, scanned_entities)
        
        # Create pending execution
        print("[DEBUG] Creating pending execution (not auto-execute)")
        execution = self.OperationExecution.objects.create(
            operation=operation,
            session=session,
            executed_by=user,
            status='pending',
            scanned_entities=json.dumps(scanned_entities),
            started_at=timezone.now()
        )
        
        return True, execution, "Operation ready for execution"
    
    def _perform_execution(
        self,
        operation: 'OperationDefinition',
        session: 'ScanSession',
        user: User,
        scanned_entities: List[Dict]
    ) -> Tuple[bool, Optional['OperationExecution'], str]:
        """Perform the actual operation execution"""
        print(f"[DEBUG _perform_execution] Starting execution for {operation.code}")
        
        execution = None
        try:
            with transaction.atomic():
                # Create execution record
                execution = self.OperationExecution.objects.create(
                    operation=operation,
                    session=session,
                    executed_by=user,
                    status='in_progress',
                    scanned_entities=json.dumps(scanned_entities),
                    started_at=timezone.now()
                )
                print(f"[DEBUG] Created execution record: {execution.id}")
                
                # Execute based on operation code
                print(f"[DEBUG] Calling _execute_by_code for {operation.code}")
                result = self._execute_by_code(operation.code, scanned_entities, user)
                print(f"[DEBUG] _execute_by_code result: {result}")
                
                # Create logs based on operation settings
                logs_created = self._create_logs(operation, scanned_entities, user, result)
                print(f"[DEBUG] Logs created: {logs_created}")
                
                # Update execution
                execution.status = 'completed'
                execution.completed_at = timezone.now()
                execution.result_data = json.dumps(result)
                execution.created_logs = json.dumps(logs_created)
                execution.save()
                print(f"[DEBUG] Execution completed successfully")
                
                return True, execution, f"Operation '{operation.name}' executed successfully"
                
        except Exception as e:
            print(f"[DEBUG ERROR] Exception in _perform_execution: {e}")
            import traceback
            print(f"[DEBUG ERROR] Traceback: {traceback.format_exc()}")
            if execution:
                execution.status = 'failed'
                execution.error_message = str(e)
                execution.completed_at = timezone.now()
                execution.save()
            return False, execution, f"Operation failed: {str(e)}"
    
    def _execute_by_code(self, code: str, entities: List[Dict], user: User) -> Dict:
        """Execute specific operation logic based on code"""
        result = {'success': True, 'actions': []}
        
        # Map operation codes to specific logic
        if code == 'BADGE_AUTH':
            result.update(self._handle_badge_auth(entities, user))
        elif code == 'DEVICE_USAGE':
            result.update(self._handle_device_usage(entities, user))
        elif code == 'END_DEVICE_USAGE':
            result.update(self._handle_end_device_usage(entities, user))
        elif code == 'DEVICE_TRANSFER':
            result.update(self._handle_device_transfer(entities, user))
        elif code == 'PATIENT_TRANSFER':
            result.update(self._handle_patient_transfer(entities, user))
        elif code == 'DEVICE_HANDOVER':
            result.update(self._handle_device_handover(entities, user))
        elif code == 'ACCESSORY_USAGE':
            result.update(self._handle_accessory_usage(entities, user))
        elif code == 'DEVICE_CLEANING':
            result.update(self._handle_device_cleaning(entities, user))
        elif code == 'DEVICE_STERILIZATION':
            result.update(self._handle_device_sterilization(entities, user))
        elif code == 'MAINTENANCE_OPEN':
            result.update(self._handle_maintenance_open(entities, user))
        elif code == 'MAINTENANCE_CLOSE':
            result.update(self._handle_maintenance_close(entities, user))
        elif code == 'DEVICE_LENDING':
            result.update(self._handle_device_lending(entities, user))
        elif code == 'OUT_OF_SERVICE':
            result.update(self._handle_out_of_service(entities, user))
        elif code == 'INVENTORY_CHECK':
            result.update(self._handle_inventory_check(entities, user))
        elif code == 'QUALITY_CONTROL':
            result.update(self._handle_quality_control(entities, user))
        elif code == 'CALIBRATION':
            result.update(self._handle_calibration(entities, user))
        elif code == 'INSPECTION':
            result.update(self._handle_inspection(entities, user))
        elif code == 'AUDIT_REPORT':
            result.update(self._handle_audit_report(entities, user))
        elif code == 'CUSTOM':
            result.update(self._handle_custom_operation(entities, user))
        else:
            # Generic operation - just record the scan sequence
            result['actions'].append(f"Recorded scan sequence for operation: {code}")
        
        return result
    
    def _handle_inventory_check(self, entities: List[Dict], user: User) -> Dict:
        """Handle inventory check operation"""
        result = {'actions': []}
        
        device_entities = [e for e in entities if e['type'] == 'device']
        
        for device_entity in device_entities:
            device = self.Device.objects.get(id=device_entity['id'])
            # Mark device as checked
            device.last_inventory_check = timezone.now()
            device.inventory_checked_by = user
            device.save()
            result['actions'].append(f"Inventory check completed for device {device.name}")
        
        return result
    
    def _handle_quality_control(self, entities: List[Dict], user: User) -> Dict:
        """Handle quality control operation"""
        result = {'actions': []}
        
        device_entities = [e for e in entities if e['type'] == 'device']
        
        for device_entity in device_entities:
            device = self.Device.objects.get(id=device_entity['id'])
            # Mark device as quality checked
            device.last_quality_check = timezone.now()
            device.quality_checked_by = user
            device.save()
            result['actions'].append(f"Quality control completed for device {device.name}")
        
        return result
    
    def _handle_calibration(self, entities: List[Dict], user: User) -> Dict:
        """Handle calibration operation"""
        result = {'actions': []}
        
        device_entities = [e for e in entities if e['type'] == 'device']
        
        for device_entity in device_entities:
            device = self.Device.objects.get(id=device_entity['id'])
            # Mark device as calibrated
            device.last_calibration_date = timezone.now()
            device.calibrated_by = user
            device.save()
            result['actions'].append(f"Calibration completed for device {device.name}")
        
        return result
    
    def _handle_inspection(self, entities: List[Dict], user: User) -> Dict:
        """Handle inspection operation"""
        result = {'actions': []}
        
        device_entities = [e for e in entities if e['type'] == 'device']
        
        for device_entity in device_entities:
            device = self.Device.objects.get(id=device_entity['id'])
            # Mark device as inspected
            device.last_inspection_date = timezone.now()
            device.inspected_by = user
            device.save()
            result['actions'].append(f"Inspection completed for device {device.name}")
        
        return result
    
    def _handle_custom_operation(self, entities: List[Dict], user: User) -> Dict:
        """Handle custom operation"""
        result = {'actions': []}
        
        # Generic handling for custom operations
        entity_types = [e['type'] for e in entities]
        result['actions'].append(f"Custom operation executed on entities: {', '.join(entity_types)}")
        
        return result
    
    def _handle_badge_auth(self, entities: List[Dict], user: User) -> Dict:
        """Handle badge authentication - Start of any operation"""
        from .models import Badge
        result = {'actions': []}
        
        badge_entity = next((e for e in entities if e['type'] == 'user'), None)
        
        if badge_entity:
            try:
                badge = Badge.objects.get(user_id=badge_entity['id'])
                badge.last_login = timezone.now()
                badge.save()
                result['actions'].append(f"تم مصادقة البطاقة للمستخدم {user.get_full_name()}")
                result['authenticated'] = True
            except Badge.DoesNotExist:
                result['actions'].append(f"لا توجد بطاقة مسجلة للمستخدم")
                result['authenticated'] = False
        
        return result
    
    def _handle_device_usage(self, entities: List[Dict], user: User) -> Dict:
        """Handle device usage operation - Link device to patient"""
        print(f"[DEBUG _handle_device_usage] Starting with {len(entities)} entities")
        result = {'actions': []}
        
        # Find badge, patient and devices
        badge_entity = next((e for e in entities if e['type'] == 'user'), None)
        patient_entity = next((e for e in entities if e['type'] == 'patient'), None)
        device_entities = [e for e in entities if e['type'] == 'device']
        
        print(f"[DEBUG] Badge: {badge_entity}, Patient: {patient_entity}, Devices: {len(device_entities)}")
        
        if patient_entity and device_entities:
            from manager.models import Patient
            patient = Patient.objects.get(id=patient_entity['id'])
            print(f"[DEBUG] Found patient: {patient}")
            
            for device_entity in device_entities:
                device = self.Device.objects.get(id=device_entity['id'])
                print(f"[DEBUG] Processing device: {device.name}, status: {device.status}")
                
                # Check if device is available
                if device.status == 'in_use':
                    result['actions'].append(f"⚠️ الجهاز {device.name} قيد الاستخدام بالفعل")
                    print(f"[DEBUG] Device {device.name} already in use")
                    continue
                    
                # Create usage log
                usage_log = self.DeviceUsageLog.objects.create(
                    device=device,
                    patient=patient,
                    used_by=user,
                    start_time=timezone.now(),
                    notes=f"ربط عبر QR - المريض: {patient.first_name} {patient.last_name}"
                )
                print(f"[DEBUG] Created usage log: {usage_log.id}")
                
                # Update device status
                device.status = 'in_use'
                device.in_use = True
                device.current_patient = patient
                device.usage_start_time = timezone.now()
                device.save()
                print(f"[DEBUG] Device {device.name} status updated to in_use")
                
                result['actions'].append(f"✅ تم ربط الجهاز {device.name} بالمريض {patient.first_name} {patient.last_name}")
        else:
            print(f"[DEBUG] Missing entities - Patient: {patient_entity is not None}, Devices: {len(device_entities)}")
            result['actions'].append("⚠️ يجب مسح المستخدم والجهاز والمريض بالترتيب")
        
        print(f"[DEBUG] Result: {result}")
        return result
    
    def _handle_end_device_usage(self, entities: List[Dict], user: User) -> Dict:
        """Handle end device usage operation"""
        result = {'actions': []}
        
        # Find badge, patient and devices
        badge_entity = next((e for e in entities if e['type'] == 'user'), None)
        patient_entity = next((e for e in entities if e['type'] == 'patient'), None)
        device_entities = [e for e in entities if e['type'] == 'device']
        
        if patient_entity and device_entities:
            from manager.models import Patient
            patient = Patient.objects.get(id=patient_entity['id'])
            
            for device_entity in device_entities:
                device = self.Device.objects.get(id=device_entity['id'])
                
                # Check if device is actually in use by this patient
                if device.current_patient != patient:
                    result['actions'].append(f"⚠️ الجهاز {device.name} غير مرتبط بالمريض {patient.first_name}")
                    continue
                
                # Find and end usage log
                usage_logs = self.DeviceUsageLog.objects.filter(
                    device=device,
                    patient=patient,
                    end_time__isnull=True
                )
                
                for log in usage_logs:
                    log.end_time = timezone.now()
                    log.save()
                
                # Update device status
                device.status = 'available'
                device.in_use = False
                device.current_patient = None
                device.usage_start_time = None
                device.save()
                
                result['actions'].append(f"✅ تم إنهاء استخدام الجهاز {device.name} من المريض {patient.first_name} {patient.last_name}")
        
        return result
    
    def _handle_device_transfer(self, entities: List[Dict], user: User) -> Dict:
        """Handle device transfer between departments"""
        result = {'actions': []}
        
        device_entities = [e for e in entities if e['type'] == 'device']
        dept_entity = next((e for e in entities if e['type'] == 'department'), None)
        
        if device_entities and dept_entity:
            from hr.models import Department
            new_dept = Department.objects.get(id=dept_entity['id'])
            
            for device_entity in device_entities:
                device = self.Device.objects.get(id=device_entity['id'])
                old_dept = device.department
                device.department = new_dept
                device.save()
                result['actions'].append(f"Device {device.name} transferred from {old_dept} to {new_dept}")
        
        return result
    
    def _handle_patient_transfer(self, entities: List[Dict], user: User) -> Dict:
        """Handle patient transfer between beds/departments"""
        result = {'actions': []}
        
        patient_entity = next((e for e in entities if e['type'] == 'patient'), None)
        bed_entity = next((e for e in entities if e['type'] == 'bed'), None)
        
        if patient_entity and bed_entity:
            from manager.models import Patient, Bed
            patient = Patient.objects.get(id=patient_entity['id'])
            new_bed = Bed.objects.get(id=bed_entity['id'])
            
            # Update patient bed assignment
            old_bed = getattr(patient, 'current_bed', None)
            patient.current_bed = new_bed
            patient.save()
            
            # Update bed status
            new_bed.is_occupied = True
            new_bed.save()
            
            if old_bed:
                old_bed.is_occupied = False
                old_bed.save()
                result['actions'].append(f"Patient {patient.full_name} transferred from bed {old_bed} to {new_bed}")
            else:
                result['actions'].append(f"Patient {patient.full_name} assigned to bed {new_bed}")
        
        return result
    
    def _handle_device_handover(self, entities: List[Dict], user: User) -> Dict:
        """Handle device handover between users"""
        result = {'actions': []}
        
        from_user = next((e for e in entities if e['type'] == 'user'), None)
        to_user = next((e for e in entities[1:] if e['type'] == 'user'), None)
        device_entities = [e for e in entities if e['type'] == 'device']
        
        if from_user and to_user and device_entities:
            from_user_obj = User.objects.get(id=from_user['id'])
            to_user_obj = User.objects.get(id=to_user['id'])
            
            for device_entity in device_entities:
                device = self.Device.objects.get(id=device_entity['id'])
                result['actions'].append(f"Device {device.name} handed over from {from_user_obj.username} to {to_user_obj.username}")
        
        return result
    
    def _handle_accessory_usage(self, entities: List[Dict], user: User) -> Dict:
        """Handle accessory usage/consumption"""
        result = {'actions': []}
        
        accessory_entities = [e for e in entities if e['type'] == 'accessory']
        patient_entity = next((e for e in entities if e['type'] == 'patient'), None)
        
        for accessory_entity in accessory_entities:
            accessory = self.DeviceAccessory.objects.get(id=accessory_entity['id'])
            
            # Decrement quantity if consumable
            if hasattr(accessory, 'quantity') and accessory.quantity > 0:
                accessory.quantity -= 1
                accessory.save()
                result['actions'].append(f"Accessory {accessory.name} consumed (remaining: {accessory.quantity})")
            else:
                result['actions'].append(f"Accessory {accessory.name} used")
        
        return result
    
    def _handle_device_cleaning(self, entities: List[Dict], user: User) -> Dict:
        """Handle device cleaning operation - Start or End cleaning cycle"""
        from .models import CleaningCycle, Badge
        result = {'actions': []}
        
        device_entities = [e for e in entities if e['type'] == 'device']
        user_entities = [e for e in entities if e['type'] == 'user']
        
        # Get user's badge if available
        badge = None
        try:
            badge = Badge.objects.get(user=user)
        except Badge.DoesNotExist:
            pass
        
        for device_entity in device_entities:
            device = self.Device.objects.get(id=device_entity['id'])
            
            # Check if there's an active cleaning cycle
            active_cycle = CleaningCycle.objects.filter(
                device=device,
                is_completed=False
            ).first()
            
            if active_cycle:
                # End the cleaning cycle
                active_cycle.end_time = timezone.now()
                active_cycle.is_completed = True
                active_cycle.notes += f"\n\nإنهاء عبر QR في: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
                active_cycle.save()
                
                # Update device status
                device.clean_status = 'clean'
                device.last_cleaned_at = timezone.now()
                device.last_cleaned_by = user
                device.save()
                
                result['actions'].append(f"تم إنهاء دورة التنظيف للجهاز {device.name}")
            else:
                # Start new cleaning cycle
                cycle = CleaningCycle.objects.create(
                    device=device,
                    user=user,
                    badge=badge,
                    notes=f"بدء عبر QR في: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                
                # Update device status
                device.clean_status = 'in_progress'
                device.save()
                
                result['actions'].append(f"تم بدء دورة التنظيف للجهاز {device.name}")
        
        return result
    
    def _handle_device_sterilization(self, entities: List[Dict], user: User) -> Dict:
        """Handle device sterilization operation - Start or End sterilization cycle"""
        from .models import SterilizationCycle, Badge
        result = {'actions': []}
        
        device_entities = [e for e in entities if e['type'] == 'device']
        user_entities = [e for e in entities if e['type'] == 'user']
        
        # Get user's badge if available
        badge = None
        try:
            badge = Badge.objects.get(user=user)
        except Badge.DoesNotExist:
            pass
        
        for device_entity in device_entities:
            device = self.Device.objects.get(id=device_entity['id'])
            
            # Check if there's an active sterilization cycle
            active_cycle = SterilizationCycle.objects.filter(
                device=device,
                is_completed=False
            ).first()
            
            if active_cycle:
                # End the sterilization cycle
                active_cycle.end_time = timezone.now()
                active_cycle.is_completed = True
                active_cycle.notes += f"\n\nإنهاء عبر QR في: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
                active_cycle.save()
                
                # Update device status
                device.sterilization_status = 'sterilized'
                device.last_sterilized_at = timezone.now()
                device.last_sterilized_by = user
                device.save()
                
                result['actions'].append(f"تم إنهاء دورة التعقيم للجهاز {device.name}")
            else:
                # Start new sterilization cycle
                cycle = SterilizationCycle.objects.create(
                    device=device,
                    user=user,
                    badge=badge,
                    method='autoclave',  # Default method
                    notes=f"بدء عبر QR في: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                
                # Update device status
                device.sterilization_status = 'in_progress'
                device.save()
                
                result['actions'].append(f"تم بدء دورة التعقيم للجهاز {device.name}")
        
        return result
    
    def _handle_device_maintenance(self, entities: List[Dict], user: User) -> Dict:
        """Handle device maintenance operation"""
        result = {'actions': []}
        
        device_entities = [e for e in entities if e['type'] == 'device']
        
        for device_entity in device_entities:
            device = self.Device.objects.get(id=device_entity['id'])
            device.maintenance_status = 'maintained'
            device.last_maintenance_at = timezone.now()
            device.last_maintained_by = user
            device.save()
            result['actions'].append(f"Device {device.name} maintenance completed")
        
        return result
    
    def _handle_maintenance_open(self, entities: List[Dict], user: User) -> Dict:
        """Handle opening maintenance work order"""
        from .models_cmms import WorkOrder
        from .models import Badge
        result = {'actions': []}
        
        badge_entity = next((e for e in entities if e['type'] == 'user'), None)
        device_entities = [e for e in entities if e['type'] == 'device']
        
        for device_entity in device_entities:
            device = self.Device.objects.get(id=device_entity['id'])
            
            # Create work order
            wo = WorkOrder.objects.create(
                device=device,
                work_type='corrective',
                priority='medium',
                status='open',
                reported_by=user,
                title=f"صيانة الجهاز {device.name}",
                description=f"أمر صيانة مفتوح عبر QR",
                scheduled_start=timezone.now(),
                scheduled_end=timezone.now() + timedelta(hours=4)
            )
            
            # Update device status
            device.status = 'under_maintenance'
            device.save()
            
            result['actions'].append(f"✅ تم فتح أمر الصيانة #{wo.work_order_number} للجهاز {device.name}")
        
        return result
    
    def _handle_maintenance_close(self, entities: List[Dict], user: User) -> Dict:
        """Handle closing maintenance work order"""
        from .models_cmms import WorkOrder
        result = {'actions': []}
        
        badge_entity = next((e for e in entities if e['type'] == 'user'), None)
        device_entities = [e for e in entities if e['type'] == 'device']
        
        for device_entity in device_entities:
            device = self.Device.objects.get(id=device_entity['id'])
            
            # Find open work orders for this device
            open_wos = WorkOrder.objects.filter(
                device=device,
                status__in=['open', 'in_progress', 'pending']
            )
            
            for wo in open_wos:
                wo.status = 'completed'
                wo.actual_end = timezone.now()
                wo.completed_by = user
                wo.resolution_notes = "تم إغلاق أمر الصيانة عبر QR"
                wo.save()
                
                result['actions'].append(f"✅ تم إغلاق أمر الصيانة #{wo.work_order_number}")
            
            # Update device status
            device.status = 'working'
            device.save()
            
            if not open_wos:
                result['actions'].append(f"⚠️ لا توجد أوامر صيانة مفتوحة للجهاز {device.name}")
        
        return result
    
    def _handle_device_lending(self, entities: List[Dict], user: User) -> Dict:
        """Handle device lending operation"""
        result = {'actions': []}
        
        # Find from_user, to_user/department, and devices
        from_user = next((e for e in entities if e['type'] == 'user'), None)
        to_entity = next((e for e in entities[1:] if e['type'] in ['user', 'department']), None)
        device_entities = [e for e in entities if e['type'] == 'device']
        
        if from_user and to_entity and device_entities:
            for device_entity in device_entities:
                device = self.Device.objects.get(id=device_entity['id'])
                
                # Create lending record
                lending_info = {
                    'lent_to': to_entity['type'],
                    'lent_to_id': to_entity['id'],
                    'lent_by': user.id,
                    'lent_date': timezone.now().isoformat(),
                    'expected_return': (timezone.now() + timedelta(days=7)).isoformat()
                }
                
                # Update device
                device.is_lent = True
                device.lending_info = json.dumps(lending_info)
                device.save()
                
                result['actions'].append(f"✅ تم إعارة الجهاز {device.name} لمدة 7 أيام")
        
        return result
    
    def _handle_out_of_service(self, entities: List[Dict], user: User) -> Dict:
        """Handle taking device out of service - requires double authentication"""
        result = {'actions': []}
        
        # Need supervisor and employee badges
        user_entities = [e for e in entities if e['type'] == 'user']
        device_entities = [e for e in entities if e['type'] == 'device']
        
        if len(user_entities) >= 2 and device_entities:
            # Double authentication verified
            supervisor = User.objects.get(id=user_entities[0]['id'])
            employee = User.objects.get(id=user_entities[1]['id'])
            
            for device_entity in device_entities:
                device = self.Device.objects.get(id=device_entity['id'])
                
                # Update device status
                device.status = 'out_of_order'
                device.out_of_service_reason = f"أخرج من الخدمة بواسطة {supervisor.get_full_name()} و {employee.get_full_name()}"
                device.out_of_service_date = timezone.now()
                device.save()
                
                result['actions'].append(f"⛔ تم إخراج الجهاز {device.name} من الخدمة")
        else:
            result['actions'].append("⚠️ يتطلب مصادقة مزدوجة (مشرف + موظف)")
        
        return result
    
    def _handle_audit_report(self, entities: List[Dict], user: User) -> Dict:
        """Handle audit and reporting - open device log"""
        result = {'actions': []}
        
        device_entities = [e for e in entities if e['type'] == 'device']
        
        for device_entity in device_entities:
            device = self.Device.objects.get(id=device_entity['id'])
            
            # Gather audit information
            from .models_cmms import WorkOrder
            
            # Recent work orders
            recent_wos = WorkOrder.objects.filter(
                device=device
            ).order_by('-created_at')[:5]
            
            # Usage logs
            recent_usage = self.DeviceUsageLog.objects.filter(
                device=device
            ).order_by('-start_time')[:5]
            
            audit_info = {
                'device_name': device.name,
                'status': device.status,
                'last_maintenance': device.last_maintenance_date.isoformat() if device.last_maintenance_date else None,
                'recent_work_orders': len(recent_wos),
                'recent_usage_count': len(recent_usage),
                'audited_by': user.get_full_name(),
                'audit_date': timezone.now().isoformat()
            }
            
            result['actions'].append(f"📊 تقرير تدقيق للجهاز {device.name}")
            result['audit_data'] = audit_info
        
        return result
    
    def _create_logs(
        self,
        operation: 'OperationDefinition',
        entities: List[Dict],
        user: User,
        result: Dict
    ) -> List[Dict]:
        """Create appropriate logs based on operation settings"""
        logs_created = []
        
        # Device Usage Log
        if operation.log_to_usage:
            device_entities = [e for e in entities if e['type'] == 'device']
            patient_entity = next((e for e in entities if e['type'] == 'patient'), None)
            
            if device_entities and patient_entity:
                from manager.models import Patient
                patient = Patient.objects.get(id=patient_entity['id'])
                
                for device_entity in device_entities:
                    device = self.Device.objects.get(id=device_entity['id'])
                    log = self.DeviceUsageLog.objects.create(
                        device=device,
                        patient=patient,
                        used_by=user,
                        start_time=timezone.now(),
                        notes=f"Via QR Operation: {operation.name}"
                    )
                    logs_created.append({
                        'type': 'DeviceUsageLog',
                        'id': log.id
                    })
        
        # Transfer Logs
        if operation.log_to_transfer:
            # Device Transfer
            device_entities = [e for e in entities if e['type'] == 'device']
            dept_entity = next((e for e in entities if e['type'] == 'department'), None)
            
            if device_entities and dept_entity:
                from hr.models import Department
                to_dept = Department.objects.get(id=dept_entity['id'])
                
                for device_entity in device_entities:
                    device = self.Device.objects.get(id=device_entity['id'])
                    log = self.DeviceTransferLog.objects.create(
                        device=device,
                        from_department=device.department,
                        to_department=to_dept,
                        transferred_by=user,
                        transfer_date=timezone.now(),
                        reason=f"QR Operation: {operation.name}"
                    )
                    logs_created.append({
                        'type': 'DeviceTransferLog',
                        'id': log.id
                    })
            
            # Patient Transfer
            patient_entity = next((e for e in entities if e['type'] == 'patient'), None)
            bed_entity = next((e for e in entities if e['type'] == 'bed'), None)
            
            if patient_entity and bed_entity:
                from manager.models import Patient, Bed
                patient = Patient.objects.get(id=patient_entity['id'])
                to_bed = Bed.objects.get(id=bed_entity['id'])
                
                log = self.PatientTransferLog.objects.create(
                    patient=patient,
                    from_bed=getattr(patient, 'current_bed', None),
                    to_bed=to_bed,
                    transferred_by=user,
                    transfer_date=timezone.now(),
                    reason=f"QR Operation: {operation.name}"
                )
                logs_created.append({
                    'type': 'PatientTransferLog',
                    'id': log.id
                })
        
        # Handover Log
        if operation.log_to_handover:
            from_user = next((e for e in entities if e['type'] == 'user'), None)
            to_user = next((e for e in entities[1:] if e['type'] == 'user'), None)
            device_entities = [e for e in entities if e['type'] == 'device']
            
            if from_user and to_user and device_entities:
                from_user_obj = User.objects.get(id=from_user['id'])
                to_user_obj = User.objects.get(id=to_user['id'])
                
                for device_entity in device_entities:
                    device = self.Device.objects.get(id=device_entity['id'])
                    
                    # Update device status automatically
                    device.in_use = True
                    device.usage_start_time = timezone.now()
                    device.availability = False
                    
                    # If previous user was responsible, end usage and create maintenance WO
                    if from_user_obj == device.responsible_user:
                        device.end_usage()  # This will trigger after_use maintenance if configured
                    
                    # Update responsible user to new user
                    device.responsible_user = to_user_obj
                    device.save()
                    
                    log = self.DeviceHandoverLog.objects.create(
                        device=device,
                        from_user=from_user_obj,
                        to_user=to_user_obj,
                        handover_date=timezone.now(),
                        notes=f"QR Operation: {operation.name}"
                    )
                    logs_created.append({
                        'type': 'DeviceHandoverLog',
                        'id': log.id
                    })
        
        return logs_created
    
    def confirm_execution(self, execution_id: int, user: User) -> Tuple[bool, str]:
        """Confirm and execute a pending operation"""
        try:
            execution = self.OperationExecution.objects.get(
                id=execution_id,
                status='pending'
            )
            
            # Parse scanned entities
            scanned_entities = json.loads(execution.scanned_entities)
            
            # Perform execution
            success, _, message = self._perform_execution(
                execution.operation,
                execution.session,
                user,
                scanned_entities
            )
            
            return success, message
            
        except self.OperationExecution.DoesNotExist:
            return False, "Execution not found or already processed"
        except Exception as e:
            return False, f"Error confirming execution: {str(e)}"
    
    def cancel_execution(self, execution_id: int) -> Tuple[bool, str]:
        """Cancel a pending operation execution"""
        try:
            execution = self.OperationExecution.objects.get(
                id=execution_id,
                status='pending'
            )
            
            execution.status = 'cancelled'
            execution.completed_at = timezone.now()
            execution.save()
            
            return True, "Operation cancelled"
            
        except self.OperationExecution.DoesNotExist:
            return False, "Execution not found or already processed"
