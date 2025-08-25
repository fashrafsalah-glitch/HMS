# اختبارات الـ API للـ CMMS
# هنا بنختبر جميع endpoints والـ serializers والاستجابات

from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta
from decimal import Decimal
import json

from maintenance.models import Device
from maintenance.models_cmms import ServiceRequest, WorkOrder, JobPlan
from maintenance.models_spare_parts import Supplier, SparePart
from maintenance.permissions import setup_cmms_permissions


class CMMSAPITestCase(TestCase):
    """الفئة الأساسية لاختبارات API"""
    
    def setUp(self):
        """إعداد البيانات المشتركة للاختبارات"""
        # إنشاء المستخدمين
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_staff=True
        )
        
        self.technician_user = User.objects.create_user(
            username='technician',
            email='tech@example.com',
            password='testpass123'
        )
        
        # إعداد الصلاحيات
        setup_cmms_permissions()
        
        admin_group = Group.objects.get(name='CMMS_Admin')
        technician_group = Group.objects.get(name='CMMS_Technician')
        
        self.admin_user.groups.add(admin_group)
        self.technician_user.groups.add(technician_group)
        
        # إنشاء البيانات الأساسية
        self.device = Device.objects.create(
            name='جهاز اختبار API',
            serial_number='API001',
            category='medical',
            status='operational'
        )
        
        self.supplier = Supplier.objects.create(
            name='مورد API',
            contact_person='أحمد محمد',
            email='supplier@example.com'
        )
        
        self.spare_part = SparePart.objects.create(
            name='قطعة API',
            part_number='API001',
            supplier=self.supplier,
            cost=Decimal('100.00'),
            quantity=10
        )
        
        self.client = APIClient()


