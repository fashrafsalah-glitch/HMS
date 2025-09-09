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
            entities.append({
                'type': scan.entity_type,
                'id': scan.entity_id,
                'data': json.loads(scan.entity_data) if scan.entity_data else {},
                'scanned_at': scan.scanned_at
            })
        return entities
    
    def match_operation(self, scanned_entities: List[Dict]) -> Optional['OperationDefinition']:
        """Match scanned sequence to an operation definition"""
        if not scanned_entities:
            return None
        
        # Get active operations
        active_operations = self.OperationDefinition.objects.filter(is_active=True)
        
        for operation in active_operations:
            steps = operation.steps.order_by('order')
            if self._sequence_matches_steps(scanned_entities, steps):
                return operation
        
        return None
    
    def _sequence_matches_steps(self, entities: List[Dict], steps) -> bool:
        """Check if scanned entities match operation steps"""
        required_steps = [s for s in steps if s.is_required]
        
        # Must have at least the required steps
        if len(entities) < len(required_steps):
            return False
        
        # Check each required step
        for i, step in enumerate(required_steps):
            if i >= len(entities):
                return False
                
            entity = entities[i]
            
            # Check entity type
            if entity['type'] != step.entity_type:
                return False
            
            # Check validation rule if exists
            if step.validation_rule:
                if not self._validate_entity(entity, step.validation_rule):
                    return False
            
            # Check allowed entity IDs if specified
            if step.allowed_entity_ids:
                allowed_ids = json.loads(step.allowed_entity_ids)
                if str(entity['id']) not in allowed_ids:
                    return False
        
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
        
        # Check if operation requires confirmation
        if operation.requires_confirmation:
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
            return self._perform_execution(operation, session, user, scanned_entities)
        
        # Create pending execution
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
                
                # Execute based on operation code
                result = self._execute_by_code(operation.code, scanned_entities, user)
                
                # Create logs based on operation settings
                logs_created = self._create_logs(operation, scanned_entities, user, result)
                
                # Update execution
                execution.status = 'completed'
                execution.completed_at = timezone.now()
                execution.result_data = json.dumps(result)
                execution.created_logs = json.dumps(logs_created)
                execution.save()
                
                return True, execution, f"Operation '{operation.name}' executed successfully"
                
        except Exception as e:
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
        if code == 'DEVICE_USAGE':
            result.update(self._handle_device_usage(entities, user))
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
        elif code == 'DEVICE_MAINTENANCE':
            result.update(self._handle_device_maintenance(entities, user))
        elif code == 'INVENTORY_CHECK':
            result.update(self._handle_inventory_check(entities, user))
        elif code == 'QUALITY_CONTROL':
            result.update(self._handle_quality_control(entities, user))
        elif code == 'CALIBRATION':
            result.update(self._handle_calibration(entities, user))
        elif code == 'INSPECTION':
            result.update(self._handle_inspection(entities, user))
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
    
    def _handle_device_usage(self, entities: List[Dict], user: User) -> Dict:
        """Handle device usage operation"""
        result = {'actions': []}
        
        # Find patient and devices
        patient_entity = next((e for e in entities if e['type'] == 'patient'), None)
        device_entities = [e for e in entities if e['type'] == 'device']
        
        if patient_entity and device_entities:
            from manager.models import Patient
            patient = Patient.objects.get(id=patient_entity['id'])
            
            for device_entity in device_entities:
                device = self.Device.objects.get(id=device_entity['id'])
                device.status = 'in_use'
                device.current_patient = patient
                device.save()
                result['actions'].append(f"Device {device.name} marked as in use by patient {patient.full_name}")
        
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
        """Handle device cleaning operation"""
        result = {'actions': []}
        
        device_entities = [e for e in entities if e['type'] == 'device']
        
        for device_entity in device_entities:
            device = self.Device.objects.get(id=device_entity['id'])
            device.clean_status = 'clean'
            device.last_cleaned_at = timezone.now()
            device.last_cleaned_by = user
            device.save()
            result['actions'].append(f"Device {device.name} marked as cleaned")
        
        return result
    
    def _handle_device_sterilization(self, entities: List[Dict], user: User) -> Dict:
        """Handle device sterilization operation"""
        result = {'actions': []}
        
        device_entities = [e for e in entities if e['type'] == 'device']
        
        for device_entity in device_entities:
            device = self.Device.objects.get(id=device_entity['id'])
            device.sterilization_status = 'sterile'
            device.last_sterilized_at = timezone.now()
            device.last_sterilized_by = user
            device.save()
            result['actions'].append(f"Device {device.name} marked as sterilized")
        
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