class DeviceAPITest(CMMSAPITestCase):
    """اختبارات API الأجهزة"""
    
    def test_device_list_api(self):
        """اختبار API قائمة الأجهزة"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/maintenance/devices/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'جهاز اختبار API')
        
    def test_device_detail_api(self):
        """اختبار API تفاصيل الجهاز"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get(f'/api/maintenance/devices/{self.device.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'جهاز اختبار API')
        self.assertEqual(response.data['serial_number'], 'API001')
        
    def test_device_create_api(self):
        """اختبار API إنشاء جهاز جديد"""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'name': 'جهاز جديد API',
            'serial_number': 'API002',
            'category': 'laboratory',
            'status': 'operational',
            'model': 'Model X',
            'manufacturer': 'Test Manufacturer'
        }
        
        response = self.client.post('/api/maintenance/devices/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'جهاز جديد API')
        
        # التحقق من إنشاء الجهاز في قاعدة البيانات
        self.assertTrue(
            Device.objects.filter(name='جهاز جديد API').exists()
        )
        
    def test_device_update_api(self):
        """اختبار API تحديث الجهاز"""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'name': 'جهاز محدث API',
            'status': 'maintenance'
        }
        
        response = self.client.patch(f'/api/maintenance/devices/{self.device.id}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'جهاز محدث API')
        self.assertEqual(response.data['status'], 'maintenance')
        
    def test_device_delete_api(self):
        """اختبار API حذف الجهاز"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.delete(f'/api/maintenance/devices/{self.device.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # التحقق من حذف الجهاز
        self.assertFalse(
            Device.objects.filter(id=self.device.id).exists()
        )


class ServiceRequestAPITest(CMMSAPITestCase):
    """اختبارات API طلبات الخدمة"""
    
    def setUp(self):
        super().setUp()
        
        self.service_request = ServiceRequest.objects.create(
            title='طلب API',
            description='وصف طلب API',
            device=self.device,
            requested_by=self.admin_user,
            priority='medium'
        )
        
    def test_service_request_list_api(self):
        """اختبار API قائمة طلبات الخدمة"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/maintenance/service-requests/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'طلب API')
        
    def test_service_request_create_api(self):
        """اختبار API إنشاء طلب خدمة"""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'title': 'طلب جديد API',
            'description': 'وصف الطلب الجديد',
            'device': self.device.id,
            'priority': 'high',
            'request_type': 'breakdown'
        }
        
        response = self.client.post('/api/maintenance/service-requests/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'طلب جديد API')
        
    def test_service_request_filter_by_status(self):
        """اختبار تصفية طلبات الخدمة حسب الحالة"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/maintenance/service-requests/?status=new')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
    def test_service_request_filter_by_device(self):
        """اختبار تصفية طلبات الخدمة حسب الجهاز"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get(f'/api/maintenance/service-requests/?device={self.device.id}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class WorkOrderAPITest(CMMSAPITestCase):
    """اختبارات API أوامر الشغل"""
    
    def setUp(self):
        super().setUp()
        
        self.service_request = ServiceRequest.objects.create(
            title='طلب API',
            description='وصف طلب API',
            device=self.device,
            requested_by=self.admin_user
        )
        
        self.job_plan = JobPlan.objects.create(
            name='خطة API',
            description='وصف خطة API',
            instructions='تعليمات API',
            estimated_duration=60,
            created_by=self.admin_user
        )
        
        self.work_order = WorkOrder.objects.create(
            service_request=self.service_request,
            assigned_technician=self.technician_user,
            job_plan=self.job_plan
        )
        
    def test_work_order_list_api(self):
        """اختبار API قائمة أوامر الشغل"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/maintenance/work-orders/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        
    def test_work_order_update_status_api(self):
        """اختبار API تحديث حالة أمر الشغل"""
        self.client.force_authenticate(user=self.technician_user)
        
        data = {
            'status': 'in_progress',
            'work_performed': 'بدء العمل عبر API',
            'start_time': timezone.now().isoformat()
        }
        
        response = self.client.patch(f'/api/maintenance/work-orders/{self.work_order.id}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'in_progress')
        
        # التحقق من التحديث في قاعدة البيانات
        self.work_order.refresh_from_db()
        self.assertEqual(self.work_order.status, 'in_progress')
        
    def test_work_order_complete_api(self):
        """اختبار API إكمال أمر الشغل"""
        self.client.force_authenticate(user=self.technician_user)
        
        data = {
            'status': 'resolved',
            'work_performed': 'تم إكمال العمل',
            'findings': 'النتائج',
            'recommendations': 'التوصيات',
            'end_time': timezone.now().isoformat(),
            'labor_hours': '2.5'
        }
        
        response = self.client.patch(f'/api/maintenance/work-orders/{self.work_order.id}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'resolved')


class SparePartAPITest(CMMSAPITestCase):
    """اختبارات API قطع الغيار"""
    
    def test_spare_part_list_api(self):
        """اختبار API قائمة قطع الغيار"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/maintenance/spare-parts/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'قطعة API')
        
    def test_spare_part_create_api(self):
        """اختبار API إنشاء قطعة غيار"""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'name': 'قطعة جديدة API',
            'part_number': 'API002',
            'supplier': self.supplier.id,
            'cost': '150.00',
            'quantity': 5,
            'minimum_stock': 2,
            'unit': 'قطعة'
        }
        
        response = self.client.post('/api/maintenance/spare-parts/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'قطعة جديدة API')
        
    def test_spare_part_low_stock_filter(self):
        """اختبار تصفية قطع الغيار المنخفضة"""
        # إنشاء قطعة غيار منخفضة
        SparePart.objects.create(
            name='قطعة منخفضة',
            part_number='LOW001',
            supplier=self.supplier,
            quantity=2,
            minimum_stock=5
        )
        
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/maintenance/spare-parts/?low_stock=true')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # يجب أن تظهر القطعة المنخفضة فقط
        low_stock_parts = [part for part in response.data['results'] 
                          if part['quantity'] <= part['minimum_stock']]
        self.assertTrue(len(low_stock_parts) > 0)


class DashboardAPITest(CMMSAPITestCase):
    """اختبارات API لوحة التحكم"""
    
    def setUp(self):
        super().setUp()
        
        # إنشاء بيانات إضافية للاختبار
        ServiceRequest.objects.create(
            title='طلب 1',
            description='وصف',
            device=self.device,
            requested_by=self.admin_user,
            status='new'
        )
        
        ServiceRequest.objects.create(
            title='طلب 2',
            description='وصف',
            device=self.device,
            requested_by=self.admin_user,
            status='assigned'
        )
        
    def test_dashboard_data_api(self):
        """اختبار API بيانات لوحة التحكم"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/maintenance/dashboard/data/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # التحقق من وجود البيانات المطلوبة
        self.assertIn('total_devices', response.data)
        self.assertIn('active_work_orders', response.data)
        self.assertIn('pending_service_requests', response.data)
        self.assertIn('low_stock_parts', response.data)
        
        # التحقق من صحة البيانات
        self.assertEqual(response.data['total_devices'], 1)
        self.assertEqual(response.data['pending_service_requests'], 2)
        
    def test_device_kpis_api(self):
        """اختبار API مؤشرات الأداء للجهاز"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get(f'/api/maintenance/devices/{self.device.id}/kpis/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # التحقق من وجود المؤشرات
        self.assertIn('mtbf', response.data)
        self.assertIn('mttr', response.data)
        self.assertIn('availability', response.data)
        self.assertIn('total_work_orders', response.data)


class PermissionsAPITest(CMMSAPITestCase):
    """اختبارات صلاحيات API"""
    
    def test_unauthorized_access(self):
        """اختبار منع الوصول غير المصرح به"""
        # محاولة الوصول بدون مصادقة
        response = self.client.get('/api/maintenance/devices/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_technician_limited_access(self):
        """اختبار الوصول المحدود للفني"""
        self.client.force_authenticate(user=self.technician_user)
        
        # يجب أن يتمكن من عرض الأجهزة
        response = self.client.get('/api/maintenance/devices/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # لكن لا يجب أن يتمكن من حذف الأجهزة
        response = self.client.delete(f'/api/maintenance/devices/{self.device.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_admin_full_access(self):
        """اختبار الوصول الكامل للمدير"""
        self.client.force_authenticate(user=self.admin_user)
        
        # يجب أن يتمكن من جميع العمليات
        operations = [
            ('GET', '/api/maintenance/devices/'),
            ('POST', '/api/maintenance/devices/', {
                'name': 'جهاز جديد',
                'serial_number': 'NEW001',
                'category': 'medical'
            }),
            ('GET', f'/api/maintenance/devices/{self.device.id}/'),
            ('PATCH', f'/api/maintenance/devices/{self.device.id}/', {
                'name': 'جهاز محدث'
            })
        ]
        
        for method, url, *data in operations:
            if method == 'GET':
                response = self.client.get(url)
            elif method == 'POST':
                response = self.client.post(url, data[0] if data else {})
            elif method == 'PATCH':
                response = self.client.patch(url, data[0] if data else {})
                
            self.assertIn(response.status_code, [200, 201, 204])


class SearchAPITest(CMMSAPITestCase):
    """اختبارات البحث في API"""
    
    def setUp(self):
        super().setUp()
        
        # إنشاء بيانات إضافية للبحث
        Device.objects.create(
            name='جهاز أشعة',
            serial_number='RAD001',
            category='radiology'
        )
        
        Device.objects.create(
            name='جهاز مختبر',
            serial_number='LAB001',
            category='laboratory'
        )
        
    def test_global_search_api(self):
        """اختبار API البحث العام"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/maintenance/search/?q=أشعة')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('devices', response.data)
        
        # يجب أن يجد الجهاز المطلوب
        devices = response.data['devices']
        self.assertTrue(any('أشعة' in device['name'] for device in devices))
        
    def test_device_search_api(self):
        """اختبار البحث في الأجهزة"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/maintenance/devices/?search=مختبر')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIn('مختبر', response.data['results'][0]['name'])


class PaginationAPITest(CMMSAPITestCase):
    """اختبارات التصفح في API"""
    
    def setUp(self):
        super().setUp()
        
        # إنشاء عدة أجهزة للاختبار
        for i in range(15):
            Device.objects.create(
                name=f'جهاز {i+2}',
                serial_number=f'TEST{i+2:03d}',
                category='medical'
            )
            
    def test_pagination_api(self):
        """اختبار التصفح في API"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/maintenance/devices/?page_size=5')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('count', response.data)
        
        # يجب أن يعرض 5 عناصر فقط
        self.assertEqual(len(response.data['results']), 5)
        
        # يجب أن يكون هناك صفحة تالية
        self.assertIsNotNone(response.data['next'])
        
    def test_pagination_next_page(self):
        """اختبار الصفحة التالية"""
        self.client.force_authenticate(user=self.admin_user)
        
        # الحصول على الصفحة الأولى
        response1 = self.client.get('/api/maintenance/devices/?page_size=5')
        
        # الحصول على الصفحة الثانية
        response2 = self.client.get('/api/maintenance/devices/?page_size=5&page=2')
        
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response2.data['results']), 5)
        
        # يجب أن تكون النتائج مختلفة
        page1_ids = [item['id'] for item in response1.data['results']]
        page2_ids = [item['id'] for item in response2.data['results']]
        self.assertNotEqual(page1_ids, page2_ids)


class ValidationAPITest(CMMSAPITestCase):
    """اختبارات التحقق من صحة البيانات في API"""
    
    def test_device_validation_api(self):
        """اختبار التحقق من بيانات الجهاز"""
        self.client.force_authenticate(user=self.admin_user)
        
        # بيانات غير صحيحة
        data = {
            'name': '',  # اسم فارغ
            'serial_number': 'API001',  # رقم مكرر
            'category': 'invalid_category'  # فئة غير صحيحة
        }
        
        response = self.client.post('/api/maintenance/devices/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)
        self.assertIn('serial_number', response.data)
        
    def test_service_request_validation_api(self):
        """اختبار التحقق من بيانات طلب الخدمة"""
        self.client.force_authenticate(user=self.admin_user)
        
        # بيانات غير صحيحة
        data = {
            'title': '',  # عنوان فارغ
            'device': 999,  # جهاز غير موجود
            'priority': 'invalid_priority'  # أولوية غير صحيحة
        }
        
        response = self.client.post('/api/maintenance/service-requests/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)
        self.assertIn('device', response.data)
        self.assertIn('priority', response.data)
